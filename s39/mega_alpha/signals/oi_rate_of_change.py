"""Open Interest Rate of Change signal: detects exhaustion via OI flow analysis."""

import numpy as np
import pandas as pd

from signals.base import Signal, SignalOutput


class OIRateOfChangeSignal(Signal):
    """Open Interest Rate of Change signal.

    Measures the FLOW of open interest (change rate), not the absolute level.

    Logic:
    - OI rising + price falling → shorts adding but getting run over → SHORT SQUEEZE setup
    - OI falling + price rising → long liquidation → bearish exhaustion
    - OI rising + price rising → new money entering → trend confirmation (bullish)
    - OI falling + price falling → shorts covering → trend weakening

    This is an exhaustion/explosion detector. It tells you when a move is
    likely to reverse or explode.

    Output range: [-1, 1]
      +1 = potential SHORT SQUEEZE (OI up + price down OR OI down + price up sharply)
      -1 = potential LONG LIQUIDATION / bearish exhaustion
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="oi_rate_of_change", lookback_days=lookback_days)
        self.oi_roc_period = 24  # 24 hours = 1 day OI change

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_signals = []

        for coin, df in data.items():
            if "open_interest" not in df.columns:
                continue

            oi = df["open_interest"].dropna()
            close = df["close"]

            if len(oi) < self.oi_roc_period + 2:
                continue

            # OI rate of change
            oi_now = oi.iloc[-1]
            oi_past = oi.iloc[-1 - self.oi_roc_period]
            oi_roc = (oi_now - oi_past) / (oi_past + 1e-10)

            # Price rate of change
            price_now = close.iloc[-1]
            price_past = close.iloc[-1 - self.oi_roc_period]
            price_roc = (price_now - price_past) / (price_past + 1e-10)

            # Signal construction
            # OI up + price down → shorts being squeezed → +1
            # OI up + price up → new longs entering → momentum confirmation → +0.5
            # OI down + price up → long liquidation → -0.5
            # OI down + price down → shorts covering → 0

            if oi_roc > 0.02:  # OI increasing significantly
                if price_roc < -0.01:  # Price falling
                    # Short squeeze: OI up, price down
                    strength = min(abs(price_roc) / 0.05, 1.0) * min(abs(oi_roc) / 0.1, 1.0)
                    signal = min(strength, 1.0)
                elif price_roc > 0.01:  # Price rising
                    # New money coming in → bullish confirmation
                    strength = min(price_roc / 0.05, 1.0) * min(oi_roc / 0.1, 1.0)
                    signal = 0.5 * strength
                else:
                    signal = 0.0
            elif oi_roc < -0.02:  # OI decreasing significantly
                if price_roc > 0.01:  # Price rising
                    # Long liquidation → bearish exhaustion
                    strength = min(price_roc / 0.05, 1.0) * min(abs(oi_roc) / 0.1, 1.0)
                    signal = -0.5 * strength
                elif price_roc < -0.01:  # Price falling
                    # Shorts covering (weak bearish)
                    signal = 0.0
                else:
                    signal = 0.0
            else:
                signal = 0.0

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
