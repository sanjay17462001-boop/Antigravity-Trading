"""
Antigravity Trading — Dhan Broker Adapter
Primary role: Historical data source (5 years of candle data).
Secondary role: None (Dhan is NOT used for live trading).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

import pandas as pd

from brokers.base import BrokerAPI
from core.config import get_settings
from core.exceptions import BrokerAuthError, BrokerConnectionError, BrokerDataError
from core.models import (
    Candle, Exchange, Instrument, Interval, Order, Position,
    Segment, Tick,
)

logger = logging.getLogger("antigravity.broker.dhan")

# Dhan interval mapping
INTERVAL_MAP = {
    Interval.M1: "1",
    Interval.M5: "5",
    Interval.M15: "15",
    Interval.M25: "25",
    Interval.H1: "60",
    Interval.D1: "D",
}

# Dhan exchange segment mapping
EXCHANGE_SEGMENT_MAP = {
    (Exchange.NSE, Segment.EQUITY): "NSE_EQ",
    (Exchange.NSE, Segment.INDEX): "IDX_I",
    (Exchange.NFO, Segment.FUTURES): "NSE_FNO",
    (Exchange.NFO, Segment.OPTIONS): "NSE_FNO",
    (Exchange.BSE, Segment.EQUITY): "BSE_EQ",
    (Exchange.BSE, Segment.INDEX): "IDX_I",
    (Exchange.BFO, Segment.FUTURES): "BSE_FNO",
    (Exchange.BFO, Segment.OPTIONS): "BSE_FNO",
    (Exchange.MCX, Segment.COMMODITY): "MCX_COMM",
    (Exchange.MCX, Segment.FUTURES): "MCX_COMM",
    (Exchange.MCX, Segment.OPTIONS): "MCX_COMM",
}


class DhanBroker(BrokerAPI):
    """
    Dhan broker adapter — historical data specialist.
    
    Key capabilities:
    - 5 years of intraday data (1m, 5m, 15m, 25m, 60m)
    - Daily data from inception
    - Expired options data
    - Open Interest data
    - 90-day chunks for minute-level data
    """

    def __init__(self):
        super().__init__("Dhan")
        self._client = None

    async def connect(self) -> None:
        """Initialize Dhan client with access token."""
        try:
            from dhanhq import dhanhq

            settings = get_settings()
            cfg = settings.brokers.dhan

            if not cfg.client_id or not cfg.access_token:
                raise BrokerAuthError("Dhan", "client_id and access_token required")

            self._client = dhanhq(cfg.client_id, cfg.access_token)
            self._connected = True
            logger.info("Dhan connected successfully (client_id=%s)", cfg.client_id)

        except ImportError:
            raise BrokerConnectionError("Dhan", "dhanhq package not installed: pip install dhanhq")
        except BrokerAuthError:
            raise
        except Exception as e:
            raise BrokerConnectionError("Dhan", str(e))

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False
        logger.info("Dhan disconnected")

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]:
        """
        Fetch historical candles from Dhan.
        
        Handles the 90-day chunking requirement for minute-level data.
        """
        if not self._connected or not self._client:
            raise BrokerConnectionError("Dhan", "Not connected")

        if interval not in INTERVAL_MAP:
            raise BrokerDataError("Dhan", f"Interval {interval} not supported. Use: {list(INTERVAL_MAP.keys())}")

        dhan_interval = INTERVAL_MAP[interval]
        security_id = instrument.dhan_security_id
        if not security_id:
            raise BrokerDataError("Dhan", f"No Dhan security ID for {instrument.display_name}")

        # Determine exchange segment
        ex_seg_key = (instrument.exchange, instrument.segment)
        exchange_segment = EXCHANGE_SEGMENT_MAP.get(ex_seg_key)
        if not exchange_segment:
            raise BrokerDataError("Dhan", f"Unsupported exchange/segment: {ex_seg_key}")

        # For minute-level data, chunk into 90-day windows
        all_candles: list[Candle] = []
        chunk_days = 90 if dhan_interval != "D" else 3650  # ~10 years for daily

        current_start = from_dt
        while current_start < to_dt:
            current_end = min(current_start + timedelta(days=chunk_days), to_dt)

            try:
                candles = await self._fetch_chunk(
                    security_id, exchange_segment, dhan_interval,
                    current_start, current_end, instrument, interval,
                )
                all_candles.extend(candles)
            except Exception as e:
                logger.warning(
                    "Dhan data fetch failed for %s [%s - %s]: %s",
                    instrument.display_name, current_start, current_end, e
                )

            current_start = current_end + timedelta(days=1)
            await asyncio.sleep(0.3)  # Rate limiting

        logger.info(
            "Fetched %d candles for %s (%s) from %s to %s",
            len(all_candles), instrument.display_name, interval.value,
            from_dt.date(), to_dt.date(),
        )
        return all_candles

    async def _fetch_chunk(
        self,
        security_id: str,
        exchange_segment: str,
        dhan_interval: str,
        from_dt: datetime,
        to_dt: datetime,
        instrument: Instrument,
        interval: Interval,
    ) -> list[Candle]:
        """Fetch a single chunk of candle data from Dhan."""
        # Run synchronous Dhan SDK call in executor
        loop = asyncio.get_event_loop()

        if dhan_interval == "D":
            response = await loop.run_in_executor(
                None,
                lambda: self._client.historical_daily_data(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    instrument_type="",
                    from_date=from_dt.strftime("%Y-%m-%d"),
                    to_date=to_dt.strftime("%Y-%m-%d"),
                ),
            )
        else:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.intraday_daily_candle_data(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    instrument_type="",
                    from_date=from_dt.strftime("%Y-%m-%d"),
                    to_date=to_dt.strftime("%Y-%m-%d"),
                    interval=dhan_interval,
                ),
            )

        if not response or response.get("status") != "success":
            error_msg = response.get("remarks", "Unknown error") if response else "No response"
            raise BrokerDataError("Dhan", f"Data fetch failed: {error_msg}")

        data = response.get("data", {})
        if not data:
            return []

        # Parse response into Candle objects
        candles = []
        timestamps = data.get("timestamp", data.get("start_Time", []))
        opens = data.get("open", [])
        highs = data.get("high", [])
        lows = data.get("low", [])
        closes = data.get("close", [])
        volumes = data.get("volume", [])

        for i in range(len(timestamps)):
            ts = timestamps[i]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            elif isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts)

            candles.append(Candle(
                timestamp=ts,
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=int(volumes[i]) if i < len(volumes) else 0,
                instrument=instrument,
                interval=interval,
            ))

        return candles

    # ------------------------------------------------------------------
    # Methods not supported by Dhan (historical-only adapter)
    # ------------------------------------------------------------------

    async def subscribe_feed(self, instruments, on_tick) -> None:
        raise NotImplementedError("Dhan adapter is for historical data only. Use Bigul for live feed.")

    async def unsubscribe_feed(self, instruments) -> None:
        raise NotImplementedError("Dhan adapter is for historical data only.")

    async def place_order(self, order) -> str:
        raise NotImplementedError("Dhan adapter is for historical data only. Use Bigul for order execution.")

    async def modify_order(self, order_id, **kwargs) -> None:
        raise NotImplementedError("Dhan adapter is for historical data only.")

    async def cancel_order(self, order_id) -> None:
        raise NotImplementedError("Dhan adapter is for historical data only.")

    async def get_positions(self) -> list[Position]:
        raise NotImplementedError("Dhan adapter is for historical data only.")

    async def get_order_book(self) -> list[Order]:
        raise NotImplementedError("Dhan adapter is for historical data only.")

    async def get_funds(self) -> dict:
        raise NotImplementedError("Dhan adapter is for historical data only.")

    async def fetch_instrument_master(self) -> list[dict]:
        """Fetch Dhan's instrument master CSV."""
        if not self._connected or not self._client:
            raise BrokerConnectionError("Dhan", "Not connected")

        loop = asyncio.get_event_loop()

        try:
            # Dhan provides instrument list as CSV download
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://images.dhan.co/api-data/api-scrip-master.csv",
                    timeout=60,
                )
                resp.raise_for_status()

            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(resp.text))
            return df.to_dict("records")

        except Exception as e:
            raise BrokerDataError("Dhan", f"Failed to fetch instrument master: {e}")
