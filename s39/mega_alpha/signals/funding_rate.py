"""Funding rate signal: contrarian signal based on funding rate extremes."""

import numpy as np
import pandas as pd

from .base import Signal, SignalOutput


class FundingRateSignal(Signal):
    """Funding rate signal for perpetual futures.

    Logic:
    - Extremely positive funding → market is overleveraged long → fade (short signal)
    - Extremely negative funding → market is overleveraged short → fade (long signal)
    - Normal funding → no edge → neutral

    Uses both current funding rate and its recent trend.

    Output range: [-1, 1]
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="funding_rate", lookback_days=lookback_days)
        # Typical perp funding: 0.01% per 8h = 0.0001
        # Extreme: >0.05% per 8h = 0.0005
        self.extreme_threshold = 0.0005  # 0.05% per 8h
        self.very_extreme_threshold = 0.001  # 0.1% per 8h

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if "funding_rate" not in df.columns:
                continue

            funding = df["funding_rate"].dropna()
            if len(funding) < 3:
                continue

            current_funding = funding.iloc[-1]
            avg_funding = funding.mean()

            # Contrarian signal: fade extreme funding
            signal = 0.0

            # Current funding signal
            if abs(current_funding) > self.extreme_threshold:
                # Fade: positive funding → short, negative → long
                intensity = min(
                    abs(current_funding) / self.very_extreme_threshold, 1.0
                )
                signal = -np.sign(current_funding) * intensity

            # Trend signal: if funding is increasing in one direction, stronger fade
            if len(funding) >= 5:
                recent_avg = funding.iloc[-5:].mean()
                if abs(recent_avg) > abs(avg_funding) * 1.5:
                    # Funding is accelerating → stronger contrarian signal
                    trend_intensity = min(
                        abs(recent_avg) / self.very_extreme_threshold, 0.5
                    )
                    signal += -np.sign(recent_avg) * trend_intensity
                    signal = np.clip(signal, -1, 1)

            all_signals.append(float(signal))

        if not all_signals:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "no_funding_data"},
            )

        avg_signal = float(np.mean(all_signals))
        avg_signal = np.clip(avg_signal, -1, 1)

        return SignalOutput(
            name=self.name,
            value=avg_signal,
            timestamp=datetime.utcnow(),
            metadata={
                "per_coin": {coin: s for coin, s in zip(data.keys(), all_signals)},
            },
        )
