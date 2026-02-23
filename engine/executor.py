"""
Antigravity Trading — Live Execution Engine
Sends real orders to Bigul (primary) or Kotak Neo (fallback).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from brokers.base import BrokerAPI
from core.event_bus import get_event_bus
from core.exceptions import BrokerOrderError, RiskViolation
from core.models import (
    Candle, Instrument, Order, OrderStatus, Signal, Tick,
)
from data.storage import DataStorage
from engine.portfolio import Portfolio
from engine.risk_manager import RiskManager
from strategy.base import Strategy, StrategyContext

logger = logging.getLogger("antigravity.engine.executor")


class LiveExecutor:
    """
    Live execution engine — sends real orders to the broker.
    
    Flow:
    1. Strategy emits a Signal
    2. Signal → Order conversion
    3. Risk manager validation
    4. Order sent to Bigul (primary) or Kotak Neo (fallback)
    5. Fill tracking and position reconciliation
    
    Safety features:
    - All orders go through RiskManager first
    - Auto square-off at configured time
    - Circuit breaker on max loss
    - Broker failover
    """

    def __init__(
        self,
        primary_broker: BrokerAPI,
        fallback_broker: Optional[BrokerAPI] = None,
        initial_capital: float = 1_000_000.0,
        storage: Optional[DataStorage] = None,
    ):
        self._primary = primary_broker
        self._fallback = fallback_broker
        self._portfolio = Portfolio(initial_capital)
        self._risk = RiskManager(initial_capital)
        self._storage = storage or DataStorage()
        self._strategies: list[Strategy] = []
        self._running = False
        self._bus = get_event_bus()

    def add_strategy(self, strategy: Strategy) -> None:
        """Register a strategy for live execution."""
        self._strategies.append(strategy)
        logger.info("Live executor: Added strategy %s", strategy.name)

    async def start(self) -> None:
        """Start live execution."""
        self._running = True
        self._risk.reset_daily()

        # Initialize strategies
        ctx = StrategyContext()
        ctx.capital = self._portfolio.cash
        for strategy in self._strategies:
            strategy.on_init(ctx)

        # Subscribe to events
        self._bus.subscribe("candle", self._on_candle)
        self._bus.subscribe("tick", self._on_tick)

        logger.info("🔴 LIVE EXECUTOR STARTED — Real money at risk!")

    async def stop(self) -> None:
        """Stop live execution and square off."""
        self._running = False

        # Square off all positions
        for pos_key, pos in self._portfolio.positions.items():
            if pos.is_open:
                logger.warning("Squaring off position: %s x%d", pos_key, pos.quantity)
                try:
                    from core.models import OrderSide, OrderType, ProductType
                    close_order = Order(
                        instrument=pos.instrument,
                        side=OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        product=ProductType.MIS,
                        quantity=abs(pos.quantity),
                        strategy_id="executor_squareoff",
                    )
                    await self._send_order(close_order)
                except Exception as e:
                    logger.error("Square-off failed for %s: %s", pos_key, e)

        for strategy in self._strategies:
            strategy.on_stop()

        self._bus.unsubscribe("candle", self._on_candle)
        self._bus.unsubscribe("tick", self._on_tick)
        logger.info("Live executor stopped")

    async def _on_candle(self, candle: Candle) -> None:
        """Process candle through strategies."""
        if not self._running:
            return

        # Check auto square-off
        if self._risk.should_square_off(candle.instrument.exchange):
            logger.warning("Auto square-off time reached!")
            await self.stop()
            return

        for strategy in self._strategies:
            try:
                strategy.ctx.current_time = candle.timestamp
                strategy.ctx.positions = self._portfolio.positions.copy()
                strategy.ctx.capital = self._portfolio.cash

                signal = strategy.on_candle(candle)

                # Process pending orders
                for order in strategy.ctx.pending_orders:
                    await self._execute_order(order)
                strategy.ctx.pending_orders.clear()

            except Exception as e:
                logger.error("Live strategy error: %s", e, exc_info=True)

    async def _on_tick(self, tick: Tick) -> None:
        """Process tick through strategies."""
        if not self._running:
            return

        for strategy in self._strategies:
            try:
                signal = strategy.on_tick(tick)
            except Exception as e:
                logger.error("Tick error: %s", e)

    async def _execute_order(self, order: Order) -> Optional[str]:
        """Execute an order through risk checks and broker."""
        try:
            # Risk check
            self._risk.pre_trade_check(
                order,
                self._portfolio.positions,
                self._portfolio.total_pnl,
            )

            # Send to broker
            broker_order_id = await self._send_order(order)
            logger.info(
                "🔴 LIVE ORDER: %s %s x%d | Broker ID: %s",
                order.side.value, order.instrument.display_name,
                order.quantity, broker_order_id,
            )
            return broker_order_id

        except RiskViolation as e:
            logger.warning("🚫 Order blocked by risk manager: %s", e)
            return None
        except BrokerOrderError as e:
            logger.error("❌ Order failed: %s", e)
            return None

    async def _send_order(self, order: Order) -> str:
        """Send order to primary broker, fallback to secondary."""
        try:
            return await self._primary.place_order(order)
        except Exception as e:
            logger.warning("Primary broker failed: %s, trying fallback...", e)
            if self._fallback and self._fallback.is_connected:
                return await self._fallback.place_order(order)
            raise

    def get_state(self) -> dict:
        """Get current live execution state."""
        return {
            "running": self._running,
            "broker": self._primary.name,
            "positions": {
                k: {"qty": v.quantity, "avg_price": v.avg_price, "mtm": v.mtm}
                for k, v in self._portfolio.positions.items() if v.is_open
            },
            "total_pnl": self._portfolio.total_pnl,
            "circuit_breaker": self._risk.is_circuit_breaker_active,
            "strategies": [s.name for s in self._strategies],
        }
