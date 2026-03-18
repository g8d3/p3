"""Data models for subnet trader."""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class SubnetData:
    """Raw on-chain data for a single subnet.
    
    Fields are marked Optional[...] when they may not be available from all sources.
    The 'has_<field>' attributes indicate data availability.
    """

    netuid: int
    name: str = ""
    symbol: str = ""
    
    # AMM Pool data
    alpha_price: float = 0.0  # Price in TAO
    tao_reserve: float = 0.0  # TAO in AMM pool
    alpha_reserve: float = 0.0  # Alpha in AMM pool
    volume_24h: float = 0.0  # Real 24h volume from taostats.io
    
    # Emission data
    emission_share: float = 0.0  # Share of total network emission (0-1)
    tao_emission_per_block: float = 0.0  # TAO emitted to this subnet per block
    
    # Registration (from taostats.io)
    registration_timestamp: Optional[datetime] = None
    
    # Price changes (from taostats.io)
    price_change_1h: Optional[float] = None  # % change in last hour
    price_change_1d: Optional[float] = None  # % change in last day
    price_change_7d: Optional[float] = None  # % change in last week
    price_change_30d: Optional[float] = None  # % change in last month
    
    # Data source flags
    has_volume: bool = False
    has_price_changes: bool = False
    has_registration: bool = False
    
    # Chain-only data (may be 0 if unavailable)
    tao_staked: float = 0.0
    alpha_staked: float = 0.0
    market_cap: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SignalScores:
    """Individual signal scores for a subnet (all normalized to 0-1).
    
    A signal_score of None means the signal could not be computed (data unavailable).
    This is intentional - we do NOT fake signals with hardcoded defaults.
    """

    # Yield signal - based on alpha_price
    yield_score: Optional[float] = None
    
    # Volume signal - based on real volume_24h from taostats.io
    volume_score: Optional[float] = None
    
    # Short-term momentum - based on price_change_1h
    momentum_1h_score: Optional[float] = None
    
    # Medium-term momentum - based on price_change_1d
    momentum_1d_score: Optional[float] = None
    
    # Long-term momentum - based on price_change_7d
    momentum_7d_score: Optional[float] = None
    
    # Age/maturity - based on registration_timestamp
    age_score: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)
    
    def has_any_signal(self) -> bool:
        """Check if at least one signal is available."""
        return any(v is not None for v in [
            self.yield_score,
            self.volume_score,
            self.momentum_1h_score,
            self.momentum_1d_score,
            self.momentum_7d_score,
            self.age_score,
        ])


@dataclass
class CompositeScore:
    """Final composite score for a subnet."""

    netuid: int
    name: str
    composite: Optional[float]  # None if no signals available
    rank: int
    signals: SignalScores
    raw_data: SubnetData
    signals_available: int  # Count of signals that could be computed

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RebalanceOrder:
    """A single rebalance action."""

    action: str  # "stake" or "unstake"
    netuid: int
    amount_tao: float
    reason: str = ""  # Why this action was taken

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnalysisResult:
    """Complete analysis output."""

    timestamp: str
    subnets: list[CompositeScore]
    orders: list[RebalanceOrder]
    signals_included: list[str]  # Which signals were actually computed

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2)
