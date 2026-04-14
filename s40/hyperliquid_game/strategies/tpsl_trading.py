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
Take-profit/Stop-loss (TP/SL) trading strategy based on horizontal levels.

Enters a position when price crosses a horizontal level, with predefined take-profit and stop-loss levels.
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


class TPSLTradingConfig(StrategyConfig, frozen=True):
    """
    Configuration for ``TPSLTrading`` instances.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID to trade.
    bar_type : str
        The bar type to subscribe to (e.g., "BTCUSDT.BINANCE-4-HOUR-LAST-INTERNAL").
    horizontal_levels : list[Price]
        List of horizontal price levels to watch for entries.
    tp_pct : NonNegativeFloat
        Take-profit percentage from entry price (e.g., 0.01 for 1%).
    sl_pct : NonNegativeFloat
        Stop-loss percentage from entry price (e.g., 0.005 for 0.5%).
    trade_size : Quantity
        The position size per trade.
    max_position : Quantity
        The maximum net exposure (long or short).
    """

    instrument_id: InstrumentId
    bar_type: str
    horizontal_levels: list[Price]
    tp_pct: NonNegativeFloat
    sl_pct: NonNegativeFloat
    trade_size: Quantity
    max_position: Quantity


class TPSLTrading(Strategy):
    """
    TP/SL trading strategy based on horizontal levels.
    """

    def __init__(self, config: TPSLTradingConfig) -> None:
        super().__init__(config)
        self._instrument: Instrument | None = None
        self._last_bar: Bar | None = None
        self._previous_bar: Bar | None = None
        self._bar_type: BarType | None = None
        self._active_orders: dict[ClientOrderId, tuple[OrderSide, Price]] = {}
        self._pending_entries: set[Price] = set()

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

        # Initialize pending entries with all levels
        self._pending_entries = set(self.config.horizontal_levels)

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
        self._previous_bar = self._last_bar
        self._last_bar = bar

        if self._previous_bar is None:
            return  # Need previous bar for cross detection

        instrument_id = self.config.instrument_id
        # Check for level crosses
        for level in list(self._pending_entries):
            if self._crossed_level(level):
                self._enter_position(level)
                self._pending_entries.remove(level)

    def on_order_filled(self, event: OrderFilled) -> None:
        """
        Actions to be performed when an order is filled.
        """
        # If it's an entry order, place TP/SL orders
        # If it's TP or SL order, remove from active orders and re-add level to pending
        order = self.cache.order(event.client_order_id)
        if order is None:
            return

        if event.client_order_id in self._active_orders:
            side, level = self._active_orders.pop(event.client_order_id)
            # If it's a take-profit or stop-loss order, re-add the level to pending entries
            # For simplicity, we assume any filled order that is not an entry is TP/SL
            # In a real implementation, we'd track order types.
            self._pending_entries.add(level)
            self.log.info(f"TP/SL order filled at {event.last_px}, re-adding level {level}")

    def on_reset(self) -> None:
        """
        Actions to be performed when the strategy is reset.
        """
        self._instrument = None
        self._last_bar = None
        self._previous_bar = None
        self._active_orders.clear()
        self._pending_entries.clear()

    def _crossed_level(self, level: Price) -> bool:
        """
        Return whether the bar crossed the given level.
        """
        if self._previous_bar is None or self._last_bar is None:
            return False

        prev_close = float(self._previous_bar.close)
        curr_close = float(self._last_bar.close)
        level_f = float(level)

        # Cross up: previous close below, current close above
        if prev_close < level_f <= curr_close:
            return True
        # Cross down: previous close above, current close below
        if prev_close > level_f >= curr_close:
            return True
        return False

    def _enter_position(self, level: Price) -> None:
        """
        Enter a position at the given level with TP/SL orders.
        """
        if self._instrument is None or self._last_bar is None:
            return

        instrument_id = self.config.instrument_id
        current_price = float(self._last_bar.close)
        level_f = float(level)

        # Determine side based on cross direction
        # If price crossed up, go long; if crossed down, go short
        # For simplicity, we assume crossing up means long, crossing down means short
        # In reality, we need to know previous bar's relation to level.
        # We'll use the previous close to decide.
        prev_close = float(self._previous_bar.close) if self._previous_bar else current_price
        if prev_close < level_f:
            side = OrderSide.BUY
        else:
            side = OrderSide.SELL

        # Check position limits
        net_position = 0.0
        for pos in self.cache.positions_open(instrument_id=instrument_id, strategy_id=self.id):
            net_position += pos.signed_qty

        max_position = float(self.config.max_position)
        trade_size = float(self.config.trade_size)

        if side == OrderSide.BUY and net_position + trade_size > max_position:
            self.log.warning(f"Cannot enter long, max position reached")
            return
        if side == OrderSide.SELL and net_position - trade_size < -max_position:
            self.log.warning(f"Cannot enter short, max position reached")
            return

        # Place entry order (market order for simplicity)
        entry_order = self.order_factory.market(
            instrument_id=instrument_id,
            order_side=side,
            quantity=self.config.trade_size,
        )
        self.submit_order(entry_order)
        self._active_orders[entry_order.client_order_id] = (side, level)

        # Calculate TP and SL prices
        if side == OrderSide.BUY:
            tp_price = Price(current_price * (1 + self.config.tp_pct), self._instrument.price_precision)
            sl_price = Price(current_price * (1 - self.config.sl_pct), self._instrument.price_precision)
        else:
            tp_price = Price(current_price * (1 - self.config.tp_pct), self._instrument.price_precision)
            sl_price = Price(current_price * (1 + self.config.sl_pct), self._instrument.price_precision)

        # Place TP order (limit order)
        tp_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        tp_order = self.order_factory.limit(
            instrument_id=instrument_id,
            order_side=tp_side,
            quantity=self.config.trade_size,
            price=tp_price,
            time_in_force=TimeInForce.GTC,
            reduce_only=True,
        )
        self.submit_order(tp_order)
        self._active_orders[tp_order.client_order_id] = (tp_side, level)

        # Place SL order (stop-market order)
        sl_order = self.order_factory.stop_market(
            instrument_id=instrument_id,
            order_side=tp_side,
            quantity=self.config.trade_size,
            trigger_price=sl_price,
            reduce_only=True,
        )
        self.submit_order(sl_order)
        self._active_orders[sl_order.client_order_id] = (tp_side, level)

        self.log.info(f"Entered {side} at {current_price}, TP={tp_price}, SL={sl_price}")
