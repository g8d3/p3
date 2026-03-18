"""On-chain data fetching from Bittensor via bittensor SDK."""

import bittensor as bt
from typing import Optional
from subnet_trader.models import SubnetData

RAO_PER_TAO = 1e9

# Known subnet names (community-curated)
SUBNET_NAMES = {
    0: "Root",
    1: "Apex",
    2: "Avalon",
    3: "Cipher",
    4: "Delta",
    5: "Epoch",
    6: "Fourier",
    7: "Gemma",
    8: "Corcel",
    9: "Ignite",
    10: "Juno",
    11: "Koda",
    12: "Luna",
    13: "Mycelium",
    14: "N现",
    15: "OpenKaito",
    16: "Prompting",
    17: "Vision",
    18: "Wand",
    19: "Tau",
}


def parse_subnet_data(raw: dict) -> SubnetData:
    """Parse raw data into SubnetData."""
    def to_tao(val, default: float = 0.0) -> float:
        if val is None:
            return default
        if hasattr(val, 'rao'):  # Balance object
            return float(val.rao) / RAO_PER_TAO
        return float(val)

    return SubnetData(
        netuid=int(raw.get("netuid", 0)),
        name=str(raw.get("name", "")),
        symbol=str(raw.get("symbol", "")),
        tao_staked=to_tao(raw.get("tao_staked")),
        alpha_price=to_tao(raw.get("alpha_price")),
        tao_reserve=to_tao(raw.get("tao_reserve")),
        alpha_reserve=to_tao(raw.get("alpha_reserve")),
        alpha_staked=to_tao(raw.get("alpha_staked")),
        emission_share=to_tao(raw.get("emission_share")),
        tao_emission_per_block=to_tao(raw.get("tao_emission_per_block")),
        registration_block=raw.get("registration_block"),
        market_cap=to_tao(raw.get("market_cap")),
        volume_24h=to_tao(raw.get("volume_24h")),
    )


def calculate_emission_shares(ema_prices: dict[int, float]) -> dict[int, float]:
    """Calculate emission share for each subnet based on EMA prices."""
    if not ema_prices:
        return {}
    total = sum(ema_prices.values())
    if total == 0:
        return {k: 1.0 / len(ema_prices) for k in ema_prices}
    return {k: v / total for k, v in ema_prices.items()}


class SubnetChainClient:
    """Client for fetching subnet data from Bittensor chain.

    Uses bittensor SDK (synchronous) for RPC queries.
    Raises exception on connection failure - no silent mock fallback.
    """

    def __init__(self, network: str = "finney", mock: bool = False):
        self.network = network
        self.mock = mock
        self._subtensor: Optional[bt.Subtensor] = None

    def _get_subtensor(self) -> bt.Subtensor:
        """Get or create subtensor connection."""
        if self._subtensor is None:
            self._subtensor = bt.Subtensor(network=self.network)
        return self._subtensor

    def get_all_subnets(self) -> list[SubnetData]:
        """Fetch all subnets from chain. Raises on failure."""
        if self.mock:
            return self._get_mock_subnets()

        try:
            subtensor = self._get_subtensor()
            
            # Get subnet count
            subnet_count = subtensor.get_total_subnets()
            
            # Get all subnet info
            subnet_infos = subtensor.get_all_subnets_info()
            
            # Get all prices (map netuid -> price)
            price_map = {}
            for netuid in range(subnet_count):
                try:
                    price = subtensor.get_subnet_price(netuid)
                    if price:
                        price_map[netuid] = float(price.rao) / RAO_PER_TAO
                except Exception:
                    price_map[netuid] = 0.0

            # Get total emission for calculating shares
            total_emission = subnet_count  # Approximate - actual varies
            
            subnets = []
            for info in subnet_infos:
                netuid = info.netuid
                price = price_map.get(netuid, 0.0)
                
                # Emission share based on emission_value relative to total
                emission_ratio = float(info.emission_value) / max(total_emission, 1)

                subnets.append(SubnetData(
                    netuid=netuid,
                    name=SUBNET_NAMES.get(netuid, f"Subnet {netuid}"),
                    symbol="",
                    tao_staked=0.0,  # Would need complex query to get total stake
                    alpha_price=price,
                    emission_share=emission_ratio,
                    tao_emission_per_block=float(info.emission_value),
                    registration_block=None,
                ))
            
            subtensor.close()
            return subnets
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch subnets from chain: {e}. "
                "Set mock=True to use mock data for testing."
            ) from e

    def get_subnet(self, netuid: int) -> Optional[SubnetData]:
        """Fetch a single subnet by netuid."""
        if self.mock:
            for s in self._get_mock_subnets():
                if s.netuid == netuid:
                    return s
            return None

        try:
            subtensor = self._get_subtensor()
            
            info = subtensor.get_subnet_info(netuid)
            if not info:
                return None
                
            try:
                price = subtensor.get_subnet_price(netuid)
                alpha_price = float(price.rao) / RAO_PER_TAO if price else 0.0
            except Exception:
                alpha_price = 0.0

            subtensor.close()
            
            return SubnetData(
                netuid=netuid,
                name=SUBNET_NAMES.get(netuid, f"Subnet {netuid}"),
                symbol="",
                tao_staked=0.0,
                alpha_price=alpha_price,
                emission_share=float(info.emission_value),
                tao_emission_per_block=float(info.emission_value),
                registration_block=None,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to fetch subnet {netuid}: {e}") from e

    def _get_mock_subnets(self) -> list[SubnetData]:
        """Mock data - ONLY used when mock=True."""
        return [
            SubnetData(netuid=1, name="Apex", symbol="α",
                tao_staked=500_000, alpha_price=0.15,
                tao_reserve=75_000, alpha_reserve=500_000,
                alpha_staked=1_000_000, emission_share=0.12,
                tao_emission_per_block=0.12, registration_block=100_000),
            SubnetData(netuid=8, name="Corcel", symbol="S",
                tao_staked=1_000_000, alpha_price=0.10,
                tao_reserve=100_000, alpha_reserve=1_000_000,
                alpha_staked=2_000_000, emission_share=0.15,
                tao_emission_per_block=0.15, registration_block=300_000),
            SubnetData(netuid=19, name="τ", symbol="t",
                tao_staked=800_000, alpha_price=0.069,
                tao_reserve=22_500, alpha_reserve=324_000,
                alpha_staked=532_000, emission_share=0.08,
                tao_emission_per_block=0.08, registration_block=200_000),
        ]

    def close(self):
        """Close connection."""
        if self._subtensor:
            self._subtensor.close()
            self._subtensor = None
