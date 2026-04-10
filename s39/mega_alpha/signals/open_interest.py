"""Open interest signal: changes in open interest as a positioning indicator."""

import numpy as np
import pandas as pd

from .base import Signal, SignalOutput


class OpenInterestSignal(Signal):
    """Open interest signal for perpetual futures.

    Logic:
    - Rising OI + rising price → new longs entering → bullish confirmation
    - Rising OI + falling price → new shorts entering → bearish confirmation
    - Falling OI + rising price → shorts covering → weak bullish (exhaustion)
    - Falling OI + falling price → longs liquidating → weak bearish (exhaustion)

    Output range: [-1, 1]
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="open_interest", lookback_days=lookback_days)
        self.oi_change_window = 5  # Look at 5-period OI change

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if "open_interest" not in df.columns:
                continue

            oi = df["open_interest"].dropna()
            close = df["close"]

            if len(oi) < self.oi_change_window + 1:
                continue

            # OI change
            current_oi = oi.iloc[-1]
            past_oi = oi.iloc[-1 - self.oi_change_window]
            oi_change = (current_oi - past_oi) / (past_oi + 1e-10)

            # Price change
            current_price = close.iloc[-1]
            past_price = close.iloc[-1 - self.oi_change_window]
            price_change = (current_price - past_price) / (past_price + 1e-10)

            # Determine signal based on OI/price relationship
            signal = 0.0

            if oi_change > 0.02:  # OI increasing significantly
                if price_change > 0:
                    # New longs → bullish
                    signal = min(abs(oi_change) * 5, 1.0)
                else:
                    # New shorts → bearish
                    signal = -min(abs(oi_change) * 5, 1.0)
            elif oi_change < -0.02:  # OI decreasing significantly
                if price_change > 0:
                    # Short covering → weak bullish
                    signal = min(abs(oi_change) * 2, 0.5)
                else:
                    # Long liquidation → weak bearish
                    signal = -min(abs(oi_change) * 2, 0.5)

            all_signals.append(float(signal))

        if not all_signals:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "no_oi_data"},
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
