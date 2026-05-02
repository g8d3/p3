"""RSI Divergence signal: measures momentum vs price divergence for reversal timing."""

import numpy as np
import pandas as pd

from signals.base import Signal, SignalOutput


class RSIDivergenceSignal(Signal):
    """RSI Divergence signal.

    Detects when price makes a new high/low but RSI doesn't confirm.
    - Price makes higher high, RSI makes lower high → bearish divergence
    - Price makes lower low, RSI makes higher low → bullish divergence

    Reversal timing signal: measures *when* to fade a move, not *direction*.
    Direction is inferred from which divergence fires.

    Output range: [-1, 1]
      +1 = strong bullish divergence (price↓ RSI↑)
      -1 = strong bearish divergence (price↑ RSI↓)
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="rsi_divergence", lookback_days=lookback_days)
        self.rsi_period = 14
        self.lookback_windows = [5, 10, 20]  # Check divergence over these windows

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if len(df) < self.rsi_period + max(self.lookback_windows) + 1:
                continue

            close = df["close"]

            # Compute RSI
            rsi = self._compute_rsi(close, self.rsi_period)
            if rsi is None or len(rsi) < 2:
                continue

            # Detect divergence over each window
            coin_signals = []
            for window in self.lookback_windows:
                if len(rsi) >= window + 1:
                    div = self._detect_divergence(rsi, close, window)
                    coin_signals.append(div)

            if coin_signals:
                all_signals.append(float(np.mean(coin_signals)))

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

    def _compute_rsi(self, close: pd.Series, period: int) -> pd.Series | None:
        """Compute RSI using Wilder's smoothing method."""
        if len(close) < period + 1:
            return None

        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        # Wilder's smoothed averages
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _detect_divergence(
        self,
        rsi: pd.Series,
        close: pd.Series,
        window: int,
    ) -> float:
        """Detect divergence over the given window.

        Returns:
            +1.0 to -1.0 signal strength.
        """
        if len(rsi) < window + 1:
            return 0.0

        rsi_vals = rsi.iloc[-window:].values
        price_vals = close.iloc[-window:].values

        rsi_trend = rsi_vals[-1] - rsi_vals[0]
        price_trend = price_vals[-1] - price_vals[0]

        if len(rsi_vals) < 2:
            return 0.0

        # Normalize trends
        rsi_range = rsi_vals.max() - rsi_vals.min()
        price_range = price_vals.max() - price_vals.min()

        if rsi_range < 1e-10 or price_range < 1e-10:
            return 0.0

        # Check for divergence
        # Bullish: price down, RSI up
        if price_trend < 0 and rsi_trend > 0:
            strength = min(abs(rsi_trend) / rsi_range, 1.0)
            return strength  # +1 = bullish divergence
        # Bearish: price up, RSI down
        elif price_trend > 0 and rsi_trend < 0:
            strength = -min(abs(rsi_trend) / rsi_range, 1.0)
            return strength  # -1 = bearish divergence

        return 0.0
