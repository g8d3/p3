"""Taostats.io API client for fetching real subnet data.

This client fetches data that cannot be obtained directly from the Bittensor chain:
- Real 24h trading volume
- Price change percentages (1h, 1d, 7d, 30d)
- Registration timestamps
- Historical pool data

API docs: https://docs.taostats.io
"""

import os
from datetime import datetime
from typing import Optional
import httpx

from subnet_trader.models import SubnetData


class TaostatsAPIError(Exception):
    """Raised when taostats.io API calls fail."""
    pass


RAO_PER_TAO = 1e9


class TaostatsClient:
    """Client for fetching subnet data from taostats.io API.
    
    This client provides data that the bittensor SDK does not expose directly,
    specifically:
    - Real trading volume (tao_volume_24_hr)
    - Price changes over various timeframes
    - Registration timestamps for age calculation
    """

    BASE_URL = "https://api.taostats.io"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client.
        
        Args:
            api_key: Optional taostats.io API key. If not provided, will try
                     to read from TAOSTATS_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("TAOSTATS_API_KEY", "")

    async def _get(self, url: str) -> dict:
        """Make a GET request to the API.
        
        Args:
            url: Full URL to fetch
            
        Returns:
            Parsed JSON response
            
        Raises:
            TaostatsAPIError: If the request fails
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise TaostatsAPIError(
                f"HTTP error {e.response.status_code} from taostats.io"
            ) from e
        except httpx.RequestError as e:
            raise TaostatsAPIError(
                f"Network error reaching taostats.io: {e}"
            ) from e
        except Exception as e:
            raise TaostatsAPIError(
                f"Failed to fetch from taostats.io: {e}"
            ) from e

    async def get_subnet_pools(
        self,
        netuids: Optional[list[int]] = None,
    ) -> list[SubnetData]:
        """Fetch current subnet pool data.
        
        This endpoint provides:
        - Current prices
        - Trading volume (24h)
        - Price changes (1h, 1d, 7d, 30d)
        - Liquidity and market cap
        - Registration timestamps
        
        Args:
            netuids: Optional list of specific netuids to fetch.
                    If None, fetches all subnets.
                    
        Returns:
            List of SubnetData with available fields populated
            
        Raises:
            TaostatsAPIError: If the API call fails
        """
        url = f"{self.BASE_URL}/api/dtao/pool/latest/v1"
        
        if netuids:
            # Filter by netuids - pass as comma-separated list
            url = f"{url}?netuid={','.join(map(str, netuids))}"
        
        response = await self._get(url)
        
        subnets = []
        for item in response.get("data", []):
            subnet = self._parse_pool_data(item)
            subnets.append(subnet)
        
        return subnets

    async def get_subnet_pool(self, netuid: int) -> Optional[SubnetData]:
        """Fetch pool data for a single subnet.
        
        Args:
            netuid: The subnet netuid
            
        Returns:
            SubnetData or None if not found
        """
        pools = await self.get_subnet_pools(netuids=[netuid])
        return pools[0] if pools else None

    def _parse_pool_data(self, data: dict) -> SubnetData:
        """Parse pool data from API response into SubnetData.
        
        Args:
            data: Raw API response data
            
        Returns:
            SubnetData with fields populated from the response
        """
        # Parse price (string in TAO)
        price_str = data.get("price", "0")
        alpha_price = float(price_str) if price_str else 0.0

        # Parse volume (already in TAO format according to docs)
        volume_str = data.get("tao_volume_24_hr", "0")
        try:
            volume_24h = float(volume_str) if volume_str else 0.0
        except (ValueError, TypeError):
            volume_24h = 0.0
        has_volume = volume_str is not None and volume_str != "0" and volume_24h > 0

        # Parse price changes (percentages as strings)
        price_change_1h = self._parse_percent(data.get("price_change_1_hour"))
        price_change_1d = self._parse_percent(data.get("price_change_1_day"))
        price_change_7d = self._parse_percent(data.get("price_change_1_week"))
        price_change_30d = self._parse_percent(data.get("price_change_1_month"))
        has_price_changes = any(v is not None for v in [
            price_change_1h, price_change_1d, price_change_7d, price_change_30d
        ])

        # Parse registration timestamp
        reg_ts = data.get("registration_timestamp")
        registration_timestamp = None
        has_registration = False
        if reg_ts:
            try:
                # Handle both formats: "2024-01-15T10:30:00Z" and "2024-01-15T10:30:00"
                registration_timestamp = datetime.fromisoformat(
                    reg_ts.replace("Z", "+00:00")
                )
                has_registration = True
            except (ValueError, TypeError):
                pass

        # Parse reserves (in rao, convert to TAO)
        tao_reserve_str = data.get("total_tao", "0")
        tao_reserve = float(tao_reserve_str) / RAO_PER_TAO if tao_reserve_str else 0.0
        
        alpha_reserve_str = data.get("total_alpha", "0")
        alpha_reserve = float(alpha_reserve_str) / RAO_PER_TAO if alpha_reserve_str else 0.0

        # Parse alpha staked
        alpha_staked_str = data.get("alpha_staked", "0")
        alpha_staked = float(alpha_staked_str) / RAO_PER_TAO if alpha_staked_str else 0.0

        # Parse market cap (in rao, convert to TAO)
        market_cap_str = data.get("market_cap", "0")
        market_cap = float(market_cap_str) / RAO_PER_TAO if market_cap_str else 0.0

        return SubnetData(
            netuid=int(data.get("netuid", 0)),
            name=str(data.get("name", "")),
            symbol=str(data.get("symbol", "")),
            alpha_price=alpha_price,
            tao_reserve=tao_reserve,
            alpha_reserve=alpha_reserve,
            alpha_staked=alpha_staked,
            volume_24h=volume_24h,
            price_change_1d=price_change_1d,
            price_change_7d=price_change_7d,
            price_change_30d=price_change_30d,
            price_change_1h=price_change_1h,
            market_cap=market_cap,
            registration_timestamp=registration_timestamp,
            has_volume=has_volume,
            has_price_changes=has_price_changes,
            has_registration=has_registration,
        )

    def _parse_percent(self, value) -> Optional[float]:
        """Parse a percentage string to float.
        
        Args:
            value: String percentage or None
            
        Returns:
            Float value or None if not parseable
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


