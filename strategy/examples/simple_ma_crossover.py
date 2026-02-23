"""
Antigravity Trading — Example Strategy: MA Crossover
A simple EMA 9/21 crossover strategy on Nifty Futures.

This demonstrates how to use the Strategy framework.
Your real strategies can be much more complex — no template restrictions.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from core.models import (
    Candle, Instrument, Interval, OrderType, ProductType,
    Signal, SignalDirection,
)
from strategy.base import Strategy, StrategyContext


class MACrossoverStrategy(Strategy):
    """
    EMA Crossover Strategy
    
    Rules:
    - BUY when fast EMA crosses above slow EMA
    - SELL when fast EMA crosses below slow EMA
    - Only one position at a time
    - Intraday only (MIS product)
    
    Params:
        fast_period: int (default 9)
        slow_period: int (default 21)
        quantity: int (default 50, i.e. 1 lot of Nifty)
    """

    def __init__(
        self,
        strategy_id: str = "ma_crossover",
        name: str = "EMA Crossover",
        params: dict[str, Any] | None = None,
    ):
        default_params = {
            "fast_period": 9,
            "slow_period": 21,
            "quantity": 50,  # 1 Nifty lot
        }
        if params:
            default_params.update(params)
        super().__init__(strategy_id, name, default_params)

        self._fast = self.params["fast_period"]
        self._slow = self.params["slow_period"]
        self._qty = self.params["quantity"]
        self._prev_fast_above = None  # Track crossover state

    def on_init(self, ctx: StrategyContext) -> None:
        super().on_init(ctx)
        self.log("Initialized with fast=%d, slow=%d, qty=%d", self._fast, self._slow, self._qty)

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        """Process each candle for crossover signals."""
        if candle.instrument is None:
            return None

        # Get historical data up to current candle
        data = self.ctx.get_data(candle.instrument)
        if data.empty or len(data) < self._slow + 1:
            return None

        # Calculate EMAs
        fast_ema = self.get_indicator("ema", data, length=self._fast)
        slow_ema = self.get_indicator("ema", data, length=self._slow)

        if fast_ema.empty or slow_ema.empty:
            return None

        # Current state
        current_fast_above = fast_ema.iloc[-1] > slow_ema.iloc[-1]
        pos = self.ctx.get_position(candle.instrument)
        has_position = pos is not None and pos.is_open

        # Detect crossover
        if self._prev_fast_above is not None:
            # Bullish crossover: fast crosses above slow
            if current_fast_above and not self._prev_fast_above:
                if not has_position:
                    self.buy(
                        candle.instrument,
                        self._qty,
                        product=ProductType.MIS,
                        tag="ma_cross_buy",
                    )
                    self._prev_fast_above = current_fast_above
                    return Signal(
                        timestamp=candle.timestamp,
                        instrument=candle.instrument,
                        direction=SignalDirection.LONG,
                        strength=80,
                        strategy_id=self.strategy_id,
                        reason=f"EMA{self._fast} crossed above EMA{self._slow}",
                        quantity=self._qty,
                    )

            # Bearish crossover: fast crosses below slow
            elif not current_fast_above and self._prev_fast_above:
                if has_position:
                    self.close_position(candle.instrument, tag="ma_cross_exit")
                    self._prev_fast_above = current_fast_above
                    return Signal(
                        timestamp=candle.timestamp,
                        instrument=candle.instrument,
                        direction=SignalDirection.EXIT,
                        strength=80,
                        strategy_id=self.strategy_id,
                        reason=f"EMA{self._fast} crossed below EMA{self._slow}",
                        quantity=self._qty,
                    )

        self._prev_fast_above = current_fast_above
        return None

    def on_stop(self) -> None:
        """Close any open position at end."""
        self.close_all()
        self.log("Strategy stopped — all positions closed")
