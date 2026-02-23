"""
Dashboard API — Data Routes
Access market data, instruments, and data catalog.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.models import Exchange, Instrument, Interval, Segment
from data.storage import DataStorage

router = APIRouter()
logger = logging.getLogger("antigravity.dashboard.data")
storage = DataStorage()


@router.get("/instruments")
async def search_instruments(
    symbol: str = Query("", description="Symbol to search"),
    exchange: str = Query("", description="Exchange filter"),
    segment: str = Query("", description="Segment filter"),
    limit: int = Query(50, description="Max results"),
):
    """Search instruments in the master."""
    from data.instruments import InstrumentManager
    mgr = InstrumentManager()

    instruments = mgr.search(
        symbol=symbol,
        exchange=Exchange(exchange) if exchange else None,
        segment=Segment(segment) if segment else None,
        limit=limit,
    )

    return {
        "instruments": [
            {
                "symbol": i.symbol,
                "exchange": i.exchange.value,
                "segment": i.segment.value,
                "display_name": i.display_name,
                "lot_size": i.lot_size,
                "expiry": i.expiry.isoformat() if i.expiry else None,
                "strike": i.strike,
                "option_type": i.option_type.value if i.option_type else None,
            }
            for i in instruments
        ],
        "count": len(instruments),
    }


@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Instrument symbol"),
    exchange: str = Query("NSE", description="Exchange"),
    segment: str = Query("INDEX", description="Segment"),
    interval: str = Query("5m", description="Candle interval"),
    from_date: str = Query("", description="From date (YYYY-MM-DD)"),
    to_date: str = Query("", description="To date (YYYY-MM-DD)"),
):
    """Get historical candle data."""
    instrument = Instrument(
        symbol=symbol,
        exchange=Exchange(exchange),
        segment=Segment(segment),
    )

    from_dt = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
    to_dt = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None

    df = storage.load_candles(instrument, Interval(interval), from_dt, to_dt)

    if df.empty:
        return {"candles": [], "count": 0}

    candles = df.to_dict("records")
    # Convert timestamps to ISO strings
    for c in candles:
        if "timestamp" in c:
            c["timestamp"] = str(c["timestamp"])

    return {"candles": candles, "count": len(candles)}


@router.get("/catalog")
async def data_catalog():
    """Get the data catalog — what data is available."""
    import sqlite3
    from core.config import get_settings
    settings = get_settings()

    with sqlite3.connect(settings.data.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM data_catalog ORDER BY symbol, exchange"
        ).fetchall()

    return {"catalog": [dict(r) for r in rows]}
