"""Tests for signal computation - normalization and ranking."""

import pytest
from subnet_trader.models import SubnetData, SignalScores
from subnet_trader.signals import (
    compute_yield_signal,
    compute_momentum_signal,
    compute_price_trend_signal,
    compute_volume_signal,
    compute_age_signal,
    normalize,
    compute_all_signals,
)


class TestNormalize:
    """Test the normalize function."""

    def test_normalize_basic(self):
        values = [10.0, 20.0, 30.0]
        result = normalize(values)
        assert result == [0.0, 0.5, 1.0]

    def test_normalize_single_value(self):
        result = normalize([42.0])
        assert result == [1.0]

    def test_normalize_all_equal(self):
        result = normalize([5.0, 5.0, 5.0])
        assert all(v == 1.0 for v in result)

    def test_normalize_empty(self):
        result = normalize([])
        assert result == []

    def test_normalize_negative_values(self):
        values = [-10.0, 0.0, 10.0]
        result = normalize(values)
        assert result == [0.0, 0.5, 1.0]

    def test_normalize_preserves_order(self):
        values = [5.0, 1.0, 3.0, 2.0, 4.0]
        result = normalize(values)
        # Original order: 5, 1, 3, 2, 4
        # Normalized:     1.0, 0.0, 0.5, 0.25, 0.75
        assert result[0] > result[2] > result[3] > result[1]
        assert result[4] > result[2]


class TestYieldSignal:
    """Test yield signal computation."""

    def test_high_yield_subnet(self, sample_subnets):
        """Subnet with high emission/stake ratio should score highest."""
        scores = compute_yield_signal(sample_subnets)
        assert len(scores) == len(sample_subnets)
        assert all(0 <= s <= 1 for s in scores)

    def test_yield_proportional_to_emission(self):
        """Higher alpha price = higher yield score (using price as proxy)."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.20),  # Higher price
            SubnetData(netuid=2, alpha_price=0.10),  # Lower price
        ]
        scores = compute_yield_signal(subnets)
        assert scores[0] > scores[1]  # Higher price = higher score

    def test_zero_stake_handled(self):
        """Zero stake should not cause division by zero."""
        subnets = [
            SubnetData(netuid=1, tao_staked=0, tao_emission_per_block=0.1),
            SubnetData(netuid=2, tao_staked=100_000e9, tao_emission_per_block=0.1),
        ]
        scores = compute_yield_signal(subnets)
        assert len(scores) == 2
        assert all(0 <= s <= 1 for s in scores)


class TestMomentumSignal:
    """Test momentum signal computation."""

    def test_positive_momentum(self):
        """Subnet gaining emission share should score higher."""
        subnets = [
            SubnetData(netuid=1, emission_share=0.15),  # Current
            SubnetData(netuid=2, emission_share=0.05),
        ]
        # Simulate: subnet 1 was at 0.10 (gaining), subnet 2 was at 0.08 (losing)
        history = {1: 0.10, 2: 0.08}
        scores = compute_momentum_signal(subnets, history)
        assert scores[0] > scores[1]  # Gaining > losing

    def test_no_history_returns_neutral(self):
        """Without history, momentum should be neutral (0.5)."""
        subnets = [SubnetData(netuid=1, emission_share=0.10)]
        scores = compute_momentum_signal(subnets, {})
        assert scores[0] == 0.5

    def test_momentum_range(self, sample_subnets):
        """All momentum scores should be in [0, 1]."""
        history = {s.netuid: s.emission_share * 0.9 for s in sample_subnets}
        scores = compute_momentum_signal(sample_subnets, history)
        assert all(0 <= s <= 1 for s in scores)


class TestPriceTrendSignal:
    """Test price trend signal computation."""

    def test_undervalued_scores_high(self):
        """Subnet with price below MA should score higher (buy signal)."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.05),  # Current price
            SubnetData(netuid=2, alpha_price=0.15),
        ]
        # MA: subnet 1 was at 0.10 (now 0.05 = 50% of MA = undervalued)
        #     subnet 2 was at 0.10 (now 0.15 = 150% of MA = overvalued)
        ma_prices = {1: 0.10, 2: 0.10}
        scores = compute_price_trend_signal(subnets, ma_prices)
        assert scores[0] > scores[1]  # Undervalued > overvalued

    def test_no_ma_returns_neutral(self):
        """Without MA data, should return neutral."""
        subnets = [SubnetData(netuid=1, alpha_price=0.10)]
        scores = compute_price_trend_signal(subnets, {})
        assert scores[0] == 0.5

    def test_price_trend_range(self, sample_subnets):
        """All scores should be in [0, 1]."""
        ma = {s.netuid: s.alpha_price * 1.1 for s in sample_subnets}
        scores = compute_price_trend_signal(sample_subnets, ma)
        assert all(0 <= s <= 1 for s in scores)


