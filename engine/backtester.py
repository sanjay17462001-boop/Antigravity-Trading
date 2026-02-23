"""
Antigravity Trading — Event-Driven Backtester
The core backtesting engine that replays historical data through strategies.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd

from core.models import (
    Candle, Instrument, Interval, Order, OrderSide, OrderStatus,
    Position, Signal, Trade,
)
from data.storage import DataStorage
from engine.order_simulator import OrderSimulator
from engine.portfolio import Portfolio
from engine.analytics import PerformanceAnalytics
from strategy.base import Strategy, StrategyContext

logger = logging.getLogger("antigravity.engine.backtester")


class BacktestResult:
    """Container for backtest results."""

    def __init__(self):
        self.trades: list[Trade] = []
        self.signals: list[Signal] = []
        self.equity_curve: list[dict] = []  # [{timestamp, equity, pnl}, ...]
        self.metrics: dict = {}
        self.run_id: str = ""
        self.strategy_id: str = ""
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.params: dict = {}

    def summary(self) -> str:
        """Human-readable summary."""
        m = self.metrics
        return (
            f"\n{'='*60}\n"
            f"  BACKTEST RESULTS -- {self.strategy_id}\n"
            f"{'='*60}\n"
            f"  Period    : {self.started_at} -> {self.completed_at}\n"
            f"  Trades    : {m.get('total_trades', 0)}\n"
            f"  Win Rate  : {m.get('win_rate', 0):.1f}%\n"
            f"  Net P&L   : Rs.{m.get('net_pnl', 0):,.2f}\n"
            f"  Return    : {m.get('total_return_pct', 0):.2f}%\n"
            f"  Max DD    : {m.get('max_drawdown_pct', 0):.2f}%\n"
            f"  Sharpe    : {m.get('sharpe_ratio', 0):.2f}\n"
            f"  Sortino   : {m.get('sortino_ratio', 0):.2f}\n"
            f"  Avg Win   : Rs.{m.get('avg_win', 0):,.2f}\n"
            f"  Avg Loss  : Rs.{m.get('avg_loss', 0):,.2f}\n"
            f"  P. Factor : {m.get('profit_factor', 0):.2f}\n"
            f"{'='*60}\n"
        )


class Backtester:
    """
    Event-driven backtesting engine.
    
    Workflow:
    1. Load historical data
    2. Initialize strategy
    3. Iterate candles chronologically
    4. Feed each candle to strategy
    5. Process signals through order simulator
    6. Track portfolio
    7. Compute performance metrics
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        slippage_pct: float = 0.01,        # 0.01% slippage per trade
        commission_per_order: float = 20.0,  # ₹20 per order
        storage: Optional[DataStorage] = None,
    ):
        self._initial_capital = initial_capital
        self._slippage_pct = slippage_pct
        self._commission = commission_per_order
        self._storage = storage or DataStorage()

    def run(
        self,
        strategy: Strategy,
        instruments: list[Instrument],
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
        data: Optional[dict[str, pd.DataFrame]] = None,
    ) -> BacktestResult:
        """
        Run a backtest.
        
        Args:
            strategy: Strategy instance to test
            instruments: Instruments to trade
            interval: Candle timeframe
            from_dt: Start date
            to_dt: End date
            data: Pre-loaded data dict {instrument.display_name_interval: DataFrame}
                  If None, loads from storage
        """
        run_id = str(uuid.uuid4())[:8]
        logger.info(
            "Starting backtest [%s] -- strategy=%s, instruments=%d, %s to %s",
            run_id, strategy.strategy_id, len(instruments),
            from_dt.date(), to_dt.date(),
        )

        # Initialize components
        portfolio = Portfolio(self._initial_capital)
        order_sim = OrderSimulator(
            slippage_pct=self._slippage_pct,
            commission=self._commission,
        )
        result = BacktestResult()
        result.run_id = run_id
        result.strategy_id = strategy.strategy_id
        result.started_at = from_dt
        result.params = strategy.params

        # Load data
        data_store: dict[str, pd.DataFrame] = {}
        if data:
            data_store = data
        else:
            for inst in instruments:
                key = f"{inst.display_name}_{interval.value}"
                df = self._storage.load_candles(inst, interval, from_dt, to_dt)
                if df.empty:
                    logger.warning("No data for %s", inst.display_name)
                    continue
                data_store[key] = df

        if not data_store:
            logger.error("No data available for any instrument")
            return result

        # Initialize strategy context
        ctx = StrategyContext()
        ctx.capital = self._initial_capital
        ctx._data_store = {}  # Will be updated slice-by-slice
        strategy.on_init(ctx)

        # Build chronological candle sequence
        all_candles = self._build_candle_sequence(instruments, data_store, interval)
        total_candles = len(all_candles)
        logger.info("Processing %d candles...", total_candles)

        # Main loop
        for i, (timestamp, instrument, candle_row) in enumerate(all_candles):
            candle = Candle(
                timestamp=timestamp,
                open=candle_row["open"],
                high=candle_row["high"],
                low=candle_row["low"],
                close=candle_row["close"],
                volume=int(candle_row.get("volume", 0)),
                oi=int(candle_row.get("oi", 0)),
                instrument=instrument,
                interval=interval,
            )

            # Update context
            ctx.current_time = timestamp
            ctx.positions = portfolio.positions.copy()
            ctx.capital = portfolio.cash

            # Update data store with data up to current bar
            for inst in instruments:
                key = f"{inst.display_name}_{interval.value}"
                if key in data_store:
                    full_df = data_store[key]
                    ctx._data_store[key] = full_df[full_df["timestamp"] <= timestamp]

            # Process pending orders from previous bar
            fills = order_sim.process_orders(ctx.pending_orders, candle)
            ctx.pending_orders.clear()

            for fill in fills:
                trade = portfolio.process_fill(fill)
                if trade:
                    result.trades.append(trade)
                    strategy.on_order_update(fill)

            # Feed candle to strategy
            try:
                signal = strategy.on_candle(candle)
                if signal:
                    result.signals.append(signal)
            except Exception as e:
                logger.error(
                    "Strategy error at %s: %s", timestamp, e, exc_info=True,
                )

            # Record equity curve point (every N candles to save memory)
            if i % max(1, total_candles // 1000) == 0 or i == total_candles - 1:
                result.equity_curve.append({
                    "timestamp": timestamp.isoformat(),
                    "equity": portfolio.current_equity(candle.close),
                    "pnl": portfolio.total_pnl,
                    "drawdown": portfolio.current_drawdown_pct,
                })

            # Progress logging
            if i > 0 and i % 5000 == 0:
                logger.info(
                    "  Progress: %d/%d (%.0f%%) | P&L: Rs.%.2f | Trades: %d",
                    i, total_candles, i / total_candles * 100,
                    portfolio.total_pnl, len(result.trades),
                )

        # Cleanup — close any remaining positions at last price
        strategy.on_stop()

        # Compute metrics
        result.completed_at = to_dt
        analytics = PerformanceAnalytics(
            trades=result.trades,
            equity_curve=result.equity_curve,
            initial_capital=self._initial_capital,
        )
        result.metrics = analytics.compute_all()

        # Persist results
        self._save_results(result)

        logger.info(result.summary())
        return result

    def _build_candle_sequence(
        self,
        instruments: list[Instrument],
        data_store: dict[str, pd.DataFrame],
        interval: Interval,
    ) -> list[tuple]:
        """Build a chronologically sorted sequence of (timestamp, instrument, row)."""
        sequence = []

        for inst in instruments:
            key = f"{inst.display_name}_{interval.value}"
            if key not in data_store:
                continue
            df = data_store[key]
            for _, row in df.iterrows():
                sequence.append((row["timestamp"], inst, row))

        sequence.sort(key=lambda x: x[0])
        return sequence

    def _save_results(self, result: BacktestResult) -> None:
        """Persist backtest results to SQLite."""
        try:
            self._storage.save_backtest_run(
                result.run_id,
                result.strategy_id,
                json.dumps(result.params),
            )

            for trade in result.trades:
                self._storage.save_trade(trade, result.run_id, mode="backtest")

            self._storage.complete_backtest_run(
                result.run_id,
                json.dumps(result.metrics, default=str),
            )
        except Exception as e:
            logger.error("Failed to save backtest results: %s", e)
