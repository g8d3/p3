"""Data models for subnet trader."""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class SubnetData:
    """Raw on-chain data for a single subnet."""

    netuid: int
    name: str = ""
    symbol: str = ""
    tao_staked: float = 0.0  # Total TAO staked in subnet
    alpha_price: float = 0.0  # Price in TAO (tao_reserve / alpha_reserve)
    tao_reserve: float = 0.0  # TAO in AMM pool
    alpha_reserve: float = 0.0  # Alpha in AMM pool
    alpha_staked: float = 0.0  # Alpha staked (out of pool)
    emission_share: float = 0.0  # Share of total network emission (0-1)
    tao_emission_per_block: float = 0.0  # TAO emitted to this subnet per block
    registration_block: Optional[int] = None
    market_cap: float = 0.0
    volume_24h: float = 0.0
    price_change_1d: float = 0.0
    price_change_7d: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SignalScores:
    """Individual signal scores for a subnet (all normalized to 0-1)."""

    yield_score: float = 0.0
    momentum_score: float = 0.0
    price_trend_score: float = 0.0
    volume_score: float = 0.0
    age_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompositeScore:
    """Final composite score for a subnet."""

    netuid: int
    name: str
    composite: float
    rank: int
    signals: SignalScores
    raw_data: SubnetData

    def to_dict(self) -> dict:
        return {
            "netuid": self.netuid,
            "name": self.name,
            "composite_score": self.composite,
            "rank": self.rank,
            "signals": self.signals.to_dict(),
            "raw_data": self.raw_data.to_dict(),
        }


@dataclass
class RebalanceOrder:
    """A single rebalance action."""

    action: str  # "stake" or "unstake"
    netuid: int
    amount_tao: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnalysisResult:
    """Complete analysis output."""

    timestamp: str
    subnets: list[CompositeScore]
    orders: list[RebalanceOrder]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "subnets": [s.to_dict() for s in self.subnets],
            "orders": [o.to_dict() for o in self.orders],
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2)
