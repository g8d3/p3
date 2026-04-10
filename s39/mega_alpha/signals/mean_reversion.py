"""Mean reversion signal: z-score deviation from moving average."""

import numpy as np
import pandas as pd

from .base import Signal, SignalOutput


class MeanReversionSignal(Signal):
    """Mean reversion signal based on z-score of price vs moving average.

    When price is significantly above its MA, signal is negative (expect reversion).
    When price is significantly below its MA, signal is positive (expect bounce).

    Uses multiple MA periods for robustness.

    Output range: [-1, 1]
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="mean_reversion", lookback_days=lookback_days)
        self.ma_periods = [20, 50]  # Use 20 and 50 period MAs
        self.z_score_cap = 2.5  # Cap z-score before normalizing to [-1, 1]

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_zscores = []

        for coin, df in data.items():
            if len(df) < 51:
                continue

            close = df["close"]
            coin_zscores = []

            for period in self.ma_periods:
                if len(close) < period:
                    continue
                ma = close.rolling(window=period).mean()
                std = close.rolling(window=period).std()

                current_price = close.iloc[-1]
                current_ma = ma.iloc[-1]
                current_std = std.iloc[-1]

                if current_std < 1e-10:
                    continue

                z = (current_price - current_ma) / current_std
                # Clip and normalize to [-1, 1]
                z_capped = np.clip(z, -self.z_score_cap, self.z_score_cap)
                z_normalized = z_capped / self.z_score_cap
                # Invert: above MA -> negative signal (expect reversion down)
                coin_zscores.append(-z_normalized)

            if coin_zscores:
                all_zscores.append(float(np.mean(coin_zscores)))

        if not all_zscores:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "insufficient_data"},
            )

        avg_zscore = float(np.mean(all_zscores))
        avg_zscore = np.clip(avg_zscore, -1, 1)

        return SignalOutput(
            name=self.name,
            value=avg_zscore,
            timestamp=datetime.utcnow(),
            metadata={
                "per_coin": {coin: z for coin, z in zip(data.keys(), all_zscores)},
                "ma_periods": self.ma_periods,
            },
        )
