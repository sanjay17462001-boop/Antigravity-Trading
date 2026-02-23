"""
Antigravity Trading — Portfolio Tracker
Tracks capital, positions, P&L, and drawdown during backtesting and live trading.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from core.models import (
    Instrument, Order, OrderSide, OrderStatus, Position, Trade,
)

logger = logging.getLogger("antigravity.engine.portfolio")


class Portfolio:
    """
    Tracks the portfolio state during strategy execution.
    
    Handles:
    - Position tracking (average price, quantity)
    - P&L calculation (realized + unrealized)
    - Drawdown tracking
    - Trade generation (from position open/close events)
    """

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, Position] = {}  # display_name → Position
        self.trades: list[Trade] = []
        self._peak_equity = initial_capital
        self._total_realized_pnl = 0.0

        # Track entry details for trade generation
        self._entry_orders: dict[str, Order] = {}  # display_name → entry order

    @property
    def total_pnl(self) -> float:
        """Total realized P&L."""
        return self._total_realized_pnl

    def current_equity(self, last_price: float = 0.0) -> float:
        """Cash + unrealized position value."""
        unrealized = sum(p.mtm for p in self.positions.values() if p.is_open)
        return self.cash + unrealized

    @property
    def current_drawdown_pct(self) -> float:
        """Current drawdown from peak equity as percentage."""
        equity = self.cash + sum(p.mtm for p in self.positions.values() if p.is_open)
        if equity > self._peak_equity:
            self._peak_equity = equity
        if self._peak_equity == 0:
            return 0.0
        return ((self._peak_equity - equity) / self._peak_equity) * 100

    def process_fill(self, order: Order) -> Optional[Trade]:
        """
        Process a filled order and update positions.
        Returns a Trade if a position was closed.
        """
        if order.status != OrderStatus.FILLED:
            return None

        key = order.instrument.display_name
        pos = self.positions.get(key)
        trade = None

        if pos is None or not pos.is_open:
            # New position
            qty = order.quantity if order.side == OrderSide.BUY else -order.quantity
            self.positions[key] = Position(
                instrument=order.instrument,
                quantity=qty,
                avg_price=order.avg_fill_price,
                ltp=order.avg_fill_price,
                strategy_id=order.strategy_id,
            )
            self._entry_orders[key] = order

            # Update cash
            self.cash -= abs(order.quantity * order.avg_fill_price)

        else:
            # Existing position
            old_qty = pos.quantity
            fill_qty = order.quantity if order.side == OrderSide.BUY else -order.quantity
            new_qty = old_qty + fill_qty

            if (old_qty > 0 and fill_qty > 0) or (old_qty < 0 and fill_qty < 0):
                # Adding to position — update average price
                total_cost = (pos.avg_price * abs(old_qty)) + (order.avg_fill_price * abs(fill_qty))
                new_avg = total_cost / abs(new_qty)
                self.positions[key] = Position(
                    instrument=order.instrument,
                    quantity=new_qty,
                    avg_price=new_avg,
                    ltp=order.avg_fill_price,
                    strategy_id=order.strategy_id,
                )
            else:
                # Closing (fully or partially)
                closed_qty = min(abs(old_qty), abs(fill_qty))

                # Calculate P&L
                if old_qty > 0:  # Was long, closing by selling
                    pnl = (order.avg_fill_price - pos.avg_price) * closed_qty
                else:  # Was short, closing by buying
                    pnl = (pos.avg_price - order.avg_fill_price) * closed_qty

                self._total_realized_pnl += pnl
                self.cash += abs(closed_qty * order.avg_fill_price) + pnl

                # Generate trade record
                entry_order = self._entry_orders.get(key)
                trade = Trade(
                    id=str(uuid.uuid4())[:8],
                    strategy_id=order.strategy_id,
                    instrument=order.instrument,
                    side=OrderSide.BUY if old_qty > 0 else OrderSide.SELL,
                    entry_price=pos.avg_price,
                    exit_price=order.avg_fill_price,
                    quantity=closed_qty,
                    entry_time=entry_order.filled_at if entry_order else order.created_at or datetime.now(),
                    exit_time=order.filled_at or datetime.now(),
                    pnl=pnl,
                    meta=order.meta,
                )
                self.trades.append(trade)

                # Update or close position
                if new_qty == 0:
                    self.positions[key] = Position(
                        instrument=order.instrument,
                        quantity=0,
                        avg_price=0.0,
                        strategy_id=order.strategy_id,
                    )
                    if key in self._entry_orders:
                        del self._entry_orders[key]
                else:
                    # Partial close — remaining position continues
                    self.positions[key] = Position(
                        instrument=order.instrument,
                        quantity=new_qty,
                        avg_price=pos.avg_price if abs(new_qty) < abs(old_qty) else order.avg_fill_price,
                        ltp=order.avg_fill_price,
                        strategy_id=order.strategy_id,
                    )
                    if (old_qty > 0 and new_qty < 0) or (old_qty < 0 and new_qty > 0):
                        # Reversed position — new entry
                        self._entry_orders[key] = order

                logger.debug(
                    "Trade closed: %s %s P&L=₹%.2f",
                    trade.side.value, trade.instrument.display_name, pnl,
                )

        # Update peak equity
        equity = self.current_equity(order.avg_fill_price)
        if equity > self._peak_equity:
            self._peak_equity = equity

        return trade

    def update_ltp(self, instrument: Instrument, ltp: float) -> None:
        """Update last traded price for MTM calculation."""
        key = instrument.display_name
        if key in self.positions:
            pos = self.positions[key]
            self.positions[key] = Position(
                instrument=pos.instrument,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                ltp=ltp,
                pnl=pos.pnl,
                strategy_id=pos.strategy_id,
            )
