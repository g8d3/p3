"""Hyperliquid exchange adapter for order execution."""

from typing import Optional

import eth_account
from loguru import logger

try:
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from hyperliquid.utils import constants as hl_constants
except ImportError:
    logger.warning("hyperliquid-python-sdk not installed")
    Exchange = None
    Info = None
    hl_constants = None


class HyperliquidExecutor:
    """Executes trades on Hyperliquid perp DEX."""

    def __init__(
        self,
        private_key: str,
        api_url: str = "https://api.hyperliquid.xyz",
        account_address: Optional[str] = None,
        slippage: float = 0.01,
    ):
        if Exchange is None:
            raise ImportError("hyperliquid-python-sdk is required")

        self.wallet = eth_account.Account.from_key(private_key)
        self.address = account_address or self.wallet.address
        self.api_url = api_url

        self.info = Info(api_url, skip_ws=True)
        self.exchange = Exchange(self.wallet, api_url, account_address=self.address)

        self.slippage = slippage
        logger.info(f"Executor initialized for address: {self.address[:10]}...")

    def open_long(
        self,
        coin: str,
        size_usd: float,
        price: Optional[float] = None,
        leverage: int = 3,
    ) -> dict:
        """Open a long position.

        Args:
            coin: Trading pair (e.g., "ETH").
            size_usd: Position size in USD.
            price: Limit price (if None, uses market order).
            leverage: Leverage to use.

        Returns:
            Order result dict.
        """
        # Set leverage
        self._set_leverage(coin, leverage)

        if price is not None:
            # Limit order
            size = size_usd / price
            result = self.exchange.order(
                coin,
                True,  # buy
                size,
                price,
                {"limit": {"tif": "Ioc"}},  # Immediate or cancel
            )
        else:
            # Market order
            result = self.exchange.market_open(
                coin,
                True,  # buy
                sz=None,
                px=None,
                slippage=self.slippage,
            )

        logger.info(f"Open long {coin}: size_usd={size_usd}, result={result}")
        return result

    def open_short(
        self,
        coin: str,
        size_usd: float,
        price: Optional[float] = None,
        leverage: int = 3,
    ) -> dict:
        """Open a short position."""
        self._set_leverage(coin, leverage)

        if price is not None:
            size = size_usd / price
            result = self.exchange.order(
                coin,
                False,  # sell
                size,
                price,
                {"limit": {"tif": "Ioc"}},
            )
        else:
            result = self.exchange.market_open(
                coin,
                False,  # sell
                sz=None,
                px=None,
                slippage=self.slippage,
            )

        logger.info(f"Open short {coin}: size_usd={size_usd}, result={result}")
        return result

    def close_position(self, coin: str) -> dict:
        """Close the entire position for a coin."""
        result = self.exchange.market_close(coin)
        logger.info(f"Close position {coin}: result={result}")
        return result

    def set_stop_loss(
        self,
        coin: str,
        trigger_price: float,
        is_long: bool,
        size: float,
    ) -> dict:
        """Set a stop-loss order.

        Args:
            coin: Trading pair.
            trigger_price: Price that triggers the stop.
            is_long: Whether the position is long.
            size: Position size to close.
        """
        result = self.exchange.order(
            coin,
            not is_long,  # Close: sell if long, buy if short
            size,
            trigger_price,
            {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": str(trigger_price),
                    "tpsl": "sl",
                }
            },
            reduce_only=True,
        )
        logger.info(f"Set SL {coin}: trigger={trigger_price}, result={result}")
        return result

    def set_take_profit(
        self,
        coin: str,
        trigger_price: float,
        is_long: bool,
        size: float,
    ) -> dict:
        """Set a take-profit order."""
        result = self.exchange.order(
            coin,
            not is_long,
            size,
            trigger_price,
            {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": str(trigger_price),
                    "tpsl": "tp",
                }
            },
            reduce_only=True,
        )
        logger.info(f"Set TP {coin}: trigger={trigger_price}, result={result}")
        return result

    def get_positions(self) -> list[dict]:
        """Get all open positions."""
        state = self.info.user_state(self.address)
        positions = []
        for ap in state.get("assetPositions", []):
            p = ap.get("position", {})
            if float(p.get("szi", "0")) != 0:
                positions.append({
                    "coin": p.get("coin"),
                    "size": float(p.get("szi", "0")),
                    "entry_price": float(p.get("entryPx", "0")),
                    "unrealized_pnl": float(p.get("unrealizedPnl", "0")),
                    "leverage": p.get("leverage", {}),
                })
        return positions

    def get_account_value(self) -> float:
        """Get total account value."""
        state = self.info.user_state(self.address)
        return float(state.get("marginSummary", {}).get("accountValue", "0"))

    def get_open_orders(self, coin: Optional[str] = None) -> list[dict]:
        """Get open orders, optionally filtered by coin."""
        orders = self.info.open_orders(self.address)
        if coin:
            orders = [o for o in orders if o.get("coin") == coin]
        return orders

    def cancel_all_orders(self, coin: Optional[str] = None) -> list:
        """Cancel all open orders, optionally for a specific coin."""
        results = []
        orders = self.get_open_orders(coin)
        for order in orders:
            result = self.exchange.cancel(order["coin"], order["oid"])
            results.append(result)
            logger.info(f"Cancelled order {order['oid']} for {order['coin']}")
        return results

    def _set_leverage(self, coin: str, leverage: int) -> dict:
        """Set leverage for a coin."""
        try:
            result = self.exchange.update_leverage(leverage, coin, is_cross=True)
            return result
        except Exception as e:
            logger.warning(f"Failed to set leverage for {coin}: {e}")
            return {}
