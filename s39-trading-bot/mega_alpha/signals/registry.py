"""Signal registry for managing and accessing all signals."""

from typing import Type

from .base import Signal
from .momentum import MomentumSignal
from .mean_reversion import MeanReversionSignal
from .funding_rate import FundingRateSignal
from .volatility import VolatilityBreakoutSignal
from .rsi_divergence import RSIDivergenceSignal
from .volume_imbalance import VolumeImbalanceSignal
from .bb_width import BollingerBandWidthSignal
from .funding_acceleration import FundingAccelerationSignal
from .cross_coin import CrossCoinSignal


class SignalRegistry:
    """Registry of available signals. Allows dynamic registration and instantiation."""

    _signals: dict[str, Type[Signal]] = {}

    def __init__(self):
        self._signals = {
            # Original signals
            "momentum": MomentumSignal,
            "mean_reversion": MeanReversionSignal,
            "funding_rate": FundingRateSignal,
            "volatility_breakout": VolatilityBreakoutSignal,
            # New signals
            "rsi_divergence": RSIDivergenceSignal,
            "volume_imbalance": VolumeImbalanceSignal,
            "bb_width": BollingerBandWidthSignal,
            "funding_acceleration": FundingAccelerationSignal,
            "cross_coin": CrossCoinSignal,
        }

    def register(self, name: str, signal_cls: Type[Signal]) -> None:
        self._signals[name] = signal_cls

    def get(self, name: str) -> Type[Signal]:
        if name not in self._signals:
            raise KeyError(
                f"Signal '{name}' not registered. Available: {list(self._signals.keys())}"
            )
        return self._signals[name]

    def create_all(self, lookback_days: int = 30) -> list[Signal]:
        """Create instances of all registered signals."""
        return [cls(lookback_days=lookback_days) for cls in self._signals.values()]

    @property
    def available(self) -> list[str]:
        return list(self._signals.keys())
