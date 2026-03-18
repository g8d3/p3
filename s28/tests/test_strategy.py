"""Tests for strategy logic - composite scoring and rebalance orders."""

import pytest
from subnet_trader.models import SubnetData, SignalScores, CompositeScore, RebalanceOrder
from subnet_trader.strategy import (
    compute_composite_score,
    rank_subnets,
    generate_rebalance_orders,
    SubnetAnalyzer,
)


class TestCompositeScore:
    """Test composite score computation."""

    def test_composite_is_weighted_sum(self):
        """Composite should equal weighted sum of signals."""
        signals = SignalScores(
            yield_score=1.0,
            momentum_score=0.8,
            price_trend_score=0.6,
            volume_score=0.4,
            age_score=0.2,
        )
        weights = {
            "yield": 0.30,
            "momentum": 0.25,
            "price_trend": 0.20,
            "volume": 0.15,
            "age": 0.10,
        }
        expected = (
            1.0 * 0.30
            + 0.8 * 0.25
            + 0.6 * 0.20
            + 0.4 * 0.15
            + 0.2 * 0.10
        )
        result = compute_composite_score(signals, weights)
        assert abs(result - expected) < 1e-10

    def test_all_max_signals(self):
        """All signals at 1.0 should give composite = 1.0."""
        signals = SignalScores(1.0, 1.0, 1.0, 1.0, 1.0)
        weights = {"yield": 0.30, "momentum": 0.25, "price_trend": 0.20, "volume": 0.15, "age": 0.10}
        result = compute_composite_score(signals, weights)
        assert abs(result - 1.0) < 1e-10

    def test_all_zero_signals(self):
        """All signals at 0.0 should give composite = 0.0."""
        signals = SignalScores(0.0, 0.0, 0.0, 0.0, 0.0)
        weights = {"yield": 0.30, "momentum": 0.25, "price_trend": 0.20, "volume": 0.15, "age": 0.10}
        result = compute_composite_score(signals, weights)
        assert abs(result - 0.0) < 1e-10

    def test_weights_sum_to_one(self):
        """Weights should sum to 1.0 for meaningful composite."""
        weights = {"yield": 0.30, "momentum": 0.25, "price_trend": 0.20, "volume": 0.15, "age": 0.10}
        assert abs(sum(weights.values()) - 1.0) < 1e-10


class TestRankSubnets:
    """Test subnet ranking."""

    def test_ranking_order(self, sample_subnets):
        """Subnets should be ranked by composite score descending."""
        signals_map = {
            1: SignalScores(0.9, 0.8, 0.7, 0.6, 1.0),   # composite ~0.80
            19: SignalScores(0.5, 0.5, 0.3, 0.9, 0.8),   # composite ~0.53
            42: SignalScores(0.7, 0.6, 0.8, 0.7, 0.1),   # composite ~0.62
            8: SignalScores(0.8, 0.9, 0.6, 0.3, 0.9),    # composite ~0.72
        }
        weights = {"yield": 0.30, "momentum": 0.25, "price_trend": 0.20, "volume": 0.15, "age": 0.10}

        result = rank_subnets(sample_subnets, signals_map, weights)

        assert len(result) == 4
        # Should be sorted by composite descending
        for i in range(len(result) - 1):
            assert result[i].composite >= result[i + 1].composite
        # Ranks should be 1, 2, 3, 4
        assert [r.rank for r in result] == [1, 2, 3, 4]

    def test_top_n_limits_results(self, sample_subnets):
        """top_n should limit the number of results."""
        signals_map = {s.netuid: SignalScores(0.5, 0.5, 0.5, 0.5, 0.5) for s in sample_subnets}
        weights = {"yield": 0.30, "momentum": 0.25, "price_trend": 0.20, "volume": 0.15, "age": 0.10}

        result = rank_subnets(sample_subnets, signals_map, weights, top_n=2)

        assert len(result) == 2
        assert result[0].rank == 1
        assert result[1].rank == 2

    def test_result_contains_all_fields(self, sample_subnets):
        """Each result should have netuid, name, composite, rank, signals, raw_data."""
        signals_map = {s.netuid: SignalScores(0.5, 0.5, 0.5, 0.5, 0.5) for s in sample_subnets}
        weights = {"yield": 0.30, "momentum": 0.25, "price_trend": 0.20, "volume": 0.15, "age": 0.10}

        result = rank_subnets(sample_subnets, signals_map, weights, top_n=1)

        score = result[0]
        assert isinstance(score, CompositeScore)
        assert score.netuid in [s.netuid for s in sample_subnets]
        assert score.name != ""
        assert 0 <= score.composite <= 1
        assert score.rank == 1
        assert isinstance(score.signals, SignalScores)
        assert isinstance(score.raw_data, SubnetData)