class TestVolumeSignal:
    """Test volume signal computation."""

    def test_higher_volume_scores_higher(self):
        """Subnet with higher alpha price should score higher (price as volume proxy)."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.20),  # Higher price
            SubnetData(netuid=2, alpha_price=0.10),  # Lower price
        ]
        scores = compute_volume_signal(subnets)
        assert scores[0] > scores[1]

    def test_volume_range(self, sample_subnets):
        scores = compute_volume_signal(sample_subnets)
        assert all(0 <= s <= 1 for s in scores)


class TestAgeSignal:
    """Test age signal computation."""

    def test_older_subnet_scores_higher(self):
        """Older subnets should score higher (more stable)."""
        # Use blocks within the maturity window (50400 blocks = ~7 days)
        subnets = [
            SubnetData(netuid=1, registration_block=1_000_000 - 10_000),  # 10k blocks old
            SubnetData(netuid=2, registration_block=1_000_000 - 50_000),  # 50k blocks old
        ]
        current_block = 1_000_000
        scores = compute_age_signal(subnets, current_block)
        # subnet 2 (50k blocks old) is older → higher age score than subnet 1 (10k blocks old)
        assert scores[1] > scores[0]  # Older = higher score

    def test_age_capped_at_one(self):
        """Age score should cap at 1.0 for very old subnets."""
        # Use a registration block that results in >1.0 (capped)
        subnets = [SubnetData(netuid=1, registration_block=1)]
        current_block = 1_000_000
        scores = compute_age_signal(subnets, current_block)
        assert scores[0] == 1.0  # Should be capped

    def test_age_range(self, sample_subnets):
        current_block = 1_000_000
        scores = compute_age_signal(sample_subnets, current_block)
        assert all(0 <= s <= 1 for s in scores)


class TestComputeAllSignals:
    """Test the combined signal computation."""

    def test_returns_signal_scores_for_each_subnet(self, sample_subnets):
        history = {s.netuid: s.emission_share * 0.9 for s in sample_subnets}
        ma = {s.netuid: s.alpha_price * 1.1 for s in sample_subnets}
        current_block = 1_000_000

        result = compute_all_signals(sample_subnets, history, ma, current_block)

        assert len(result) == len(sample_subnets)
        for netuid, signals in result.items():
            assert isinstance(signals, SignalScores)
            assert 0 <= signals.yield_score <= 1
            assert 0 <= signals.momentum_score <= 1
            assert 0 <= signals.price_trend_score <= 1
            assert 0 <= signals.volume_score <= 1
            assert 0 <= signals.age_score <= 1

    def test_all_subnets_present(self, sample_subnets):
        history = {s.netuid: s.emission_share for s in sample_subnets}
        ma = {s.netuid: s.alpha_price for s in sample_subnets}

        result = compute_all_signals(sample_subnets, history, ma, 1_000_000)

        for subnet in sample_subnets:
            assert subnet.netuid in result
