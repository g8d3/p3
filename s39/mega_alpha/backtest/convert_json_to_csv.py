"""Convert legacy backtest JSON results to append-only CSV."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


IC_COLUMNS = [
    "IC_momentum",
    "IC_mean_reversion",
    "IC_funding_rate",
    "IC_volatility_breakout",
    "IC_rsi_divergence",
    "IC_volume_imbalance",
    "IC_bb_width",
    "IC_funding_acceleration",
    "IC_cross_coin",
]

PARAM_COLUMNS = [
    "momentum_windows",
    "mean_reversion_ma_periods",
    "funding_extreme_threshold",
    "bb_period",
    "bb_std",
    "rsi_period",
    "volume_ma_period",
    "cross_coin_lead_window",
    "combination_min_history",
    "regression_lookback",
    "vol_lookback",
    "rebalance_interval",
    "kelly_fraction",
    "max_fraction",
    "min_edge",
    "position_sizing",
    "fixed_fraction",
    "stop_loss_pct",
    "take_profit_pct",
    "max_leverage",
]


def build_columns() -> list[str]:
    return [
        "run_id",
        "timestamp",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "total_return",
        "win_rate",
        "profit_factor",
        "total_trades",
        "avg_trade_pnl",
        "combination_ir",
        "is_promising",
        "test_sharpe_ratio",
        "test_sortino_ratio",
        "test_max_drawdown",
        "test_total_return",
        "test_win_rate",
        "test_total_trades",
        "test_profit_factor",
        *PARAM_COLUMNS,
        *IC_COLUMNS,
    ]


def json_or_value(value):
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value)
    return value


def convert_run(result: dict) -> dict:
    row = {column: math.nan for column in build_columns()}

    row["run_id"] = result.get("run_id")
    row["timestamp"] = result.get("timestamp")
    row["sharpe_ratio"] = result.get("sharpe")
    row["max_drawdown"] = result.get("max_drawdown")
    row["total_return"] = result.get("total_return")
    row["win_rate"] = result.get("win_rate")
    row["profit_factor"] = result.get("profit_factor")
    row["total_trades"] = result.get("total_trades")
    row["avg_trade_pnl"] = math.nan
    row["combination_ir"] = math.nan
    row["is_promising"] = result.get("is_promising")

    params = result.get("params", {})
    for name in PARAM_COLUMNS:
        row[name] = json_or_value(params.get(name))

    per_signal_ic = result.get("per_signal_ic", {})
    signal_map = {
        "momentum": "IC_momentum",
        "mean_reversion": "IC_mean_reversion",
        "funding_rate": "IC_funding_rate",
        "volatility_breakout": "IC_volatility_breakout",
        "rsi_divergence": "IC_rsi_divergence",
        "volume_imbalance": "IC_volume_imbalance",
        "bb_width": "IC_bb_width",
        "funding_acceleration": "IC_funding_acceleration",
        "cross_coin": "IC_cross_coin",
    }
    for old_name, new_name in signal_map.items():
        row[new_name] = per_signal_ic.get(old_name, math.nan)

    return row


def main() -> None:
    results_path = ROOT / "backtest_results" / "all_results.json"
    output_path = ROOT / "backtest_results" / "all_results.csv"

    with results_path.open() as f:
        results = json.load(f)

    columns = build_columns()
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for result in results:
            writer.writerow(convert_run(result))

    print(f"Converted {len(results)} runs to CSV. Columns: {len(columns)}")


if __name__ == "__main__":
    main()
