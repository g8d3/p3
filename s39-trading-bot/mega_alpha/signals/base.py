"""Base signal class for the Mega Alpha trading system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SignalOutput:
    """Output from a single signal evaluation."""

    name: str
    value: float  # Raw signal value, typically [-1, 1] or probability [0, 1]
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def direction(self) -> int:
        """Return 1 for long, -1 for short, 0 for neutral."""
        if self.value > 0.05:
            return 1
        elif self.value < -0.05:
            return -1
        return 0


class Signal(ABC):
    """Abstract base class for trading signals.

    Each signal must:
    - Have a unique name
    - Produce a SignalOutput when evaluated
    - Track historical returns for the combination engine
    - Be independently evaluable
    """

    def __init__(self, name: str, lookback_days: int = 30):
        self.name = name
        self.lookback_days = lookback_days
        self._history: list[SignalOutput] = []
        self._returns_history: list[float] = []

    @abstractmethod
    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        """Compute the signal value from market data.

        Args:
            data: Dict mapping coin -> DataFrame with OHLCV + other data.
                  DataFrame columns: open, high, low, close, volume, etc.

        Returns:
            SignalOutput with the computed signal value.
        """
        ...

    def record_return(self, realized_return: float) -> None:
        """Record the realized return from the last signal for the combination engine."""
        self._returns_history.append(realized_return)

    @property
    def returns_history(self) -> np.ndarray:
        """Get historical returns as numpy array."""
        return np.array(self._returns_history)

    @property
    def mean_return(self) -> float:
        """Mean of historical returns."""
        if len(self._returns_history) == 0:
            return 0.0
        return float(np.mean(self._returns_history))

    @property
    def volatility(self) -> float:
        """Volatility (std) of historical returns."""
        if len(self._returns_history) < 2:
            return 1.0
        return float(np.std(self._returns_history, ddof=1))

    @property
    def ic(self) -> float:
        """Information coefficient: correlation between signal and subsequent returns.

        This is estimated from the rank correlation of historical signal values
        with their realized returns.
        """
        if len(self._returns_history) < 10:
            return 0.0
        # Use recent history as a proxy
        returns = np.array(self._returns_history[-60:])
        if np.std(returns) < 1e-10:
            return 0.0
        # IC is approximated by mean_return / volatility (Sharpe-like)
        return float(np.mean(returns) / (np.std(returns, ddof=1) + 1e-10))

    def reset(self) -> None:
        """Reset signal history."""
        self._history.clear()
        self._returns_history.clear()
