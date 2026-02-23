"""
Antigravity Trading — Strategy Base Class
Flexible framework for writing custom strategies.

Your strategies can be as simple or complex as you want.
The base class provides helper methods, but doesn't force any pattern.
You can override any hook or ignore the ones you don't need.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from core.models import (
    Candle, Instrument, Interval, Order, OrderSide, OrderType,
    Position, ProductType, Signal, SignalDirection, Tick,
)

logger = logging.getLogger("antigravity.strategy")


class StrategyContext:
    """
    Runtime context provided to strategies by the engine.
    
    Contains:
    - Current portfolio state
    - Data access methods
    - Order submission methods
    
    The engine (backtester / forward tester / live) injects the appropriate
    context, so your strategy code works identically across all modes.
    """

    def __init__(self):
        self.capital: float = 0.0
        self.positions: dict[str, Position] = {}  # instrument.display_name → Position
        self.pending_orders: list[Order] = []
        self.trades: list = []
        self.signals: list[Signal] = []
        self.current_time: datetime = datetime.now()

        # Data access (set by engine)
        self._data_store: dict[str, pd.DataFrame] = {}  # key → DataFrame
        self._order_callback: Optional[callable] = None

    def get_data(self, instrument: Instrument, interval: Interval = Interval.M5) -> pd.DataFrame:
        """Get historical data for an instrument (up to current bar)."""
        key = f"{instrument.display_name}_{interval.value}"
        return self._data_store.get(key, pd.DataFrame())

    def get_position(self, instrument: Instrument) -> Optional[Position]:
        """Get current position for an instrument."""
        return self.positions.get(instrument.display_name)

    @property
    def total_pnl(self) -> float:
        """Total realized + unrealized P&L."""
        realized = sum(t.pnl for t in self.trades if hasattr(t, 'pnl'))
        unrealized = sum(p.mtm for p in self.positions.values())
        return realized + unrealized

    @property
    def open_positions(self) -> list[Position]:
        """All open positions."""
        return [p for p in self.positions.values() if p.is_open]


class Strategy(ABC):
    """
    Base class for all trading strategies.
    
    DESIGN PHILOSOPHY:
    This is a framework, NOT a template. Your strategy logic can be as
    unique as you want. The base class just provides:
    
    1. Lifecycle hooks (on_init, on_candle, on_tick, etc.)
    2. Helper methods (buy, sell, get_indicator, etc.)
    3. A context object with portfolio state and data access
    
    You choose which hooks to override. A simple strategy might only use
    on_candle(). A complex options strategy might use on_tick() + on_candle()
    + custom methods you define yourself.
    
    EXAMPLES:
    - Simple: Override on_candle(), call self.buy() / self.sell()
    - Indicator-based: Use self.get_indicator() in on_candle()
    - Options: Use options module directly, create spreads manually
    - Multi-timeframe: Subscribe to multiple intervals, cross-reference
    - Event-driven: Override on_tick() for tick-level logic
    - Hybrid: Mix candle + tick + custom signals + external data
    """

    def __init__(self, strategy_id: str, name: str = "", params: dict[str, Any] | None = None):
        self.strategy_id = strategy_id
        self.name = name or strategy_id
        self.params = params or {}
        self.ctx: StrategyContext = StrategyContext()
        self._logger = logging.getLogger(f"antigravity.strategy.{strategy_id}")

    # ------------------------------------------------------------------
    # Lifecycle hooks — override what you need
    # ------------------------------------------------------------------

    def on_init(self, ctx: StrategyContext) -> None:
        """
        Called once when strategy starts.
        Use this to:
        - Set up indicators
        - Define your instruments
        - Initialize any state
        """
        self.ctx = ctx

    @abstractmethod
    def on_candle(self, candle: Candle) -> Optional[Signal]:
        """
        Called on each new candle. This is the primary hook.
        
        Return a Signal to generate a trade, or None to do nothing.
        You can also call self.buy() / self.sell() directly instead.
        """
        ...

    def on_tick(self, tick: Tick) -> Optional[Signal]:
        """
        Called on each market tick (live/forward test only).
        Override for tick-level strategies (scalping, options gamma).
        Default: does nothing.
        """
        return None

    def on_signal(self, signal: Signal) -> None:
        """
        Called when another strategy emits a signal.
        Use for strategy chaining / multi-strategy coordination.
        """
        pass

    def on_order_update(self, order: Order) -> None:
        """
        Called when an order status changes (filled, rejected, etc.)
        Use for order management logic.
        """
        pass

    def on_stop(self) -> None:
        """
        Called when strategy is stopped.
        Cleanup any resources.
        """
        pass

    # ------------------------------------------------------------------
    # Helper methods — convenience wrappers
    # ------------------------------------------------------------------

    def buy(
        self,
        instrument: Instrument,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: float = 0.0,
        trigger_price: float = 0.0,
        product: ProductType = ProductType.MIS,
        tag: str = "",
        meta: dict[str, Any] | None = None,
    ) -> Order:
        """Create a buy order."""
        order = Order(
            instrument=instrument,
            side=OrderSide.BUY,
            order_type=order_type,
            product=product,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            strategy_id=self.strategy_id,
            tag=tag or self.name,
            created_at=self.ctx.current_time,
            meta=meta or {},
        )
        self.ctx.pending_orders.append(order)
        self._logger.debug("BUY %s x%d @ %s", instrument.display_name, quantity, price or "MARKET")
        return order

    def sell(
        self,
        instrument: Instrument,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: float = 0.0,
        trigger_price: float = 0.0,
        product: ProductType = ProductType.MIS,
        tag: str = "",
        meta: dict[str, Any] | None = None,
    ) -> Order:
        """Create a sell order."""
        order = Order(
            instrument=instrument,
            side=OrderSide.SELL,
            order_type=order_type,
            product=product,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            strategy_id=self.strategy_id,
            tag=tag or self.name,
            created_at=self.ctx.current_time,
            meta=meta or {},
        )
        self.ctx.pending_orders.append(order)
        self._logger.debug("SELL %s x%d @ %s", instrument.display_name, quantity, price or "MARKET")
        return order

    def close_position(self, instrument: Instrument, tag: str = "") -> Optional[Order]:
        """Close an existing position."""
        pos = self.ctx.get_position(instrument)
        if pos and pos.is_open:
            if pos.quantity > 0:
                return self.sell(instrument, abs(pos.quantity), tag=tag or "close")
            elif pos.quantity < 0:
                return self.buy(instrument, abs(pos.quantity), tag=tag or "close")
        return None

    def close_all(self) -> list[Order]:
        """Close all open positions."""
        orders = []
        for pos in self.ctx.open_positions:
            order = self.close_position(pos.instrument, tag="close_all")
            if order:
                orders.append(order)
        return orders

    def get_indicator(self, name: str, data: pd.DataFrame, **kwargs) -> pd.Series | pd.DataFrame:
        """
        Calculate a technical indicator.
        
        Args:
            name: Indicator name (e.g. "sma", "ema", "rsi", "macd")
            data: DataFrame with OHLCV columns
            **kwargs: Indicator parameters (e.g. length=14)
            
        Returns:
            Series or DataFrame with indicator values
        """
        from strategy.indicators import calculate_indicator
        return calculate_indicator(name, data, **kwargs)

    def log(self, msg: str, *args) -> None:
        """Log a strategy-specific message."""
        self._logger.info(msg, *args)

    def __repr__(self) -> str:
        return f"<Strategy:{self.strategy_id} '{self.name}'>"
