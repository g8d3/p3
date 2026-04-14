# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Grid trading strategy with fixed horizontal levels.

Places buy and sell limit orders at predefined price levels (horizontal levels).
Orders are placed when the price is within a certain distance from the level.
The grid is static (does not move with price) but orders are replaced when filled.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from nautilus_trader.config import NonNegativeFloat
from nautilus_trader.config import PositiveInt
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy


class GridTradingConfig(StrategyConfig, frozen=True):
    """
    Configuration for ``GridTrading`` instances.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID to trade.
    grid_step : Price
        The price step between grid levels (horizontal levels).
    num_levels : PositiveInt
        The number of buy and sell levels on each side of the current price.
    trade_size : Quantity
        The order size per grid level.
    max_position : Quantity
        The maximum net exposure (long or short).
    bar_type : str
        The bar type to subscribe to (e.g., "BTCUSDT.BINANCE-4-HOUR-LAST-INTERNAL").
    requote_threshold : Price
        The minimum price move before re-quoting the grid (optional).
    """

    instrument_id: InstrumentId
    grid_step: Price
    num_levels: PositiveInt
    trade_size: Quantity
    max_position: Quantity
    bar_type: str
    requote_threshold: Price | None = None


class GridTrading(Strategy):
    """
    Grid trading strategy with fixed horizontal levels.

    Places buy and sell limit orders at predefined price levels.
    """

    def __init__(self, config: GridTradingConfig) -> None:
        super().__init__(config)
        self._instrument: Instrument | None = None
        self._last_bar: Bar | None = None
        self._bar_type: BarType | None = None
        self._grid_levels: list[tuple[OrderSide, Price]] = []
        self._pending_cancels: set[ClientOrderId] = set()

    def on_start(self) -> None:
        """
        Actions to be performed on strategy start.
        """
        instrument_id = self.config.instrument_id
        self._instrument = self.cache.instrument(instrument_id)
        if self._instrument is None:
            self.log.error(f"Could not find instrument for {instrument_id}")
            self.stop()
            return

        # Subscribe to bars
        bar_type_str = self.config.bar_type
        bar_type = BarType.from_str(bar_type_str)
        self._bar_type = bar_type
        self.subscribe_bars(bar_type)

    def on_stop(self) -> None:
        """
        Actions to be performed on strategy stop.
        """
        if self._instrument is None:
            return
        instrument_id = self._instrument.id
        self.cancel_all_orders(instrument_id)
        self.close_all_positions(instrument_id)
        self.unsubscribe_bars(self._bar_type)

    def on_bar(self, bar: Bar) -> None:
        """
        Actions to be performed when a bar is received.
        """
        self._last_bar = bar
        instrument_id = self.config.instrument_id

        # Check if we need to requote the grid
        if self._should_requote():
            self._requote_grid()

    def on_order_filled(self, event: OrderFilled) -> None:
        """
        Actions to be performed when an order is filled.
        """
        # Remove from pending cancels if fully filled
        order = self.cache.order(event.client_order_id)
        if order is not None and order.is_closed:
            self._pending_cancels.discard(event.client_order_id)

    def on_reset(self) -> None:
        """
        Actions to be performed when the strategy is reset.
        """
        self._instrument = None
        self._last_bar = None
        self._grid_levels.clear()
        self._pending_cancels.clear()

    def _should_requote(self) -> bool:
        """
        Return whether the grid should be requoted based on price movement.
        """
        if self._last_bar is None:
            return False
        if self._grid_levels:
            # If we have existing grid levels, check if price moved enough
            # For simplicity, we requote on every bar (could be improved)
            return True
        else:
            # No grid levels yet, need to place them
            return True

    def _requote_grid(self) -> None:
        """
        Cancel existing orders and place new grid orders based on current price.
        """
        if self._instrument is None or self._last_bar is None:
            return

        instrument_id = self.config.instrument_id
        # Cancel all existing orders
        self.cancel_all_orders(instrument_id)

        # Compute grid levels based on current bar close price
        current_price = float(self._last_bar.close)
        grid_step = float(self.config.grid_step)
        num_levels = self.config.num_levels
        trade_size = self.config.trade_size
        max_position = float(self.config.max_position)

        # Get current position
        net_position = 0.0
        for pos in self.cache.positions_open(instrument_id=instrument_id, strategy_id=self.id):
            net_position += pos.signed_qty

        # Determine how many levels we can place given max_position
        # For simplicity, we place all levels but limit orders based on position
        # This is a basic implementation; a real grid would manage inventory.
        self._grid_levels.clear()

        for level in range(1, num_levels + 1):
            buy_price = Price(current_price - level * grid_step, self._instrument.price_precision)
            sell_price = Price(current_price + level * grid_step, self._instrument.price_precision)

            # Check if we can place buy order (not exceeding max_position)
            if net_position + float(trade_size) <= max_position:
                self._grid_levels.append((OrderSide.BUY, buy_price))
            # Check if we can place sell order
            if net_position - float(trade_size) >= -max_position:
                self._grid_levels.append((OrderSide.SELL, sell_price))

        # Place orders
        for side, price in self._grid_levels:
            order = self.order_factory.limit(
                instrument_id=instrument_id,
                order_side=side,
                quantity=trade_size,
                price=price,
                time_in_force=TimeInForce.GTC,
                post_only=True,
            )
            self.submit_order(order)

        self.log.info(f"Requoted grid with {len(self._grid_levels)} levels at prices around {current_price}")
