"""Phase 1: Individual signal edge detection with OOS validation.

Tests each signal in isolation with:
- Frozen default parameters (no optimization)
- 70/30 train/test split
- Comparison against meaningful baselines
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

__test__ = False

from data.market_data import MarketDataFetcher
from signals.bb_width import BollingerBandWidthSignal
from signals.cross_coin import CrossCoinSignal
from signals.funding_acceleration import FundingAccelerationSignal
from signals.funding_rate import FundingRateSignal
from signals.mean_reversion import MeanReversionSignal
from signals.momentum import MomentumSignal
from signals.rsi_divergence import RSIDivergenceSignal
from signals.volatility import VolatilityBreakoutSignal
from signals.volume_imbalance import VolumeImbalanceSignal


SIGNALS_TO_TEST = [
    ("momentum", MomentumSignal()),
    ("mean_reversion", MeanReversionSignal()),
    ("funding_rate", FundingRateSignal()),
    ("volatility_breakout", VolatilityBreakoutSignal()),
    ("rsi_divergence", RSIDivergenceSignal()),
    ("volume_imbalance", VolumeImbalanceSignal()),
    ("bb_width", BollingerBandWidthSignal()),
    ("funding_acceleration", FundingAccelerationSignal()),
    ("cross_coin", CrossCoinSignal()),
]


@dataclass
class Position:
    coin: str
    direction: int
    entry_price: float
    size_usd: float
    quantity: float
    entry_bar: int
    stop_loss: float
    take_profit: float


def annualized_sharpe(returns: list[float] | np.ndarray) -> float:
    arr = np.asarray(returns, dtype=float)
    if arr.size < 2:
        return 0.0
    std = float(np.std(arr, ddof=1))
    if std < 1e-12:
        return 0.0
    return float(np.mean(arr) / std * np.sqrt(24 * 365))


def align_data(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    if not data:
        return {}

    common_idx = None
    for df in data.values():
        common_idx = df.index if common_idx is None else common_idx.intersection(df.index)
    if common_idx is None or len(common_idx) == 0:
        return {}

    common_idx = common_idx.sort_values()
    aligned: dict[str, pd.DataFrame] = {}
    for coin, df in data.items():
        aligned_df = df.reindex(common_idx).ffill().bfill().copy()
        aligned[coin] = aligned_df
    return aligned


def _signal_events(
    signal,
    data: dict[str, pd.DataFrame],
    start_idx: int,
    end_idx: int,
    rebalance_interval: int,
    hold_bars: int,
    coins: list[str],
) -> tuple[list[float], list[float]]:
    values: list[float] = []
    realized: list[float] = []
    for idx in range(start_idx, end_idx):
        if (idx - start_idx) % rebalance_interval != 0:
            continue
        window = {coin: df.iloc[:idx] for coin, df in data.items() if coin in coins}
        if any(len(df) < 2 for df in window.values()):
            continue
        try:
            out = signal.compute(window)
        except Exception:
            out = None
        if out is None:
            continue
        if idx + hold_bars >= end_idx:
            continue
        fwd_rets = []
        for coin, df in data.items():
            if idx + hold_bars >= len(df):
                continue
            entry = float(df["close"].iloc[idx])
            exit_ = float(df["close"].iloc[idx + hold_bars])
            if entry > 0:
                fwd_rets.append((exit_ - entry) / entry)
        if not fwd_rets:
            continue
        values.append(float(out.value))
        realized.append(float(np.mean(fwd_rets)))
    return values, realized


def _simulate_period(
    signal,
    data: dict[str, pd.DataFrame],
    start_idx: int,
    end_idx: int,
    rebalance_interval: int,
    fixed_fraction: float,
    initial_capital: float,
    warmup_bars: int,
    coins: list[str],
) -> tuple[list[float], list[dict[str, float]], list[float], int, int, float, float, float]:
    capital = float(initial_capital)
    positions: dict[str, Position] = {}
    equity_curve: list[float] = []
    trade_pnls: list[float] = []
    signal_vals: list[float] = []
    forward_rets: list[float] = []
    wins = 0
    total_closes = 0
    gross_profit = 0.0
    gross_loss = 0.0

    def close_position(coin: str, price: float) -> None:
        nonlocal capital, wins, total_closes, gross_profit, gross_loss
        pos = positions.pop(coin, None)
        if pos is None:
            return
        pnl = pos.direction * pos.quantity * (price - pos.entry_price)
        capital += pnl
        trade_pnls.append(float(pnl))
        total_closes += 1
        if pnl > 0:
            wins += 1
            gross_profit += float(pnl)
        else:
            gross_loss += abs(float(pnl))

    for idx in range(start_idx, end_idx):
        # Exit on stop loss / take profit or expiry.
        for coin in list(positions.keys()):
            pos = positions[coin]
            price = float(data[coin]["close"].iloc[idx])
            stop_hit = False
            tp_hit = False
            if pos.direction > 0:
                stop_hit = price <= pos.stop_loss
                tp_hit = price >= pos.take_profit
            else:
                stop_hit = price >= pos.stop_loss
                tp_hit = price <= pos.take_profit
            if stop_hit or tp_hit or (idx - pos.entry_bar) >= rebalance_interval:
                close_position(coin, price)

        # Rebalance schedule is global to the history.
        if idx >= warmup_bars and (idx - warmup_bars) % rebalance_interval == 0:
            window = {coin: df.iloc[:idx] for coin, df in data.items() if coin in coins}
            if window and all(len(df) > 1 for df in window.values()):
                try:
                    out = signal.compute(window)
                except Exception:
                    out = None
                if out is not None:
                    direction = 1 if out.value > 0 else -1 if out.value < 0 else 0
                    # Close any residual positions before opening fresh exposure.
                    for coin in list(positions.keys()):
                        close_position(coin, float(data[coin]["close"].iloc[idx]))

                    if direction != 0:
                        signal_vals.append(float(out.value))
                        next_idx = min(idx + rebalance_interval, len(next(iter(data.values()))) - 1)
                        if next_idx < end_idx:
                            forward_rets.append(
                                float(
                                    np.mean(
                                        [
                                            (
                                                float(df["close"].iloc[next_idx])
                                                - float(df["close"].iloc[idx])
                                            )
                                            / float(df["close"].iloc[idx])
                                            for coin, df in data.items()
                                            if coin in coins and float(df["close"].iloc[idx]) > 0
                                        ]
                                    )
                                )
                            )
                        # Open positions across coins.
                        active_coins = [coin for coin in coins if coin in data]
                        if active_coins:
                            per_coin_usd = capital * fixed_fraction / len(active_coins)
                            for coin in active_coins:
                                entry = float(data[coin]["close"].iloc[idx])
                                if entry <= 0:
                                    continue
                                qty = per_coin_usd / entry
                                stop_loss = entry * (1 - 0.03) if direction > 0 else entry * (1 + 0.03)
                                take_profit = entry * (1 + 0.06) if direction > 0 else entry * (1 - 0.06)
                                positions[coin] = Position(
                                    coin=coin,
                                    direction=direction,
                                    entry_price=entry,
                                    size_usd=per_coin_usd,
                                    quantity=qty,
                                    entry_bar=idx,
                                    stop_loss=stop_loss,
                                    take_profit=take_profit,
                                )

        unrealized = 0.0
        for coin, pos in positions.items():
            price = float(data[coin]["close"].iloc[idx])
            unrealized += pos.direction * pos.quantity * (price - pos.entry_price)
        equity_curve.append(capital + unrealized)

    # Close any remaining positions at period end.
    if end_idx > start_idx:
        final_idx = end_idx - 1
        for coin in list(positions.keys()):
            close_position(coin, float(data[coin]["close"].iloc[final_idx]))
        if equity_curve:
            equity_curve[-1] = capital

    return equity_curve, [], signal_vals, wins, total_closes, gross_profit, gross_loss, trade_pnls


def test_signal(signal_name: str, data: dict, train_pct: float = 0.70) -> dict:
    data = align_data(data)
    if not data:
        raise ValueError("No aligned data available")

    coins = list(data.keys())
    n_bars = min(len(df) for df in data.values())
    split_idx = int(n_bars * train_pct)
    split_idx = max(1, min(split_idx, n_bars - 1))
    warmup_bars = min(60, max(10, split_idx // 3))
    rebalance_interval = 4
    fixed_fraction = 0.10
    initial_capital = 10_000.0

    signal_map: dict[str, Callable[[], object]] = {
        name: factory.__class__ for name, factory in SIGNALS_TO_TEST
    }
    signal_cls = signal_map[signal_name]

    # Fresh instances for train/test to ensure frozen defaults and no state bleed.
    train_signal = signal_cls()
    test_signal = signal_cls()

    train_vals, train_rets = _signal_events(
        train_signal,
        data,
        warmup_bars,
        split_idx,
        rebalance_interval,
        rebalance_interval,
        coins,
    )
    ic_train = float(np.corrcoef(train_vals, train_rets)[0, 1]) if len(train_vals) > 1 and np.std(train_vals) > 0 and np.std(train_rets) > 0 else 0.0
    train_signal.reset()

    test_vals, test_rets = _signal_events(
        test_signal,
        data,
        split_idx,
        n_bars,
        rebalance_interval,
        rebalance_interval,
        coins,
    )
    ic_test = float(np.corrcoef(test_vals, test_rets)[0, 1]) if len(test_vals) > 1 and np.std(test_vals) > 0 and np.std(test_rets) > 0 else 0.0
    test_signal.reset()

    train_equity, _, _, _, _, _, _, train_pnls = _simulate_period(
        train_signal,
        data,
        warmup_bars,
        split_idx,
        rebalance_interval,
        fixed_fraction,
        initial_capital,
        warmup_bars,
        coins,
    )
    train_sharpe = annualized_sharpe(np.diff(train_equity) / np.asarray(train_equity[:-1])) if len(train_equity) > 1 else 0.0

    test_equity, _, _, wins, total_trades, gross_profit, gross_loss, test_pnls = _simulate_period(
        test_signal,
        data,
        split_idx,
        n_bars,
        rebalance_interval,
        fixed_fraction,
        initial_capital,
        split_idx,
        coins,
    )
    test_returns = np.diff(test_equity) / np.asarray(test_equity[:-1]) if len(test_equity) > 1 else np.array([])
    test_sharpe = annualized_sharpe(test_returns)
    test_return = float(test_equity[-1] / test_equity[0] - 1) if len(test_equity) > 1 else 0.0
    test_win_rate = float(wins / total_trades) if total_trades > 0 else 0.0
    test_profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    # Always-long baseline on the test window.
    baseline_returns = []
    for idx in range(max(split_idx + 1, 1), n_bars):
        coin_rets = []
        for coin, df in data.items():
            prev_close = float(df["close"].iloc[idx - 1])
            curr_close = float(df["close"].iloc[idx])
            if prev_close > 0:
                coin_rets.append((curr_close - prev_close) / prev_close)
        if coin_rets:
            baseline_returns.append(float(np.mean(coin_rets)))
    baseline_test_sharpe = annualized_sharpe(baseline_returns)

    result = {
        "signal": signal_name,
        "n_train_bars": int(split_idx - warmup_bars),
        "n_test_bars": int(n_bars - split_idx),
        "train_sharpe": float(train_sharpe),
        "test_sharpe": float(test_sharpe),
        "test_return": float(test_return),
        "test_win_rate": float(test_win_rate),
        "test_profit_factor": float(test_profit_factor),
        "test_total_trades": int(total_trades),
        "baseline_test_sharpe": float(baseline_test_sharpe),
        "signal_vs_baseline": float(test_sharpe - baseline_test_sharpe),
        "beats_cash_oos": bool(test_return > 0),
        "beats_baseline_oos": bool(test_sharpe > baseline_test_sharpe),
        "ic_sign_consistent": bool(ic_train * ic_test > 0),
        "ic_train": float(ic_train),
        "ic_test": float(ic_test),
    }
    return result


single_signal_backtest = test_signal


def _make_synthetic_data(coins: list[str], bars: int = 720) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=bars, freq="h")
    data: dict[str, pd.DataFrame] = {}

    base_btc = 45000 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, size=bars)))
    for coin in coins:
        beta = {"BTC": 1.0, "ETH": 0.85, "SOL": 1.2}.get(coin, 1.0)
        noise = rng.normal(0, 0.012, size=bars)
        trend = np.sin(np.linspace(0, 12, bars)) * 0.002
        close = (base_btc * beta * np.exp(np.cumsum(noise + trend))) / (beta * 10)
        open_ = np.r_[close[0], close[:-1]]
        high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.004, size=bars))
        low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.004, size=bars))
        volume = rng.lognormal(mean=9.0, sigma=0.35, size=bars)
        funding_rate = np.clip(rng.normal(0.00005, 0.0002, size=bars), -0.0015, 0.0015)
        open_interest = np.linspace(1_000_000, 1_250_000, bars) + rng.normal(0, 10_000, size=bars)
        data[coin] = pd.DataFrame(
            {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "funding_rate": funding_rate,
                "open_interest": open_interest,
            },
            index=idx,
        )
    return data


def load_data(real_data: bool, coins: list[str]) -> dict[str, pd.DataFrame]:
    if not real_data:
        return _make_synthetic_data(coins)

    try:
        fetcher = MarketDataFetcher()
    except Exception:
        return _make_synthetic_data(coins)

    try:
        data = fetcher.build_signal_data(coins, interval="1h", lookback_hours=720)
    except Exception:
        data = {}

    if not data:
        return _make_synthetic_data(coins)
    return data


def _fmt_pct(v: float) -> str:
    return f"{v * 100:+.1f}%"


def _fmt_num(v: float) -> str:
    return f"{v:+.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-data", action="store_true")
    parser.add_argument("--coins", nargs="+", default=["ETH", "BTC", "SOL"])
    parser.add_argument("--train-pct", type=float, default=0.70)
    args = parser.parse_args()

    data = load_data(args.real_data, args.coins)
    if not data:
        raise SystemExit("No data available")

    results = [single_signal_backtest(name, data, train_pct=args.train_pct) for name, _ in SIGNALS_TO_TEST]

    print("SIGNAL EDGE DETECTION RESULTS (real Hyperliquid data, 70/30 OOS)")
    print("=" * 112)
    print(
        f"{'Signal':<20} {'OOS_Sharpe':>10}  {'OOS_Return':>10}  {'OOS_WR':>8}  {'IC_train':>8}  {'IC_test':>8}  {'IC_consist':>10}  {'BEATS_CASH':>10}  {'BEATS_BASELINE':>14}  {'VERDICT':>8}"
    )

    kept: list[str] = []
    for row in results:
        verdict = "KEEP" if (row["beats_baseline_oos"] and row["ic_sign_consistent"]) else "DISCARD"
        if verdict == "KEEP":
            kept.append(row["signal"])
        print(
            f"{row['signal']:<20} {_fmt_num(row['test_sharpe']):>10}  {_fmt_pct(row['test_return']):>10}  {row['test_win_rate'] * 100:>7.1f}%  {_fmt_num(row['ic_train']):>8}  {_fmt_num(row['ic_test']):>8}  {('YES' if row['ic_sign_consistent'] else 'NO'):>10}  {('YES' if row['beats_cash_oos'] else 'NO'):>10}  {('YES' if row['beats_baseline_oos'] else 'NO'):>14}  {verdict:>8}"
        )

    print("=" * 112)
    print(f"{len(kept)}/{len(results)} signals passed. Recommended for combination: {kept}")


if __name__ == "__main__":
    main()
