"""
Antigravity Trading — Order Simulator
Simulates order fills with realistic slippage and commissions.
Used by backtester and forward tester.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from core.models import (
    Candle, Order, OrderSide, OrderStatus, OrderType,
)

logger = logging.getLogger("antigravity.engine.order_sim")


class OrderSimulator:
    """
    Simulates order fills during backtesting.
    
    Fill logic:
    - MARKET: fills at next candle open ± slippage
    - LIMIT BUY: fills if candle low ≤ limit price
    - LIMIT SELL: fills if candle high ≥ limit price
    - SL BUY: triggers if candle high ≥ trigger, fills at trigger + slippage
    - SL SELL: triggers if candle low ≤ trigger, fills at trigger - slippage
    - SL_M (Stop Market): triggers and fills at market
    """

    def __init__(
        self,
        slippage_pct: float = 0.01,        # 0.01% default
        commission: float = 20.0,           # ₹ per order
    ):
        self._slippage_pct = slippage_pct / 100
        self._commission = commission

    def process_orders(self, orders: list[Order], candle: Candle) -> list[Order]:
        """
        Process pending orders against the current candle.
        Returns list of filled orders (with updated status and fill details).
        """
        filled = []

        for order in orders:
            if order.status != OrderStatus.PENDING:
                continue

            fill_price = self._check_fill(order, candle)
            if fill_price is not None:
                # Apply slippage
                if order.side == OrderSide.BUY:
                    fill_price *= (1 + self._slippage_pct)
                else:
                    fill_price *= (1 - self._slippage_pct)

                # Round to tick size
                tick = order.instrument.tick_size
                fill_price = round(fill_price / tick) * tick

                # Update order
                order.status = OrderStatus.FILLED
                order.filled_qty = order.quantity
                order.avg_fill_price = fill_price
                order.filled_at = candle.timestamp
                order.updated_at = candle.timestamp

                if not order.id:
                    order.id = str(uuid.uuid4())[:8]

                filled.append(order)

                logger.debug(
                    "FILL: %s %s %s x%d @ ₹%.2f (slippage: %.2f%%)",
                    order.side.value, order.instrument.display_name,
                    order.order_type.value, order.quantity,
                    fill_price, self._slippage_pct * 100,
                )

        return filled

    def _check_fill(self, order: Order, candle: Candle) -> Optional[float]:
        """
        Check if an order would fill on this candle.
        Returns fill price or None.
        """
        if order.order_type == OrderType.MARKET:
            return candle.open

        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                # Buy limit fills if price drops to limit
                if candle.low <= order.price:
                    return min(order.price, candle.open)  # Can fill at open if gap down
            else:
                # Sell limit fills if price rises to limit
                if candle.high >= order.price:
                    return max(order.price, candle.open)

        elif order.order_type == OrderType.SL:
            if order.side == OrderSide.BUY:
                # SL Buy triggers when price goes above trigger
                if candle.high >= order.trigger_price:
                    return max(order.trigger_price, order.price)
            else:
                # SL Sell triggers when price falls below trigger
                if candle.low <= order.trigger_price:
                    return min(order.trigger_price, order.price)

        elif order.order_type == OrderType.SL_M:
            if order.side == OrderSide.BUY:
                if candle.high >= order.trigger_price:
                    return order.trigger_price
            else:
                if candle.low <= order.trigger_price:
                    return order.trigger_price

        return None

    def calculate_charges(
        self,
        price: float,
        quantity: int,
        side: OrderSide,
        is_intraday: bool = True,
    ) -> dict[str, float]:
        """
        Calculate trading charges (brokerage + taxes) for Indian markets.
        Returns breakdown of all charges.
        """
        turnover = price * quantity

        # Brokerage
        brokerage = min(self._commission, turnover * 0.0003)  # ₹20 or 0.03%

        # STT/CTT (Securities Transaction Tax)
        if is_intraday:
            stt = turnover * 0.00025 if side == OrderSide.SELL else 0  # Only on sell side
        else:
            stt = turnover * 0.001  # Delivery

        # Exchange charges
        exchange_charges = turnover * 0.0000345

        # SEBI charges
        sebi_charges = turnover * 0.000001

        # GST (on brokerage + exchange charges)
        gst = (brokerage + exchange_charges + sebi_charges) * 0.18

        # Stamp duty (on buy side only)
        stamp_duty = turnover * 0.00003 if side == OrderSide.BUY else 0

        total = brokerage + stt + exchange_charges + sebi_charges + gst + stamp_duty

        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "exchange_charges": round(exchange_charges, 2),
            "sebi_charges": round(sebi_charges, 2),
            "gst": round(gst, 2),
            "stamp_duty": round(stamp_duty, 2),
            "total": round(total, 2),
        }
