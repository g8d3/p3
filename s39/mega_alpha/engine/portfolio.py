"""Portfolio management: tracks positions, PnL, and capital."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from engine.kelly import PositionSize


@dataclass
class Position:
    """An open position."""

    coin: str
    direction: int  # 1 = long, -1 = short
    size_usd: float
    entry_price: float
    timestamp: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @property
    def is_long(self) -> bool:
        return self.direction > 0

    @property
    def is_short(self) -> bool:
        return self.direction < 0


@dataclass
class PortfolioState:
    """Current state of the trading portfolio."""

    capital: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def total_equity(self) -> float:
        return self.capital + self.unrealized_pnl

    @property
    def total_exposure(self) -> float:
        return sum(p.size_usd for p in self.positions.values())

    @property
    def net_exposure(self) -> float:
        long_exposure = sum(p.size_usd for p in self.positions.values() if p.is_long)
        short_exposure = sum(p.size_usd for p in self.positions.values() if p.is_short)
        return long_exposure - short_exposure

    @property
    def gross_leverage(self) -> float:
        if self.capital <= 0:
            return 0.0
        return self.total_exposure / self.capital


class Portfolio:
    """Portfolio manager that tracks positions and capital."""

    def __init__(self, initial_capital: float = 10000.0, max_leverage: float = 3.0):
        self.state = PortfolioState(capital=initial_capital)
        self.max_leverage = max_leverage
        self._history: list[dict] = []

    def can_open_position(self, coin: str, size: PositionSize) -> bool:
        """Check if we can open a new position."""
        # Check leverage limit
        projected_exposure = self.state.total_exposure + size.size_usd
        projected_leverage = projected_exposure / self.state.capital
        if projected_leverage > self.max_leverage:
            return False

        # Check if already have a position in this coin
        if coin in self.state.positions:
            existing = self.state.positions[coin]
            # Allow if same direction and adding
            if existing.direction == size.direction:
                return True
            # Opposite direction → close existing first
            return False

        return True

    def open_position(
        self,
        coin: str,
        size: PositionSize,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Position:
        """Open a new position."""
        if not self.can_open_position(coin, size):
            raise ValueError(f"Cannot open position for {coin}")

        position = Position(
            coin=coin,
            direction=size.direction,
            size_usd=size.size_usd,
            entry_price=price,
            timestamp=datetime.utcnow(),
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        self.state.positions[coin] = position
        self._record_action("open", coin, size.size_usd, price)
        return position

    def close_position(self, coin: str, price: float) -> float:
        """Close a position and realize PnL.

        Returns the realized PnL.
        """
        if coin not in self.state.positions:
            return 0.0

        pos = self.state.positions[coin]
        if pos.is_long:
            pnl = (price - pos.entry_price) / pos.entry_price * pos.size_usd
        else:
            pnl = (pos.entry_price - price) / pos.entry_price * pos.size_usd

        self.state.realized_pnl += pnl
        self.state.capital += pnl
        del self.state.positions[coin]

        # Recalculate unrealized PnL since this position is now gone
        self.state.unrealized_pnl -= pnl  # Remove this position's contribution

        self._record_action("close", coin, pos.size_usd, price, pnl=pnl)
        return pnl

    def update_unrealized_pnl(self, prices: dict[str, float]) -> None:
        """Update unrealized PnL based on current prices."""
        total_unrealized = 0.0
        for coin, pos in self.state.positions.items():
            if coin in prices:
                if pos.is_long:
                    pnl = (prices[coin] - pos.entry_price) / pos.entry_price * pos.size_usd
                else:
                    pnl = (pos.entry_price - prices[coin]) / pos.entry_price * pos.size_usd
                total_unrealized += pnl

        self.state.unrealized_pnl = total_unrealized

    def get_position(self, coin: str) -> Optional[Position]:
        return self.state.positions.get(coin)

    def _record_action(
        self,
        action: str,
        coin: str,
        size: float,
        price: float,
        pnl: float = 0.0,
    ) -> None:
        self._history.append({
            "action": action,
            "coin": coin,
            "size": size,
            "price": price,
            "pnl": pnl,
            "capital": self.state.capital,
            "timestamp": datetime.utcnow().isoformat(),
        })
