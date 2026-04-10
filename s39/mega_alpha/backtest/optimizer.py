"""Parameter optimizer: continuous search over strategy parameter space.

Uses a two-phase approach:
1. Broad random search to explore the parameter space
2. Bayesian-style refinement around promising regions

Keeps searching until it finds a configuration that meets the
"promising" threshold (Sharpe > 0.5, max DD < 30%, etc.).
"""

import csv
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

from backtest.engine import BacktestEngine, BacktestResult


# ─── Parameter Space Definition ───

PARAM_SPACE = {
    # Signal params
    "momentum_windows": {
        "type": "choice",
        "options": [
            [1, 3, 7, 14, 30],
            [1, 5, 10, 20],
            [3, 7, 14, 30],
            [1, 2, 5, 10, 20, 30],
            [5, 10, 20],
            [1, 3, 5],
            [7, 14, 30],
        ],
    },
    "mean_reversion_ma_periods": {
        "type": "choice",
        "options": [
            [20, 50],
            [10, 30],
            [20, 40, 60],
            [15, 30, 50],
            [10, 20],
            [30, 60],
        ],
    },
    "funding_extreme_threshold": {
        "type": "float",
        "low": 0.0002,
        "high": 0.002,
    },
    "bb_period": {
        "type": "int",
        "low": 10,
        "high": 30,
    },
    "bb_std": {
        "type": "float",
        "low": 1.5,
        "high": 3.0,
    },
    # RSI Divergence params
    "rsi_period": {
        "type": "int",
        "low": 7,
        "high": 21,
    },
    # Volume Imbalance params
    "volume_ma_period": {
        "type": "int",
        "low": 10,
        "high": 40,
    },
    # Cross-Coin lead window
    "cross_coin_lead_window": {
        "type": "int",
        "low": 1,
        "high": 12,
    },
    # Engine params
    "combination_min_history": {
        "type": "int",
        "low": 5,
        "high": 40,
    },
    "regression_lookback": {
        "type": "int",
        "low": 10,
        "high": 40,
    },
    "vol_lookback": {
        "type": "int",
        "low": 20,
        "high": 100,
    },
    "rebalance_interval": {
        "type": "int",
        "low": 1,
        "high": 12,
    },
    # Kelly params
    "kelly_fraction": {
        "type": "float",
        "low": 0.1,
        "high": 1.0,
    },
    "max_fraction": {
        "type": "float",
        "low": 0.05,
        "high": 0.50,
    },
    "min_edge": {
        "type": "float",
        "low": 0.005,
        "high": 0.10,
    },
    # Position sizing mode — always "fixed" (Kelly produces near-zero positions when IR≈0)
    "position_sizing": {
        "type": "choice",
        "options": ["fixed"],
    },
    "fixed_fraction": {
        "type": "float",
        "low": 0.02,
        "high": 0.30,
    },
    # Risk params
    "stop_loss_pct": {
        "type": "float",
        "low": 0.01,
        "high": 0.08,
    },
    "take_profit_pct": {
        "type": "float",
        "low": 0.02,
        "high": 0.15,
    },
    "max_leverage": {
        "type": "float",
        "low": 1.0,
        "high": 5.0,
    },
}


@dataclass
class SearchResult:
    """A single search result."""

    run_id: int
    params: dict
    sharpe: float
    sortino: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    profit_factor: float
    avg_trade_pnl: float
    combination_ir: float
    per_signal_ic: dict[str, float]
    train_sharpe: float
    test_sharpe: Optional[float]
    test_sortino: Optional[float]
    test_max_drawdown: Optional[float]
    test_total_return: Optional[float]
    test_win_rate: Optional[float]
    test_total_trades: Optional[int]
    test_profit_factor: Optional[float]
    is_promising: bool
    timestamp: str

    @property
    def train_sharre(self) -> float:
        """Backward-compatible alias for the common typo."""
        return self.train_sharpe


