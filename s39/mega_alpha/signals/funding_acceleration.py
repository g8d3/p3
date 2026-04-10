"""Funding Rate Acceleration signal: measures the change in funding rate momentum."""

import numpy as np
import pandas as pd

from signals.base import Signal, SignalOutput


class FundingAccelerationSignal(Signal):
    """Funding Rate Acceleration signal.

    Measures the RATE OF CHANGE of funding rates.

    Logic:
    - Funding rate going from 0 → very negative (deep contango) → likely bounce
    - Funding rate going from 0 → very positive (premium) → likely reversal
    - Funding ACCELERATING toward extremes → stronger signal

    This is a 2nd-derivative signal. The existing funding_rate signal measures
    the LEVEL. This measures the MOMENTUM of funding.

    Output range: [-1, 1]
      -1 = funding rate accelerating toward positive extremes (bearish)
      +1 = funding rate accelerating toward negative extremes (bullish)
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="funding_acceleration", lookback_days=lookback_days)
        self.accel_period = 8  # How many funding periods to measure acceleration over
        # Typical: 8 hours between funding payments

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if "funding_rate" not in df.columns:
                continue

            funding = df["funding_rate"].dropna()
            if len(funding) < self.accel_period + 2:
                continue

            # Current funding rate
            current = funding.iloc[-1]

            # Funding rate N periods ago
            past = funding.iloc[-1 - self.accel_period]

            # Acceleration: change in funding over period
            # A simple proxy: difference between current and past
            funding_change = current - past

            # Normalize by typical funding magnitude (0.0001 = 0.01%)
            typical_magnitude = 0.0001
            normalized_change = funding_change / typical_magnitude

            # Also compute 2nd derivative: is funding change increasing?
            if len(funding) >= self.accel_period * 2 + 1:
                prev_change = funding.iloc[-1 - self.accel_period] - funding.iloc[-1 - self.accel_period * 2]
                accel = funding_change - prev_change
                # Combine rate and acceleration
                signal_value = normalized_change + 0.5 * accel / typical_magnitude
            else:
                signal_value = normalized_change

            # Clip and invert: if funding is going up (toward positive = premium),
            # that's bearish (expect reversal). So signal = -normalized_change
            signal = -np.clip(signal_value / 3.0, -1, 1)

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
