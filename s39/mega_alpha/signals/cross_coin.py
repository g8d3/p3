"""Cross-Coin Signal: BTC leads ETH/SOL — detects when one coin predicts another.

In crypto markets, BTC often leads ETH and SOL by 15-60 minutes due to:
- BTC being the "risk on/off" proxy for crypto
- BTC having deeper perp markets and more sophisticated traders
- ETF flows and institutional money entering via BTC first

This signal detects when BTC makes a move but ETH/SOL haven't followed yet,
creating a probabilistic prediction for the laggard coins.

Output: for each laggard coin, the predicted direction based on BTC's recent move.
Range: [-1, 1]
  +1 = BTC bullish → expect ETH/SOL to follow up
  -1 = BTC bearish → expect ETH/SOL to follow down
"""

import numpy as np
import pandas as pd

from signals.base import Signal, SignalOutput


class CrossCoinSignal(Signal):
    """Cross-Coin signal: BTC leads detection.

    Detects when BTC moves but ETH/SOL haven't followed yet.
    Uses price momentum across multiple timeframes to identify the lead.

    This signal outputs one value PER COIN (ETH, SOL) based on BTC's behavior.
    """

    def __init__(self, lookback_days: int = 30):
        super().__init__(name="cross_coin", lookback_days=lookback_days)
        self.lead_windows = [1, 4, 12]  # hours: BTC leading by 1h, 4h, 12h
        self.btc_coin = "BTC"
        self.laggard_coins = ["ETH", "SOL"]

    def compute(self, data: dict[str, pd.DataFrame]) -> SignalOutput:
        from datetime import datetime

        # Must have BTC and at least one laggard
        if self.btc_coin not in data:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "no_btc_data"},
            )

        btc_df = data[self.btc_coin]
        if len(btc_df) < max(self.lead_windows) + 2:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "insufficient_btc_history"},
            )

        # Compute BTC momentum across windows
        btc_momenta = []
        for window in self.lead_windows:
            if len(btc_df) > window:
                btc_ret = (btc_df["close"].iloc[-1] / btc_df["close"].iloc[-1 - window]) - 1
                btc_momenta.append(btc_ret)

        if not btc_momenta:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "no_btc_momentum"},
            )

        avg_btc_momentum = np.mean(btc_momenta)

        # Check each laggard coin
        coin_signals = {}
        for coin in self.laggard_coins:
            if coin not in data:
                continue

            laggard_df = data[coin]
            if len(laggard_df) < max(self.lead_windows) + 2:
                coin_signals[coin] = 0.0
                continue

            # Compute laggard momentum over same windows
            laggard_momenta = []
            for window in self.lead_windows:
                if len(laggard_df) > window:
                    lag_ret = (laggard_df["close"].iloc[-1] / laggard_df["close"].iloc[-1 - window]) - 1
                    laggard_momenta.append(lag_ret)

            if not laggard_momenta:
                coin_signals[coin] = 0.0
                continue

            avg_lag_momentum = np.mean(laggard_momenta)

            # Signal: BTC momentum minus laggard momentum
            # Positive = BTC is leading up (BTC up more than laggard)
            # Negative = BTC is leading down
            momentum_gap = avg_btc_momentum - avg_lag_momentum

            # Also check: is BTC trending? If BTC is flat, no signal
            btc_trend = abs(avg_btc_momentum)
            if btc_trend < 0.005:  # Less than 0.5% BTC move → no signal
                coin_signals[coin] = 0.0
                continue

            # Normalize gap to [-1, 1]
            signal = np.clip(momentum_gap / 0.03, -1, 1)  # 3% gap = full signal
            coin_signals[coin] = float(signal)

        # Average signal across laggards
        if not coin_signals:
            return SignalOutput(
                name=self.name,
                value=0.0,
                timestamp=datetime.utcnow(),
                metadata={"reason": "no_lag_coins"},
            )

        avg_signal = float(np.mean(list(coin_signals.values())))

        return SignalOutput(
            name=self.name,
            value=avg_signal,
            timestamp=datetime.utcnow(),
            metadata={
                "btc_momentum": float(avg_btc_momentum),
                "per_coin": coin_signals,
            },
        )