class ParameterOptimizer:
    """Continuous parameter optimizer for the trading system.

    Runs backtests with different parameter combinations, tracks results,
    and refines the search around promising regions.
    """

    def __init__(
        self,
        engine: BacktestEngine,
        results_dir: str = "backtest_results",
        target_sharpe: float = 0.5,
        target_max_dd: float = 0.30,
        min_trades: int = 10,
        max_iterations: int = 1000,
        refinement_top_k: int = 10,
        refinement_radius: float = 0.2,  # 20% perturbation around best params
        train_end_pct: float = 0.70,
    ):
        self.engine = engine
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.target_sharpe = target_sharpe
        self.target_max_dd = target_max_dd
        self.min_trades = min_trades
        self.max_iterations = max_iterations
        self.refinement_top_k = refinement_top_k
        self.refinement_radius = refinement_radius
        self.train_end_pct = train_end_pct

        self.results: list[SearchResult] = []
        self.best_result: Optional[SearchResult] = None
        self._run_counter = 0
        self._phase = "exploration"  # "exploration" or "refinement"

        csv_path = self.results_dir / "all_results.csv"
        if csv_path.exists():
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            if rows:
                self._run_counter = max(int(r["run_id"]) for r in rows)
                logger.info(f"Resuming from run #{self._run_counter + 1} (found {len(rows)} existing CSV rows)")
                self.results = [self._search_result_from_csv_row(row) for row in rows]
                self.best_result = max(self.results, key=lambda r: r.sharpe)

    def search(self) -> Optional[SearchResult]:
        """Run the continuous search loop.

        Alternates between:
        - Exploration: random sampling from the full parameter space
        - Refinement: local search around the best results found so far

        Stops when:
        - A promising configuration is found (Sharpe > target, DD < target)
        - Max iterations reached
        """
        logger.info("=" * 60)
        logger.info("STARTING CONTINUOUS PARAMETER SEARCH")
        logger.info(f"Target: Sharpe > {self.target_sharpe}, Max DD < {self.target_max_dd:.0%}")
        logger.info(f"Max iterations: {self.max_iterations}")
        logger.info("=" * 60)

        start_time = time.time()

        for iteration in range(self.max_iterations):
            # Decide phase
            if len(self.results) >= 20 and self._phase == "exploration":
                # Check if we should switch to refinement
                promising = [r for r in self.results if r.is_promising]
                if promising:
                    self._phase = "refinement"
                    logger.info(f"Switching to REFINEMENT phase (found {len(promising)} promising configs)")

            # Generate parameters
            if self._phase == "refinement":
                params = self._sample_refinement()
            else:
                params = self._sample_random()

            # Run backtest
            self._run_counter += 1
            logger.info(f"Run #{self._run_counter} ({self._phase}): testing params...")

            try:
                if self.train_end_pct < 1.0:
                    result, oob_result = self.engine.run_oos(
                        params,
                        train_end_pct=self.train_end_pct,
                    )
                    search_result = self._to_search_result(result, oob_result)
                else:
                    result = self.engine.run(params)
                    search_result = self._to_search_result(result)
                self.results.append(search_result)
                self._append_result_csv(search_result)

                # Log result
                logger.info(
                    f"  Sharpe={search_result.sharpe:.3f}, "
                    f"DD={search_result.max_drawdown:.1%}, "
                    f"Return={search_result.total_return:.1%}, "
                    f"Trades={search_result.total_trades}, "
                    f"WinRate={search_result.win_rate:.1%}, "
                    f"PF={search_result.profit_factor:.2f}, "
                    f"Promising={'YES' if search_result.is_promising else 'no'}"
                )

                # Log per-signal IC
                ic_str = ", ".join(f"{k}={v:.3f}" for k, v in search_result.per_signal_ic.items())
                logger.info(f"  ICs: {ic_str}")

                # Update best
                if self.best_result is None or search_result.sharpe > self.best_result.sharpe:
                    self.best_result = search_result
                    logger.info(f"  ★ NEW BEST: Sharpe={search_result.sharpe:.3f}")

                # Check if we found a winner
                if search_result.is_promising:
                    elapsed = time.time() - start_time
                    logger.info("=" * 60)
                    logger.info("PROMISING CONFIGURATION FOUND!")
                    logger.info(f"  Sharpe: {search_result.sharpe:.3f}")
                    logger.info(f"  Max DD: {search_result.max_drawdown:.1%}")
                    logger.info(f"  Return: {search_result.total_return:.1%}")
                    logger.info(f"  Trades: {search_result.total_trades}")
                    logger.info(f"  Win Rate: {search_result.win_rate:.1%}")
                    logger.info(f"  Profit Factor: {search_result.profit_factor:.2f}")
                    if search_result.test_sharpe is not None:
                        logger.info(
                            f"  OOS Sharpe={search_result.test_sharpe:.3f}, "
                            f"DD={search_result.test_max_drawdown:.1%}, "
                            f"Return={search_result.test_total_return:.1%}, "
                            f"Trades={search_result.test_total_trades}, "
                            f"WinRate={search_result.test_win_rate:.1%}, "
                            f"PF={search_result.test_profit_factor:.2f}"
                        )
                    logger.info(f"  Params: {json.dumps(search_result.params, indent=2)}")
                    logger.info(f"  Time: {elapsed:.0f}s, Iterations: {self._run_counter}")
                    logger.info("=" * 60)

                    # Save the promising result
                    self._save_result(search_result)

                    # Keep searching — don't stop on first promising result.
                    # Only stop if we find an exceptionally strong config
                    # (Sharpe > 2x target AND meaningful return AND real drawdown)
                    if (search_result.sharpe > self.target_sharpe * 2
                            and abs(search_result.total_return) > 0.05
                            and search_result.max_drawdown > 0.01):
                        logger.info("Found exceptionally strong config with real edge. Stopping search.")
                        return search_result

            except Exception as e:
                logger.error(f"Backtest failed: {e}")
                continue

            # Periodic save
            if self._run_counter % 10 == 0:
                self._save_all_results()

        # Final report
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"SEARCH COMPLETE: {self._run_counter} iterations in {elapsed:.0f}s")
        if self.best_result:
            logger.info(f"Best Sharpe: {self.best_result.sharpe:.3f}")
            logger.info(f"Best DD: {self.best_result.max_drawdown:.1%}")
            logger.info(f"Best Return: {self.best_result.total_return:.1%}")
            logger.info(f"Promising: {self.best_result.is_promising}")
        else:
            logger.info("No valid results found.")
        logger.info("=" * 60)

        self._save_all_results()
        return self.best_result

    def _sample_random(self) -> dict:
        """Sample a random parameter configuration from the full space."""
        params = {}
        for name, spec in PARAM_SPACE.items():
            if spec["type"] == "float":
                params[name] = float(np.random.uniform(spec["low"], spec["high"]))
            elif spec["type"] == "int":
                params[name] = int(np.random.randint(spec["low"], spec["high"] + 1))
            elif spec["type"] == "choice":
                params[name] = spec["options"][np.random.randint(len(spec["options"]))]
        return params

    def _sample_refinement(self) -> dict:
        """Sample around the best results found so far.

        Takes the top-K results and perturbs their parameters.
        """
        # Get top results by Sharpe
        sorted_results = sorted(self.results, key=lambda r: r.sharpe, reverse=True)
        top = sorted_results[:self.refinement_top_k]

        # Pick a random top result to perturb
        base = top[np.random.randint(len(top))]
        params = dict(base.params)

        # Perturb each numeric parameter
        for name, spec in PARAM_SPACE.items():
            if spec["type"] == "float":
                current = params.get(name, (spec["low"] + spec["high"]) / 2)
                delta = (spec["high"] - spec["low"]) * self.refinement_radius
                new_val = current + np.random.uniform(-delta, delta)
                params[name] = float(np.clip(new_val, spec["low"], spec["high"]))
            elif spec["type"] == "int":
                current = params.get(name, (spec["low"] + spec["high"]) // 2)
                delta = max(1, int((spec["high"] - spec["low"]) * self.refinement_radius))
                new_val = current + np.random.randint(-delta, delta + 1)
                params[name] = int(np.clip(new_val, spec["low"], spec["high"]))
            elif spec["type"] == "choice":
                # 70% keep same, 30% try different
                if np.random.random() < 0.3:
                    params[name] = spec["options"][np.random.randint(len(spec["options"]))]

        return params

    def _to_search_result(
        self,
        result: BacktestResult,
        oob_result: Optional[BacktestResult] = None,
    ) -> SearchResult:
        """Convert a BacktestResult to a SearchResult."""
        return SearchResult(
            run_id=self._run_counter,
            params=result.params,
            sharpe=result.sharpe_ratio,
            sortino=result.sortino_ratio,
            max_drawdown=result.max_drawdown,
            total_return=result.total_return,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            profit_factor=result.profit_factor,
            avg_trade_pnl=result.avg_trade_pnl,
            combination_ir=result.combination_ir,
            per_signal_ic=result.per_signal_ic,
            train_sharpe=result.sharpe_ratio,
            test_sharpe=oob_result.sharpe_ratio if oob_result is not None else None,
            test_sortino=oob_result.sortino_ratio if oob_result is not None else None,
            test_max_drawdown=oob_result.max_drawdown if oob_result is not None else None,
            test_total_return=oob_result.total_return if oob_result is not None else None,
            test_win_rate=oob_result.win_rate if oob_result is not None else None,
            test_total_trades=oob_result.total_trades if oob_result is not None else None,
            test_profit_factor=oob_result.profit_factor if oob_result is not None else None,
            is_promising=result.is_promising,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _save_result(self, result: SearchResult) -> None:
        """Save a single promising result."""
        path = self.results_dir / f"promising_{result.run_id}.json"
        with open(path, "w") as f:
            json.dump({
                "run_id": result.run_id,
                "params": result.params,
                "sharpe": result.sharpe,
                "sortino": result.sortino,
                "max_drawdown": result.max_drawdown,
                "total_return": result.total_return,
                "win_rate": result.win_rate,
                "total_trades": result.total_trades,
                "profit_factor": result.profit_factor,
                "avg_trade_pnl": result.avg_trade_pnl,
                "combination_ir": result.combination_ir,
                "per_signal_ic": result.per_signal_ic,
                "train_sharpe": result.train_sharpe,
                "test_sharpe": result.test_sharpe,
                "test_sortino": result.test_sortino,
                "test_max_drawdown": result.test_max_drawdown,
                "test_total_return": result.test_total_return,
                "test_win_rate": result.test_win_rate,
                "test_total_trades": result.test_total_trades,
                "test_profit_factor": result.test_profit_factor,
                "timestamp": result.timestamp,
            }, f, indent=2)
        logger.info(f"Saved promising result to {path}")

    def _save_all_results(self) -> None:
        """Save all search results."""
        path = self.results_dir / "all_results.json"
        existing: list[dict] = []
        if path.exists():
            with open(path) as f:
                existing = json.load(f)

        all_runs: dict[int, dict] = {}
        for run in existing:
            all_runs[int(run["run_id"])] = run
        for r in self.results:
            all_runs[r.run_id] = self._search_result_to_dict(r)

        data = list(all_runs.values())
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(data)} results to {path}")

    def _search_result_to_dict(self, result: SearchResult) -> dict:
        return {
            "run_id": result.run_id,
            "params": result.params,
            "sharpe": result.sharpe,
            "sortino": result.sortino,
            "max_drawdown": result.max_drawdown,
            "total_return": result.total_return,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "profit_factor": result.profit_factor,
            "avg_trade_pnl": result.avg_trade_pnl,
            "combination_ir": result.combination_ir,
            "per_signal_ic": result.per_signal_ic,
            "train_sharpe": result.train_sharpe,
            "test_sharpe": result.test_sharpe,
            "test_sortino": result.test_sortino,
            "test_max_drawdown": result.test_max_drawdown,
            "test_total_return": result.test_total_return,
            "test_win_rate": result.test_win_rate,
            "test_total_trades": result.test_total_trades,
            "test_profit_factor": result.test_profit_factor,
            "is_promising": result.is_promising,
            "timestamp": result.timestamp,
        }

    def _search_result_from_csv_row(self, row: dict[str, str]) -> SearchResult:
        import math

        def is_missing(v) -> bool:
            if v is None:
                return True
            s = str(v).strip()
            return s in ("", "None", "nan", "NaN") or (isinstance(v, float) and math.isnan(v))

        def parse_optional_float(value: str) -> Optional[float]:
            if is_missing(value):
                return None
            return float(value)

        def parse_optional_int(value: str) -> Optional[int]:
            if is_missing(value):
                return None
            return int(float(value))

        def parse_bool(value: str) -> bool:
            return str(value).strip().lower() in {"true", "1", "yes"}

        params = {}
        for name, spec in PARAM_SPACE.items():
            value = row.get(name)
            if spec["type"] == "choice" and value is not None:
                if value.startswith("["):
                    params[name] = json.loads(value)
                else:
                    params[name] = value
            elif spec["type"] == "int" and value not in (None, "", "None"):
                params[name] = int(float(value))
            elif spec["type"] == "float" and value not in (None, "", "None"):
                params[name] = float(value)
            else:
                params[name] = value

        ic = {
            "momentum": float(row.get("IC_momentum", 0.0) or 0.0),
            "mean_reversion": float(row.get("IC_mean_reversion", 0.0) or 0.0),
            "funding_rate": float(row.get("IC_funding_rate", 0.0) or 0.0),
            "volatility_breakout": float(row.get("IC_volatility_breakout", 0.0) or 0.0),
            "rsi_divergence": float(row.get("IC_rsi_divergence", 0.0) or 0.0),
            "volume_imbalance": float(row.get("IC_volume_imbalance", 0.0) or 0.0),
            "bb_width": float(row.get("IC_bb_width", 0.0) or 0.0),
            "funding_acceleration": float(row.get("IC_funding_acceleration", 0.0) or 0.0),
            "cross_coin": float(row.get("IC_cross_coin", 0.0) or 0.0),
        }

        return SearchResult(
            run_id=int(row["run_id"]),
            params=params,
            sharpe=float(row["sharpe_ratio"]),
            sortino=float(row["sortino_ratio"]),
            max_drawdown=float(row["max_drawdown"]),
            total_return=float(row["total_return"]),
            win_rate=float(row["win_rate"]),
            total_trades=int(float(row["total_trades"])),
            profit_factor=float(row["profit_factor"]),
            avg_trade_pnl=float(row["avg_trade_pnl"]),
            combination_ir=float(row["combination_ir"]),
            per_signal_ic=ic,
            train_sharpe=float(row["sharpe_ratio"]),
            test_sharpe=parse_optional_float(row.get("test_sharpe_ratio")),
            test_sortino=parse_optional_float(row.get("test_sortino_ratio")),
            test_max_drawdown=parse_optional_float(row.get("test_max_drawdown")),
            test_total_return=parse_optional_float(row.get("test_total_return")),
            test_win_rate=parse_optional_float(row.get("test_win_rate")),
            test_total_trades=parse_optional_int(row.get("test_total_trades")),
            test_profit_factor=parse_optional_float(row.get("test_profit_factor")),
            is_promising=parse_bool(row.get("is_promising", "False")),
            timestamp=row.get("timestamp", ""),
        )

    def _get_csv_columns(self) -> list[str]:
        """Return the fixed CSV column order."""
        columns = [
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
        ]
        columns.extend(PARAM_SPACE.keys())
        columns.extend([
            "IC_momentum",
            "IC_mean_reversion",
            "IC_funding_rate",
            "IC_volatility_breakout",
            "IC_rsi_divergence",
            "IC_volume_imbalance",
            "IC_bb_width",
            "IC_funding_acceleration",
            "IC_cross_coin",
        ])
        return columns

    def _append_result_csv(self, result: SearchResult) -> None:
        """Append a single result row to the CSV store."""
        path = self.results_dir / "all_results.csv"
        columns = self._get_csv_columns()
        row = {
            "run_id": result.run_id,
            "timestamp": datetime.now().isoformat(),
            "sharpe_ratio": result.sharpe,
            "sortino_ratio": result.sortino,
            "max_drawdown": result.max_drawdown,
            "total_return": result.total_return,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "total_trades": result.total_trades,
            "avg_trade_pnl": result.avg_trade_pnl,
            "combination_ir": result.combination_ir,
            "is_promising": result.is_promising,
            "test_sharpe_ratio": result.test_sharpe,
            "test_sortino_ratio": result.test_sortino,
            "test_max_drawdown": result.test_max_drawdown,
            "test_total_return": result.test_total_return,
            "test_win_rate": result.test_win_rate,
            "test_total_trades": result.test_total_trades,
            "test_profit_factor": result.test_profit_factor,
        }

        # Flatten params.
        for name in PARAM_SPACE.keys():
            value = result.params.get(name)
            if isinstance(value, (list, tuple)):
                row[name] = json.dumps(value)
            else:
                row[name] = value

        # Flatten per-signal ICs.
        ic_columns = {
            "IC_momentum": result.per_signal_ic.get("momentum", 0.0),
            "IC_mean_reversion": result.per_signal_ic.get("mean_reversion", 0.0),
            "IC_funding_rate": result.per_signal_ic.get("funding_rate", 0.0),
            "IC_volatility_breakout": result.per_signal_ic.get("volatility_breakout", 0.0),
            "IC_rsi_divergence": result.per_signal_ic.get("rsi_divergence", 0.0),
            "IC_volume_imbalance": result.per_signal_ic.get("volume_imbalance", 0.0),
            "IC_bb_width": result.per_signal_ic.get("bb_width", 0.0),
            "IC_funding_acceleration": result.per_signal_ic.get("funding_acceleration", 0.0),
            "IC_cross_coin": result.per_signal_ic.get("cross_coin", 0.0),
        }
        row.update(ic_columns)

        file_exists = path.exists() and path.stat().st_size > 0
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
