"""
Antigravity Trading — Risk Manager
Pre-trade and runtime risk checks to protect capital.
"""

from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Optional

from core.config import get_settings
from core.exceptions import (
    CircuitBreakerTriggered, MaxLossBreached, PositionLimitBreached, RiskViolation,
)
from core.models import Exchange, Order, OrderSide, Position

logger = logging.getLogger("antigravity.engine.risk")


class RiskManager:
    """
    Pre-trade and runtime risk management.
    
    Checks:
    1. Max loss per day
    2. Max loss per strategy
    3. Max position value
    4. Max open positions count
    5. Circuit breaker (drawdown threshold)
    6. Auto square-off times (NSE 3:15 PM, MCX 11:25 PM)
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        max_loss_per_day: Optional[float] = None,
        max_loss_per_strategy: Optional[float] = None,
        max_position_value: Optional[float] = None,
        max_open_positions: Optional[int] = None,
        circuit_breaker_pct: Optional[float] = None,
    ):
        settings = get_settings()
        risk_cfg = settings.risk

        self._initial_capital = initial_capital
        self._max_loss_day = max_loss_per_day or risk_cfg.max_loss_per_day
        self._max_loss_strategy = max_loss_per_strategy or risk_cfg.max_loss_per_strategy
        self._max_position_value = max_position_value or risk_cfg.max_position_value
        self._max_open_positions = max_open_positions or risk_cfg.max_open_positions
        self._circuit_breaker_pct = circuit_breaker_pct or risk_cfg.circuit_breaker_drawdown_pct

        # State
        self._daily_pnl: float = 0.0
        self._strategy_pnl: dict[str, float] = {}
        self._circuit_breaker_active = False
        self._today: Optional[str] = None

    def pre_trade_check(
        self,
        order: Order,
        current_positions: dict[str, Position],
        daily_pnl: float,
    ) -> None:
        """
        Run all pre-trade validations.
        Raises RiskViolation subclass if any check fails.
        """
        # Reset daily tracking if new day
        today = datetime.now().strftime("%Y-%m-%d")
        if self._today != today:
            self._today = today
            self._daily_pnl = 0.0

        self._daily_pnl = daily_pnl

        # 1. Circuit breaker
        if self._circuit_breaker_active:
            raise CircuitBreakerTriggered(
                "circuit_breaker",
                f"Circuit breaker active. Daily loss: ₹{abs(self._daily_pnl):,.2f}"
            )

        # 2. Max daily loss
        if abs(self._daily_pnl) >= self._max_loss_day:
            self._circuit_breaker_active = True
            raise MaxLossBreached(
                "max_daily_loss",
                f"Daily loss ₹{abs(self._daily_pnl):,.2f} exceeds limit ₹{self._max_loss_day:,.2f}"
            )

        # 3. Max strategy loss
        strategy_pnl = self._strategy_pnl.get(order.strategy_id, 0.0)
        if abs(strategy_pnl) >= self._max_loss_strategy:
            raise MaxLossBreached(
                "max_strategy_loss",
                f"Strategy {order.strategy_id} loss ₹{abs(strategy_pnl):,.2f} "
                f"exceeds limit ₹{self._max_loss_strategy:,.2f}"
            )

        # 4. Max open positions
        open_count = sum(1 for p in current_positions.values() if p.is_open)
        if open_count >= self._max_open_positions and order.side == OrderSide.BUY:
            raise PositionLimitBreached(
                "max_positions",
                f"Open positions ({open_count}) at limit ({self._max_open_positions})"
            )

        # 5. Max position value
        order_value = order.quantity * (order.price or order.trigger_price or 0)
        if order_value > self._max_position_value:
            raise PositionLimitBreached(
                "max_position_value",
                f"Order value ₹{order_value:,.2f} exceeds limit ₹{self._max_position_value:,.2f}"
            )

        # 6. Circuit breaker on drawdown
        drawdown_pct = (abs(self._daily_pnl) / self._initial_capital) * 100
        if drawdown_pct >= self._circuit_breaker_pct:
            self._circuit_breaker_active = True
            raise CircuitBreakerTriggered(
                "drawdown_circuit_breaker",
                f"Drawdown {drawdown_pct:.2f}% exceeds circuit breaker {self._circuit_breaker_pct:.2f}%"
            )

        logger.debug("Risk check passed for %s %s x%d", order.side.value, order.instrument.display_name, order.quantity)

    def update_pnl(self, strategy_id: str, pnl: float) -> None:
        """Update P&L tracking after a trade."""
        self._daily_pnl += pnl
        self._strategy_pnl[strategy_id] = self._strategy_pnl.get(strategy_id, 0.0) + pnl

    def should_square_off(self, exchange: Exchange) -> bool:
        """Check if it's past the auto square-off time."""
        settings = get_settings()
        now = datetime.now().time()

        if exchange in (Exchange.NSE, Exchange.NFO, Exchange.BSE, Exchange.BFO):
            sq_time = datetime.strptime(settings.risk.auto_square_off_nse, "%H:%M").time()
        elif exchange == Exchange.MCX:
            sq_time = datetime.strptime(settings.risk.auto_square_off_mcx, "%H:%M").time()
        else:
            return False

        return now >= sq_time

    def reset_daily(self) -> None:
        """Reset daily tracking (call at start of each trading day)."""
        self._daily_pnl = 0.0
        self._strategy_pnl.clear()
        self._circuit_breaker_active = False
        self._today = datetime.now().strftime("%Y-%m-%d")
        logger.info("Daily risk counters reset")

    @property
    def is_circuit_breaker_active(self) -> bool:
        return self._circuit_breaker_active
