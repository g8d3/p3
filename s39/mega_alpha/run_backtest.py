#!/usr/bin/env python3
"""Run backtests with real Hyperliquid data.

Usage:
    uv run python3 run_backtest.py
    uv run python3 run_backtest.py --iterations 100 --target-sharpe 0.5
    uv run python3 run_backtest.py --coins ETH BTC SOL --lookback-hours 2160
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from loguru import logger

from data.market_data import MarketDataFetcher
from backtest.engine import BacktestEngine
from backtest.optimizer import ParameterOptimizer


# ─── Charting ────────────────────────────────────────────────────────────────

def plot_equity_curves(results: list, save_dir: Path, top_n: int = 10) -> None:
    """Plot equity curves and bar charts for the top-N results by Sharpe."""
    if not results:
        return

    sorted_results = sorted(results, key=lambda r: r.get("sharpe", 0), reverse=True)
    top = [r for r in sorted_results if r.get("equity_curve")]

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [2, 1]})

    ax1 = axes[0]
    colors = plt.cm.plasma(np.linspace(0.15, 0.85, len(top)))

    for i, r in enumerate(top[:top_n]):
        equity_list = r["equity_curve"]
        if not equity_list:
            continue
        equity = pd.Series(equity_list)
        label = (
            f"#{r['run_id']:3d} | "
            f"Sharpe={r.get('sharpe', 0):+.2f} | "
            f"Ret={r.get('total_return', 0)*100:+.1f}% | "
            f"DD={r.get('max_drawdown', 0)*100:+.1f}% | "
            f"WR={r.get('win_rate', 0)*100:.0f}% | "
            f"PF={r.get('profit_factor', 0):.2f}"
        )
        ax1.plot(equity.values, color=colors[i], alpha=0.8, linewidth=1.1, label=label)

    ax1.set_title(
        f"Mega Alpha Backtest — Equity Curves (Top {min(top_n, len(top))} configs)\n"
        f"Coins: ETH, BTC, SOL | TF: 1H | Period: 2026-01-10 → 2026-04-10 | "
        f"{len(results)} total runs",
        fontsize=11, fontweight="bold",
    )
    ax1.set_ylabel("Portfolio Value ($)", fontsize=10)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))
    ax1.legend(fontsize=7, loc="upper left", ncol=1)
    ax1.grid(alpha=0.25)

    # ── Stats bar chart ──
    ax2 = axes[1]
    valid = [r for r in sorted_results if r.get("total_trades", 0) > 0][:top_n]
    if valid:
        x = np.arange(len(valid))
        w = 0.22
        run_labels = [f"#{r['run_id']}" for r in valid]
        sharpes = [r.get("sharpe", 0) for r in valid]
        rets    = [r.get("total_return", 0) * 100 for r in valid]
        dds     = [r.get("max_drawdown", 0) * 100 for r in valid]

        ax2.bar(x - w, sharpes, w, label="Sharpe", color="#2196F3", alpha=0.85)
        ax2.bar(x,      rets,    w, label="Return %", color="#4CAF50", alpha=0.85)
        ax2.bar(x + w, dds,     w, label="Max DD %", color="#F44336", alpha=0.85)
        ax2.set_xticks(x)
        ax2.set_xticklabels(run_labels, fontsize=8)
        ax2.axhline(0, color="black", linewidth=0.6)
        ax2.legend(fontsize=9)
        ax2.set_ylabel("Value", fontsize=10)
        ax2.grid(alpha=0.25, axis="y")
        ax2.set_title("Sharpe / Return% / MaxDD% comparison", fontsize=10)

    plt.tight_layout()
    path = save_dir / "equity_curves.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Saved: {path}")


def plot_signal_ic_heatmap(results: list, save_dir: Path) -> None:
    """Plot per-signal IC heatmap across all runs."""
    signal_names = [
        "momentum", "mean_reversion", "funding_rate",
        "orderbook_imbalance", "volatility_breakout", "open_interest",
    ]

    rows = {}
    for r in results:
        row = {}
        for sig in signal_names:
            row[sig] = r.get("per_signal_ic", {}).get(sig, 0.0)
        rows[f"#{r['run_id']}"] = row

    df = pd.DataFrame(rows).T  # rows = runs, cols = signals

    fig, ax = plt.subplots(figsize=(11, max(5, len(df) * 0.35)))
    im = ax.imshow(df.values, aspect="auto", cmap="RdYlGn", vmin=-0.25, vmax=0.25)

    ax.set_xticks(range(len(signal_names)))
    ax.set_xticklabels(signal_names, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df.index, fontsize=7)

    for i in range(len(df)):
        for j in range(len(signal_names)):
            val = df.values[i, j]
            color = "white" if abs(val) > 0.12 else "black"
            ax.text(j, i, f"{val:+.3f}", ha="center", va="center",
                   fontsize=7, color=color)

    ax.set_title(
        "Per-Signal IC Heatmap — green = predictive, red =contrarian\n"
        "(IC = correlation between signal value and subsequent return)",
        fontsize=10, fontweight="bold",
    )
    plt.colorbar(im, ax=ax, label="IC (higher = more predictive)", shrink=0.6)
    plt.tight_layout()
    path = save_dir / "signal_ic_heatmap.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Saved: {path}")


# ─── Data Fetching ───────────────────────────────────────────────────────────

def fetch_real_data(coins: list[str], lookback_hours: int = 2160) -> dict[str, pd.DataFrame]:
    """Fetch real data from Hyperliquid and build signal-ready DataFrames."""
    fetcher = MarketDataFetcher("https://api.hyperliquid.xyz")
    data = {}

    for coin in coins:
        try:
            df = fetcher.get_ohlcv(coin, "1h", lookback_hours)
            if df.empty:
                logger.warning(f"  {coin}: no OHLCV data, skipping")
                continue

            # Funding rate
            funding = fetcher.get_funding_rate(coin, lookback_hours)
            if not funding.empty:
                df["funding_rate"] = funding.reindex(df.index, method="ffill").fillna(0)
            else:
                df["funding_rate"] = 0.0

            # Open interest (current value — static for backtest history)
            oi = fetcher.get_open_interest(coin)
            df["open_interest"] = oi if oi else 0.0

            # Orderbook imbalance
            book = fetcher.get_orderbook(coin)
            if book and "levels" in book:
                bids, asks = book["levels"]
                if bids and asks:
                    df["bid_volume"] = sum(float(b.get("sz", 0)) for b in bids[:5])
                    df["ask_volume"] = sum(float(a.get("sz", 0)) for a in asks[:5])

            data[coin] = df

            p0, p1 = df["close"].iloc[0], df["close"].iloc[-1]
            chg = (p1 - p0) / p0 * 100
            sign = "+" if chg > 0 else ""
            bar = "█" * int(abs(chg) / 2)
            logger.info(
                f"  {coin:4s}: {len(df)} bars | "
                f"{p0:.2f} → {p1:.2f} ({sign}{chg:.1f}%) | "
                f"OI={df['open_interest'].iloc[-1]:>12,.0f} | "
                f"{bar}"
            )
        except Exception as e:
            logger.error(f"  {coin}: failed — {e}")

    return data


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mega Alpha Backtester — Real Hyperliquid Data")
    parser.add_argument("--coins", nargs="+", default=["ETH", "BTC", "SOL"])
    parser.add_argument("--capital", type=float, default=10_000.0)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--target-sharpe", type=float, default=0.5)
    parser.add_argument("--target-dd", type=float, default=0.25)
    parser.add_argument("--lookback-hours", type=int, default=2160)
    parser.add_argument("--results-dir", type=str, default="backtest_results")
    args = parser.parse_args()

    # Logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    )

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # ── Fetch data ──
    logger.info("=" * 70)
    logger.info("FETCHING REAL DATA FROM HYPERLIQUID")
    logger.info("=" * 70)

    data = fetch_real_data(args.coins, args.lookback_hours)
    if not data:
        logger.error("No data fetched. Check API connectivity.")
        sys.exit(1)

    # Reference info
    ref = list(data.values())[0]
    date_start = ref.index[0].strftime("%Y-%m-%d")
    date_end   = ref.index[-1].strftime("%Y-%m-%d")
    n_bars     = len(ref)

    # ── Config summary ──
    logger.info("")
    logger.info("─" * 70)
    logger.info("BACKTEST CONFIGURATION")
    logger.info("─" * 70)
    logger.info(f"  Coins:           {', '.join(args.coins)}")
    logger.info(f"  Timeframe:       1H (hourly candles)")
    logger.info(f"  Date range:      {date_start} → {date_end}  ({n_bars} bars = {n_bars/24:.0f} days)")
    logger.info(f"  Initial capital: ${args.capital:,.0f}")
    logger.info(f"  Commission:       5 bps (0.05%) per trade")
    logger.info(f"  Slippage:        3 bps (0.03%) per trade")
    logger.info(f"  Iterations:      {args.iterations} random parameter sets")
    logger.info(f"  Target Sharpe:  > {args.target_sharpe}")
    logger.info(f"  Target Max DD:  < {args.target_dd:.0%}")
    logger.info("─" * 70)
    logger.info("")

    # ── Run optimizer ──
    logger.info("STARTING CONTINUOUS PARAMETER SEARCH")
    logger.info("=" * 70)

    engine = BacktestEngine(
        data=data,
        initial_capital=args.capital,
        commission_bps=5.0,
        slippage_bps=3.0,
    )

    optimizer = ParameterOptimizer(
        engine=engine,
        results_dir=str(results_dir),
        target_sharpe=args.target_sharpe,
        target_max_dd=args.target_dd,
        max_iterations=args.iterations,
    )

    best = optimizer.search()

    # ── Save charts ──
    all_results = [
        {
            "run_id": sr.run_id,
            "sharpe": sr.sharpe,
            "sortino": sr.sharpe,
            "total_return": sr.total_return,
            "max_drawdown": sr.max_drawdown,
            "win_rate": sr.win_rate,
            "profit_factor": sr.profit_factor,
            "total_trades": sr.total_trades,
            "per_signal_ic": sr.per_signal_ic,
            "params": sr.params,
            "is_promising": sr.is_promising,
            "equity_curve": [],
        }
        for sr in optimizer.results
    ]

    plot_equity_curves(all_results, results_dir)
    plot_signal_ic_heatmap(all_results, results_dir)

    # ── Summary table ──
    logger.info("")
    logger.info("=" * 70)
    logger.info("ALL RUNS SUMMARY (sorted by Sharpe)")
    logger.info("=" * 70)
    hdr = (f"{'Run':>4}  {'Sharpe':>8}  {'Return':>8}  {'MaxDD':>7}  "
            f"{'WR':>6}  {'PF':>6}  {'Trades':>6}  {'FixedFrac':>10}  Promising")
    logger.info(hdr)
    logger.info("-" * 70)
    for sr in sorted(optimizer.results, key=lambda r: r.sharpe, reverse=True):
        logger.info(
            f"#{sr.run_id:3d}  "
            f"{sr.sharpe:8.3f}  "
            f"{sr.total_return:7.1%}  "
            f"{sr.max_drawdown:6.1%}  "
            f"{sr.win_rate:6.1%}  "
            f"{sr.profit_factor:6.2f}  "
            f"{sr.total_trades:6d}  "
            f"{sr.params.get('fixed_fraction', 0):10.3f}  "
            f"{'✅' if sr.is_promising else ''}"
        )

    # ── Best result ──
    if best:
        logger.info("")
        logger.info("=" * 70)
        logger.info("BEST CONFIGURATION")
        logger.info("=" * 70)
        logger.info(
            f"  Sharpe Ratio:    {best.sharpe:+.3f}   "
            f"({'✅ BEATS TARGET' if best.sharpe > args.target_sharpe else '❌ below target'})"
        )
        logger.info(f"  Max Drawdown:   {best.max_drawdown:+.1%}")
        logger.info(f"  Total Return:   {best.total_return:+.1%}")
        logger.info(f"  Win Rate:       {best.win_rate:.1%}")
        logger.info(f"  Profit Factor:  {best.profit_factor:.2f}")
        logger.info(f"  Total Trades:   {best.total_trades}")
        logger.info(f"  Promising:      {'✅ YES' if best.is_promising else '❌ NO'}")
        logger.info("")
        logger.info("PER-SIGNAL IC (information coefficient — correlation with forward returns):")
        logger.info("  (green ✅ = predictive, red = contrarian, blank = no edge)")
        for name, ic in sorted(best.per_signal_ic.items(), key=lambda x: abs(x[1]), reverse=True):
            bar_len = max(1, int(abs(ic) / 0.01))
            bar = "█" * bar_len
            sign = "+" if ic > 0 else "-"
            flag = "✅" if abs(ic) > 0.03 else ("⚠️" if abs(ic) > 0.01 else "")
            logger.info(f"  {name:25s} {sign}{abs(ic):.4f}  {bar} {flag}")
        logger.info("")
        logger.info("BEST PARAMETERS:")
        for k, v in sorted(best.params.items()):
            logger.info(f"  {k:35s} = {v}")
    else:
        logger.warning("No valid results — check data or signals.")

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Results saved to: {results_dir}/")
    logger.info(f"  equity_curves.png     — equity curves + Sharpe bar chart")
    logger.info(f"  signal_ic_heatmap.png — per-signal IC heatmap")
    logger.info(f"  all_results.json      — all {len(all_results)} runs (JSON)")


if __name__ == "__main__":
    main()
