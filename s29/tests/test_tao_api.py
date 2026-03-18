"""Tests for taostats.io API client."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from subnet_trader.models import SubnetData


class TestTaostatsClient:
    """Tests for TaostatsClient - verifies real data fetching."""

    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response from taostats.io."""
        return {
            "data": [
                {
                    "netuid": 1,
                    "name": "Apex",
                    "symbol": "α",
                    "price": "0.15",
                    "liquidity": "50000000000000",
                    "total_tao": "25000000000000",
                    "total_alpha": "200000000000000",
                    "alpha_in_pool": "100000000000000",
                    "alpha_staked": "100000000000000",
                    "tao_volume_24_hr": "1500000000000",
                    "tao_volume_24_hr_change_1_day": "10.5",
                    "price_change_1_hour": "2.5",
                    "price_change_1_day": "-5.0",
                    "price_change_1_week": "15.3",
                    "price_change_1_month": "-3.2",
                    "market_cap": "3000000000000000",
                    "registration_timestamp": "2024-01-15T10:30:00Z",
                },
                {
                    "netuid": 8,
                    "name": "Corcel",
                    "symbol": "S",
                    "price": "0.10",
                    "liquidity": "30000000000000",
                    "total_tao": "15000000000000",
                    "total_alpha": "180000000000000",
                    "alpha_in_pool": "90000000000000",
                    "alpha_staked": "90000000000000",
                    "tao_volume_24_hr": "800000000000",
                    "tao_volume_24_hr_change_1_day": "5.2",
                    "price_change_1_hour": "-1.0",
                    "price_change_1_day": "3.0",
                    "price_change_1_week": "-8.5",
                    "price_change_1_month": "12.0",
                    "market_cap": "2000000000000000",
                    "registration_timestamp": "2024-03-20T14:45:00Z",
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_fetch_subnet_pools_returns_real_data(self, mock_response):
        """Verify that fetching pools returns structured data with all fields."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient()
        
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            pools = await client.get_subnet_pools()
            
            assert len(pools) == 2
            # Verify structure
            assert pools[0].netuid == 1
            assert pools[0].name == "Apex"
            assert pools[0].has_volume is True
            assert pools[0].has_price_changes is True
            assert pools[0].has_registration is True

    @pytest.mark.asyncio
    async def test_fetch_pool_data_correctly_parsed(self, mock_response):
        """Verify numeric values are correctly parsed from API response."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient()
        
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            pools = await client.get_subnet_pools()
            
            pool1 = pools[0]
            # Check real volume data (already in TAO format per docs)
            assert pool1.volume_24h == 1500000000000.0  # As provided in mock
            # Check price changes
            assert pool1.price_change_1h == 2.5
            assert pool1.price_change_1d == -5.0
            assert pool1.price_change_7d == 15.3
            # Check registration timestamp (compare date only since timezone varies)
            assert pool1.registration_timestamp.year == 2024
            assert pool1.registration_timestamp.month == 1
            assert pool1.registration_timestamp.day == 15

    @pytest.mark.asyncio
    async def test_api_failure_raises_error(self):
        """Verify that API failures raise informative errors."""
        import httpx
        from subnet_trader.tao_api import TaostatsClient, TaostatsAPIError
        
        client = TaostatsClient()
        
        # Mock httpx.AsyncClient to raise RequestError
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            with pytest.raises(TaostatsAPIError) as exc_info:
                await client.get_subnet_pools()
            
            assert "404" in str(exc_info.value) or "HTTP error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_response_handled(self):
        """Verify empty API response is handled gracefully."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient()
        
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": []}
            
            pools = await client.get_subnet_pools()
            
            assert pools == []

    @pytest.mark.asyncio
    async def test_missing_fields_in_response(self):
        """Verify partial data is handled - missing fields become None/False."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient()
        
        # Response with some fields missing
        partial_response = {
            "data": [
                {
                    "netuid": 99,
                    "name": "NewSubnet",
                    "symbol": "N",
                    "price": "0.05",
                    # Missing: liquidity, volume, price_changes, registration
                }
            ]
        }
        
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = partial_response
            
            pools = await client.get_subnet_pools()
            
            pool = pools[0]
            assert pool.netuid == 99
            assert pool.alpha_price == 0.05
            assert pool.has_volume is False
            assert pool.has_price_changes is False
            assert pool.has_registration is False
            assert pool.volume_24h == 0.0
            assert pool.price_change_1d is None

    @pytest.mark.asyncio
    async def test_batch_fetch_multiple_netuids(self):
        """Verify we can fetch data for multiple specific subnets."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient()
        
        response = {
            "data": [
                {"netuid": 1, "name": "Apex", "price": "0.15"},
                {"netuid": 19, "name": "Tau", "price": "0.07"},
            ]
        }
        
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = response
            
            pools = await client.get_subnet_pools(netuids=[1, 19])
            
            assert len(pools) == 2
            netuids = [p.netuid for p in pools]
            assert 1 in netuids
            assert 19 in netuids


class TestTaostatsAPIEndpoints:
    """Tests verifying correct API endpoint construction."""

    @pytest.mark.asyncio
    async def test_correct_endpoint_used(self):
        """Verify the correct taostats.io API endpoint is called."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient()
        
        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": []}
            
            await client.get_subnet_pools()
            
            # Verify the URL includes the correct endpoint
            call_args = mock_get.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get('url', '')
            assert "api.taostats.io" in url or "taostats.io" in url

    @pytest.mark.asyncio
    async def test_api_key_header_included(self):
        """Verify API key is included in request headers."""
        from subnet_trader.tao_api import TaostatsClient
        
        client = TaostatsClient(api_key="test-key-123")
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_request.return_value = mock_response
            
            await client._get("https://api.test.io/test")
            
            # Verify headers include Authorization
            call_kwargs = mock_request.call_args[1]
            assert "Authorization" in call_kwargs.get("headers", {})
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key-123"
