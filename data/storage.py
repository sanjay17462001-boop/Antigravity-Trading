"""
Antigravity Trading — Data Storage Engine
Parquet for candle data, SQLite for metadata/strategies/trades.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from core.config import get_settings, CANDLES_DIR, DB_PATH
from core.models import Candle, Instrument, Interval, Trade

logger = logging.getLogger("antigravity.data.storage")


class DataStorage:
    """
    Manages persistent storage for the platform.
    
    Candle data → Parquet files (fast columnar reads for backtest)
    Strategies, trades, results → SQLite (structured queries)
    """

    def __init__(self):
        settings = get_settings()
        self._candles_dir = Path(settings.data.candles_dir)
        self._db_path = Path(settings.data.db_path)
        self._candles_dir.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # SQLite initialization
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create SQLite tables if they don't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    version INTEGER DEFAULT 1,
                    code TEXT DEFAULT '',
                    params TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    params TEXT DEFAULT '{}',
                    result_summary TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'running',
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                );

                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    run_id TEXT,
                    strategy_id TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    pnl REAL DEFAULT 0,
                    charges REAL DEFAULT 0,
                    slippage REAL DEFAULT 0,
                    meta TEXT DEFAULT '{}',
                    mode TEXT DEFAULT 'backtest',
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                );

                CREATE TABLE IF NOT EXISTS signals_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    strategy_id TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    strength REAL DEFAULT 100,
                    reason TEXT DEFAULT '',
                    mode TEXT DEFAULT 'backtest'
                );

                CREATE TABLE IF NOT EXISTS data_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    from_date TEXT NOT NULL,
                    to_date TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    row_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, exchange, segment, interval, from_date, to_date)
                );

                CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id);
                CREATE INDEX IF NOT EXISTS idx_trades_run ON trades(run_id);
                CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals_log(strategy_id);
                CREATE INDEX IF NOT EXISTS idx_catalog_symbol ON data_catalog(symbol, exchange);
            """)
            logger.debug("SQLite database initialized at %s", self._db_path)

    # ------------------------------------------------------------------
    # Candle data (Parquet)
    # ------------------------------------------------------------------

    def _candle_path(self, instrument: Instrument, interval: Interval) -> Path:
        """Get the Parquet file path for an instrument/interval."""
        safe_symbol = instrument.symbol.replace(" ", "_")
        exchange = instrument.exchange.value
        segment = instrument.segment.value
        subdir = self._candles_dir / exchange / segment
        subdir.mkdir(parents=True, exist_ok=True)

        # Include expiry/strike for derivatives
        if instrument.is_option and instrument.expiry and instrument.strike:
            fname = (
                f"{safe_symbol}_{instrument.expiry.strftime('%Y%m%d')}"
                f"_{int(instrument.strike)}_{instrument.option_type.value}"
                f"_{interval.value}.parquet"
            )
        elif instrument.is_derivative and instrument.expiry:
            fname = (
                f"{safe_symbol}_{instrument.expiry.strftime('%Y%m%d')}"
                f"_FUT_{interval.value}.parquet"
            )
        else:
            fname = f"{safe_symbol}_{interval.value}.parquet"

        return subdir / fname

    def save_candles(self, candles: list[Candle], instrument: Instrument, interval: Interval) -> Path:
        """Save candles to Parquet file (append or create)."""
        if not candles:
            return Path()

        df = pd.DataFrame([{
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "oi": c.oi,
        } for c in candles])

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"])

        path = self._candle_path(instrument, interval)

        # Append to existing file
        if path.exists():
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df]).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

        df.to_parquet(path, index=False, engine="pyarrow")

        # Update catalog
        self._update_catalog(
            instrument, interval,
            df["timestamp"].min().isoformat(),
            df["timestamp"].max().isoformat(),
            str(path), len(df),
        )

        logger.info("Saved %d candles to %s", len(df), path.name)
        return path

    def load_candles(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Load candles from Parquet file, optionally filtered by date range."""
        path = self._candle_path(instrument, interval)

        if not path.exists():
            logger.warning("No data file found: %s", path)
            return pd.DataFrame()

        df = pd.read_parquet(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        if from_dt:
            df = df[df["timestamp"] >= pd.Timestamp(from_dt)]
        if to_dt:
            df = df[df["timestamp"] <= pd.Timestamp(to_dt)]

        return df.sort_values("timestamp").reset_index(drop=True)

    def has_data(self, instrument: Instrument, interval: Interval) -> bool:
        """Check if Parquet data exists for an instrument/interval."""
        return self._candle_path(instrument, interval).exists()

    def get_data_range(self, instrument: Instrument, interval: Interval) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get the date range of existing data."""
        path = self._candle_path(instrument, interval)
        if not path.exists():
            return None, None

        df = pd.read_parquet(path, columns=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df["timestamp"].min().to_pydatetime(), df["timestamp"].max().to_pydatetime()

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    def _update_catalog(self, instrument, interval, from_date, to_date, file_path, row_count):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO data_catalog 
                (symbol, exchange, segment, interval, from_date, to_date, file_path, row_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                instrument.symbol, instrument.exchange.value, instrument.segment.value,
                interval.value, from_date, to_date, file_path, row_count,
                datetime.now().isoformat(),
            ))

    # ------------------------------------------------------------------
    # Trades (SQLite)
    # ------------------------------------------------------------------

    def save_trade(self, trade: Trade, run_id: str = "", mode: str = "backtest") -> None:
        """Save a completed trade."""
        import json
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trades 
                (id, run_id, strategy_id, instrument, side, entry_price, exit_price,
                 quantity, entry_time, exit_time, pnl, charges, slippage, meta, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id, run_id, trade.strategy_id, trade.instrument.display_name,
                trade.side.value, trade.entry_price, trade.exit_price,
                trade.quantity, trade.entry_time.isoformat(), trade.exit_time.isoformat(),
                trade.pnl, trade.charges, trade.slippage,
                json.dumps(trade.meta), mode,
            ))

    def get_trades(self, strategy_id: str = "", run_id: str = "", mode: str = "") -> list[dict]:
        """Query trades with optional filters."""
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        if strategy_id:
            query += " AND strategy_id = ?"
            params.append(strategy_id)
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        if mode:
            query += " AND mode = ?"
            params.append(mode)
        query += " ORDER BY entry_time"

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Strategy CRUD
    # ------------------------------------------------------------------

    def save_strategy(self, strategy_id: str, name: str, description: str = "",
                      code: str = "", params: str = "{}") -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO strategies 
                (id, name, description, code, params, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (strategy_id, name, description, code, params, datetime.now().isoformat()))

    def get_strategies(self) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM strategies ORDER BY updated_at DESC").fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Backtest runs
    # ------------------------------------------------------------------

    def save_backtest_run(self, run_id: str, strategy_id: str, params: str = "{}") -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO backtest_runs (id, strategy_id, params)
                VALUES (?, ?, ?)
            """, (run_id, strategy_id, params))

    def complete_backtest_run(self, run_id: str, result_summary: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                UPDATE backtest_runs SET completed_at = ?, result_summary = ?, status = 'completed'
                WHERE id = ?
            """, (datetime.now().isoformat(), result_summary, run_id))
