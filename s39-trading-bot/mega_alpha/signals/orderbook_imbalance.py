"""Orderbook imbalance signal: bid/ask pressure from the order book."""

import numpy as np
import pandas as pd

from .base import Signal, SignalOutput


class OrderbookImbalanceSignal(Signal):
    """Orderbook imbalance signal.

    Measures the ratio of bid vs ask volume in the order book.
    Heavy bid side → buying pressure → long signal
    Heavy ask side → selling pressure → short signal

    Uses multiple depth levels for robustness.

    Output range: [-1, 1]
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="orderbook_imbalance", lookback_days=lookback_days)
        self.depth_levels = 5  # Top N levels to consider
        self.imbalance_history: list[float] = []

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        all_imbalances = []

        for coin, df in data.items():
            # Check for orderbook data columns
            if "bid_volume" not in df.columns or "ask_volume" not in df.columns:
                # Fall back to volume-based proxy using tick data
                if "volume" in df.columns and len(df) >= 5:
                    # Use volume-weighted close position as proxy
                    recent = df.iloc[-5:]
                    high_low_range = recent["high"] - recent["low"]
                    close_low = recent["close"] - recent["low"]

                    if high_low_range.mean() > 0:
                        # CLV (Close Location Value) as proxy
                        clv = ((recent["close"] - recent["low"]) -
                               (recent["high"] - recent["close"])) / high_low_range
                        volume_weighted_clv = (clv * recent["volume"]).sum() / recent["volume"].sum()
                        imbalance = float(np.clip(volume_weighted_clv, -1, 1))
                        all_imbalances.append(imbalance)
                continue

            bid_vol = df["bid_volume"].iloc[-1]
            ask_vol = df["ask_volume"].iloc[-1]

            total = bid_vol + ask_vol
            if total < 1e-10:
                continue

            # Imbalance: +1 = all bids, -1 = all asks
            imbalance = (bid_vol - ask_vol) / total
            all_imbalances.append(float(imbalance))

        if not all_imbalances:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "no_orderbook_data"},
            )

        avg_imbalance = float(np.mean(all_imbalances))
        avg_imbalance = np.clip(avg_imbalance, -1, 1)

        # Track history for the combination engine
        self.imbalance_history.append(avg_imbalance)

        return SignalOutput(
            name=self.name,
            value=avg_imbalance,
            timestamp=datetime.utcnow(),
            metadata={
                "per_coin": {coin: imb for coin, imb in zip(data.keys(), all_imbalances)},
            },
        )
