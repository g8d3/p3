"""Volatility breakout signal: Bollinger Band / ATR breakout detection."""

import numpy as np
import pandas as pd

from .base import Signal, SignalOutput


class VolatilityBreakoutSignal(Signal):
    """Volatility breakout signal.

    Detects when price breaks out of a volatility envelope (Bollinger Bands).
    Breakouts above the upper band → momentum long signal.
    Breakouts below the lower band → momentum short signal.

    Also detects volatility compression (squeeze) which precedes big moves.

    Output range: [-1, 1]
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="volatility_breakout", lookback_days=lookback_days)
        self.bb_period = 20
        self.bb_std = 2.0
        self.atr_period = 14

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if len(df) < self.bb_period + 1:
                continue

            close = df["close"]
            high = df["high"]
            low = df["low"]

            # Bollinger Bands
            sma = close.rolling(window=self.bb_period).mean()
            std = close.rolling(window=self.bb_period).std()
            upper_band = sma + self.bb_std * std
            lower_band = sma - self.bb_std * std

            current_price = close.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_sma = sma.iloc[-1]

            if pd.isna(current_upper) or pd.isna(current_lower):
                continue

            # Bandwidth (for squeeze detection)
            bandwidth = (current_upper - current_lower) / current_sma
            avg_bandwidth = (upper_band.rolling(50).mean() - lower_band.rolling(50).mean()) / sma.rolling(50).mean()

            signal = 0.0

            # Breakout detection
            if current_price > current_upper:
                # Breakout above upper band → bullish momentum
                breakout_strength = (current_price - current_upper) / (current_upper - current_sma + 1e-10)
                signal = min(breakout_strength, 1.0)
            elif current_price < current_lower:
                # Breakout below lower band → bearish momentum
                breakout_strength = (current_lower - current_price) / (current_sma - current_lower + 1e-10)
                signal = -min(breakout_strength, 1.0)

            # Squeeze detection: if bandwidth is very narrow, expect a big move
            if not pd.isna(avg_bandwidth.iloc[-1]) and avg_bandwidth.iloc[-1] > 0:
                squeeze_ratio = bandwidth / avg_bandwidth.iloc[-1]
                if squeeze_ratio < 0.5:
                    # In a squeeze - use ATR direction to predict breakout direction
                    if len(df) >= self.atr_period + 1:
                        atr = (high - low).rolling(window=self.atr_period).mean()
                        recent_atr = atr.iloc[-1]
                        prev_atr = atr.iloc[-2] if not pd.isna(atr.iloc[-2]) else recent_atr

                        # If ATR is expanding, trade in the direction of the move
                        if recent_atr > prev_atr:
                            direction = 1 if current_price > current_sma else -1
                            signal = direction * 0.5  # Moderate confidence in squeeze breakout

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
