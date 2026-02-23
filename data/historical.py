"""
Antigravity Trading — Historical Data Fetcher
Smart caching layer: fetches from Dhan (primary) or Bigul (fallback),
caches to Parquet, and only fetches missing date ranges.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from brokers.base import BrokerAPI
from core.models import Candle, Instrument, Interval
from data.storage import DataStorage

logger = logging.getLogger("antigravity.data.historical")


class HistoricalDataFetcher:
    """
    Intelligent historical data fetcher with caching.
    
    - Primary source: Dhan (5yr intraday, daily from inception)
    - Fallback: Bigul XTS
    - Caches everything to Parquet
    - Only fetches missing date ranges (gap-fill)
    """

    def __init__(
        self,
        primary_broker: BrokerAPI,
        fallback_broker: Optional[BrokerAPI] = None,
        storage: Optional[DataStorage] = None,
    ):
        self._primary = primary_broker
        self._fallback = fallback_broker
        self._storage = storage or DataStorage()

    async def get_candles(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Get historical candles — from cache if available, else from broker.
        
        Args:
            instrument: Security to fetch
            interval: Candle timeframe
            from_dt: Start date
            to_dt: End date
            force_refresh: If True, re-fetch even if cached
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, oi
        """
        # Check cache first
        if not force_refresh and self._storage.has_data(instrument, interval):
            cached_from, cached_to = self._storage.get_data_range(instrument, interval)

            if cached_from and cached_to:
                # If cache covers the requested range, return from cache
                if cached_from <= from_dt and cached_to >= to_dt:
                    logger.info(
                        "Cache hit: %s %s [%s - %s]",
                        instrument.display_name, interval.value,
                        from_dt.date(), to_dt.date(),
                    )
                    return self._storage.load_candles(instrument, interval, from_dt, to_dt)

                # Partial cache — fetch only the missing ranges
                gaps = self._find_gaps(from_dt, to_dt, cached_from, cached_to)
                if gaps:
                    await self._fill_gaps(instrument, interval, gaps)
                    return self._storage.load_candles(instrument, interval, from_dt, to_dt)

        # No cache — full fetch
        logger.info(
            "Fetching %s %s from %s to %s",
            instrument.display_name, interval.value,
            from_dt.date(), to_dt.date(),
        )
        candles = await self._fetch_from_broker(instrument, interval, from_dt, to_dt)

        if candles:
            self._storage.save_candles(candles, instrument, interval)

        return self._storage.load_candles(instrument, interval, from_dt, to_dt)

    def _find_gaps(
        self,
        requested_from: datetime,
        requested_to: datetime,
        cached_from: datetime,
        cached_to: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Find date ranges not covered by cache."""
        gaps = []

        if requested_from < cached_from:
            gaps.append((requested_from, cached_from - timedelta(days=1)))

        if requested_to > cached_to:
            gaps.append((cached_to + timedelta(days=1), requested_to))

        return gaps

    async def _fill_gaps(
        self,
        instrument: Instrument,
        interval: Interval,
        gaps: list[tuple[datetime, datetime]],
    ) -> None:
        """Fetch and cache missing date ranges."""
        for gap_from, gap_to in gaps:
            logger.info(
                "Filling gap: %s %s [%s - %s]",
                instrument.display_name, interval.value,
                gap_from.date(), gap_to.date(),
            )
            candles = await self._fetch_from_broker(instrument, interval, gap_from, gap_to)
            if candles:
                self._storage.save_candles(candles, instrument, interval)

    async def _fetch_from_broker(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]:
        """Try primary broker, fall back to secondary."""
        try:
            return await self._primary.get_historical_candles(
                instrument, interval, from_dt, to_dt
            )
        except Exception as e:
            logger.warning("Primary broker (%s) failed: %s", self._primary.name, e)

            if self._fallback:
                try:
                    logger.info("Trying fallback broker (%s)...", self._fallback.name)
                    return await self._fallback.get_historical_candles(
                        instrument, interval, from_dt, to_dt
                    )
                except Exception as e2:
                    logger.error("Fallback broker (%s) also failed: %s", self._fallback.name, e2)

            return []

    async def prefetch(
        self,
        instruments: list[Instrument],
        interval: Interval,
        years: int = 5,
    ) -> None:
        """
        Pre-fetch historical data for multiple instruments.
        Useful for batch-loading data before backtesting.
        """
        to_dt = datetime.now()
        from_dt = to_dt - timedelta(days=years * 365)

        for instrument in instruments:
            try:
                await self.get_candles(instrument, interval, from_dt, to_dt)
                await asyncio.sleep(0.5)  # Rate limiting between instruments
            except Exception as e:
                logger.error(
                    "Failed to prefetch %s: %s",
                    instrument.display_name, e,
                )
