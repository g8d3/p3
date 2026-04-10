"""Backtest engine: walk-forward replay of the signal + combination + Kelly pipeline.

Replays historical candle data through the full trading system, tracking
equity curve, per-signal IC, and trade-by-trade results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from signals.base import Signal, SignalOutput
from signals.registry import SignalRegistry
from engine.combination import CombinationEngine, CombinationResult
from engine.kelly import KellySizer, PositionSize
from engine.portfolio import Portfolio, Position


@dataclass
class TradeRecord:
    """Record of a single trade in the backtest."""

    timestamp: datetime
    coin: str
    action: str  # "open_long", "open_short", "close"
    price: float
    size_usd: float
    pnl: float = 0.0
    combined_signal: float = 0.0
    confidence: float = 0.0


@dataclass
class BacktestResult:
    """Complete result of a backtest run."""

    equity_curve: pd.Series
    trades: list[TradeRecord]
    final_equity: float
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # in bars
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_pnl: float
    per_signal_ic: dict[str, float]
    per_signal_contribution: dict[str, float]
    combination_ir: float
    params: dict  # The parameters used for this run

    @property
    def is_promising(self) -> bool:
        """Quick check if this result looks promising enough to investigate.

        Requires meaningful trading activity and returns, not just
        a lucky few trades with tiny positions.
        """
        return (
            self.sharpe_ratio > 0.5
            and self.max_drawdown < 0.30
            and self.total_trades >= 20
            and self.win_rate > 0.40
            and abs(self.total_return) > 0.01  # At least 1% absolute return
            and self.profit_factor > 1.0
        )


class BacktestEngine:
    """Walk-forward backtest engine.

    Replays historical data bar-by-bar through the full pipeline:
    data → signals → combination → kelly → portfolio → trades

    Supports configurable parameters for optimization.
    """

    def __init__(
        self,
        data: dict[str, pd.DataFrame],
        initial_capital: float = 10000.0,
        commission_bps: float = 5.0,  # 5 bps = 0.05% per trade
        slippage_bps: float = 3.0,  # 3 bps slippage
    ):
        """
        Args:
            data: Dict mapping coin -> DataFrame with OHLCV + extras.
                  Must have columns: open, high, low, close, volume
                  Optional: funding_rate, open_interest
            initial_capital: Starting capital.
            commission_bps: Commission in basis points per trade.
            slippage_bps: Slippage in basis points per trade.
        """
        self.data = data
        self.initial_capital = initial_capital
        self.commission_rate = commission_bps / 10000
        self.slippage_rate = slippage_bps / 10000

        # Align all coins to the same time index
        self._align_data()

    def _align_data(self) -> None:
        """Align all coin DataFrames to a common time index."""
        if not self.data:
            self.dates = pd.DatetimeIndex([])
            return

        # Find common date range
        all_indices = [df.index for df in self.data.values()]
        common_idx = all_indices[0]
        for idx in all_indices[1:]:
            common_idx = common_idx.intersection(idx)

        self.dates = common_idx.sort_values()
        for coin in self.data:
            self.data[coin] = self.data[coin].reindex(common_idx).ffill().bfill()

    def run(
        self,
        params: dict,
        verbose: bool = False,
        signals: list[Signal] | None = None,
    ) -> BacktestResult:
        """Run a backtest with the given parameters.

        Args:
            params: Dict of parameters controlling the backtest.
                Signal params:
                    momentum_windows: list[int]
                    mean_reversion_ma_periods: list[int]
                    funding_extreme_threshold: float
                    bb_period: int
                    bb_std: float
                    oi_change_window: int
                Engine params:
                    combination_min_history: int
                    regression_lookback: int
                    vol_lookback: int
                Kelly params:
                    kelly_fraction: float (0.5 = half-Kelly)
                    max_fraction: float
                    min_edge: float
                Risk params:
                    stop_loss_pct: float
                    take_profit_pct: float
                    max_leverage: float
            verbose: Print progress.

        Returns:
            BacktestResult with full performance metrics.
        """
        # ─── Build signals from params ───
        signals = signals or self._build_signals(params)
        if not signals:
            return self._empty_result(params)

        # ─── Build engine components ───
        combination_engine = CombinationEngine(
            min_history=params.get("combination_min_history", 20),
            regression_lookback=params.get("regression_lookback", 20),
            vol_lookback=params.get("vol_lookback", 60),
        )

        kelly_sizer = KellySizer(
            capital=self.initial_capital,
            max_fraction=params.get("max_fraction", 0.25),
            min_edge=params.get("min_edge", 0.02),
            kelly_fraction=params.get("kelly_fraction", 0.5),
        )

        portfolio = Portfolio(
            initial_capital=self.initial_capital,
            max_leverage=params.get("max_leverage", 3.0),
        )

        stop_loss_pct = params.get("stop_loss_pct", 0.03)
        take_profit_pct = params.get("take_profit_pct", 0.06)

        # ─── Walk forward ───
        equity_curve = []
        trades: list[TradeRecord] = []
        signal_values: dict[str, list[float]] = {s.name: [] for s in signals}
        forward_returns: dict[str, list[float]] = {s.name: [] for s in signals}
        combination_values: list[float] = []

        coins = list(self.data.keys())
        warmup = params.get("warmup_bars", 50)  # Skip first N bars for indicator warmup
        rebalance_interval = params.get("rebalance_interval", 4)  # Rebalance every N bars

        # Track last signal computation for rebalance_interval
        last_signal_bar = -rebalance_interval  # Force compute on first bar
        cached_combination = None
        cached_position_size = None
        signal_realized_returns: dict[str, list[float]] = {signal.name: [] for signal in signals}

        for t_idx in range(warmup, len(self.dates)):
            timestamp = self.dates[t_idx]

            # Build data window up to current bar (limit to last 200 bars for speed)
            max_window = params.get("signal_window", 200)
            start_idx = max(0, t_idx + 1 - max_window)
            window_data = {}
            for coin, df in self.data.items():
                window_data[coin] = df.iloc[start_idx:t_idx]

            # Current prices
            prices = {}
            for coin, df in self.data.items():
                if t_idx < len(df):
                    prices[coin] = df["close"].iloc[t_idx]

            # ─── Compute signals (only on rebalance bars) ───
            should_rebalance = (t_idx - last_signal_bar) >= rebalance_interval

            if should_rebalance:
                last_signal_bar = t_idx

                outputs = []
                for signal in signals:
                    try:
                        out = signal.compute(window_data)
                        outputs.append(out)
                        signal_values[signal.name].append(out.value)
                    except Exception:
                        outputs.append(SignalOutput(
                            name=signal.name, value=0.0, timestamp=timestamp
                        ))
                        signal_values[signal.name].append(0.0)

                # ─── Combine signals ───
                combination = combination_engine.combine(signals, outputs)
                combination_values.append(combination.combined_value)

                # ─── Size position ───
                sizing_mode = params.get("position_sizing", "kelly")

                if sizing_mode == "fixed":
                    # Fixed-fraction sizing: ignore Kelly, use signal strength directly
                    # This lets us evaluate signal quality without Kelly conservatism
                    direction = 1 if combination.combined_value > 0 else -1
                    edge = abs(combination.combined_value)
                    fixed_frac = params.get("fixed_fraction", 0.10)  # 10% of capital per coin
                    # Scale by signal strength: stronger signal → bigger position
                    scale = min(edge / 0.1, 1.0)  # Full size at edge=0.1, linear ramp
                    per_coin_usd = portfolio.state.capital * fixed_frac * scale / len(coins)
                    position_size = PositionSize(
                        fraction=fixed_frac * scale,
                        size_usd=per_coin_usd * len(coins),
                        direction=direction if edge >= params.get("min_edge", 0.005) else 0,
                        kelly_fraction=0.0,
                        cv_edge=0.0,
                        confidence=edge,
                    )
                else:
                    position_size = kelly_sizer.size(combination)

                cached_combination = combination
                cached_position_size = position_size
            else:
                combination = cached_combination
                position_size = cached_position_size

            # ─── Execute trades ───
            for coin in coins:
                if coin not in prices:
                    continue

                price = prices[coin]
                # Apply slippage
                if position_size.direction > 0:
                    exec_price = price * (1 + self.slippage_rate)
                elif position_size.direction < 0:
                    exec_price = price * (1 - self.slippage_rate)
                else:
                    exec_price = price

                existing = portfolio.get_position(coin)
                coin_size = PositionSize(
                    fraction=position_size.fraction / len(coins),
                    size_usd=position_size.size_usd / len(coins),
                    direction=position_size.direction,
                    kelly_fraction=position_size.kelly_fraction,
                    cv_edge=position_size.cv_edge,
                    confidence=position_size.confidence,
                )

                if existing:
                    # Check stop loss / take profit
                    sl_hit = False
                    tp_hit = False
                    if existing.is_long:
                        if existing.stop_loss and price <= existing.stop_loss:
                            sl_hit = True
                        if existing.take_profit and price >= existing.take_profit:
                            tp_hit = True
                    else:
                        if existing.stop_loss and price >= existing.stop_loss:
                            sl_hit = True
                        if existing.take_profit and price <= existing.take_profit:
                            tp_hit = True

                    if sl_hit or tp_hit:
                        pnl = portfolio.close_position(coin, exec_price)
                        commission = existing.size_usd * self.commission_rate
                        portfolio.state.capital -= commission
                        kelly_sizer.update_capital(portfolio.state.capital)
                        trades.append(TradeRecord(
                            timestamp=timestamp, coin=coin,
                            action="close_sl" if sl_hit else "close_tp",
                            price=exec_price, size_usd=existing.size_usd,
                            pnl=pnl - commission,
                            combined_signal=combination.combined_value,
                            confidence=position_size.confidence,
                        ))

                    # Direction change → close and reopen
                    elif existing.direction != coin_size.direction and coin_size.direction != 0:
                        pnl = portfolio.close_position(coin, exec_price)
                        commission = existing.size_usd * self.commission_rate
                        portfolio.state.capital -= commission
                        trades.append(TradeRecord(
                            timestamp=timestamp, coin=coin, action="close",
                            price=exec_price, size_usd=existing.size_usd,
                            pnl=pnl - commission,
                            combined_signal=combination.combined_value,
                            confidence=position_size.confidence,
                        ))
                        # Open new
                        self._open_position(
                            portfolio, kelly_sizer, coin, coin_size,
                            exec_price, stop_loss_pct, take_profit_pct,
                            timestamp, combination, trades
                        )

                    elif coin_size.direction == 0:
                        # Signal neutral → close
                        pnl = portfolio.close_position(coin, exec_price)
                        commission = existing.size_usd * self.commission_rate
                        portfolio.state.capital -= commission
                        trades.append(TradeRecord(
                            timestamp=timestamp, coin=coin, action="close",
                            price=exec_price, size_usd=existing.size_usd,
                            pnl=pnl - commission,
                            combined_signal=combination.combined_value,
                            confidence=position_size.confidence,
                        ))

                else:
                    # No position → open if signal is strong enough
                    if coin_size.direction != 0 and coin_size.size_usd > 0:
                        self._open_position(
                            portfolio, kelly_sizer, coin, coin_size,
                            exec_price, stop_loss_pct, take_profit_pct,
                            timestamp, combination, trades
                        )

            # ─── Update unrealized PnL ───
            portfolio.update_unrealized_pnl(prices)

            # ─── Record equity ───
            equity_curve.append(portfolio.state.total_equity)

            # ─── Feed returns back to signals ───
            if t_idx > warmup and should_rebalance:
                coin_returns = []
                for coin in coins:
                    if coin in self.data:
                        prev_price = self.data[coin]["close"].iloc[t_idx - 1]
                        curr_price = self.data[coin]["close"].iloc[t_idx]
                        if prev_price > 0:
                            coin_returns.append((curr_price - prev_price) / prev_price)

                if coin_returns:
                    avg_coin_return = float(np.mean(coin_returns))
                    for signal, output in zip(signals, outputs):
                        if output.value > 0:
                            realized_return = avg_coin_return
                        elif output.value < 0:
                            realized_return = -avg_coin_return
                        else:
                            realized_return = 0.0

                        signal_realized_returns[signal.name].append(realized_return)
                        signal.record_return(realized_return)

            if verbose and t_idx % 500 == 0:
                logger.info(f"Bar {t_idx}/{len(self.dates)}: equity=${portfolio.state.total_equity:.2f}")

        # ─── Close remaining positions ───
        for coin in list(portfolio.state.positions.keys()):
            if coin in prices:
                pnl = portfolio.close_position(coin, prices[coin])
                pos = portfolio.state.positions.get(coin)
                if pos:
                    trades.append(TradeRecord(
                        timestamp=self.dates[-1], coin=coin, action="close_eod",
                        price=prices[coin], size_usd=pos.size_usd, pnl=pnl,
                    ))

        # ─── Compute metrics ───
        return self._compute_metrics(
            equity_curve, trades, signals, signal_values,
            combination_values, params
        )

    def run_oos(
        self,
        params: dict,
        train_end_pct: float = 0.70,
        verbose: bool = False,
    ) -> tuple[BacktestResult, BacktestResult]:
        """Run backtest with proper train/test split.

        First runs backtest on train window (first train_end_pct of data).
        Then evaluates the same params on test window (remaining data).

        Returns:
            (train_result, test_result) tuple
        """
        if train_end_pct >= 1.0 or len(self.dates) < 2:
            result = self.run(params, verbose=verbose)
            return result, result

        split_idx = int(len(self.dates) * train_end_pct)
        split_idx = max(1, min(split_idx, len(self.dates) - 1))

        train_dates = self.dates[:split_idx]
        test_dates = self.dates[split_idx:]

        train_data = {
            coin: df.reindex(train_dates).ffill().bfill().copy()
            for coin, df in self.data.items()
        }
        test_data = {
            coin: df.reindex(test_dates).ffill().bfill().copy()
            for coin, df in self.data.items()
        }

        train_engine = BacktestEngine(
            data=train_data,
            initial_capital=self.initial_capital,
            commission_bps=self.commission_rate * 10000,
            slippage_bps=self.slippage_rate * 10000,
        )
        test_engine = BacktestEngine(
            data=test_data,
            initial_capital=self.initial_capital,
            commission_bps=self.commission_rate * 10000,
            slippage_bps=self.slippage_rate * 10000,
        )

        signals = self._build_signals(params)
        train_result = train_engine.run(params, verbose=verbose, signals=signals)

        for signal in signals:
            signal.reset()

        test_result = test_engine.run(params, verbose=verbose, signals=signals)
        return train_result, test_result

    def _open_position(
        self,
        portfolio: Portfolio,
        kelly_sizer: KellySizer,
        coin: str,
        size: PositionSize,
        price: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        timestamp: datetime,
        combination: CombinationResult,
        trades: list[TradeRecord],
    ) -> None:
        """Open a position and record the trade."""
        if not portfolio.can_open_position(coin, size):
            return

        if size.direction > 0:
            sl = price * (1 - stop_loss_pct)
            tp = price * (1 + take_profit_pct)
        else:
            sl = price * (1 + stop_loss_pct)
            tp = price * (1 - take_profit_pct)

        commission = size.size_usd * self.commission_rate
        portfolio.state.capital -= commission
        kelly_sizer.update_capital(portfolio.state.capital)

        try:
            portfolio.open_position(coin, size, price, stop_loss=sl, take_profit=tp)
            trades.append(TradeRecord(
                timestamp=timestamp, coin=coin,
                action="open_long" if size.direction > 0 else "open_short",
                price=price, size_usd=size.size_usd,
                combined_signal=combination.combined_value,
                confidence=size.confidence,
            ))
        except ValueError:
            pass

    def _build_signals(self, params: dict) -> list[Signal]:
        """Build signal instances from parameters."""
        from signals.momentum import MomentumSignal
        from signals.mean_reversion import MeanReversionSignal
        from signals.funding_rate import FundingRateSignal
        from signals.volatility import VolatilityBreakoutSignal
        from signals.rsi_divergence import RSIDivergenceSignal
        from signals.volume_imbalance import VolumeImbalanceSignal
        from signals.bb_width import BollingerBandWidthSignal
        from signals.funding_acceleration import FundingAccelerationSignal
        from signals.cross_coin import CrossCoinSignal

        signals = []

        # Momentum
        mom = MomentumSignal()
        if "momentum_windows" in params:
            mom.windows = params["momentum_windows"]
            mom.weights = [1.0 / len(mom.windows)] * len(mom.windows)
        signals.append(mom)

        # Mean reversion
        mr = MeanReversionSignal()
        if "mean_reversion_ma_periods" in params:
            mr.ma_periods = params["mean_reversion_ma_periods"]
        signals.append(mr)

        # Funding rate
        fr = FundingRateSignal()
        if "funding_extreme_threshold" in params:
            fr.extreme_threshold = params["funding_extreme_threshold"]
        signals.append(fr)

        # Volatility breakout
        vb = VolatilityBreakoutSignal()
        if "bb_period" in params:
            vb.bb_period = params["bb_period"]
        if "bb_std" in params:
            vb.bb_std = params["bb_std"]
        signals.append(vb)

        # RSI Divergence
        rsi_sig = RSIDivergenceSignal()
        if "rsi_period" in params:
            rsi_sig.rsi_period = params["rsi_period"]
        signals.append(rsi_sig)

        # Volume Imbalance
        vol_sig = VolumeImbalanceSignal()
        if "volume_ma_period" in params:
            vol_sig.volume_ma_period = params["volume_ma_period"]
        signals.append(vol_sig)

        # BB Width
        bbw = BollingerBandWidthSignal()
        if "bb_period" in params:
            bbw.bb_period = params["bb_period"]
        if "bb_std" in params:
            bbw.bb_std = params["bb_std"]
        signals.append(bbw)

        # Funding Acceleration
        signals.append(FundingAccelerationSignal())

        # Cross-Coin
        cross = CrossCoinSignal()
        if self.data and "BTC" in self.data:
            cross.btc_coin = "BTC"
            cross.laggard_coins = [c for c in self.data.keys() if c != "BTC"]
        if "cross_coin_lead_window" in params:
            cross.lead_windows = [params["cross_coin_lead_window"]]
        signals.append(cross)

        return signals

    def _compute_metrics(
        self,
        equity_curve: list[float],
        trades: list[TradeRecord],
        signals: list[Signal],
        signal_values: dict[str, list[float]],
        combination_values: list[float],
        params: dict,
    ) -> BacktestResult:
        """Compute all performance metrics from backtest results."""
        equity = np.array(equity_curve)

        # Returns
        if len(equity) > 1:
            returns = np.diff(equity) / equity[:-1]
        else:
            returns = np.array([])

        # Total return
        total_return = (equity[-1] / equity[0] - 1) if len(equity) > 0 else 0.0

        # Sharpe ratio (annualized, assuming hourly bars)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(24 * 365)
        else:
            sharpe = 0.0

        # Sortino ratio
        downside = returns[returns < 0]
        if len(downside) > 1 and np.std(downside) > 0:
            sortino = np.mean(returns) / np.std(downside, ddof=1) * np.sqrt(24 * 365)
        else:
            sortino = 0.0

        # Max drawdown
        if len(equity) > 0:
            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / peak
            max_dd = float(np.max(drawdown))
            # Max drawdown duration
            in_dd = drawdown > 0
            max_dd_dur = 0
            current_dur = 0
            for dd_flag in in_dd:
                if dd_flag:
                    current_dur += 1
                    max_dd_dur = max(max_dd_dur, current_dur)
                else:
                    current_dur = 0
        else:
            max_dd = 0.0
            max_dd_dur = 0

        # Trade stats
        closed_trades = [t for t in trades if t.action.startswith("close")]
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]
        total_trades = len(closed_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0

        avg_pnl = np.mean([t.pnl for t in closed_trades]) if closed_trades else 0.0

        # Per-signal IC (rank correlation of signal values with forward returns)
        per_signal_ic = {}
        per_signal_contribution = {}
        for signal in signals:
            vals = np.array(signal_values[signal.name])
            rets = signal.returns_history
            if len(vals) > 10 and len(rets) > 10:
                min_len = min(len(vals), len(rets))
                try:
                    ic = float(np.corrcoef(vals[:min_len], rets[:min_len])[0, 1])
                    if np.isnan(ic):
                        ic = 0.0
                except (ValueError, FloatingPointError):
                    ic = 0.0
            else:
                ic = 0.0
            per_signal_ic[signal.name] = ic
            per_signal_contribution[signal.name] = ic * np.std(vals) if np.std(vals) > 0 else 0.0

        # Combination IR
        if len(combination_values) > 10:
            comb_arr = np.array(combination_values)
            comb_ir = float(np.mean(comb_arr) / (np.std(comb_arr) + 1e-10))
        else:
            comb_ir = 0.0

        equity_series = pd.Series(equity, index=self.dates[len(self.dates) - len(equity):])

        return BacktestResult(
            equity_curve=equity_series,
            trades=trades,
            final_equity=float(equity[-1]) if len(equity) > 0 else self.initial_capital,
            total_return=float(total_return),
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            max_drawdown=float(max_dd),
            max_drawdown_duration=max_dd_dur,
            win_rate=float(win_rate),
            profit_factor=float(profit_factor),
            total_trades=total_trades,
            avg_trade_pnl=float(avg_pnl),
            per_signal_ic=per_signal_ic,
            per_signal_contribution=per_signal_contribution,
            combination_ir=float(comb_ir),
            params=params,
        )

    def _empty_result(self, params: dict) -> BacktestResult:
        """Return an empty result for failed backtests."""
        return BacktestResult(
            equity_curve=pd.Series(dtype=float),
            trades=[],
            final_equity=self.initial_capital,
            total_return=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            avg_trade_pnl=0.0,
            per_signal_ic={},
            per_signal_contribution={},
            combination_ir=0.0,
            params=params,
        )
