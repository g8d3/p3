"""Tests for strategy - ranking and rebalancing."""

import pytest
from datetime import datetime
from subnet_trader.models import (
    SubnetData,
    SignalScores,
    CompositeScore,
    RebalanceOrder,
)
from subnet_trader.strategy import rank_subnets, generate_orders, compute_composite_score


class TestRanking:
    """Test subnet ranking based on composite scores."""

    def test_ranked_by_composite_score(self):
        """Subnets should be ranked by composite score (highest first)."""
        subnets = [
            SubnetData(netuid=1, name="A", alpha_price=0.10),
            SubnetData(netuid=2, name="B", alpha_price=0.20),
            SubnetData(netuid=3, name="C", alpha_price=0.15),
        ]
        
        signals = {
            1: SignalScores(yield_score=0.3),  # Lowest
            2: SignalScores(yield_score=1.0),  # Highest
            3: SignalScores(yield_score=0.6),  # Middle
        }
        
        ranked = rank_subnets(subnets, signals)
        
        assert ranked[0].netuid == 2  # Highest score = rank 1
        assert ranked[1].netuid == 3  # Middle
        assert ranked[2].netuid == 1  # Lowest

    def test_signals_available_counted(self):
        """Verify signals_available is correctly counted."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.15),
        ]
        
        signals = {
            1: SignalScores(
                yield_score=1.0,
                volume_score=0.8,
                momentum_1h_score=None,
                momentum_1d_score=0.6,
                momentum_7d_score=None,
                age_score=0.9,
            ),
        }
        
        ranked = rank_subnets(subnets, signals)
        
        assert ranked[0].signals_available == 4  # yield, volume, momentum_1d, age

    def test_subnets_with_no_signals_get_none_composite(self):
        """Subnets with no computable signals should have composite=None."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.0),  # No price data
        ]
        
        signals = {
            1: SignalScores(
                yield_score=None,
                volume_score=None,
                momentum_1h_score=None,
                momentum_1d_score=None,
                momentum_7d_score=None,
                age_score=None,
            ),
        }
        
        ranked = rank_subnets(subnets, signals)
        
        assert ranked[0].composite is None

    def test_partial_signals_compute_composite(self):
        """Subnets with partial signals should still get a composite score."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.15),
        ]
        
        signals = {
            1: SignalScores(
                yield_score=1.0,  # Only yield available
                volume_score=None,
                momentum_1h_score=None,
                momentum_1d_score=None,
                momentum_7d_score=None,
                age_score=None,
            ),
        }
        
        ranked = rank_subnets(subnets, signals)
        
        assert ranked[0].composite is not None
        assert ranked[0].composite == 1.0  # Only yield, so composite = yield


class TestCompositeScoreCalculation:
    """Test the composite score calculation logic."""

    def test_weighted_average_of_available_signals(self):
        """Composite should be weighted average of available signals."""
        signals = SignalScores(
            yield_score=1.0,      # 30% weight
            volume_score=0.5,     # 20% weight (if available)
            momentum_1h_score=None,
            momentum_1d_score=0.8,  # 25% weight
            momentum_7d_score=None,
            age_score=0.6,       # 10% weight
        )
        
        # Only 3 signals available: yield(0.3), volume(0.2), age(0.1) = 0.6 weight
        # Remaining weight redistributed
        composite = compute_composite_score(signals)
        
        # With yield=1.0, volume=0.5, age=0.6
        # Total weight for available signals = 0.3 + 0.2 + 0.1 = 0.6
        # If weights are normalized: 1.0*0.5 + 0.5*0.33 + 0.6*0.17 ≈ 0.82
        assert composite is not None
        assert 0 <= composite <= 1

    def test_all_signals_equal_weights_normalized(self):
        """When all signals present, weights should sum to 1.0."""
        signals = SignalScores(
            yield_score=0.5,
            volume_score=0.5,
            momentum_1h_score=0.5,
            momentum_1d_score=0.5,
            momentum_7d_score=0.5,
            age_score=0.5,
        )
        
        composite = compute_composite_score(signals)
        
        # All 0.5, weighted sum = 0.5 regardless of weights
        assert composite == 0.5

    def test_no_signals_returns_none(self):
        """When no signals are available, composite should be None."""
        signals = SignalScores(
            yield_score=None,
            volume_score=None,
            momentum_1h_score=None,
            momentum_1d_score=None,
            momentum_7d_score=None,
            age_score=None,
        )
        
        composite = compute_composite_score(signals)
        
        assert composite is None


class TestRebalanceOrders:
    """Test rebalance order generation."""

    def test_generate_stake_orders_for_top_ranked(self):
        """Top ranked subnets should receive stake orders."""
        ranked = [
            CompositeScore(
                netuid=1, name="A", composite=0.9, rank=1,
                signals=SignalScores(yield_score=1.0),
                raw_data=SubnetData(netuid=1),
                signals_available=1,
            ),
            CompositeScore(
                netuid=2, name="B", composite=0.7, rank=2,
                signals=SignalScores(yield_score=0.7),
                raw_data=SubnetData(netuid=2),
                signals_available=1,
            ),
            CompositeScore(
                netuid=3, name="C", composite=0.5, rank=3,
                signals=SignalScores(yield_score=0.5),
                raw_data=SubnetData(netuid=3),
                signals_available=1,
            ),
        ]
        
        orders = generate_orders(ranked, total_stake_tao=1000.0, top_n=2)
        
        # Should stake in top 2
        assert len(orders) == 2
        assert all(o.action == "stake" for o in orders)
        assert {o.netuid for o in orders} == {1, 2}

    def test_generate_unstake_orders_for_bottom_ranked(self):
        """Low ranked subnets should receive unstake orders."""
        ranked = [
            CompositeScore(
                netuid=1, name="A", composite=0.9, rank=1,
                signals=SignalScores(yield_score=1.0),
                raw_data=SubnetData(netuid=1),
                signals_available=1,
            ),
            CompositeScore(
                netuid=2, name="B", composite=0.7, rank=2,
                signals=SignalScores(yield_score=0.7),
                raw_data=SubnetData(netuid=2),
                signals_available=1,
            ),
            CompositeScore(
                netuid=3, name="C", composite=0.1, rank=3,  # Low score
                signals=SignalScores(yield_score=0.1),
                raw_data=SubnetData(netuid=3),
                signals_available=1,
            ),
        ]
        
        orders = generate_orders(ranked, total_stake_tao=1000.0, top_n=0, bottom_n=1)
        
        # Should unstake bottom 1
        assert len(orders) == 1
        assert orders[0].action == "unstake"
        assert orders[0].netuid == 3

    def test_amounts_proportional_to_scores(self):
        """Stake amounts should be proportional to composite scores."""
        ranked = [
            CompositeScore(
                netuid=1, name="A", composite=0.9, rank=1,
                signals=SignalScores(yield_score=1.0),
                raw_data=SubnetData(netuid=1),
                signals_available=1,
            ),
            CompositeScore(
                netuid=2, name="B", composite=0.3, rank=2,
                signals=SignalScores(yield_score=0.3),
                raw_data=SubnetData(netuid=2),
                signals_available=1,
            ),
        ]
        
        orders = generate_orders(ranked, total_stake_tao=100.0, top_n=2)
        
        # A gets more than B (higher score)
        order_a = next(o for o in orders if o.netuid == 1)
        order_b = next(o for o in orders if o.netuid == 2)
        
        assert order_a.amount_tao > order_b.amount_tao

    def test_skip_subnets_with_no_composite(self):
        """Subnets with composite=None should be skipped in ranking."""
        ranked = [
            CompositeScore(
                netuid=1, name="A", composite=0.8, rank=1,
                signals=SignalScores(yield_score=1.0),
                raw_data=SubnetData(netuid=1),
                signals_available=1,
            ),
            CompositeScore(
                netuid=2, name="B", composite=None, rank=2,  # No signals
                signals=SignalScores(),
                raw_data=SubnetData(netuid=2),
                signals_available=0,
            ),
        ]
        
        orders = generate_orders(ranked, total_stake_tao=100.0, top_n=1)
        
        # Should only stake in A, not B (which has no composite score)
        assert len(orders) == 1
        assert orders[0].netuid == 1

    def test_order_has_reason(self):
        """Each order should include a reason explaining the action."""
        ranked = [
            CompositeScore(
                netuid=1, name="A", composite=0.9, rank=1,
                signals=SignalScores(yield_score=1.0),
                raw_data=SubnetData(netuid=1),
                signals_available=1,
            ),
        ]
        
        orders = generate_orders(ranked, total_stake_tao=100.0, top_n=1)
        
        assert len(orders) == 1
        assert orders[0].reason != ""
        assert "rank" in orders[0].reason.lower() or "score" in orders[0].reason.lower()
