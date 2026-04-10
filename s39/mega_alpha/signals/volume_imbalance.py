"""Volume Imbalance signal: measures volume participation quality vs price direction."""

import numpy as np
import pandas as pd

from signals.base import Signal, SignalOutput


class VolumeImbalanceSignal(Signal):
    """Volume Imbalance signal.

    Detects when volume surges in the direction of price moves — or against them.
    - Rising price + surging volume = confirmed move (momentum)
    - Falling price + surging volume = distribution (smart sellers)
    - Falling price + falling volume = weak selling (potential reversal)
    - Rising price + falling volume = thin volume (potential reversal)

    This is the "smart money" signal: it detects when institutional players
    are actively buying or selling vs retail.

    Output range: [-1, 1]
      +1 = bullish volume pressure (volume surging on up moves or drying up on down)
      -1 = bearish volume pressure
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="volume_imbalance", lookback_days=lookback_days)
        self.volume_ma_period = 20  # Compare current volume to this MA
        self.roc_period = 5  # Rate of change period

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if len(df) < self.volume_ma_period + self.roc_period + 1:
                continue

            close = df["close"]
            volume = df["volume"]

            # Volume MA
            vol_ma = volume.rolling(window=self.volume_ma_period).mean()

            # Volume ROC (rate of change)
            vol_roc = (volume - volume.shift(self.roc_period)) / (
                volume.shift(self.roc_period) + 1e-10
            )

            # Price change over the same period
            price_change = (close - close.shift(self.roc_period)) / (
                close.shift(self.roc_period) + 1e-10
            )

            # Current values
            current_vol_roc = vol_roc.iloc[-1]
            current_price_change = price_change.iloc[-1]

            if np.isnan(current_vol_roc) or np.isnan(current_price_change):
                continue

            # Volume relative to MA
            current_vol = volume.iloc[-1]
            current_vol_ma = vol_ma.iloc[-1]
            vol_ratio = current_vol / (current_vol_ma + 1e-10)

            # Signal construction:
            # If price up AND volume surging → bullish confirmation
            # If price up AND volume shrinking → weak, potential reversal
            # If price down AND volume surging → bearish distribution
            # If price down AND volume shrinking → weak selling, potential bounce

            if current_price_change > 0:
                # Price rising
                if vol_ratio > 1.0:
                    # Volume surging with price → bullish
                    signal = min(vol_ratio - 1.0, 2.0) / 2.0
                else:
                    # Volume shrinking with price rise → potential reversal
                    signal = -(1.0 - vol_ratio) / 2.0
            else:
                # Price falling
                if vol_ratio > 1.0:
                    # Volume surging with price drop → bearish distribution
                    signal = -min(vol_ratio - 1.0, 2.0) / 2.0
                else:
                    # Volume shrinking with price drop → potential bounce
                    signal = (1.0 - vol_ratio) / 2.0

            all_signals.append(float(signal))

        if not all_signals:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "insufficient_data"},
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
