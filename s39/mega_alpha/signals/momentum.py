"""Momentum signal: time-series momentum across multiple lookback periods."""

import numpy as np
import pandas as pd

from .base import Signal, SignalOutput


class MomentumSignal(Signal):
    """Multi-timeframe momentum signal.

    Computes momentum as the normalized return over multiple lookback windows,
    then combines them with a weighted average (shorter windows get less weight
    to reduce noise).

    Output range: [-1, 1]
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="momentum", lookback_days=lookback_days)
        self.windows = [1, 3, 7, 14, 30]  # days
        self.weights = [0.1, 0.15, 0.25, 0.25, 0.25]

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_momenta = []

        for coin, df in data.items():
            if len(df) < 31:
                continue

            close = df["close"].values
            momenta = []

            for window, weight in zip(self.windows, self.weights):
                if len(close) > window:
                    ret = (close[-1] / close[-1 - window]) - 1
                    # Normalize: annualized vol ~50% for crypto, so daily ~3%
                    # A 5% move over window is strong
                    normalized = np.clip(ret / (0.03 * np.sqrt(window)), -1, 1)
                    momenta.append(normalized * weight)

            if momenta:
                coin_momentum = sum(momenta)
                all_momenta.append(coin_momentum)

        if not all_momenta:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "insufficient_data"},
            )

        # Average across coins
        avg_momentum = float(np.mean(all_momenta))
        avg_momentum = np.clip(avg_momentum, -1, 1)

        return SignalOutput(
            name=self.name,
            value=avg_momentum,
            timestamp=datetime.utcnow(),
            metadata={
                "per_coin": {coin: m for coin, m in zip(data.keys(), all_momenta)},
                "windows": self.windows,
            },
        )
