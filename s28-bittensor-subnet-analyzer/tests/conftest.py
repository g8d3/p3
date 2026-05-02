"""Shared test fixtures."""

import pytest
from subnet_trader.models import SubnetData


@pytest.fixture
def sample_subnets():
    """Sample subnet data for testing."""
    return [
        SubnetData(
            netuid=1,
            name="Apex",
            symbol="α",
            tao_staked=500_000e9,
            alpha_price=0.15,
            tao_reserve=75_000e9,
            alpha_reserve=500_000e9,
            alpha_staked=1_000_000e9,
            emission_share=0.12,
            tao_emission_per_block=0.12,
            registration_block=100_000,
            market_cap=150_000e9,
            volume_24h=10_000e9,
            price_change_1d=-2.5,
            price_change_7d=-8.0,
        ),
        SubnetData(
            netuid=19,
            name="τ",
            symbol="t",
            tao_staked=800_000e9,
            alpha_price=0.069,
            tao_reserve=22_500e9,
            alpha_reserve=324_000e9,
            alpha_staked=532_000e9,
            emission_share=0.08,
            tao_emission_per_block=0.08,
            registration_block=200_000,
            market_cap=60_000e9,
            volume_24h=5_600e9,
            price_change_1d=-5.0,
            price_change_7d=-29.0,
        ),
        SubnetData(
            netuid=42,
            name="NewSubnet",
            symbol="NS",
            tao_staked=50_000e9,
            alpha_price=0.50,
            tao_reserve=25_000e9,
            alpha_reserve=50_000e9,
            alpha_staked=100_000e9,
            emission_share=0.05,
            tao_emission_per_block=0.05,
            registration_block=900_000,  # Very new
            market_cap=25_000e9,
            volume_24h=8_000e9,
            price_change_1d=15.0,
            price_change_7d=40.0,
        ),
        SubnetData(
            netuid=8,
            name="Stable",
            symbol="S",
            tao_staked=1_000_000e9,
            alpha_price=0.10,
            tao_reserve=100_000e9,
            alpha_reserve=1_000_000e9,
            alpha_staked=2_000_000e9,
            emission_share=0.15,
            tao_emission_per_block=0.15,
            registration_block=300_000,
            market_cap=100_000e9,
            volume_24h=3_000e9,
            price_change_1d=0.5,
            price_change_7d=2.0,
        ),
    ]


@pytest.fixture
def mock_rpc_subnets_response():
    """Mock RPC response for subnet list query."""
    return {
        "netuids": [1, 8, 19, 42],
        "names": ["Apex", "Stable", "τ", "NewSubnet"],
    }


@pytest.fixture
def mock_rpc_pool_response():
    """Mock RPC response for subnet pool reserves."""
    return {
        1: {"tao_reserve": 75_000e9, "alpha_reserve": 500_000e9},
        8: {"tao_reserve": 100_000e9, "alpha_reserve": 1_000_000e9},
        19: {"tao_reserve": 22_500e9, "alpha_reserve": 324_000e9},
        42: {"tao_reserve": 25_000e9, "alpha_reserve": 50_000e9},
    }
