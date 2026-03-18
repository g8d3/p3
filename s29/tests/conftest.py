"""Shared pytest fixtures for subnet trader tests."""

import pytest
from datetime import datetime
from subnet_trader.models import SubnetData, SignalScores


@pytest.fixture
def sample_subnets():
    """Sample subnets with varied data for testing."""
    return [
        SubnetData(
            netuid=1,
            name="Apex",
            alpha_price=0.15,
            volume_24h=1_500_000,
            has_volume=True,
            price_change_1h=2.5,
            price_change_1d=-5.0,
            price_change_7d=15.3,
            has_price_changes=True,
            registration_timestamp=datetime(2024, 1, 15, 10, 30, 0),
            has_registration=True,
        ),
        SubnetData(
            netuid=8,
            name="Corcel",
            alpha_price=0.10,
            volume_24h=800_000,
            has_volume=True,
            price_change_1h=-1.0,
            price_change_1d=3.0,
            price_change_7d=-8.5,
            has_price_changes=True,
            registration_timestamp=datetime(2024, 3, 20, 14, 45, 0),
            has_registration=True,
        ),
        SubnetData(
            netuid=19,
            name="Tau",
            alpha_price=0.069,
            volume_24h=500_000,
            has_volume=True,
            price_change_1h=0.5,
            price_change_1d=1.2,
            price_change_7d=-3.0,
            has_price_changes=True,
            registration_timestamp=datetime(2023, 11, 1, 8, 0, 0),
            has_registration=True,
        ),
    ]


@pytest.fixture
def subnets_partial_data():
    """Subnets with only some data available."""
    return [
        SubnetData(
            netuid=1,
            name="Apex",
            alpha_price=0.15,
            has_volume=False,  # No volume
            has_price_changes=False,  # No price changes
            has_registration=False,  # No registration
        ),
        SubnetData(
            netuid=2,
            name="NewSubnet",
            alpha_price=0.05,
            has_volume=False,
            has_price_changes=False,
            has_registration=False,
        ),
    ]


@pytest.fixture
def current_time():
    """Current timestamp for testing."""
    return datetime(2024, 6, 1, 12, 0, 0)
