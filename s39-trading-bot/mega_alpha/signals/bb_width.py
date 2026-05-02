"""Bollinger Band Width signal: measures volatility regime and overbought/oversold levels."""

import numpy as np
import pandas as pd

from signals.base import Signal, SignalOutput


class BollingerBandWidthSignal(Signal):
    """Bollinger Band Width (%B) signal.

    %B = (price - lower_band) / (upper_band - lower_band)

    Measures where price is relative to its volatility envelope:
    - %B near 0: price at lower band (oversold in mean reversion terms)
    - %B near 1: price at upper band (overbought)
    - %B near 0.5: price in the middle of the band

    Different from volatility_breakout which measures breakouts OUTSIDE the band.
    This measures position INSIDE the band — it's a mean reversion / regime signal.

    Output range: [-1, 1]
      -1 = price at lower band (potential bounce / long signal)
      +1 = price at upper band (potential reversal / short signal)
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="bb_width", lookback_days=lookback_days)
        self.bb_period = 20
        self.bb_std = 2.0
        self.regime_threshold = 0.15  # %B < this = oversold, > 1-threshold = overbought

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if len(df) < self.bb_period + 1:
                continue

            close = df["close"]

            # Bollinger Bands
            sma = close.rolling(window=self.bb_period).mean()
            std = close.rolling(window=self.bb_period).std()
            upper_band = sma + self.bb_std * std
            lower_band = sma - self.bb_std * std

            current_price = close.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            band_width = current_upper - current_lower

            if pd.isna(current_upper) or pd.isna(current_lower) or band_width < 1e-10:
                continue

            # %B: position within the band
            bb_percent = (current_price - current_lower) / band_width

            # Signal: mean-reversion view
            # %B near 0 → price at lower band → potential long signal (oversold)
            # %B near 1 → price at upper band → potential short signal (overbought)
            # Map [0, 1] to [-1, 1]: 0 → -1, 0.5 → 0, 1 → +1
            signal = (bb_percent - 0.5) * 2

            # Also check bandwidth for squeeze detection
            bandwidth_series = (upper_band - lower_band) / sma
            current_bandwidth = bandwidth_series.iloc[-1]
            avg_bandwidth = bandwidth_series.rolling(50).mean().iloc[-1]

            if not pd.isna(avg_bandwidth) and avg_bandwidth > 0:
                squeeze_ratio = current_bandwidth / avg_bandwidth
                # If in a squeeze, the signal is weaker (potential big move coming)
                # but direction still matters
                if squeeze_ratio < 0.7:
                    signal *= 0.5  # Reduce confidence during squeeze

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
