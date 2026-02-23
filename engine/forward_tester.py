"""
Antigravity Trading — Forward Tester (Paper Trading Engine)
Runs strategies against live market data with virtual orders.
No real money at risk — perfect for validating strategies.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from core.event_bus import get_event_bus
from core.models import (
    Candle, Instrument, Interval, Order, Signal, Tick,
)
from data.storage import DataStorage
from engine.order_simulator import OrderSimulator
from engine.portfolio import Portfolio
from engine.analytics import PerformanceAnalytics
from strategy.base import Strategy, StrategyContext

logger = logging.getLogger("antigravity.engine.forward_tester")


class ForwardTester:
    """
    Paper trading engine — runs strategies on live data with virtual orders.
    
    Modes:
    1. LIVE: Consumes real-time feed from Bigul/Kotak Neo
    2. REPLAY: Replays historical data at configurable speed
    
    All trades are virtual — no real orders sent to broker.
    Records everything to SQLite for later analysis.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        slippage_pct: float = 0.02,        # Slightly higher for paper
        commission: float = 20.0,
        storage: Optional[DataStorage] = None,
    ):
        self._initial_capital = initial_capital
        self._portfolio = Portfolio(initial_capital)
        self._order_sim = OrderSimulator(slippage_pct, commission)
        self._storage = storage or DataStorage()
        self._strategies: list[Strategy] = []
        self._running = False
        self._run_id = ""
        self._bus = get_event_bus()

        # Metrics tracking
        self._signals: list[Signal] = []
        self._equity_curve: list[dict] = []

    @property
    def is_running(self) -> bool:
        return self._running

    def add_strategy(self, strategy: Strategy) -> None:
        """Register a strategy for forward testing."""
        self._strategies.append(strategy)
        logger.info("Added strategy: %s", strategy.name)

    async def start(self) -> None:
        """Start the forward tester."""
        self._run_id = str(uuid.uuid4())[:8]
        self._running = True

        # Initialize strategy contexts
        ctx = StrategyContext()
        ctx.capital = self._initial_capital
        for strategy in self._strategies:
            strategy.on_init(ctx)

        # Subscribe to event bus
        self._bus.subscribe("candle", self._on_candle)
        self._bus.subscribe("tick", self._on_tick)

        logger.info(
            "Forward tester started [%s] with %d strategies",
            self._run_id, len(self._strategies),
        )

    async def stop(self) -> dict:
        """Stop the forward tester and return results."""
        self._running = False

        # Stop strategies
        for strategy in self._strategies:
            strategy.on_stop()

        # Unsubscribe from events
        self._bus.unsubscribe("candle", self._on_candle)
        self._bus.unsubscribe("tick", self._on_tick)

        # Compute final metrics
        analytics = PerformanceAnalytics(
            trades=self._portfolio.trades,
            equity_curve=self._equity_curve,
            initial_capital=self._initial_capital,
        )
        metrics = analytics.compute_all()

        # Save results
        try:
            self._storage.save_backtest_run(
                self._run_id,
                ",".join(s.strategy_id for s in self._strategies),
                json.dumps({"mode": "forward_test"}),
            )
            for trade in self._portfolio.trades:
                self._storage.save_trade(trade, self._run_id, mode="paper")
            self._storage.complete_backtest_run(self._run_id, json.dumps(metrics, default=str))
        except Exception as e:
            logger.error("Failed to save paper trading results: %s", e)

        logger.info("Forward tester stopped [%s]. Trades: %d, P&L: ₹%.2f",
                     self._run_id, len(self._portfolio.trades), self._portfolio.total_pnl)

        return metrics

    async def _on_candle(self, candle: Candle) -> None:
        """Process a new candle through all strategies."""
        if not self._running:
            return

        for strategy in self._strategies:
            try:
                # Update context
                strategy.ctx.current_time = candle.timestamp
                strategy.ctx.positions = self._portfolio.positions.copy()
                strategy.ctx.capital = self._portfolio.cash

                # Process pending orders
                fills = self._order_sim.process_orders(
                    strategy.ctx.pending_orders, candle
                )
                strategy.ctx.pending_orders.clear()

                for fill in fills:
                    trade = self._portfolio.process_fill(fill)
                    if trade:
                        strategy.on_order_update(fill)
                        logger.info(
                            "📝 Paper trade: %s %s P&L=₹%.2f",
                            trade.side.value, trade.instrument.display_name, trade.pnl,
                        )

                # Feed candle
                signal = strategy.on_candle(candle)
                if signal:
                    self._signals.append(signal)
                    await self._bus.publish("signal", signal)

            except Exception as e:
                logger.error("Forward test error in %s: %s", strategy.name, e, exc_info=True)

        # Record equity
        self._equity_curve.append({
            "timestamp": candle.timestamp.isoformat(),
            "equity": self._portfolio.current_equity(candle.close),
            "pnl": self._portfolio.total_pnl,
        })

    async def _on_tick(self, tick: Tick) -> None:
        """Process a tick through strategies that implement on_tick."""
        if not self._running:
            return

        for strategy in self._strategies:
            try:
                signal = strategy.on_tick(tick)
                if signal:
                    self._signals.append(signal)
            except Exception as e:
                logger.error("Tick processing error in %s: %s", strategy.name, e)

    def get_state(self) -> dict:
        """Get current forward test state for dashboard."""
        return {
            "run_id": self._run_id,
            "running": self._running,
            "capital": self._portfolio.cash,
            "positions": {
                k: {"qty": v.quantity, "avg_price": v.avg_price, "pnl": v.mtm}
                for k, v in self._portfolio.positions.items() if v.is_open
            },
            "trades_count": len(self._portfolio.trades),
            "total_pnl": self._portfolio.total_pnl,
            "signals_count": len(self._signals),
            "strategies": [s.name for s in self._strategies],
        }
