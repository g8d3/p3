"""Tests for chain data fetching and RPC response parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from subnet_trader.chain import SubnetChainClient, parse_subnet_data
from subnet_trader.models import SubnetData


class TestParseSubnetData:
    """Test parsing raw RPC responses into SubnetData."""

    def test_parse_basic_fields(self):
        raw = {
            "netuid": 19,
            "name": "τ",
            "symbol": "t",
            "tao_staked": 22509002321719,
            "alpha_price": 0.0694,
            "tao_reserve": 22509002321719,
            "alpha_reserve": 324305642595491,
            "alpha_staked": 532116231800096,
            "emission_share": 0.08,
            "tao_emission_per_block": 0.08,
            "registration_block": 200000,
            "market_cap": 59441463321024,
            "volume_24h": 5625165881462,
            "price_change_1d": -5.03,
            "price_change_7d": -29.21,
        }
        result = parse_subnet_data(raw)

        assert isinstance(result, SubnetData)
        assert result.netuid == 19
        assert result.name == "τ"
        assert result.symbol == "t"
        assert result.alpha_price == pytest.approx(0.0694, rel=0.01)
        assert result.emission_share == 0.08

    def test_parse_missing_fields_use_defaults(self):
        """Missing fields should use default values."""
        raw = {"netuid": 42}
        result = parse_subnet_data(raw)

        assert result.netuid == 42
        assert result.name == ""
        assert result.tao_staked == 0.0
        assert result.alpha_price == 0.0

    def test_parse_converts_rao_to_tao(self):
        """Values in rao (1e-9 TAO) should be converted to TAO."""
        raw = {
            "netuid": 1,
            "tao_staked": 500_000.0,  # Already in TAO
            "alpha_price": 0.15,
        }
        result = parse_subnet_data(raw)

        assert result.tao_staked == pytest.approx(500_000.0, rel=0.01)


class TestSubnetChainClient:
    """Test the chain client."""

    def test_client_initialization(self):
        client = SubnetChainClient(network="finney")
        assert client.network == "finney"
        client.close()

    def test_get_all_subnets_returns_list(self):
        """get_all_subnets should return a list of SubnetData."""
        client = SubnetChainClient(mock=True)
        result = client.get_all_subnets()

        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(s, SubnetData) for s in result)
        client.close()

    def test_get_subnet_by_id(self):
        """get_subnet should return data for a specific subnet."""
        client = SubnetChainClient(mock=True)
        result = client.get_subnet(1)

        assert result is not None
        assert result.netuid == 1
        client.close()

    def test_get_nonexistent_subnet_returns_none(self):
        client = SubnetChainClient(mock=True)
        result = client.get_subnet(9999)

        assert result is None
        client.close()


class TestEmissionCalculation:
    """Test emission share calculation from EMA prices."""

    def test_emission_share_proportional_to_ema_price(self):
        """Subnet with higher EMA price should get higher emission share."""
        from subnet_trader.chain import calculate_emission_shares

        ema_prices = {1: 0.5, 8: 0.3, 19: 0.2}
        shares = calculate_emission_shares(ema_prices)

        assert shares[1] == pytest.approx(0.5, rel=0.01)
        assert shares[8] == pytest.approx(0.3, rel=0.01)
        assert shares[19] == pytest.approx(0.2, rel=0.01)
        assert sum(shares.values()) == pytest.approx(1.0, rel=0.01)

    def test_emission_share_equal_prices(self):
        """Equal EMA prices should give equal shares."""
        from subnet_trader.chain import calculate_emission_shares

        ema_prices = {1: 0.1, 2: 0.1, 3: 0.1}
        shares = calculate_emission_shares(ema_prices)

        for share in shares.values():
            assert share == pytest.approx(1 / 3, rel=0.01)

    def test_emission_share_empty(self):
        from subnet_trader.chain import calculate_emission_shares
        assert calculate_emission_shares({}) == {}
