"""
Antigravity Trading — Core Data Models
All domain objects used across the platform.
Designed for flexibility: strategies can use any combination of these.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NFO = "NFO"      # NSE F&O
    BFO = "BFO"      # BSE F&O
    CDS = "CDS"      # Currency derivatives
    MCX_FO = "MCX"   # MCX futures & options


class Segment(str, Enum):
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"


class OptionType(str, Enum):
    CE = "CE"   # Call
    PE = "PE"   # Put


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"          # Stop-Loss Limit
    SL_M = "SL_M"      # Stop-Loss Market


class ProductType(str, Enum):
    MIS = "MIS"        # Intraday
    NRML = "NRML"      # Overnight / positional
    CNC = "CNC"        # Delivery (equity)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRIGGER_PENDING = "TRIGGER_PENDING"


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"
    HOLD = "HOLD"


class Interval(str, Enum):
    """Candle intervals supported across the platform."""
    TICK = "tick"
    S1 = "1s"
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M25 = "25m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1M"


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------

class Instrument(BaseModel):
    """Unified instrument representation across all brokers."""
    symbol: str                        # e.g. "NIFTY", "CRUDEOIL"
    exchange: Exchange
    segment: Segment
    name: str = ""                     # Full name

    # Identifiers per broker (filled from instrument master)
    dhan_security_id: str = ""
    bigul_exchange_instrument_id: str = ""
    kotak_instrument_token: str = ""

    # Derivatives-specific
    expiry: Optional[datetime] = None
    strike: Optional[float] = None
    option_type: Optional[OptionType] = None

    # Contract specs
    lot_size: int = 1
    tick_size: float = 0.05

    @property
    def is_derivative(self) -> bool:
        return self.segment in (Segment.FUTURES, Segment.OPTIONS)

    @property
    def is_option(self) -> bool:
        return self.segment == Segment.OPTIONS

    @property
    def display_name(self) -> str:
        parts = [self.symbol]
        if self.expiry:
            parts.append(self.expiry.strftime("%d%b%y").upper())
        if self.strike is not None:
            parts.append(str(int(self.strike)))
        if self.option_type:
            parts.append(self.option_type.value)
        return " ".join(parts)

    class Config:
        frozen = True

    def __hash__(self):
        return hash((self.symbol, self.exchange, self.segment,
                      self.expiry, self.strike, self.option_type))


# ---------------------------------------------------------------------------
# Market Data
# ---------------------------------------------------------------------------

class Candle(BaseModel):
    """OHLCV candle — the primary data unit for strategies."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    oi: int = 0                          # Open Interest (derivatives)
    instrument: Optional[Instrument] = None
    interval: Interval = Interval.M5

    class Config:
        frozen = True


class Tick(BaseModel):
    """Real-time market tick."""
    timestamp: datetime
    instrument: Instrument
    ltp: float                           # Last traded price
    bid: float = 0.0
    ask: float = 0.0
    bid_qty: int = 0
    ask_qty: int = 0
    volume: int = 0
    oi: int = 0
    total_buy_qty: int = 0
    total_sell_qty: int = 0


# ---------------------------------------------------------------------------
# Orders & Trades
# ---------------------------------------------------------------------------

class Order(BaseModel):
    """Order representation — used by both backtester and live engine."""
    id: str = ""                         # Assigned by system or broker
    instrument: Instrument
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    product: ProductType = ProductType.MIS
    quantity: int = 1
    price: float = 0.0                   # For LIMIT / SL
    trigger_price: float = 0.0           # For SL / SL_M
    status: OrderStatus = OrderStatus.PENDING
    strategy_id: str = ""
    tag: str = ""                        # Custom tag for tracking

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None

    # Fill details
    filled_qty: int = 0
    avg_fill_price: float = 0.0
    broker_order_id: str = ""

    # Metadata — strategies can store anything here
    meta: dict[str, Any] = Field(default_factory=dict)


class Trade(BaseModel):
    """A completed trade (entry + exit)."""
    id: str = ""
    strategy_id: str = ""
    instrument: Instrument
    side: OrderSide                      # Entry side
    entry_price: float
    exit_price: float
    quantity: int
    entry_time: datetime
    exit_time: datetime
    pnl: float = 0.0                     # Realized P&L (after charges)
    charges: float = 0.0                 # Brokerage + taxes
    slippage: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)

    @property
    def return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == OrderSide.BUY:
            return ((self.exit_price - self.entry_price) / self.entry_price) * 100
        return ((self.entry_price - self.exit_price) / self.entry_price) * 100


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

class Position(BaseModel):
    """Current open position."""
    instrument: Instrument
    quantity: int = 0                    # +ve = long, -ve = short
    avg_price: float = 0.0
    ltp: float = 0.0
    pnl: float = 0.0                    # Unrealized P&L
    strategy_id: str = ""

    @property
    def is_open(self) -> bool:
        return self.quantity != 0

    @property
    def side(self) -> Optional[OrderSide]:
        if self.quantity > 0:
            return OrderSide.BUY
        elif self.quantity < 0:
            return OrderSide.SELL
        return None

    @property
    def mtm(self) -> float:
        """Mark-to-market P&L."""
        if self.quantity > 0:
            return (self.ltp - self.avg_price) * self.quantity
        elif self.quantity < 0:
            return (self.avg_price - self.ltp) * abs(self.quantity)
        return 0.0


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class Signal(BaseModel):
    """Strategy output — a trading signal with metadata."""
    timestamp: datetime
    instrument: Instrument
    direction: SignalDirection
    strength: float = 100.0              # 0-100 confidence
    strategy_id: str = ""
    reason: str = ""                     # Human-readable reason

    # Suggested order params (strategy can override in executor)
    quantity: int = 0
    order_type: OrderType = OrderType.MARKET
    price: float = 0.0
    stop_loss: float = 0.0
    target: float = 0.0

    # Freeform metadata for any custom strategy logic
    meta: dict[str, Any] = Field(default_factory=dict)
