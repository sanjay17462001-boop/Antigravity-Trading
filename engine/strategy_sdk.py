"""
Antigravity Trading — Strategy SDK
====================================
Clean Python API for AI-generated strategy code.
Gemini writes code that uses StrategyContext to access data,
open/close positions, and compute P&L — enabling unlimited strategy logic.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np

from engine.cost_model import CostModel, CostConfig, TradeCost

logger = logging.getLogger("antigravity.strategy_sdk")


# =========================================================================
# Data Types
# =========================================================================

@dataclass
class Position:
    """A single open or closed position."""
    id: int
    strike: str          # "ATM", "ATM+1", etc.
    option_type: str     # "CE" or "PE"
    action: str          # "BUY" or "SELL"
    lots: int
    quantity: int        # lots * lot_size
    entry_price: float
    entry_time: str
    label: str = ""
    # Filled on close
    exit_price: float = 0.0
    exit_time: str = ""
    exit_reason: str = ""
    is_open: bool = True
    gross_pnl: float = 0.0
    cost: Optional[TradeCost] = None
    net_pnl: float = 0.0
    # Live tracking
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        if not self.is_open:
            return 0.0
        if self.action == "SELL":
            return (self.entry_price - self.current_price) * self.quantity
        else:
            return (self.current_price - self.entry_price) * self.quantity


@dataclass
class TradeRecord:
    """A completed trade for results output."""
    trade_date: date
    strike: str
    option_type: str
    absolute_strike: float
    action: str
    lots: int
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    exit_reason: str
    gross_pnl: float
    net_pnl: float
    dte: int
    spot_at_entry: float
    vix_at_entry: float
    label: str = ""
    cost: Optional[TradeCost] = None


@dataclass
class DayResult:
    """Result from one trading day."""
    trade_date: date
    trades: list[TradeRecord] = field(default_factory=list)
    daily_pnl: float = 0.0
    logs: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


# =========================================================================
# Strategy Context — the API Gemini-generated code uses
# =========================================================================

class StrategyContext:
    """
    Provided to AI-generated strategy code as `ctx`.
    Contains all data and methods needed to implement any strategy logic.
    """

    def __init__(
        self,
        day_data: pd.DataFrame,
        trade_date: date,
        dte: int,
        lot_size: int,
        cost_model: CostModel,
        entry_time_str: str = "09:20",
        exit_time_str: str = "15:15",
    ):
        self._day_data = day_data
        self._trade_date = trade_date
        self._dte = dte
        self._lot_size = lot_size
        self._cost_model = cost_model
        self._entry_time_str = entry_time_str
        self._exit_time_str = exit_time_str

        self._positions: list[Position] = []
        self._closed_positions: list[Position] = []
        self._next_id = 1
        self._logs: list[str] = []

        # Precompute spot and VIX from first available candle
        if not day_data.empty:
            first = day_data.iloc[0]
            self._spot = float(first.get("spot_price", 0))
            self._vix = float(first.get("india_vix", 0)) if pd.notna(first.get("india_vix")) else 0.0
        else:
            self._spot = 0.0
            self._vix = 0.0

    @staticmethod
    def _to_time(t) -> time:
        """Convert string 'HH:MM' or time object to time. Handles both."""
        if isinstance(t, time):
            return t
        if isinstance(t, str):
            parts = t.replace(":", " ").split()
            return time(int(parts[0]), int(parts[1]))
        return t

    # ── Read-only properties ──

    @property
    def date(self) -> date:
        """Current trading date."""
        return self._trade_date

    @property
    def dte(self) -> int:
        """Days to expiry."""
        return self._dte

    @property
    def spot(self) -> float:
        """NIFTY spot price (from first candle of the day)."""
        return self._spot

    @property
    def vix(self) -> float:
        """India VIX value."""
        return self._vix

    @property
    def lot_size(self) -> int:
        """NIFTY lot size."""
        return self._lot_size

    @property
    def entry_time(self) -> str:
        """Configured entry time."""
        return self._entry_time_str

    @property
    def exit_time(self) -> str:
        """Configured exit time."""
        return self._exit_time_str

    # ── Data Access ──

    def get_candles(self, strike: str = "ATM", option_type: str = "CE") -> pd.DataFrame:
        """
        Get 1-minute OHLC candles for a specific strike.

        Args:
            strike: "ATM", "ATM+1", "ATM-1", etc.
            option_type: "CE" or "PE"

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, oi,
                                     spot_price, absolute_strike
        """
        if self._day_data.empty:
            return pd.DataFrame()

        leg_type = "CALL" if option_type.upper() == "CE" else "PUT"
        mask = (self._day_data["strike_rel"] == strike) & (self._day_data["type"] == leg_type)
        df = self._day_data[mask].copy().sort_values("timestamp").reset_index(drop=True)
        return df

    def get_spot_price_at(self, t) -> float:
        """Get spot price at a specific time of day. Accepts time object or 'HH:MM' string."""
        t = self._to_time(t)
        if self._day_data.empty:
            return 0.0
        mask = (self._day_data["timestamp"].dt.hour == t.hour) & \
               (self._day_data["timestamp"].dt.minute == t.minute)
        rows = self._day_data[mask]
        if rows.empty:
            return self._spot
        return float(rows.iloc[0].get("spot_price", self._spot))

    def get_option_price_at(self, strike: str, option_type: str, t) -> float:
        """Get option open price at a specific time. Accepts time object or 'HH:MM' string."""
        t = self._to_time(t)
        candles = self.get_candles(strike, option_type)
        if candles.empty:
            return 0.0
        mask = (candles["timestamp"].dt.hour == t.hour) & \
               (candles["timestamp"].dt.minute == t.minute)
        rows = candles[mask]
        if rows.empty:
            return 0.0
        return float(rows.iloc[0]["open"])

    def get_available_strikes(self) -> list[str]:
        """Get list of available relative strikes for the day."""
        if self._day_data.empty:
            return []
        return sorted(self._day_data["strike_rel"].unique().tolist())

    # ── Position Management ──

    def open_position(
        self,
        strike: str,
        option_type: str,
        action: str,
        lots: int = 1,
        label: str = "",
        price: Optional[float] = None,
        at_time = None,
    ) -> int:
        """
        Open a new position.

        Args:
            strike: "ATM", "ATM+1", etc.
            option_type: "CE" or "PE"
            action: "BUY" or "SELL"
            lots: Number of lots
            label: Optional label (e.g., "CE leg", "hedge")
            price: Override entry price (otherwise uses open price at at_time or entry_time)
            at_time: Time to enter — accepts time object or 'HH:MM' string

        Returns:
            position_id (int) for tracking
        """
        if at_time is not None:
            at_time = self._to_time(at_time)
        if price is None:
            if at_time is None:
                h, m = map(int, self._entry_time_str.split(":"))
                at_time = time(h, m)
            price = self.get_option_price_at(strike, option_type, at_time)

        if price <= 0:
            self.log(f"WARN: Cannot open {action} {strike} {option_type} — no price data at {at_time}")
            return -1

        pid = self._next_id
        self._next_id += 1

        pos = Position(
            id=pid,
            strike=strike,
            option_type=option_type,
            action=action.upper(),
            lots=lots,
            quantity=lots * self._lot_size,
            entry_price=price,
            entry_time=f"{at_time.hour:02d}:{at_time.minute:02d}" if at_time else self._entry_time_str,
            label=label,
            current_price=price,
        )
        self._positions.append(pos)
        return pid

    def close_position(self, position_id: int, price: Optional[float] = None,
                        reason: str = "manual", at_time: Optional[str] = None) -> bool:
        """
        Close a specific open position.

        Args:
            position_id: ID from open_position()
            price: Exit price (auto-computed from current_price if None)
            reason: Exit reason string
            at_time: Exit time string "HH:MM"

        Returns:
            True if position was found and closed
        """
        for pos in self._positions:
            if pos.id == position_id and pos.is_open:
                exit_price = price if price is not None else pos.current_price
                pos.exit_price = exit_price
                pos.exit_time = at_time or ""
                pos.exit_reason = reason
                pos.is_open = False

                # Calculate P&L
                if pos.action == "SELL":
                    pos.gross_pnl = (pos.entry_price - exit_price) * pos.quantity
                else:
                    pos.gross_pnl = (exit_price - pos.entry_price) * pos.quantity

                # Calculate costs
                pos.cost = self._cost_model.calculate(
                    trade_date=self._trade_date,
                    action=pos.action,
                    premium=pos.entry_price,
                    exit_premium=exit_price,
                    quantity=pos.quantity,
                    num_legs=1,
                )
                pos.net_pnl = pos.gross_pnl - pos.cost.total

                self._closed_positions.append(pos)
                self._positions.remove(pos)
                return True
        return False

    def close_all(self, reason: str = "close_all", price_map: Optional[dict] = None,
                   at_time: Optional[str] = None):
        """
        Close all open positions.

        Args:
            reason: Exit reason for all
            price_map: Optional dict of {position_id: exit_price}
            at_time: Exit time string "HH:MM"
        """
        open_ids = [p.id for p in self._positions if p.is_open]
        for pid in open_ids:
            price = price_map.get(pid) if price_map else None
            self.close_position(pid, price=price, reason=reason, at_time=at_time)

    def get_open_positions(self) -> list[Position]:
        """Get all currently open positions."""
        return [p for p in self._positions if p.is_open]

    def get_position(self, position_id: int) -> Optional[Position]:
        """Get a specific position by ID (open or closed)."""
        for p in self._positions + self._closed_positions:
            if p.id == position_id:
                return p
        return None

    def update_prices(self, candle_time):
        """
        Update current_price for all open positions based on candle close at the given time.
        Accepts time object or 'HH:MM' string.
        """
        candle_time = self._to_time(candle_time)
        for pos in self._positions:
            if not pos.is_open:
                continue
            candles = self.get_candles(pos.strike, pos.option_type)
            if candles.empty:
                continue
            mask = (candles["timestamp"].dt.hour == candle_time.hour) & \
                   (candles["timestamp"].dt.minute == candle_time.minute)
            rows = candles[mask]
            if not rows.empty:
                pos.current_price = float(rows.iloc[0]["close"])

    # ── P&L ──

    def get_total_pnl(self) -> float:
        """
        Current combined P&L of all positions (realized + unrealized).
        """
        realized = sum(p.gross_pnl for p in self._closed_positions)
        unrealized = sum(p.unrealized_pnl for p in self._positions if p.is_open)
        return realized + unrealized

    def get_realized_pnl(self) -> float:
        """P&L from closed positions only."""
        return sum(p.gross_pnl for p in self._closed_positions)

    def get_unrealized_pnl(self) -> float:
        """P&L from open positions only."""
        return sum(p.unrealized_pnl for p in self._positions if p.is_open)

    # ── Logging ──

    def log(self, message: str):
        """Add a log message (included in results)."""
        self._logs.append(f"[{self._trade_date}] {message}")

    # ── Internal: Collect Results ──

    def _force_close_open_positions(self, reason: str = "time_exit"):
        """Close any positions still open at end of day."""
        exit_h, exit_m = map(int, self._exit_time_str.split(":"))
        exit_t = time(exit_h, exit_m)

        for pos in list(self._positions):
            if pos.is_open:
                # Get price at exit time
                candles = self.get_candles(pos.strike, pos.option_type)
                exit_price = pos.current_price
                if not candles.empty:
                    mask = (candles["timestamp"].dt.hour >= exit_h)
                    late_candles = candles[mask]
                    if not late_candles.empty:
                        exit_price = float(late_candles.iloc[0]["open"])

                self.close_position(
                    pos.id, price=exit_price, reason=reason,
                    at_time=f"{exit_h:02d}:{exit_m:02d}",
                )

    def _collect_day_result(self) -> DayResult:
        """Collect all trades and logs for this day."""
        # Force-close any remaining open positions
        self._force_close_open_positions()

        trades = []
        for pos in self._closed_positions:
            # Get absolute strike from data
            candles = self.get_candles(pos.strike, pos.option_type)
            abs_strike = float(candles.iloc[0]["absolute_strike"]) if not candles.empty else 0

            trades.append(TradeRecord(
                trade_date=self._trade_date,
                strike=pos.strike,
                option_type=pos.option_type,
                absolute_strike=abs_strike,
                action=pos.action,
                lots=pos.lots,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                exit_price=pos.exit_price,
                entry_time=pos.entry_time,
                exit_time=pos.exit_time,
                exit_reason=pos.exit_reason,
                gross_pnl=pos.gross_pnl,
                net_pnl=pos.net_pnl,
                dte=self._dte,
                spot_at_entry=self._spot,
                vix_at_entry=self._vix,
                label=pos.label,
                cost=pos.cost,
            ))

        daily_pnl = sum(t.net_pnl for t in trades)

        return DayResult(
            trade_date=self._trade_date,
            trades=trades,
            daily_pnl=daily_pnl,
            logs=self._logs.copy(),
        )


# =========================================================================
# Strategy Result — aggregated across all days
# =========================================================================

@dataclass
class StrategyResult:
    """Complete result from a codegen backtest run."""
    strategy_name: str
    generated_code: str
    user_prompt: str
    from_date: date
    to_date: date
    lot_size: int

    trades: list[TradeRecord] = field(default_factory=list)
    daily_pnl: dict = field(default_factory=dict)   # date -> float
    logs: list[str] = field(default_factory=list)
    skipped_days: list[dict] = field(default_factory=list)
    execution_errors: list[str] = field(default_factory=list)

    # ── Metrics (computed) ──

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def winning_trades(self) -> int:
        return len([t for t in self.trades if t.net_pnl > 0])

    @property
    def losing_trades(self) -> int:
        return len([t for t in self.trades if t.net_pnl < 0])

    @property
    def win_rate(self) -> float:
        return (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

    @property
    def gross_pnl(self) -> float:
        return sum(t.gross_pnl for t in self.trades)

    @property
    def total_cost(self) -> float:
        return sum(t.cost.total for t in self.trades if t.cost)

    @property
    def net_pnl(self) -> float:
        return sum(t.net_pnl for t in self.trades)

    @property
    def max_drawdown(self) -> float:
        equity = 0
        peak = 0
        max_dd = 0
        for t in self.trades:
            equity += t.net_pnl
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        return max_dd

    @property
    def avg_win(self) -> float:
        wins = [t.net_pnl for t in self.trades if t.net_pnl > 0]
        return sum(wins) / len(wins) if wins else 0

    @property
    def avg_loss(self) -> float:
        losses = [t.net_pnl for t in self.trades if t.net_pnl < 0]
        return sum(losses) / len(losses) if losses else 0

    @property
    def max_win(self) -> float:
        wins = [t.net_pnl for t in self.trades if t.net_pnl > 0]
        return max(wins) if wins else 0

    @property
    def max_loss(self) -> float:
        losses = [t.net_pnl for t in self.trades if t.net_pnl < 0]
        return min(losses) if losses else 0

    @property
    def profit_factor(self) -> float:
        gross_wins = sum(t.net_pnl for t in self.trades if t.net_pnl > 0)
        gross_losses = abs(sum(t.net_pnl for t in self.trades if t.net_pnl < 0))
        return (gross_wins / gross_losses) if gross_losses > 0 else float('inf')

    @property
    def payoff_ratio(self) -> float:
        return (self.avg_win / abs(self.avg_loss)) if self.avg_loss != 0 else float('inf')

    @property
    def expectancy(self) -> float:
        wr = self.win_rate / 100
        return (wr * self.avg_win) - ((1 - wr) * abs(self.avg_loss))

    @property
    def sharpe_ratio(self) -> float:
        vals = list(self.daily_pnl.values())
        if len(vals) < 2:
            return 0
        mean = np.mean(vals)
        std = np.std(vals)
        return float(mean / std * (252 ** 0.5)) if std > 0 else 0

    @property
    def calmar_ratio(self) -> float:
        if self.max_drawdown == 0:
            return 0
        trading_days = len(self.daily_pnl)
        if trading_days == 0:
            return 0
        annual_pnl = self.net_pnl * (252 / trading_days)
        return annual_pnl / self.max_drawdown

    @property
    def max_consecutive_wins(self) -> int:
        return self._max_consecutive(True)

    @property
    def max_consecutive_losses(self) -> int:
        return self._max_consecutive(False)

    def _max_consecutive(self, winning: bool) -> int:
        count = 0
        max_count = 0
        for t in self.trades:
            if (winning and t.net_pnl > 0) or (not winning and t.net_pnl < 0):
                count += 1
                max_count = max(max_count, count)
            else:
                count = 0
        return max_count

    def equity_curve(self) -> list[dict]:
        """Build equity curve from daily P&L."""
        curve = []
        cumulative = 0
        for d in sorted(self.daily_pnl.keys()):
            cumulative += self.daily_pnl[d]
            curve.append({
                "date": str(d),
                "daily_pnl": round(self.daily_pnl[d], 2),
                "cumulative": round(cumulative, 2),
            })
        return curve

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for API response."""
        import math

        def safe(v):
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    return 0
                return round(v, 2)
            return v

        trades_list = []
        for t in self.trades:
            trades_list.append({
                "date": str(t.trade_date),
                "strike": t.strike,
                "option_type": t.option_type,
                "absolute_strike": t.absolute_strike,
                "action": t.action,
                "lots": t.lots,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "exit_reason": t.exit_reason,
                "gross_pnl": round(t.gross_pnl, 2),
                "net_pnl": round(t.net_pnl, 2),
                "dte": t.dte,
                "spot": round(t.spot_at_entry, 2),
                "vix": round(t.vix_at_entry, 2),
                "label": t.label,
                "leg": t.label or f"{t.action} {t.strike} {t.option_type}",
                "costs": t.cost.to_dict() if t.cost else {},
            })

        return {
            "strategy_name": self.strategy_name,
            "generated_code": self.generated_code,
            "user_prompt": self.user_prompt,
            "summary": {
                "total_trades": self.total_trades,
                "trading_days": len(self.daily_pnl),
                "winners": self.winning_trades,
                "losers": self.losing_trades,
                "breakeven": self.total_trades - self.winning_trades - self.losing_trades,
                "win_rate": safe(self.win_rate),
                "gross_pnl": safe(self.gross_pnl),
                "total_cost": safe(self.total_cost),
                "net_pnl": safe(self.net_pnl),
                "max_drawdown": safe(self.max_drawdown),
                "profit_factor": safe(self.profit_factor) if self.profit_factor != float('inf') else 999,
                "payoff_ratio": safe(self.payoff_ratio) if self.payoff_ratio != float('inf') else 999,
                "expectancy": safe(self.expectancy),
                "avg_win": safe(self.avg_win),
                "avg_loss": safe(self.avg_loss),
                "max_win": safe(self.max_win),
                "max_loss": safe(self.max_loss),
                "sharpe_ratio": safe(self.sharpe_ratio),
                "calmar_ratio": safe(self.calmar_ratio),
                "max_consecutive_wins": self.max_consecutive_wins,
                "max_consecutive_losses": self.max_consecutive_losses,
                "avg_daily_pnl": safe(np.mean(list(self.daily_pnl.values()))) if self.daily_pnl else 0,
                "skipped_days": len(self.skipped_days),
            },
            "trades": trades_list,
            "equity_curve": self.equity_curve(),
            "logs": self.logs[-200:],  # Limit logs
            "execution_errors": self.execution_errors,
        }