async def fetch_all_subnet_data(
    chain_client,
    tao_client: TaostatsClient,
) -> list[SubnetData]:
    """Fetch complete subnet data from both chain and taostats.io.
    
    This function merges data from both sources:
    - Chain provides: emission values, subnet metadata
    - Taostats provides: volume, price changes, registration
    
    Args:
        chain_client: SubnetChainClient for chain data
        tao_client: TaostatsClient for taostats data
        
    Returns:
        List of SubnetData with merged data from both sources
    """
    # Fetch from both sources in parallel would be ideal,
    # but for simplicity we fetch sequentially
    chain_subnets = chain_client.get_all_subnets()
    tao_subnets = await tao_client.get_subnet_pools()
    
    # Create lookup by netuid
    tao_by_netuid = {s.netuid: s for s in tao_subnets}
    
    # Merge data
    merged = []
    for chain_subnet in chain_subnets:
        tao_subnet = tao_by_netuid.get(chain_subnet.netuid)
        
        if tao_subnet:
            # Merge: start with chain data, overlay tao data
            merged_subnet = SubnetData(
                netuid=chain_subnet.netuid,
                name=chain_subnet.name or tao_subnet.name,
                symbol=chain_subnet.symbol or tao_subnet.symbol,
                # Use chain price if tao price is 0
                alpha_price=tao_subnet.alpha_price or chain_subnet.alpha_price,
                tao_reserve=tao_subnet.tao_reserve,
                alpha_reserve=tao_subnet.alpha_reserve,
                alpha_staked=tao_subnet.alpha_staked,
                volume_24h=tao_subnet.volume_24h,
                price_change_1h=tao_subnet.price_change_1h,
                price_change_1d=tao_subnet.price_change_1d,
                price_change_7d=tao_subnet.price_change_7d,
                price_change_30d=tao_subnet.price_change_30d,
                market_cap=tao_subnet.market_cap,
                registration_timestamp=tao_subnet.registration_timestamp,
                emission_share=chain_subnet.emission_share,
                tao_emission_per_block=chain_subnet.tao_emission_per_block,
                has_volume=tao_subnet.has_volume,
                has_price_changes=tao_subnet.has_price_changes,
                has_registration=tao_subnet.has_registration,
            )
        else:
            # No taostats data - use chain data only
            merged_subnet = chain_subnet
        
        merged.append(merged_subnet)
    
    return merged
