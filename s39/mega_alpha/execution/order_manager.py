"""Order management: bridges the portfolio/position layer with execution."""

from datetime import datetime
from typing import Optional

from loguru import logger

from engine.kelly import PositionSize
from engine.portfolio import Portfolio, Position
from execution.hyperliquid import HyperliquidExecutor


class OrderManager:
    """Manages the lifecycle of orders: from signal → position → execution.

    Bridges the portfolio layer (which tracks desired positions) with the
    Hyperliquid executor (which places actual orders).
    """

    def __init__(
        self,
        portfolio: Portfolio,
        executor: HyperliquidExecutor,
        default_leverage: int = 3,
        stop_loss_pct: float = 0.03,  # 3% stop loss
        take_profit_pct: float = 0.06,  # 6% take profit
    ):
        self.portfolio = portfolio
        self.executor = executor
        self.default_leverage = default_leverage
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def execute_signal(
        self,
        coin: str,
        size: PositionSize,
        current_price: float,
    ) -> Optional[Position]:
        """Execute a trading signal.

        Args:
            coin: Trading pair.
            size: Position sizing result from Kelly.
            current_price: Current market price.

        Returns:
            The opened Position, or None if not executed.
        """
        if size.direction == 0 or size.size_usd <= 0:
            logger.debug(f"No trade signal for {coin} (direction={size.direction}, size={size.size_usd})")
            return None

        # Check if we can open the position
        if not self.portfolio.can_open_position(coin, size):
            logger.warning(f"Cannot open position for {coin}: portfolio constraints")
            return None

        # Calculate stop loss and take profit
        if size.direction > 0:  # Long
            stop_loss = current_price * (1 - self.stop_loss_pct)
            take_profit = current_price * (1 + self.take_profit_pct)
        else:  # Short
            stop_loss = current_price * (1 + self.stop_loss_pct)
            take_profit = current_price * (1 - self.take_profit_pct)

        # Execute the order
        try:
            if size.direction > 0:
                result = self.executor.open_long(
                    coin, size.size_usd, leverage=self.default_leverage
                )
            else:
                result = self.executor.open_short(
                    coin, size.size_usd, leverage=self.default_leverage
                )

            # Check if order was successful
            if self._is_order_success(result):
                position = self.portfolio.open_position(
                    coin=coin,
                    size=size,
                    price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )

                # Set stop loss and take profit on exchange
                try:
                    position_size = size.size_usd / current_price
                    self.executor.set_stop_loss(coin, stop_loss, size.direction > 0, position_size)
                    self.executor.set_take_profit(coin, take_profit, size.direction > 0, position_size)
                except Exception as e:
                    logger.warning(f"Failed to set SL/TP for {coin}: {e}")

                logger.info(
                    f"Opened {'LONG' if size.direction > 0 else 'SHORT'} {coin}: "
                    f"size=${size.size_usd:.2f}, entry={current_price}, "
                    f"SL={stop_loss:.2f}, TP={take_profit:.2f}, "
                    f"confidence={size.confidence:.2f}"
                )
                return position
            else:
                logger.warning(f"Order failed for {coin}: {result}")
                return None

        except Exception as e:
            logger.error(f"Error executing signal for {coin}: {e}")
            return None

    def close_position(self, coin: str, current_price: float) -> Optional[float]:
        """Close a position.

        Returns the realized PnL, or None if no position exists.
        """
        position = self.portfolio.get_position(coin)
        if position is None:
            return None

        try:
            # Cancel any open orders for this coin
            self.executor.cancel_all_orders(coin)

            # Close on exchange
            result = self.executor.close_position(coin)

            # Close in portfolio
            pnl = self.portfolio.close_position(coin, current_price)
            logger.info(f"Closed {coin} position: PnL=${pnl:.2f}")
            return pnl

        except Exception as e:
            logger.error(f"Error closing position for {coin}: {e}")
            return None

    def check_stop_losses(self, prices: dict[str, float]) -> list[str]:
        """Check if any positions have hit their stop loss.

        Returns list of coins that should be closed.
        """
        to_close = []
        for coin, position in self.portfolio.state.positions.items():
            if coin not in prices:
                continue

            price = prices[coin]
            if position.stop_loss is not None:
                if position.is_long and price <= position.stop_loss:
                    to_close.append(coin)
                    logger.warning(f"Stop loss triggered for {coin}: price={price}, SL={position.stop_loss}")
                elif position.is_short and price >= position.stop_loss:
                    to_close.append(coin)
                    logger.warning(f"Stop loss triggered for {coin}: price={price}, SL={position.stop_loss}")

            if position.take_profit is not None:
                if position.is_long and price >= position.take_profit:
                    to_close.append(coin)
                    logger.info(f"Take profit triggered for {coin}: price={price}, TP={position.take_profit}")
                elif position.is_short and price <= position.take_profit:
                    to_close.append(coin)
                    logger.info(f"Take profit triggered for {coin}: price={price}, TP={position.take_profit}")

        return to_close

    def sync_with_exchange(self) -> None:
        """Sync portfolio state with actual exchange positions."""
        try:
            exchange_positions = self.executor.get_positions()
            account_value = self.executor.get_account_value()

            # Update capital
            self.portfolio.state.capital = account_value

            # Sync positions
            exchange_coins = {p["coin"] for p in exchange_positions}
            portfolio_coins = set(self.portfolio.state.positions.keys())

            # Close positions that no longer exist on exchange
            for coin in portfolio_coins - exchange_coins:
                logger.info(f"Position {coin} no longer on exchange, removing from portfolio")
                del self.portfolio.state.positions[coin]

        except Exception as e:
            logger.error(f"Error syncing with exchange: {e}")

    def _is_order_success(self, result: dict | tuple) -> bool:
        """Check if an order was successful."""
        if isinstance(result, tuple):
            status = result[0]
            return "success" in str(status).lower() if isinstance(status, str) else True
        if isinstance(result, dict):
            status = result.get("status", "")
            return "success" in str(status).lower() or "filled" in str(status).lower()
        return True
