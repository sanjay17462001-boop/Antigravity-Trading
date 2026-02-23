"""
Antigravity Trading — Bigul Broker Adapter (XTS)
Primary role: Live market feed + Order execution.
Secondary role: Historical data (fallback if Dhan unavailable).

Uses Symphony/XTS API via xts-pythonclient-api-sdk.
Supports TOTP-based authentication.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

import pyotp

from brokers.base import BrokerAPI
from core.config import get_settings
from core.exceptions import (
    BrokerAuthError, BrokerConnectionError, BrokerDataError, BrokerOrderError,
)
from core.models import (
    Candle, Exchange, Instrument, Interval, Order, OrderSide, OrderStatus,
    OrderType, Position, ProductType, Segment, Tick,
)

logger = logging.getLogger("antigravity.broker.bigul")


class BigulBroker(BrokerAPI):
    """
    Bigul / XTS broker adapter — primary live broker.
    
    Handles:
    - TOTP-based login
    - WebSocket market data subscription
    - Order placement, modification, cancellation
    - Position and order book queries
    """

    def __init__(self):
        super().__init__("Bigul")
        self._market_client = None
        self._interactive_client = None
        self._market_token = ""
        self._interactive_token = ""
        self._ws = None

    async def connect(self) -> None:
        """Connect to Bigul XTS API with TOTP authentication."""
        settings = get_settings()
        cfg = settings.brokers.bigul

        if not cfg.api_key or not cfg.api_secret:
            raise BrokerAuthError("Bigul", "api_key and api_secret required")

        try:
            # Generate TOTP if secret provided
            totp_value = ""
            if cfg.totp_secret:
                totp = pyotp.TOTP(cfg.totp_secret)
                totp_value = totp.now()
                logger.debug("Generated TOTP for Bigul login")

            # Initialize XTS Market Data client
            from XtsConnect.MarketDataSocketClient import MDSocket_io
            from XtsConnect import XTSConnect

            # Market Data API
            self._market_client = XTSConnect.XTSConnect(
                cfg.market_url, None, cfg.source
            )
            market_login = self._market_client.marketdata_login(
                cfg.api_key, cfg.api_secret
            )

            if market_login.get("type") == "error":
                raise BrokerAuthError("Bigul", f"Market login failed: {market_login.get('description', '')}")

            self._market_token = market_login.get("result", {}).get("token", "")
            logger.info("Bigul Market Data API connected")

            # Interactive API (for orders)
            self._interactive_client = XTSConnect.XTSConnect(
                cfg.interactive_url, None, cfg.source
            )
            interactive_login = self._interactive_client.interactive_login(
                cfg.api_key, cfg.api_secret
            )

            if interactive_login.get("type") == "error":
                raise BrokerAuthError("Bigul", f"Interactive login failed: {interactive_login.get('description', '')}")

            self._interactive_token = interactive_login.get("result", {}).get("token", "")
            logger.info("Bigul Interactive API connected")

            self._connected = True
            logger.info("Bigul fully connected (Market + Interactive)")

        except (BrokerAuthError, BrokerConnectionError):
            raise
        except ImportError:
            raise BrokerConnectionError(
                "Bigul", 
                "XTS SDK not installed. Install from: pip install xts-pythonclient-api-sdk"
            )
        except Exception as e:
            raise BrokerConnectionError("Bigul", str(e))

    async def disconnect(self) -> None:
        """Disconnect from Bigul API."""
        try:
            if self._market_client:
                self._market_client.marketdata_logout()
            if self._interactive_client:
                self._interactive_client.interactive_logout()
        except Exception as e:
            logger.warning("Bigul disconnect error: %s", e)
        finally:
            self._market_client = None
            self._interactive_client = None
            self._connected = False
            logger.info("Bigul disconnected")

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]:
        """Fetch historical OHLC from Bigul XTS."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        # XTS interval mapping
        interval_map = {
            Interval.M1: 60,
            Interval.M3: 180,
            Interval.M5: 300,
            Interval.M15: 900,
            Interval.M30: 1800,
            Interval.H1: 3600,
            Interval.D1: 86400,
        }

        xts_interval = interval_map.get(interval)
        if not xts_interval:
            raise BrokerDataError("Bigul", f"Interval {interval} not supported")

        exchange_id = self._get_exchange_id(instrument)

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._market_client.get_ohlc(
                    exchangeSegment=exchange_id,
                    exchangeInstrumentID=int(instrument.bigul_exchange_instrument_id),
                    startTime=from_dt.strftime("%b %d %Y %H%M%S"),
                    endTime=to_dt.strftime("%b %d %Y %H%M%S"),
                    compressionValue=xts_interval,
                ),
            )

            if not response or response.get("type") == "error":
                raise BrokerDataError("Bigul", f"OHLC fetch failed: {response}")

            # Parse response
            candles = []
            result = response.get("result", {})
            data_list = result.get("dataReponse", "").split(",") if isinstance(result, dict) else []

            # XTS returns pipe-separated OHLCV records
            if isinstance(result, dict) and "dataReponse" in result:
                raw = result["dataReponse"]
                records = raw.split(",") if raw else []
                for record in records:
                    fields = record.strip().split("|")
                    if len(fields) >= 6:
                        candles.append(Candle(
                            timestamp=datetime.fromtimestamp(int(fields[0])),
                            open=float(fields[1]),
                            high=float(fields[2]),
                            low=float(fields[3]),
                            close=float(fields[4]),
                            volume=int(fields[5]),
                            instrument=instrument,
                            interval=interval,
                        ))

            return candles

        except BrokerDataError:
            raise
        except Exception as e:
            raise BrokerDataError("Bigul", str(e))

    async def subscribe_feed(
        self,
        instruments: list[Instrument],
        on_tick: Callable[[Tick], None],
    ) -> None:
        """Subscribe to live market data via WebSocket."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        # Build subscription list
        subscription_list = []
        for inst in instruments:
            exchange_id = self._get_exchange_id(inst)
            subscription_list.append({
                "exchangeSegment": exchange_id,
                "exchangeInstrumentID": int(inst.bigul_exchange_instrument_id),
            })

        try:
            # Subscribe via REST API
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._market_client.send_subscription(
                    Instruments=subscription_list,
                    xtsMessageCode=1502,  # Touchline
                ),
            )

            if response and response.get("type") == "error":
                raise BrokerConnectionError("Bigul", f"Subscription failed: {response}")

            logger.info("Subscribed to %d instruments on Bigul", len(instruments))

        except BrokerConnectionError:
            raise
        except Exception as e:
            raise BrokerConnectionError("Bigul", f"Feed subscription failed: {e}")

    async def unsubscribe_feed(self, instruments: list[Instrument]) -> None:
        """Unsubscribe from live market data."""
        if not self._connected:
            return

        subscription_list = []
        for inst in instruments:
            exchange_id = self._get_exchange_id(inst)
            subscription_list.append({
                "exchangeSegment": exchange_id,
                "exchangeInstrumentID": int(inst.bigul_exchange_instrument_id),
            })

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._market_client.send_unsubscription(
                    Instruments=subscription_list,
                    xtsMessageCode=1502,
                ),
            )
        except Exception as e:
            logger.warning("Bigul unsubscribe error: %s", e)

    async def place_order(self, order: Order) -> str:
        """Place order via Bigul Interactive API."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        exchange_id = self._get_exchange_id(order.instrument)

        # Map order type
        order_type_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.SL: "STOPLIMIT",
            OrderType.SL_M: "STOPMARKET",
        }

        product_map = {
            ProductType.MIS: "MIS",
            ProductType.NRML: "NRML",
            ProductType.CNC: "CNC",
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._interactive_client.place_order(
                    exchangeSegment=exchange_id,
                    exchangeInstrumentID=int(order.instrument.bigul_exchange_instrument_id),
                    productType=product_map.get(order.product, "MIS"),
                    orderType=order_type_map.get(order.order_type, "MARKET"),
                    orderSide=order.side.value,
                    timeInForce="DAY",
                    disclosedQuantity=0,
                    orderQuantity=order.quantity,
                    limitPrice=order.price if order.order_type in (OrderType.LIMIT, OrderType.SL) else 0,
                    stopPrice=order.trigger_price if order.order_type in (OrderType.SL, OrderType.SL_M) else 0,
                    orderUniqueIdentifier=order.tag or f"AG_{order.strategy_id}",
                ),
            )

            if response and response.get("type") == "success":
                broker_order_id = str(response.get("result", {}).get("AppOrderID", ""))
                logger.info(
                    "Order placed: %s %s %s x%d @ %s | ID=%s",
                    order.side.value, order.instrument.display_name,
                    order.order_type.value, order.quantity, order.price, broker_order_id,
                )
                return broker_order_id
            else:
                error_msg = response.get("description", "Unknown error") if response else "No response"
                raise BrokerOrderError("Bigul", error_msg, order.id)

        except BrokerOrderError:
            raise
        except Exception as e:
            raise BrokerOrderError("Bigul", str(e), order.id)

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> None:
        """Modify an existing order."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        try:
            params = {"appOrderID": int(order_id)}
            if quantity is not None:
                params["modifiedOrderQuantity"] = quantity
            if price is not None:
                params["modifiedLimitPrice"] = price
            if trigger_price is not None:
                params["modifiedStopPrice"] = trigger_price
            if order_type is not None:
                params["modifiedOrderType"] = order_type

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._interactive_client.modify_order(**params),
            )

            if response and response.get("type") == "error":
                raise BrokerOrderError("Bigul", f"Modify failed: {response.get('description')}", order_id)

            logger.info("Order %s modified", order_id)

        except BrokerOrderError:
            raise
        except Exception as e:
            raise BrokerOrderError("Bigul", str(e), order_id)

    async def cancel_order(self, order_id: str) -> None:
        """Cancel an open order."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._interactive_client.cancel_order(appOrderID=int(order_id)),
            )

            if response and response.get("type") == "error":
                raise BrokerOrderError("Bigul", f"Cancel failed: {response.get('description')}", order_id)

            logger.info("Order %s cancelled", order_id)

        except BrokerOrderError:
            raise
        except Exception as e:
            raise BrokerOrderError("Bigul", str(e), order_id)

    async def get_positions(self) -> list[Position]:
        """Get current positions from Bigul."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._interactive_client.get_position_daywise(),
            )

            positions = []
            if response and response.get("type") == "success":
                for pos_data in response.get("result", {}).get("positionList", []):
                    positions.append(Position(
                        instrument=Instrument(
                            symbol=pos_data.get("TradingSymbol", ""),
                            exchange=Exchange.NSE,
                            segment=Segment.EQUITY,
                            bigul_exchange_instrument_id=str(pos_data.get("ExchangeInstrumentId", "")),
                        ),
                        quantity=int(pos_data.get("Quantity", 0)),
                        avg_price=float(pos_data.get("BuyAveragePrice", 0)),
                        ltp=float(pos_data.get("LastTradedPrice", 0)),
                        pnl=float(pos_data.get("RealizedGrossProfit", 0)),
                    ))

            return positions

        except Exception as e:
            logger.error("Failed to get positions: %s", e)
            return []

    async def get_order_book(self) -> list[Order]:
        """Get today's order book."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._interactive_client.get_order_book(),
            )

            orders = []
            if response and response.get("type") == "success":
                for ord_data in response.get("result", []):
                    status_map = {
                        "New": OrderStatus.OPEN,
                        "Filled": OrderStatus.FILLED,
                        "PartiallyFilled": OrderStatus.PARTIAL,
                        "Cancelled": OrderStatus.CANCELLED,
                        "Rejected": OrderStatus.REJECTED,
                    }
                    orders.append(Order(
                        id=str(ord_data.get("AppOrderID", "")),
                        instrument=Instrument(
                            symbol=ord_data.get("TradingSymbol", ""),
                            exchange=Exchange.NSE,
                            segment=Segment.EQUITY,
                            bigul_exchange_instrument_id=str(ord_data.get("ExchangeInstrumentId", "")),
                        ),
                        side=OrderSide.BUY if ord_data.get("OrderSide") == "BUY" else OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=int(ord_data.get("OrderQuantity", 0)),
                        price=float(ord_data.get("OrderPrice", 0)),
                        status=status_map.get(ord_data.get("OrderStatus", ""), OrderStatus.PENDING),
                        filled_qty=int(ord_data.get("CumulativeQuantity", 0)),
                        avg_fill_price=float(ord_data.get("OrderAverageTradedPrice", 0)),
                        broker_order_id=str(ord_data.get("ExchangeOrderID", "")),
                    ))

            return orders

        except Exception as e:
            logger.error("Failed to get order book: %s", e)
            return []

    async def get_funds(self) -> dict:
        """Get available margin."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._interactive_client.get_balance(),
            )

            if response and response.get("type") == "success":
                return response.get("result", {})
            return {}

        except Exception as e:
            logger.error("Failed to get funds: %s", e)
            return {}

    async def fetch_instrument_master(self) -> list[dict]:
        """Fetch XTS instrument master."""
        if not self._connected:
            raise BrokerConnectionError("Bigul", "Not connected")

        instruments = []
        for exchange_segment in [1, 2, 11]:  # NSECM, NSEFO, MCXFO
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda seg=exchange_segment: self._market_client.get_master(
                        exchangeSegmentList=[seg]
                    ),
                )

                if response and response.get("type") == "success":
                    raw = response.get("result", "")
                    # Parse pipe-delimited master data
                    for line in raw.split("\n"):
                        fields = line.strip().split("|")
                        if len(fields) >= 5:
                            instruments.append({
                                "exchange_segment": exchange_segment,
                                "exchange_instrument_id": fields[0],
                                "instrument_type": fields[1] if len(fields) > 1 else "",
                                "name": fields[2] if len(fields) > 2 else "",
                                "description": fields[3] if len(fields) > 3 else "",
                                "series": fields[4] if len(fields) > 4 else "",
                            })
            except Exception as e:
                logger.warning("Failed to fetch master for segment %d: %s", exchange_segment, e)

        return instruments

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_exchange_id(self, instrument: Instrument) -> int:
        """Map Instrument exchange to XTS exchange segment ID."""
        exchange_map = {
            Exchange.NSE: 1,      # NSECM (Cash)
            Exchange.NFO: 2,      # NSEFO (F&O)
            Exchange.BSE: 3,      # BSECM
            Exchange.BFO: 4,      # BSEFO
            Exchange.MCX: 11,     # MCXFO
        }
        return exchange_map.get(instrument.exchange, 1)
