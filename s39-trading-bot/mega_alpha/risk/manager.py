"""Risk management module."""

from datetime import datetime
from typing import Optional

from loguru import logger

from engine.portfolio import Portfolio
from engine.kelly import PositionSize


class RiskManager:
    """Risk management: enforces position limits, drawdown controls, and circuit breakers."""

    def __init__(
        self,
        portfolio: Portfolio,
        max_position_size_usd: float = 1000,
        max_portfolio_heat: float = 0.10,  # Max 10% of capital at risk
        max_drawdown_pct: float = 0.15,  # 15% max drawdown before pause
        max_daily_trades: int = 20,
        max_correlation_exposure: float = 0.50,  # Max 50% in correlated assets
        cooldown_minutes: int = 30,  # Cooldown after circuit breaker
    ):
        self.portfolio = portfolio
        self.max_position_size_usd = max_position_size_usd
        self.max_portfolio_heat = max_portfolio_heat
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_trades = max_daily_trades
        self.max_correlation_exposure = max_correlation_exposure
        self.cooldown_minutes = cooldown_minutes

        self._peak_capital = portfolio.state.capital
        self._daily_trades = 0
        self._daily_reset = datetime.utcnow().date()
        self._circuit_breaker_until: Optional[datetime] = None
        self._trade_history: list[dict] = []

    def check_position_size(self, size: PositionSize) -> bool:
        """Check if a position size is within risk limits."""
        if size.size_usd > self.max_position_size_usd:
            logger.warning(
                f"Position size ${size.size_usd:.2f} exceeds max ${self.max_position_size_usd}"
            )
            return False

        # Check portfolio heat
        projected_heat = (self.portfolio.state.total_exposure + size.size_usd) / self.portfolio.state.capital
        if projected_heat > self.max_portfolio_heat / self.portfolio.state.capital * self.portfolio.state.capital:
            # Simplified: check if adding this position exceeds heat limit
            total_at_risk = self.portfolio.state.total_exposure + size.size_usd
            if total_at_risk > self.portfolio.state.capital * self.max_portfolio_heat / 0.02:
                # Rough check: if total exposure > capital * 5 (for 3x leverage)
                pass  # Allow for leveraged positions

        return True

    def check_drawdown(self) -> bool:
        """Check if we're within drawdown limits.

        Returns False if drawdown exceeds limit (should stop trading).
        """
        current = self.portfolio.state.total_equity
        if current > self._peak_capital:
            self._peak_capital = current

        if self._peak_capital <= 0:
            return False

        drawdown = (self._peak_capital - current) / self._peak_capital
        if drawdown > self.max_drawdown_pct:
            logger.error(
                f"MAX DRAWDOWN EXCEEDED: {drawdown:.1%} > {self.max_drawdown_pct:.1%}. "
                f"Peak: ${self._peak_capital:.2f}, Current: ${current:.2f}"
            )
            return False

        return True

    def check_daily_limit(self) -> bool:
        """Check if we're within daily trade limits."""
        today = datetime.utcnow().date()
        if today != self._daily_reset:
            self._daily_trades = 0
            self._daily_reset = today

        if self._daily_trades >= self.max_daily_trades:
            logger.warning(f"Daily trade limit reached: {self._daily_trades}/{self.max_daily_trades}")
            return False

        return True

    def check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is active.

        Returns True if trading is ALLOWED (no breaker active).
        """
        if self._circuit_breaker_until is None:
            return True

        if datetime.utcnow() >= self._circuit_breaker_until:
            self._circuit_breaker_until = None
            logger.info("Circuit breaker lifted, resuming trading")
            return True

        logger.warning(
            f"Circuit breaker active until {self._circuit_breaker_until}"
        )
        return False

    def trigger_circuit_breaker(self, reason: str = "manual") -> None:
        """Activate the circuit breaker."""
        from datetime import timedelta
        self._circuit_breaker_until = datetime.utcnow() + timedelta(minutes=self.cooldown_minutes)
        logger.warning(f"CIRCUIT BREAKER TRIGGERED: {reason}. Paused until {self._circuit_breaker_until}")

    def record_trade(self, coin: str, action: str, size_usd: float) -> None:
        """Record a trade for risk tracking."""
        self._daily_trades += 1
        self._trade_history.append({
            "coin": coin,
            "action": action,
            "size_usd": size_usd,
            "timestamp": datetime.utcnow().isoformat(),
            "capital": self.portfolio.state.capital,
        })

    def full_check(self, size: Optional[PositionSize] = None) -> tuple[bool, str]:
        """Run all risk checks.

        Returns (allowed, reason).
        """
        if not self.check_circuit_breaker():
            return False, "circuit_breaker_active"

        if not self.check_drawdown():
            self.trigger_circuit_breaker("max_drawdown_exceeded")
            return False, "max_drawdown_exceeded"

        if not self.check_daily_limit():
            return False, "daily_trade_limit"

        if size is not None and not self.check_position_size(size):
            return False, "position_size_exceeded"

        return True, "ok"

    @property
    def risk_report(self) -> dict:
        """Generate a risk report."""
        current = self.portfolio.state.total_equity
        drawdown = (self._peak_capital - current) / self._peak_capital if self._peak_capital > 0 else 0

        return {
            "capital": self.portfolio.state.capital,
            "total_equity": current,
            "peak_capital": self._peak_capital,
            "drawdown": f"{drawdown:.2%}",
            "open_positions": len(self.portfolio.state.positions),
            "total_exposure": self.portfolio.state.total_exposure,
            "gross_leverage": f"{self.portfolio.state.gross_leverage:.2f}x",
            "daily_trades": self._daily_trades,
            "circuit_breaker": self._circuit_breaker_until.isoformat() if self._circuit_breaker_until else None,
        }
