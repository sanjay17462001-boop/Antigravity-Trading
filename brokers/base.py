"""
Antigravity Trading — Abstract Broker API
Unified interface that all broker implementations must follow.
This ensures strategies and engines are broker-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Optional

from core.models import (
    Candle, Instrument, Interval, Order, Position, Tick,
)


class BrokerAPI(ABC):
    """
    Abstract interface for all broker implementations.
    
    Each broker adapter (Dhan, Bigul, Kotak Neo) implements this interface.
    The platform code never talks to broker SDKs directly — always through
    this abstraction.
    """

    def __init__(self, name: str):
        self.name = name
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def connect(self) -> None:
        """Authenticate and establish connection."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close all connections and cleanup."""
        ...

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]:
        """
        Fetch historical OHLCV candles.
        
        Args:
            instrument: The security to fetch data for
            interval: Candle timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            from_dt: Start datetime (inclusive)
            to_dt: End datetime (inclusive)
            
        Returns:
            List of Candle objects, sorted by timestamp ascending
        """
        ...

    # ------------------------------------------------------------------
    # Live market feed
    # ------------------------------------------------------------------

    @abstractmethod
    async def subscribe_feed(
        self,
        instruments: list[Instrument],
        on_tick: Callable[[Tick], None],
    ) -> None:
        """
        Subscribe to real-time market data for given instruments.
        
        Args:
            instruments: List of instruments to subscribe to
            on_tick: Callback invoked on each tick
        """
        ...

    @abstractmethod
    async def unsubscribe_feed(self, instruments: list[Instrument]) -> None:
        """Unsubscribe from real-time data."""
        ...

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    @abstractmethod
    async def place_order(self, order: Order) -> str:
        """
        Place an order on the exchange.
        
        Returns:
            Broker-assigned order ID
        """
        ...

    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> None:
        """Modify an open order."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> None:
        """Cancel an open order."""
        ...

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all open positions from broker."""
        ...

    @abstractmethod
    async def get_order_book(self) -> list[Order]:
        """Get today's order book."""
        ...

    @abstractmethod
    async def get_funds(self) -> dict:
        """Get available margin / funds."""
        ...

    # ------------------------------------------------------------------
    # Instrument master
    # ------------------------------------------------------------------

    @abstractmethod
    async def fetch_instrument_master(self) -> list[dict]:
        """
        Download the full instrument master from broker.
        Returns list of raw instrument dicts (broker-specific format).
        The InstrumentManager will normalize these.
        """
        ...

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} connected={self._connected}>"
