"""
Antigravity Trading — Instrument Manager
Unified instrument master across all brokers with exchange token mapping.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from core.config import get_settings, STORAGE_DIR
from core.exceptions import InstrumentNotFoundError
from core.models import (
    Exchange, Instrument, OptionType, Segment,
)

logger = logging.getLogger("antigravity.data.instruments")

INSTRUMENT_DB = STORAGE_DIR / "instruments.db"


class InstrumentManager:
    """
    Unified instrument master — maps symbols across Dhan, Bigul, Kotak Neo.
    
    Key features:
    - Auto-loads from broker APIs
    - Search by symbol, exchange, segment
    - Option chain builder (all strikes for an expiry)
    - Futures chain (current + next expiry)
    """

    def __init__(self):
        self._db_path = INSTRUMENT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS instruments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    dhan_security_id TEXT DEFAULT '',
                    bigul_exchange_instrument_id TEXT DEFAULT '',
                    kotak_instrument_token TEXT DEFAULT '',
                    expiry TEXT,
                    strike REAL,
                    option_type TEXT,
                    lot_size INTEGER DEFAULT 1,
                    tick_size REAL DEFAULT 0.05,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, exchange, segment, expiry, strike, option_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_inst_symbol ON instruments(symbol);
                CREATE INDEX IF NOT EXISTS idx_inst_exchange ON instruments(exchange, segment);
                CREATE INDEX IF NOT EXISTS idx_inst_expiry ON instruments(expiry);
            """)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(
        self,
        symbol: str,
        exchange: Exchange,
        segment: Segment = Segment.EQUITY,
        expiry: Optional[datetime] = None,
        strike: Optional[float] = None,
        option_type: Optional[OptionType] = None,
    ) -> Instrument:
        """Find a specific instrument."""
        query = "SELECT * FROM instruments WHERE symbol = ? AND exchange = ? AND segment = ?"
        params: list = [symbol, exchange.value, segment.value]

        if expiry:
            query += " AND expiry = ?"
            params.append(expiry.strftime("%Y-%m-%d"))
        else:
            query += " AND expiry IS NULL"

        if strike is not None:
            query += " AND strike = ?"
            params.append(strike)

        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.value)

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, params).fetchone()

        if not row:
            raise InstrumentNotFoundError(symbol, exchange.value)

        return self._row_to_instrument(dict(row))

    def search(
        self,
        symbol: str = "",
        exchange: Optional[Exchange] = None,
        segment: Optional[Segment] = None,
        expiry_from: Optional[datetime] = None,
        expiry_to: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Instrument]:
        """Search instruments with flexible filters."""
        query = "SELECT * FROM instruments WHERE 1=1"
        params: list = []

        if symbol:
            query += " AND symbol LIKE ?"
            params.append(f"%{symbol}%")
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange.value)
        if segment:
            query += " AND segment = ?"
            params.append(segment.value)
        if expiry_from:
            query += " AND expiry >= ?"
            params.append(expiry_from.strftime("%Y-%m-%d"))
        if expiry_to:
            query += " AND expiry <= ?"
            params.append(expiry_to.strftime("%Y-%m-%d"))

        query += f" ORDER BY symbol, expiry, strike LIMIT {limit}"

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_instrument(dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Option chain
    # ------------------------------------------------------------------

    def get_option_chain(
        self,
        symbol: str,
        exchange: Exchange,
        expiry: datetime,
        strike_from: Optional[float] = None,
        strike_to: Optional[float] = None,
    ) -> dict[float, dict[str, Instrument]]:
        """
        Get full option chain for a symbol/expiry.
        
        Returns:
            {strike: {"CE": Instrument, "PE": Instrument}, ...}
        """
        query = """
            SELECT * FROM instruments 
            WHERE symbol = ? AND exchange = ? AND segment = 'OPTIONS' AND expiry = ?
        """
        params: list = [symbol, exchange.value, expiry.strftime("%Y-%m-%d")]

        if strike_from is not None:
            query += " AND strike >= ?"
            params.append(strike_from)
        if strike_to is not None:
            query += " AND strike <= ?"
            params.append(strike_to)

        query += " ORDER BY strike, option_type"

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        chain: dict[float, dict[str, Instrument]] = {}
        for row in rows:
            inst = self._row_to_instrument(dict(row))
            if inst.strike is not None and inst.option_type:
                if inst.strike not in chain:
                    chain[inst.strike] = {}
                chain[inst.strike][inst.option_type.value] = inst

        return chain

    def get_futures_chain(
        self,
        symbol: str,
        exchange: Exchange,
    ) -> list[Instrument]:
        """Get all active futures for a symbol, sorted by expiry."""
        today = datetime.now().strftime("%Y-%m-%d")
        query = """
            SELECT * FROM instruments 
            WHERE symbol = ? AND exchange = ? AND segment = 'FUTURES' AND expiry >= ?
            ORDER BY expiry
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (symbol, exchange.value, today)).fetchall()

        return [self._row_to_instrument(dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # ATM/ITM/OTM helpers
    # ------------------------------------------------------------------

    def get_atm_strike(self, spot_price: float, tick_size: float = 50.0) -> float:
        """Calculate ATM strike from spot price."""
        return round(spot_price / tick_size) * tick_size

    def get_strikes_around_atm(
        self,
        symbol: str,
        exchange: Exchange,
        expiry: datetime,
        spot_price: float,
        num_strikes: int = 10,
        tick_size: float = 50.0,
    ) -> dict[float, dict[str, Instrument]]:
        """Get N strikes above and below ATM."""
        atm = self.get_atm_strike(spot_price, tick_size)
        strike_from = atm - (num_strikes * tick_size)
        strike_to = atm + (num_strikes * tick_size)
        return self.get_option_chain(symbol, exchange, expiry, strike_from, strike_to)

    # ------------------------------------------------------------------
    # Bulk load from broker
    # ------------------------------------------------------------------

    def load_from_dhan(self, raw_instruments: list[dict]) -> int:
        """Load instruments from Dhan's scrip master."""
        count = 0
        with sqlite3.connect(self._db_path) as conn:
            for row in raw_instruments:
                try:
                    sym = row.get("SEM_CUSTOM_SYMBOL", row.get("SM_SYMBOL_NAME", ""))
                    if not sym:
                        continue

                    exchange = self._map_dhan_exchange(row.get("SEM_EXM_EXCH_ID", ""))
                    segment = self._map_dhan_segment(row.get("SEM_INSTRUMENT_NAME", ""))
                    if not exchange or not segment:
                        continue

                    expiry = None
                    if row.get("SEM_EXPIRY_DATE"):
                        try:
                            expiry = datetime.strptime(str(row["SEM_EXPIRY_DATE"])[:10], "%Y-%m-%d")
                        except (ValueError, TypeError):
                            pass

                    conn.execute("""
                        INSERT OR REPLACE INTO instruments 
                        (symbol, exchange, segment, name, dhan_security_id, expiry, strike, 
                         option_type, lot_size, tick_size, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sym, exchange, segment,
                        row.get("SEM_TRADING_SYMBOL", ""),
                        str(row.get("SEM_SMST_SECURITY_ID", "")),
                        expiry.strftime("%Y-%m-%d") if expiry else None,
                        float(row["SEM_STRIKE_PRICE"]) if row.get("SEM_STRIKE_PRICE") else None,
                        row.get("SEM_OPTION_TYPE"),
                        int(row.get("SEM_LOT_UNITS", 1)),
                        float(row.get("SEM_TICK_SIZE", 0.05)),
                        datetime.now().isoformat(),
                    ))
                    count += 1
                except Exception as e:
                    logger.debug("Skip instrument %s: %s", row.get("SEM_CUSTOM_SYMBOL", "?"), e)

        logger.info("Loaded %d instruments from Dhan", count)
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_instrument(self, row: dict) -> Instrument:
        expiry = None
        if row.get("expiry"):
            try:
                expiry = datetime.strptime(row["expiry"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        option_type = None
        if row.get("option_type"):
            try:
                option_type = OptionType(row["option_type"])
            except ValueError:
                pass

        return Instrument(
            symbol=row["symbol"],
            exchange=Exchange(row["exchange"]),
            segment=Segment(row["segment"]),
            name=row.get("name", ""),
            dhan_security_id=row.get("dhan_security_id", ""),
            bigul_exchange_instrument_id=row.get("bigul_exchange_instrument_id", ""),
            kotak_instrument_token=row.get("kotak_instrument_token", ""),
            expiry=expiry,
            strike=float(row["strike"]) if row.get("strike") is not None else None,
            option_type=option_type,
            lot_size=int(row.get("lot_size", 1)),
            tick_size=float(row.get("tick_size", 0.05)),
        )

    def _map_dhan_exchange(self, exch: str) -> str:
        mapping = {
            "NSE": "NSE", "BSE": "BSE", "MCX": "MCX",
            "NFO": "NFO", "BFO": "BFO", "CDS": "CDS",
        }
        return mapping.get(exch, "")

    def _map_dhan_segment(self, instrument_type: str) -> str:
        mapping = {
            "EQUITY": "EQUITY", "EQUITIES": "EQUITY",
            "FUTIDX": "FUTURES", "FUTSTK": "FUTURES",
            "FUTCOM": "FUTURES", "FUTCUR": "FUTURES",
            "OPTIDX": "OPTIONS", "OPTSTK": "OPTIONS",
            "OPTFUT": "OPTIONS", "OPTCUR": "OPTIONS",
            "INDEX": "INDEX",
        }
        return mapping.get(instrument_type, "")
