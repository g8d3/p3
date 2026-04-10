#!/usr/bin/env python3
"""Mega Alpha Trading System — Main Entry Point.

Institutional-grade multi-signal combination trading system for
perpetual DEXes (starting with Hyperliquid).

Based on the Fundamental Law of Active Management:
    IR = IC × √N

Combines multiple weak, independent signals into a single high-conviction
mega-alpha position using the 11-step combination engine, with empirical
Kelly position sizing and comprehensive risk management.
"""

import sys
import time
import signal as sig
from datetime import datetime
from pathlib import Path

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from signals import SignalRegistry
from engine.combination import CombinationEngine
from engine.kelly import KellySizer
from engine.portfolio import Portfolio
from data.market_data import MarketDataFetcher
from execution.hyperliquid import HyperliquidExecutor
from execution.order_manager import OrderManager
from risk.manager import RiskManager


class MegaAlphaTrader:
    """Main trading system orchestrator."""

    def __init__(self):
        self.settings = get_settings()
        self._running = False

        # Initialize components
        self._init_logging()
        self._init_components()

    def _init_logging(self) -> None:
        """Configure logging."""
        logger.remove()
        logger.add(
            sys.stderr,
            level=self.settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        )
        logger.add(
            "mega_alpha_{time}.log",
            rotation="1 day",
            retention="30 days",
            level="DEBUG",
        )

    def _init_components(self) -> None:
        """Initialize all system components."""
        s = self.settings

        # Signal registry and instances
        self.registry = SignalRegistry()
        self.signals = self.registry.create_all( lookback_days=s.signal.lookback_days)
        logger.info(f"Initialized {len(self.signals)} signals: {[s.name for s in self.signals]}")

        # Combination engine
        self.combination_engine = CombinationEngine(
            min_history=s.signal.min_signal_history,
        )

        # Market data
        self.data_fetcher = MarketDataFetcher(api_url=s.hyperliquid.api_url)

        # Portfolio
        self.portfolio = Portfolio(
            initial_capital=s.trading.max_position_size_usd * 5,  # 5x max position
            max_leverage=s.trading.max_leverage,
        )

        # Kelly sizer
        self.kelly_sizer = KellySizer(
            capital=self.portfolio.state.capital,
            max_fraction=s.trading.risk_per_trade,
        )

        # Exchange executor
        if not s.hyperliquid.private_key:
            logger.warning("No private key configured. Running in DRY RUN mode.")
            self.executor = None
        else:
            self.executor = HyperliquidExecutor(
                private_key=s.hyperliquid.private_key,
                api_url=s.hyperliquid.api_url,
            )
            # Sync capital from exchange
            try:
                account_value = self.executor.get_account_value()
                if account_value > 0:
                    self.portfolio.state.capital = account_value
                    self.kelly_sizer.update_capital(account_value)
                    logger.info(f"Synced capital from exchange: ${account_value:.2f}")
            except Exception as e:
                logger.warning(f"Could not sync capital from exchange: {e}")

        # Order manager
        self.order_manager = OrderManager(
            portfolio=self.portfolio,
            executor=self.executor,
            default_leverage=int(s.trading.max_leverage),
        ) if self.executor else None

        # Risk manager
        self.risk_manager = RiskManager(
            portfolio=self.portfolio,
            max_position_size_usd=s.trading.max_position_size_usd,
        )

        self.coins = s.trading.coins
        self.cycle_interval = 300  # 5 minutes between cycles

    def run(self) -> None:
        """Start the main trading loop."""
        self._running = True
        logger.info("=" * 60)
        logger.info("MEGA ALPHA TRADING SYSTEM STARTING")
        logger.info(f"Coins: {self.coins}")
        logger.info(f"Mode: {'LIVE' if self.executor else 'DRY RUN'}")
        logger.info(f"Capital: ${self.portfolio.state.capital:.2f}")
        logger.info(f"Signals: {len(self.signals)}")
        logger.info("=" * 60)

        # Register signal handlers for graceful shutdown
        sig.signal(sig.SIGINT, self._shutdown)
        sig.signal(sig.SIGTERM, self._shutdown)

        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}", exc_info=True)
                self.risk_manager.trigger_circuit_breaker(f"cycle_error: {e}")

            if self._running:
                logger.debug(f"Sleeping {self.cycle_interval}s until next cycle...")
                time.sleep(self.cycle_interval)

        logger.info("Mega Alpha Trading System stopped.")

    def _run_cycle(self) -> None:
        """Execute one trading cycle."""
        cycle_start = datetime.utcnow()
        logger.info(f"--- Cycle started at {cycle_start.isoformat()} ---")

        # 1. Fetch market data
        logger.info("Fetching market data...")
        try:
            market_data = self.data_fetcher.build_signal_data(self.coins)
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return

        if not market_data:
            logger.warning("No market data available, skipping cycle")
            return

        # 2. Get current prices
        prices = {}
        for coin in self.coins:
            price = self.data_fetcher.get_mid_price(coin)
            if price:
                prices[coin] = price
        logger.info(f"Current prices: {prices}")

        # 3. Update portfolio with current prices
        self.portfolio.update_unrealized_pnl(prices)

        # 4. Check risk limits
        risk_ok, risk_reason = self.risk_manager.full_check()
        if not risk_ok:
            logger.warning(f"Risk check failed: {risk_reason}. Skipping new trades.")
            self._manage_existing_positions(prices)
            return

        # 5. Compute all signals
        logger.info("Computing signals...")
        signal_outputs = []
        for signal in self.signals:
            try:
                output = signal.compute(market_data)
                signal_outputs.append(output)
                logger.info(f"  {signal.name}: {output.value:.4f} (direction={output.direction})")
            except Exception as e:
                logger.error(f"Signal {signal.name} failed: {e}")
                from signals.base import SignalOutput
                signal_outputs.append(SignalOutput(
                    name=signal.name, value=0.0, timestamp=datetime.utcnow()
                ))

        # 6. Run combination engine
        logger.info("Running combination engine...")
        combination = self.combination_engine.combine(self.signals, signal_outputs)
        logger.info(
            f"Combined signal: {combination.combined_value:.4f} | "
            f"IR: {combination.information_ratio:.4f} | "
            f"Weights: {combination.weights}"
        )

        # 7. Compute position size
        position_size = self.kelly_sizer.size(combination)
        logger.info(
            f"Position size: fraction={position_size.fraction:.4f}, "
            f"usd=${position_size.size_usd:.2f}, "
            f"direction={'LONG' if position_size.direction > 0 else 'SHORT' if position_size.direction < 0 else 'NEUTRAL'}, "
            f"confidence={position_size.confidence:.4f}"
        )

        # 8. Execute trades per coin
        for coin in self.coins:
            if coin not in prices:
                continue

            # Per-coin signal: use the combined signal for direction
            # but size based on the coin's price
            from engine.kelly import PositionSize as PS
            coin_size = PS(
                fraction=position_size.fraction / len(self.coins),
                size_usd=position_size.size_usd / len(self.coins),
                direction=position_size.direction,
                kelly_fraction=position_size.kelly_fraction,
                cv_edge=position_size.cv_edge,
                confidence=position_size.confidence,
            )

            if self.order_manager:
                # Live trading
                existing = self.portfolio.get_position(coin)

                if existing:
                    # Check if we should close or reverse
                    if existing.direction != coin_size.direction and coin_size.direction != 0:
                        logger.info(f"Reversing {coin}: {existing.direction} → {coin_size.direction}")
                        self.order_manager.close_position(coin, prices[coin])
                        self.risk_manager.record_trade(coin, "close", existing.size_usd)
                        # Open new position
                        pos = self.order_manager.execute_signal(coin, coin_size, prices[coin])
                        if pos:
                            self.risk_manager.record_trade(coin, "open", coin_size.size_usd)
                    elif coin_size.direction == 0:
                        logger.info(f"Closing {coin}: signal neutral")
                        self.order_manager.close_position(coin, prices[coin])
                        self.risk_manager.record_trade(coin, "close", existing.size_usd)
                else:
                    # No existing position
                    if coin_size.direction != 0:
                        pos = self.order_manager.execute_signal(coin, coin_size, prices[coin])
                        if pos:
                            self.risk_manager.record_trade(coin, "open", coin_size.size_usd)
            else:
                # Dry run mode
                if coin_size.direction != 0:
                    logger.info(
                        f"[DRY RUN] Would {'BUY' if coin_size.direction > 0 else 'SELL'} "
                        f"{coin}: ${coin_size.size_usd:.2f} @ {prices[coin]}"
                    )

        # 9. Manage existing positions (stop losses, take profits)
        self._manage_existing_positions(prices)

        # 10. Record signal returns for the combination engine
        self._update_signal_returns(prices)

        # 11. Log risk report
        logger.info(f"Risk report: {self.risk_manager.risk_report}")

        cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
        logger.info(f"--- Cycle completed in {cycle_time:.1f}s ---")

    def _manage_existing_positions(self, prices: dict[str, float]) -> None:
        """Check stop losses and take profits for existing positions."""
        if not self.order_manager:
            return

        to_close = self.order_manager.check_stop_losses(prices)
        for coin in to_close:
            if coin in prices:
                self.order_manager.close_position(coin, prices[coin])
                self.risk_manager.record_trade(coin, "sl_tp", 0)

    def _update_signal_returns(self, prices: dict[str, float]) -> None:
        """Update signal return histories for the combination engine.

        Compares current prices to previous cycle's prices to compute
        realized returns, then feeds them back to each signal.
        """
        if not hasattr(self, '_prev_prices'):
            self._prev_prices = prices
            return

        for coin in self.coins:
            if coin in prices and coin in self._prev_prices:
                prev = self._prev_prices[coin]
                curr = prices[coin]
                if prev > 0:
                    realized_return = (curr - prev) / prev
                    for signal in self.signals:
                        signal.record_return(realized_return)

        self._prev_prices = prices

    def _shutdown(self, signum, frame) -> None:
        """Graceful shutdown handler."""
        logger.info(f"Shutdown signal received ({signum}). Stopping gracefully...")
        self._running = False


def main():
    """Entry point."""
    trader = MegaAlphaTrader()
    trader.run()


if __name__ == "__main__":
    main()
