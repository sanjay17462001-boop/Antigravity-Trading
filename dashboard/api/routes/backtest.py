"""
Dashboard API — Backtest Routes
Run backtests and retrieve results.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.models import Exchange, Instrument, Interval, Segment
from data.storage import DataStorage
from engine.backtester import Backtester
from strategy.examples.simple_ma_crossover import MACrossoverStrategy

router = APIRouter()
logger = logging.getLogger("antigravity.dashboard.backtest")
storage = DataStorage()


class BacktestRequest(BaseModel):
    strategy_id: str = "ma_crossover"
    symbol: str = "NIFTY"
    exchange: str = "NFO"
    segment: str = "FUTURES"
    interval: str = "5m"
    from_date: str = "2024-01-01"
    to_date: str = "2024-12-31"
    initial_capital: float = 1_000_000
    params: dict = {}


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """Run a backtest with specified parameters."""
    try:
        # Create instrument
        instrument = Instrument(
            symbol=request.symbol,
            exchange=Exchange(request.exchange),
            segment=Segment(request.segment),
        )

        # Create strategy
        if request.strategy_id == "ma_crossover":
            strategy = MACrossoverStrategy(params=request.params)
        else:
            raise HTTPException(400, f"Unknown strategy: {request.strategy_id}")

        # Run backtest
        backtester = Backtester(
            initial_capital=request.initial_capital,
            storage=storage,
        )

        result = backtester.run(
            strategy=strategy,
            instruments=[instrument],
            interval=Interval(request.interval),
            from_dt=datetime.strptime(request.from_date, "%Y-%m-%d"),
            to_dt=datetime.strptime(request.to_date, "%Y-%m-%d"),
        )

        return {
            "run_id": result.run_id,
            "strategy_id": result.strategy_id,
            "metrics": result.metrics,
            "trades_count": len(result.trades),
            "signals_count": len(result.signals),
            "equity_curve_points": len(result.equity_curve),
        }

    except Exception as e:
        logger.error("Backtest failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Backtest failed: {str(e)}")


@router.get("/results/{run_id}")
async def get_backtest_results(run_id: str):
    """Get detailed results for a backtest run."""
    trades = storage.get_trades(run_id=run_id)
    if not trades:
        raise HTTPException(404, "Backtest run not found")

    return {
        "run_id": run_id,
        "trades": trades,
        "count": len(trades),
    }


@router.get("/history")
async def backtest_history():
    """Get all backtest runs."""
    import sqlite3
    from core.config import get_settings
    settings = get_settings()
    db_path = settings.data.db_path

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM backtest_runs ORDER BY started_at DESC LIMIT 50"
        ).fetchall()

    return {"runs": [dict(r) for r in rows]}
