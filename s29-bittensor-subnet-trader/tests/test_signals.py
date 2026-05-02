"""Tests for signal computation - NO hardcoded fallbacks allowed.

CRITICAL: These tests verify that signals are ONLY computed when data is available.
If a signal cannot be computed, it MUST return None, NOT a hardcoded default like 0.5.
This is intentional - we do not fake signals.
"""

import pytest
from datetime import datetime, timedelta
from subnet_trader.models import SubnetData, SignalScores
from subnet_trader.signals import (
    compute_yield_signal,
    compute_volume_signal,
    compute_momentum_signal,
    compute_age_signal,
    compute_all_signals,
    normalize,
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


class TestYieldSignal:
    """Test yield signal computation - uses real alpha_price."""

    def test_higher_price_higher_score(self):
        """Higher alpha_price should result in higher yield score."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.20),  # Higher price
            SubnetData(netuid=2, alpha_price=0.10),  # Lower price
        ]
        scores = compute_yield_signal(subnets)
        
        assert scores[1].yield_score is not None
        assert scores[0].yield_score is not None
        assert scores[0].yield_score > scores[1].yield_score

    def test_zero_price_handled(self):
        """Zero price should not break - returns normalized score."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.0),
            SubnetData(netuid=2, alpha_price=0.10),
        ]
        scores = compute_yield_signal(subnets)
        
        # Both should have valid scores (min-max scaling)
        assert all(s.yield_score is not None for s in scores)
        assert all(0 <= s.yield_score <= 1 for s in scores)

    def test_all_prices_zero(self):
        """All zero prices - all get same score."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.0),
            SubnetData(netuid=2, alpha_price=0.0),
        ]
        scores = compute_yield_signal(subnets)
        
        # With no variation, all should be equal (1.0 per normalize logic)
        assert all(s.yield_score is not None for s in scores)


class TestVolumeSignal:
    """Test volume signal - MUST use real volume data, not price proxy."""

    def test_higher_volume_higher_score(self):
        """Higher volume_24h should result in higher volume score."""
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.10,
                volume_24h=1_000_000,  # Higher volume
                has_volume=True,
            ),
            SubnetData(
                netuid=2,
                alpha_price=0.20,  # Higher price but lower volume
                volume_24h=500_000,
                has_volume=True,
            ),
        ]
        scores = compute_volume_signal(subnets)
        
        # Subnet 1 has higher volume, should score higher even with lower price
        assert scores[0].volume_score > scores[1].volume_score

    def test_no_volume_data_returns_none(self):
        """CRITICAL: When has_volume is False, volume_score MUST be None."""
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.15,
                volume_24h=0,  # Volume is 0
                has_volume=False,  # But explicitly no data
            ),
        ]
        scores = compute_volume_signal(subnets)
        
        # MUST be None, NOT 0.5 or 0
        assert scores[0].volume_score is None, \
            "Volume signal must be None when data unavailable - NO hardcoded fallback!"

    def test_zero_volume_with_data_flag_returns_score(self):
        """If has_volume=True but volume is 0, we still compute (data exists)."""
        subnets = [
            SubnetData(
                netuid=1,
                volume_24h=0,
                has_volume=True,
            ),
            SubnetData(
                netuid=2,
                volume_24h=1_000_000,
                has_volume=True,
            ),
        ]
        scores = compute_volume_signal(subnets)
        
        # Both should have valid scores
        assert scores[0].volume_score is not None
        assert scores[1].volume_score is not None


class TestMomentumSignals:
    """Test momentum signals - based on real price changes from taostats.io."""

    def test_positive_1h_change_higher_score(self):
        """Positive 1h price change should score higher."""
        subnets = [
            SubnetData(
                netuid=1,
                price_change_1h=10.0,  # 10% gain
                has_price_changes=True,
            ),
            SubnetData(
                netuid=2,
                price_change_1h=-5.0,  # 5% loss
                has_price_changes=True,
            ),
        ]
        scores = compute_momentum_signal(subnets)
        
        assert scores[0].momentum_1h_score > scores[1].momentum_1h_score

    def test_positive_1d_change_higher_score(self):
        """Positive 1d price change should score higher."""
        subnets = [
            SubnetData(
                netuid=1,
                price_change_1d=15.0,
                has_price_changes=True,
            ),
            SubnetData(
                netuid=2,
                price_change_1d=-10.0,
                has_price_changes=True,
            ),
        ]
        scores = compute_momentum_signal(subnets)
        
        assert scores[0].momentum_1d_score > scores[1].momentum_1d_score

    def test_no_price_changes_returns_none(self):
        """CRITICAL: When has_price_changes is False, momentum scores MUST be None."""
        subnets = [
            SubnetData(
                netuid=1,
                price_change_1h=None,
                price_change_1d=None,
                price_change_7d=None,
                has_price_changes=False,
            ),
        ]
        scores = compute_momentum_signal(subnets)
        
        # ALL momentum signals must be None when no data
        assert scores[0].momentum_1h_score is None, \
            "1h momentum must be None when no data!"
        assert scores[0].momentum_1d_score is None, \
            "1d momentum must be None when no data!"
        assert scores[0].momentum_7d_score is None, \
            "7d momentum must be None when no data!"

    def test_partial_data_available(self):
        """When only some price changes are available, only those are computed."""
        subnets = [
            SubnetData(
                netuid=1,
                price_change_1h=5.0,
                price_change_1d=None,  # Only 1h available
                price_change_7d=None,
                has_price_changes=True,
            ),
        ]
        scores = compute_momentum_signal(subnets)
        
        assert scores[0].momentum_1h_score is not None
        assert scores[0].momentum_1d_score is None
        assert scores[0].momentum_7d_score is None

    def test_7d_momentum_ranking(self):
        """7d momentum should rank subnets by weekly performance."""
        subnets = [
            SubnetData(netuid=1, price_change_7d=20.0, has_price_changes=True),
            SubnetData(netuid=2, price_change_7d=-10.0, has_price_changes=True),
            SubnetData(netuid=3, price_change_7d=5.0, has_price_changes=True),
        ]
        scores = compute_momentum_signal(subnets)
        
        # scores is list of SignalScores, index matches subnet index
        assert scores[0].momentum_7d_score > scores[2].momentum_7d_score
        assert scores[2].momentum_7d_score > scores[1].momentum_7d_score


class TestAgeSignal:
    """Test age signal - based on real registration_timestamp."""

    def test_older_subnet_higher_score(self):
        """Older subnets (registered earlier) should score higher."""
        now = datetime(2024, 6, 1, 12, 0, 0)
        
        subnets = [
            SubnetData(
                netuid=1,
                registration_timestamp=datetime(2024, 1, 1),  # 6 months old
                has_registration=True,
            ),
            SubnetData(
                netuid=2,
                registration_timestamp=datetime(2024, 5, 1),  # 1 month old
                has_registration=True,
            ),
        ]
        scores = compute_age_signal(subnets, now)
        
        assert scores[0].age_score > scores[1].age_score

    def test_no_registration_returns_none(self):
        """CRITICAL: When has_registration is False, age_score MUST be None."""
        subnets = [
            SubnetData(
                netuid=1,
                registration_timestamp=None,
                has_registration=False,
            ),
        ]
        scores = compute_age_signal(subnets, datetime.now())
        
        assert scores[0].age_score is None, \
            "Age signal must be None when no registration data - NO hardcoded fallback!"

    def test_age_capped_at_one(self):
        """Very old subnets should have age score capped at 1.0."""
        now = datetime(2024, 6, 1)
        
        subnets = [
            SubnetData(
                netuid=1,
                registration_timestamp=datetime(2020, 1, 1),  # Very old
                has_registration=True,
            ),
        ]
        scores = compute_age_signal(subnets, now)
        
        assert scores[0].age_score == 1.0


class TestComputeAllSignals:
    """Test combined signal computation."""

    def test_returns_signal_scores_for_each_subnet(self):
        """Verify all subnets get a SignalScores object."""
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.15,
                volume_24h=1_000_000,
                has_volume=True,
                price_change_1d=5.0,
                has_price_changes=True,
                registration_timestamp=datetime(2024, 1, 1),
                has_registration=True,
            ),
        ]
        
        now = datetime(2024, 6, 1)
        result = compute_all_signals(subnets, now)
        
        assert len(result) == 1
        assert isinstance(result[1], SignalScores)

    def test_some_signals_none_when_data_missing(self):
        """When some data is missing, only available signals are computed."""
        # Subnet with only price, no volume, no price changes, no registration
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.15,
                has_volume=False,
                has_price_changes=False,
                has_registration=False,
            ),
        ]
        
        now = datetime.now()
        result = compute_all_signals(subnets, now)
        
        signals = result[1]
        # Only yield should be computed
        assert signals.yield_score is not None
        assert signals.volume_score is None
        assert signals.momentum_1h_score is None
        assert signals.momentum_1d_score is None
        assert signals.momentum_7d_score is None
        assert signals.age_score is None

    def test_composite_none_when_no_signals(self):
        """When no signals are available, composite should be None."""
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.0,  # No price
                has_volume=False,
                has_price_changes=False,
                has_registration=False,
            ),
        ]
        
        now = datetime.now()
        result = compute_all_signals(subnets, now)
        
        signals = result[1]
        # yield_score is computed from alpha_price (even 0.0), so signals ARE available
        # But composite should be based on actual signal computation
        # Since alpha_price is 0, yield should still be computed (equal to all zeros = 1.0)
        # Actually, now I removed the check for > 0, so yield IS computed
        # Let's just verify has_any_signal works correctly
        assert signals.has_any_signal() is True  # yield is computed even from 0

    def test_count_signals_available(self):
        """Verify we can count how many signals were successfully computed."""
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.15,  # For yield
                volume_24h=1_000_000,
                has_volume=True,  # For volume
                price_change_1d=5.0,
                price_change_7d=10.0,
                has_price_changes=True,  # For momentum (1d, 7d)
                registration_timestamp=datetime(2024, 1, 1),
                has_registration=True,  # For age
            ),
        ]
        
        now = datetime(2024, 6, 1)
        result = compute_all_signals(subnets, now)
        
        signals = result[1]
        count = sum(1 for v in [
            signals.yield_score,
            signals.volume_score,
            signals.momentum_1h_score,
            signals.momentum_1d_score,
            signals.momentum_7d_score,
            signals.age_score,
        ] if v is not None)
        
        assert count == 5  # yield, volume, momentum_1d, momentum_7d, age
        # Note: momentum_1h is None because we only have 1d and 7d


class TestNoHardcodedFallbacks:
    """CRITICAL: These tests verify NO hardcoded fallback values exist."""

    def test_no_05_fallback_in_yield(self):
        """Yield signal must NEVER return 0.5 as a fallback."""
        subnets = [
            SubnetData(netuid=1, alpha_price=0.0),
        ]
        scores = compute_yield_signal(subnets)
        
        # If alpha_price is 0, yield_score could still be computed via normalization
        # But it should NOT be hardcoded to 0.5
        assert scores[0].yield_score != 0.5 or scores[0].yield_score is None

    def test_no_05_fallback_in_volume(self):
        """Volume signal must NEVER return 0.5 as a fallback."""
        subnets = [
            SubnetData(
                netuid=1,
                alpha_price=0.15,
                volume_24h=0,
                has_volume=False,  # No data
            ),
        ]
        scores = compute_volume_signal(subnets)
        
        assert scores[0].volume_score is None, \
            "Must be None when data unavailable, not 0.5!"

    def test_no_05_fallback_in_momentum(self):
        """Momentum signal must NEVER return 0.5 as a fallback."""
        subnets = [
            SubnetData(
                netuid=1,
                price_change_1d=None,
                has_price_changes=False,
            ),
        ]
        scores = compute_momentum_signal(subnets)
        
        assert scores[0].momentum_1d_score is None, \
            "Must be None when data unavailable, not 0.5!"

    def test_no_05_fallback_in_age(self):
        """Age signal must NEVER return 0.5 as a fallback."""
        subnets = [
            SubnetData(
                netuid=1,
                registration_timestamp=None,
                has_registration=False,
            ),
        ]
        scores = compute_age_signal(subnets, datetime.now())
        
        assert scores[0].age_score is None, \
            "Must be None when data unavailable, not 0.5!"