class TestGenerateRebalanceOrders:
    """Test rebalance order generation."""

    def test_stake_into_top_subnets(self):
        """Should generate stake orders for top-ranked subnets."""
        ranked = [
            CompositeScore(1, "Apex", 0.9, 1, SignalScores(), SubnetData(netuid=1)),
            CompositeScore(8, "Stable", 0.7, 2, SignalScores(), SubnetData(netuid=8)),
        ]
        current_holdings = {}  # No current holdings
        total_tao = 200.0

        orders = generate_rebalance_orders(ranked, current_holdings, total_tao)

        stake_orders = [o for o in orders if o.action == "stake"]
        assert len(stake_orders) == 2
        assert sum(o.amount_tao for o in stake_orders) == pytest.approx(total_tao, rel=0.01)

    def test_unstake_from_exited_subnets(self):
        """Should generate unstake orders for subnets no longer in top."""
        ranked = [
            CompositeScore(1, "Apex", 0.9, 1, SignalScores(), SubnetData(netuid=1)),
        ]
        current_holdings = {1: 50.0, 19: 100.0}  # Holding subnet 19 which is not in top
        total_tao = 150.0

        orders = generate_rebalance_orders(ranked, current_holdings, total_tao)

        unstake_orders = [o for o in orders if o.action == "unstake"]
        assert any(o.netuid == 19 for o in unstake_orders)

    def test_proportional_allocation(self):
        """Stake should be proportional to composite score."""
        ranked = [
            CompositeScore(1, "A", 0.8, 1, SignalScores(), SubnetData(netuid=1)),
            CompositeScore(8, "B", 0.2, 2, SignalScores(), SubnetData(netuid=8)),
        ]
        current_holdings = {}
        total_tao = 100.0

        orders = generate_rebalance_orders(ranked, current_holdings, total_tao)

        stake_orders = {o.netuid: o for o in orders if o.action == "stake"}
        # 0.8 / (0.8 + 0.2) = 0.8 → 80 TAO
        # 0.2 / (0.8 + 0.2) = 0.2 → 20 TAO
        assert stake_orders[1].amount_tao == pytest.approx(80.0, rel=0.01)
        assert stake_orders[8].amount_tao == pytest.approx(20.0, rel=0.01)

    def test_no_orders_when_already_optimal(self):
        """No orders needed if current holdings match target."""
        ranked = [
            CompositeScore(1, "A", 0.9, 1, SignalScores(), SubnetData(netuid=1)),
        ]
        current_holdings = {1: 100.0}
        total_tao = 100.0

        orders = generate_rebalance_orders(ranked, current_holdings, total_tao)

        # Should have no stake/unstake orders (already holding the right thing)
        assert len(orders) == 0

    def test_order_to_dict(self):
        """Orders should serialize to dict correctly."""
        order = RebalanceOrder(action="stake", netuid=1, amount_tao=50.0)
        d = order.to_dict()
        assert d == {"action": "stake", "netuid": 1, "amount_tao": 50.0}


class TestSubnetAnalyzer:
    """Test the high-level analyzer interface."""

    def test_analyzer_produces_valid_output(self, sample_subnets):
        """Analyzer should produce AnalysisResult with subnets and orders."""
        # This will be a mock-based test once we have the full implementation
        # For now, test the interface exists
        from subnet_trader.strategy import SubnetAnalyzer
        assert hasattr(SubnetAnalyzer, "rank_subnets")
        assert hasattr(SubnetAnalyzer, "analyze")
