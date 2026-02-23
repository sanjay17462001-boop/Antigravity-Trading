"""
Antigravity Trading — Kotak Neo Broker Adapter
Role: Hot standby for live feed and execution (fallback if Bigul is down).
Uses Kotak Neo SDK v2.0.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

import pyotp

from brokers.base import BrokerAPI
from core.config import get_settings
from core.exceptions import (
    BrokerAuthError, BrokerConnectionError, BrokerDataError, BrokerOrderError,
)
from core.models import (
    Candle, Exchange, Instrument, Interval, Order, OrderSide,
    OrderStatus, OrderType, Position, ProductType, Segment, Tick,
)

logger = logging.getLogger("antigravity.broker.kotak")


class KotakNeoBroker(BrokerAPI):
    """
    Kotak Neo broker adapter — hot standby.
    
    Activated automatically when Bigul connection fails.
    Supports feed subscription and order execution.
    """

    def __init__(self):
        super().__init__("KotakNeo")
        self._client = None

    async def connect(self) -> None:
        """Connect using Kotak Neo SDK v2.0 with TOTP."""
        settings = get_settings()
        cfg = settings.brokers.kotak_neo

        if not cfg.consumer_key or not cfg.consumer_secret:
            raise BrokerAuthError("KotakNeo", "consumer_key and consumer_secret required")

        try:
            from neo_api_client import NeoAPI

            # Generate TOTP
            totp_value = ""
            if cfg.totp_secret:
                totp = pyotp.TOTP(cfg.totp_secret)
                totp_value = totp.now()

            self._client = NeoAPI(
                consumer_key=cfg.consumer_key,
                consumer_secret=cfg.consumer_secret,
                environment="prod",
            )

            # Login flow
            loop = asyncio.get_event_loop()
            login_resp = await loop.run_in_executor(
                None,
                lambda: self._client.login(
                    mobilenumber=cfg.mobile_number,
                    password=cfg.password,
                ),
            )

            # Complete 2FA with TOTP
            if totp_value:
                await loop.run_in_executor(
                    None,
                    lambda: self._client.session_2fa(OTP=totp_value),
                )

            self._connected = True
            logger.info("Kotak Neo connected successfully")

        except ImportError:
            raise BrokerConnectionError(
                "KotakNeo",
                "neo_api_client not installed. Install from Kotak Neo GitHub."
            )
        except BrokerAuthError:
            raise
        except Exception as e:
            raise BrokerConnectionError("KotakNeo", str(e))

    async def disconnect(self) -> None:
        """Disconnect from Kotak Neo."""
        try:
            if self._client:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._client.logout)
        except Exception as e:
            logger.warning("Kotak Neo disconnect error: %s", e)
        finally:
            self._client = None
            self._connected = False
            logger.info("Kotak Neo disconnected")

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: Interval,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Candle]:
        """Kotak Neo historical data (limited availability)."""
        raise BrokerDataError(
            "KotakNeo",
            "Historical data not reliably available. Use Dhan for historical data."
        )

    async def subscribe_feed(
        self,
        instruments: list[Instrument],
        on_tick: Callable[[Tick], None],
    ) -> None:
        """Subscribe to Kotak Neo live feed."""
        if not self._connected or not self._client:
            raise BrokerConnectionError("KotakNeo", "Not connected")

        instrument_tokens = []
        for inst in instruments:
            token = inst.kotak_instrument_token
            if token:
                instrument_tokens.append({
                    "instrument_token": token,
                    "exchange_segment": self._get_exchange_segment(inst),
                })

        try:
            def on_message(message):
                """Process incoming tick data."""
                try:
                    tick = Tick(
                        timestamp=datetime.now(),
                        instrument=instruments[0],  # Will be mapped properly
                        ltp=float(message.get("ltp", 0)),
                        volume=int(message.get("volume", 0)),
                    )
                    on_tick(tick)
                except Exception as e:
                    logger.error("Tick processing error: %s", e)

            self._client.subscribe(
                instrument_tokens=instrument_tokens,
                isIndex=False,
            )
            # Set the callback
            self._client.on_message = on_message
            logger.info("Subscribed to %d instruments on Kotak Neo", len(instruments))

        except Exception as e:
            raise BrokerConnectionError("KotakNeo", f"Feed subscription failed: {e}")

    async def unsubscribe_feed(self, instruments: list[Instrument]) -> None:
        """Unsubscribe from Kotak Neo feed."""
        if not self._connected or not self._client:
            return

        try:
            instrument_tokens = []
            for inst in instruments:
                if inst.kotak_instrument_token:
                    instrument_tokens.append({
                        "instrument_token": inst.kotak_instrument_token,
                        "exchange_segment": self._get_exchange_segment(inst),
                    })
            self._client.unsubscribe(instrument_tokens=instrument_tokens)
        except Exception as e:
            logger.warning("Kotak Neo unsubscribe error: %s", e)

    async def place_order(self, order: Order) -> str:
        """Place order via Kotak Neo."""
        if not self._connected or not self._client:
            raise BrokerConnectionError("KotakNeo", "Not connected")

        try:
            order_type_map = {
                OrderType.MARKET: "MKT",
                OrderType.LIMIT: "L",
                OrderType.SL: "SL",
                OrderType.SL_M: "SL-M",
            }

            product_map = {
                ProductType.MIS: "MIS",
                ProductType.NRML: "NRML",
                ProductType.CNC: "CNC",
            }

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.place_order(
                    exchange_segment=self._get_exchange_segment(order.instrument),
                    product=product_map.get(order.product, "MIS"),
                    price=str(order.price) if order.price else "0",
                    order_type=order_type_map.get(order.order_type, "MKT"),
                    quantity=str(order.quantity),
                    validity="DAY",
                    trading_symbol=order.instrument.symbol,
                    transaction_type=order.side.value,
                    trigger_price=str(order.trigger_price) if order.trigger_price else "0",
                    tag=order.tag or f"AG_{order.strategy_id}",
                ),
            )

            if response and "nOrdNo" in response:
                broker_order_id = str(response["nOrdNo"])
                logger.info("Kotak Neo order placed: %s", broker_order_id)
                return broker_order_id
            else:
                raise BrokerOrderError("KotakNeo", f"Order failed: {response}", order.id)

        except BrokerOrderError:
            raise
        except Exception as e:
            raise BrokerOrderError("KotakNeo", str(e), order.id)

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> None:
        """Modify order on Kotak Neo."""
        if not self._connected or not self._client:
            raise BrokerConnectionError("KotakNeo", "Not connected")

        try:
            params = {"order_id": order_id}
            if quantity is not None:
                params["quantity"] = str(quantity)
            if price is not None:
                params["price"] = str(price)
            if trigger_price is not None:
                params["trigger_price"] = str(trigger_price)
            if order_type is not None:
                params["order_type"] = order_type

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.modify_order(**params),
            )
            logger.info("Kotak Neo order %s modified", order_id)

        except Exception as e:
            raise BrokerOrderError("KotakNeo", str(e), order_id)

    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on Kotak Neo."""
        if not self._connected or not self._client:
            raise BrokerConnectionError("KotakNeo", "Not connected")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.cancel_order(order_id=order_id),
            )
            logger.info("Kotak Neo order %s cancelled", order_id)

        except Exception as e:
            raise BrokerOrderError("KotakNeo", str(e), order_id)

    async def get_positions(self) -> list[Position]:
        """Get positions from Kotak Neo."""
        if not self._connected or not self._client:
            return []

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self._client.positions
            )
            # Parse response into Position objects
            positions = []
            if response and isinstance(response, dict):
                for pos in response.get("data", []):
                    positions.append(Position(
                        instrument=Instrument(
                            symbol=pos.get("trdSym", ""),
                            exchange=Exchange.NSE,
                            segment=Segment.EQUITY,
                            kotak_instrument_token=pos.get("tok", ""),
                        ),
                        quantity=int(pos.get("flBuyQty", 0)) - int(pos.get("flSellQty", 0)),
                        avg_price=float(pos.get("buyAmt", 0)),
                        ltp=float(pos.get("ltp", 0)),
                    ))
            return positions

        except Exception as e:
            logger.error("Failed to get Kotak Neo positions: %s", e)
            return []

    async def get_order_book(self) -> list[Order]:
        """Get order book from Kotak Neo."""
        if not self._connected or not self._client:
            return []

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self._client.order_report
            )
            orders = []
            if response and isinstance(response, dict):
                for ord_data in response.get("data", []):
                    orders.append(Order(
                        id=str(ord_data.get("nOrdNo", "")),
                        instrument=Instrument(
                            symbol=ord_data.get("trdSym", ""),
                            exchange=Exchange.NSE,
                            segment=Segment.EQUITY,
                        ),
                        side=OrderSide.BUY if ord_data.get("trnsTp") == "B" else OrderSide.SELL,
                        quantity=int(ord_data.get("qty", 0)),
                        price=float(ord_data.get("prc", 0)),
                        status=OrderStatus.OPEN,
                    ))
            return orders

        except Exception as e:
            logger.error("Failed to get Kotak Neo orders: %s", e)
            return []

    async def get_funds(self) -> dict:
        """Get available margin from Kotak Neo."""
        if not self._connected or not self._client:
            return {}

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self._client.limits
            )
            return response if isinstance(response, dict) else {}
        except Exception as e:
            logger.error("Failed to get Kotak Neo funds: %s", e)
            return {}

    async def fetch_instrument_master(self) -> list[dict]:
        """Fetch Kotak Neo scrip master."""
        if not self._connected or not self._client:
            raise BrokerConnectionError("KotakNeo", "Not connected")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self._client.scrip_master()
            )
            return response if isinstance(response, list) else []
        except Exception as e:
            raise BrokerDataError("KotakNeo", f"Scrip master fetch failed: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_exchange_segment(self, instrument: Instrument) -> str:
        """Map to Kotak Neo exchange segment string."""
        segment_map = {
            Exchange.NSE: "nse_cm",
            Exchange.NFO: "nse_fo",
            Exchange.BSE: "bse_cm",
            Exchange.BFO: "bse_fo",
            Exchange.MCX: "mcx_fo",
        }
        return segment_map.get(instrument.exchange, "nse_cm")
