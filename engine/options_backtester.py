"""
Antigravity Trading — NIFTY Options Backtester
================================================
Rule-accurate backtester for NIFTY options strategies.

Rules:
  A) Entry/exit at candle OPEN price
  B) Hard SL: exit at SL price if candle high/low breaches
     Close SL: exit at candle CLOSE if close breaches
  C) Same logic for targets
  D) General factors (slippage, brokerage, taxes, VIX) applied post-trade
  E) Each trade tagged with DTE (days to expiry)
  F) Data boundary: skip days where required strikes leave ±10 ATM range
"""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, time
from pathlib import Path
from typing import Optional

from strategy.strategy_config import StrategyConfig, LegConfig
from engine.cost_model import CostModel, CostConfig, TradeCost

logger = logging.getLogger("antigravity.backtester.options")

DATA_DIR = Path(__file__).resolve().parent.parent / "storage" / "candles" / "nifty_options"
EXPIRY_CALENDAR_PATH = Path(__file__).resolve().parent.parent / "storage" / "candles" / "NIFTY_CONSENSUS_EXPIRY_CALENDAR.csv"

IST_OFFSET = pd.Timedelta(hours=5, minutes=30)


# =========================================================================
# Trade Record
# =========================================================================

@dataclass
class OptionTrade:
    """Record of a single leg trade."""
    trade_date: date
    leg_id: int
    action: str            # "BUY" or "SELL"
    strike: str            # "ATM", "ATM+1", etc.
    option_type: str       # "CE" or "PE"
    absolute_strike: float
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    exit_reason: str       # "time_exit", "sl_hard", "sl_close", "target_hard", "target_close"
    quantity: int
    gross_pnl: float
    dte: int               # Days to expiry at entry
    spot_at_entry: float
    vix_at_entry: float
    cost: Optional[TradeCost] = None
    net_pnl: float = 0.0
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class BacktestResult:
    """Complete backtest output."""
    strategy: StrategyConfig
    trades: list[OptionTrade] = field(default_factory=list)
    skipped_days: list[dict] = field(default_factory=list)
    cost_config: Optional[CostConfig] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # ── Core metrics ──

    @property
    def active_trades(self) -> list[OptionTrade]:
        return [t for t in self.trades if not t.skipped]

    @property
    def total_trades(self) -> int:
        return len(self.active_trades)

    @property
    def winning_trades(self) -> int:
        return len([t for t in self.active_trades if t.net_pnl > 0])

    @property
    def losing_trades(self) -> int:
        return len([t for t in self.active_trades if t.net_pnl < 0])

    @property
    def breakeven_trades(self) -> int:
        return len([t for t in self.active_trades if t.net_pnl == 0])

    @property
    def total_pnl(self) -> float:
        return sum(t.net_pnl for t in self.active_trades)

    @property
    def gross_pnl(self) -> float:
        return sum(t.gross_pnl for t in self.active_trades)

    @property
    def total_cost(self) -> float:
        return sum(t.cost.total for t in self.active_trades if t.cost)

    @property
    def total_brokerage(self) -> float:
        return sum(t.cost.brokerage for t in self.active_trades if t.cost)

    @property
    def total_stt(self) -> float:
        return sum(t.cost.stt for t in self.active_trades if t.cost)

    @property
    def total_exchange_charges(self) -> float:
        return sum(t.cost.exchange_charges for t in self.active_trades if t.cost)

    @property
    def total_gst(self) -> float:
        return sum(t.cost.gst for t in self.active_trades if t.cost)

    @property
    def total_sebi_fees(self) -> float:
        return sum(t.cost.sebi_fee for t in self.active_trades if t.cost)

    @property
    def total_stamp_duty(self) -> float:
        return sum(t.cost.stamp_duty for t in self.active_trades if t.cost)

    @property
    def total_slippage(self) -> float:
        return sum(t.cost.slippage for t in self.active_trades if t.cost)

    @property
    def win_rate(self) -> float:
        total = self.total_trades
        return (self.winning_trades / total * 100) if total > 0 else 0

    @property
    def max_drawdown(self) -> float:
        if not self.trades:
            return 0
        equity = 0
        peak = 0
        max_dd = 0
        for t in self.active_trades:
            equity += t.net_pnl
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)
        return max_dd

    # ── Advanced Ratios (Fix #5) ──

    @property
    def avg_win(self) -> float:
        wins = [t.net_pnl for t in self.active_trades if t.net_pnl > 0]
        return sum(wins) / len(wins) if wins else 0

    @property
    def avg_loss(self) -> float:
        losses = [t.net_pnl for t in self.active_trades if t.net_pnl < 0]
        return sum(losses) / len(losses) if losses else 0

    @property
    def max_win(self) -> float:
        wins = [t.net_pnl for t in self.active_trades if t.net_pnl > 0]
        return max(wins) if wins else 0

    @property
    def max_loss(self) -> float:
        losses = [t.net_pnl for t in self.active_trades if t.net_pnl < 0]
        return min(losses) if losses else 0

    @property
    def profit_factor(self) -> float:
        """Total winning / Total losing (absolute). >1 = profitable."""
        gross_wins = sum(t.net_pnl for t in self.active_trades if t.net_pnl > 0)
        gross_losses = abs(sum(t.net_pnl for t in self.active_trades if t.net_pnl < 0))
        return (gross_wins / gross_losses) if gross_losses > 0 else float('inf')

    @property
    def payoff_ratio(self) -> float:
        """Avg win / Avg loss (absolute). Also called reward-to-risk ratio."""
        return (self.avg_win / abs(self.avg_loss)) if self.avg_loss != 0 else float('inf')

    @property
    def expectancy(self) -> float:
        """Expected P&L per trade = (WR * avg_win) - ((1-WR) * |avg_loss|)."""
        wr = self.win_rate / 100
        return (wr * self.avg_win) - ((1 - wr) * abs(self.avg_loss))

    @property
    def avg_daily_pnl(self) -> float:
        daily = self.daily_pnl()
        vals = list(daily.values())
        return np.mean(vals) if vals else 0

    @property
    def sharpe_ratio(self) -> float:
        daily = self.daily_pnl()
        vals = list(daily.values())
        if len(vals) < 2:
            return 0
        mean = np.mean(vals)
        std = np.std(vals)
        return (mean / std * (252 ** 0.5)) if std > 0 else 0

    @property
    def calmar_ratio(self) -> float:
        """Annualized return / Max drawdown."""
        if self.max_drawdown == 0:
            return 0
        daily = self.daily_pnl()
        trading_days = len(daily)
        if trading_days == 0:
            return 0
        annual_pnl = self.total_pnl * (252 / trading_days)
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
        for t in self.active_trades:
            if (winning and t.net_pnl > 0) or (not winning and t.net_pnl < 0):
                count += 1
                max_count = max(max_count, count)
            else:
                count = 0
        return max_count

    # ── P&L Helpers ──

    def daily_pnl(self) -> dict[date, float]:
        """P&L grouped by date."""
        daily = {}
        for t in self.active_trades:
            d = t.trade_date
            daily[d] = daily.get(d, 0) + t.net_pnl
        return daily

    def dte_breakdown(self, buckets: list[tuple[int, int]] | None = None) -> dict[str, dict]:
        """Performance grouped by DTE bucket. Accepts custom buckets as list of (min, max) tuples."""
        if buckets is None:
            buckets = [(0, 3), (4, 7), (8, 14), (15, 999)]

        bucket_map: dict[str, list] = {}
        for lo, hi in buckets:
            label = f"{lo}-{hi}" if hi < 999 else f"{lo}+"
            bucket_map[label] = (lo, hi, [])

        for t in self.active_trades:
            for label, (lo, hi, trades) in bucket_map.items():
                if lo <= t.dte <= hi:
                    trades.append(t)
                    break

        result = {}
        for label, (lo, hi, trades) in bucket_map.items():
            if trades:
                result[label] = {
                    "count": len(trades),
                    "total_pnl": round(sum(t.net_pnl for t in trades), 2),
                    "avg_pnl": round(sum(t.net_pnl for t in trades) / len(trades), 2),
                    "win_rate": round(len([t for t in trades if t.net_pnl > 0]) / len(trades) * 100, 1),
                }
        return result

    def cost_breakdown(self) -> dict:
        """Detailed cost breakdown for the entire backtest period."""
        return {
            "brokerage": round(self.total_brokerage, 2),
            "stt": round(self.total_stt, 2),
            "exchange_charges": round(self.total_exchange_charges, 2),
            "gst": round(self.total_gst, 2),
            "sebi_fees": round(self.total_sebi_fees, 2),
            "stamp_duty": round(self.total_stamp_duty, 2),
            "slippage": round(self.total_slippage, 2),
            "total": round(self.total_cost, 2),
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            "=" * 60,
            f"BACKTEST RESULT: {self.strategy.name}",
            "=" * 60,
            f"  Period: {self.trades[0].trade_date if self.trades else '?'} to "
            f"{self.trades[-1].trade_date if self.trades else '?'}",
            f"  Total Trading Days: {len(set(t.trade_date for t in self.active_trades))}",
            f"  Skipped Days: {len(self.skipped_days)}",
            f"  Total Trades: {self.total_trades}",
            f"  Winners: {self.winning_trades} | Losers: {self.losing_trades}",
            f"  Win Rate: {self.win_rate:.1f}%",
            f"  Gross P&L: Rs.{self.gross_pnl:,.2f}",
            f"  Total Costs: Rs.{self.total_cost:,.2f}",
            f"  Net P&L: Rs.{self.total_pnl:,.2f}",
            f"  Max Drawdown: Rs.{self.max_drawdown:,.2f}",
            f"  Profit Factor: {self.profit_factor:.2f}",
            f"  Payoff Ratio: {self.payoff_ratio:.2f}",
            f"  Expectancy: Rs.{self.expectancy:,.2f}",
            f"  Avg Win: Rs.{self.avg_win:,.2f} | Avg Loss: Rs.{self.avg_loss:,.2f}",
            f"  Max Win: Rs.{self.max_win:,.2f} | Max Loss: Rs.{self.max_loss:,.2f}",
            f"  Sharpe: {self.sharpe_ratio:.2f} | Calmar: {self.calmar_ratio:.2f}",
        ]
        dte = self.dte_breakdown()
        if dte:
            lines.append("  DTE Breakdown:")
            for bucket, stats in dte.items():
                lines.append(f"    {bucket}: {stats['count']} trades, "
                             f"Rs.{stats['total_pnl']:,.0f}, "
                             f"WR={stats['win_rate']:.0f}%")
        costs = self.cost_breakdown()
        lines.append("  Cost Breakdown:")
        lines.append(f"    Brokerage: Rs.{costs['brokerage']:,.2f}")
        lines.append(f"    STT: Rs.{costs['stt']:,.2f}")
        lines.append(f"    Exchange: Rs.{costs['exchange_charges']:,.2f}")
        lines.append(f"    GST: Rs.{costs['gst']:,.2f}")
        lines.append(f"    Slippage: Rs.{costs['slippage']:,.2f}")
        lines.append("=" * 60)
        return "\n".join(lines)


# =========================================================================
# Expiry Calendar
# =========================================================================

def load_expiry_calendar() -> pd.DataFrame:
    """Load NIFTY expiry calendar."""
    if EXPIRY_CALENDAR_PATH.exists():
        df = pd.read_csv(EXPIRY_CALENDAR_PATH)
        # Try to parse expiry dates
        for col in df.columns:
            if "expiry" in col.lower() or "date" in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception:
                    pass
        return df
    return pd.DataFrame()


def get_next_expiry(trade_date: date, expiry_df: pd.DataFrame, expiry_type: str = "MONTH") -> Optional[date]:
    """Find the next expiry date on or after trade_date."""
    if expiry_df.empty:
        return None

    # Try common column names
    date_col = None
    for col in expiry_df.columns:
        if "expiry" in col.lower() or "date" in col.lower():
            date_col = col
            break

    if date_col is None:
        return None

    future_expiries = expiry_df[expiry_df[date_col] >= pd.Timestamp(trade_date)]
    if future_expiries.empty:
        return None

    return future_expiries[date_col].iloc[0].date()


# =========================================================================
# Optimized Data Loader (Fix #1 — Speed)
# =========================================================================

class DataLoader:
    """
    Preloads a file index and caches entire CSV files in memory.
    Avoids re-globbing and re-reading per trading day.
    """

    def __init__(self):
        self._file_index: list[tuple[pd.Timestamp, pd.Timestamp, Path]] = []
        self._file_cache: dict[str, pd.DataFrame] = {}
        self._day_cache: dict[str, pd.DataFrame] = {}
        self._index_built = False

    def _build_index(self):
        """Build sorted list of (from_date, to_date, filepath)."""
        if self._index_built:
            return
        for f in DATA_DIR.glob("NIFTY_Options_*.csv"):
            parts = f.stem.replace("NIFTY_Options_", "").replace("NIFTY_Options_Phase2_", "")
            try:
                dates = parts.split("_")
                file_from = pd.Timestamp(dates[0])
                file_to = pd.Timestamp(dates[1])
                self._file_index.append((file_from, file_to, f))
            except Exception:
                continue
        self._file_index.sort(key=lambda x: x[0])
        self._index_built = True
        logger.info("Data index built: %d files", len(self._file_index))

    def _load_file(self, f: Path) -> pd.DataFrame:
        """Load and cache an entire CSV file with timestamp conversion."""
        key = str(f)
        if key in self._file_cache:
            return self._file_cache[key]

        df = pd.read_csv(f)

        # Parse timestamp — convert UTC to IST (+5:30)
        if df["timestamp"].dtype in ("int64", "float64"):
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s") + IST_OFFSET
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")

        df["date"] = df["timestamp"].dt.date
        self._file_cache[key] = df
        return df

    def load_day(self, trade_date: date) -> Optional[pd.DataFrame]:
        """Load data for a single trading day, using file + day cache."""
        self._build_index()

        cache_key = str(trade_date)
        if cache_key in self._day_cache:
            return self._day_cache[cache_key]

        target_ts = pd.Timestamp(trade_date)

        for file_from, file_to, f in self._file_index:
            if file_from <= target_ts <= file_to:
                df = self._load_file(f)
                day_df = df[df["date"] == trade_date].copy()
                if not day_df.empty:
                    day_df = day_df.sort_values("timestamp").reset_index(drop=True)
                    self._day_cache[cache_key] = day_df
                    return day_df

        return None

    def preload_range(self, from_date: date, to_date: date):
        """Preload all files covering the date range into memory."""
        self._build_index()
        from_ts = pd.Timestamp(from_date)
        to_ts = pd.Timestamp(to_date)

        loaded = 0
        for file_from, file_to, f in self._file_index:
            if file_to >= from_ts and file_from <= to_ts:
                self._load_file(f)
                loaded += 1
        logger.info("Preloaded %d files for %s to %s", loaded, from_date, to_date)

    def clear_cache(self):
        self._file_cache.clear()
        self._day_cache.clear()


# Singleton data loader
_data_loader = DataLoader()


def load_day_data(trade_date: date, data_cache: dict = None) -> Optional[pd.DataFrame]:
    """Load options data for a single trading day (uses optimized loader)."""
    return _data_loader.load_day(trade_date)


# =========================================================================
# Core Backtesting Logic
# =========================================================================

def check_data_boundary(day_data: pd.DataFrame, config: StrategyConfig) -> tuple[bool, str]:
    """
    Rule G: Check if all required strikes have data for the full session.
    Returns (is_valid, reason).
    """
    required_strikes = set()
    for leg in config.legs:
        required_strikes.add(leg.strike)

    available_strikes = set(day_data["strike_rel"].unique())

    missing = required_strikes - available_strikes
    if missing:
        return False, f"Missing strikes: {missing}"

    # Check each required strike has data from entry to exit time
    entry_h, entry_m = map(int, config.entry_time.split(":"))
    exit_h, exit_m = map(int, config.exit_time.split(":"))

    for strike in required_strikes:
        strike_data = day_data[day_data["strike_rel"] == strike]
        if strike_data.empty:
            return False, f"No data for strike {strike}"

        first_ts = strike_data["timestamp"].iloc[0]
        last_ts = strike_data["timestamp"].iloc[-1]

        entry_ts = first_ts.replace(hour=entry_h, minute=entry_m, second=0)
        exit_ts = first_ts.replace(hour=exit_h, minute=exit_m, second=0)

        if first_ts > entry_ts or last_ts < exit_ts:
            return False, f"Strike {strike} data doesn't cover {config.entry_time}-{config.exit_time}"

    return True, ""


def execute_leg(
    day_data: pd.DataFrame,
    leg: LegConfig,
    config: StrategyConfig,
    trade_date: date,
    dte: int,
    cost_model: CostModel,
) -> OptionTrade:
    """Execute a single leg for one day."""
    entry_h, entry_m = map(int, config.entry_time.split(":"))
    exit_h, exit_m = map(int, config.exit_time.split(":"))

    # Filter to this strike and type
    leg_type = "CALL" if leg.option_type == "CE" else "PUT"
    mask = (day_data["strike_rel"] == leg.strike) & (day_data["type"] == leg_type)
    strike_data = day_data[mask].copy().sort_values("timestamp")

    if strike_data.empty:
        return OptionTrade(
            trade_date=trade_date, leg_id=0, action=leg.action,
            strike=leg.strike, option_type=leg.option_type,
            absolute_strike=0, entry_time=config.entry_time,
            exit_time=config.exit_time, entry_price=0, exit_price=0,
            exit_reason="no_data", quantity=0, gross_pnl=0, dte=dte,
            spot_at_entry=0, vix_at_entry=0, skipped=True,
            skip_reason="No data for this strike/type",
        )

    # Find entry candle (OPEN of entry_time candle)
    entry_mask = (strike_data["timestamp"].dt.hour == entry_h) & \
                 (strike_data["timestamp"].dt.minute == entry_m)
    entry_candles = strike_data[entry_mask]

    if entry_candles.empty:
        return OptionTrade(
            trade_date=trade_date, leg_id=0, action=leg.action,
            strike=leg.strike, option_type=leg.option_type,
            absolute_strike=0, entry_time=config.entry_time,
            exit_time=config.exit_time, entry_price=0, exit_price=0,
            exit_reason="no_entry_candle", quantity=0, gross_pnl=0, dte=dte,
            spot_at_entry=0, vix_at_entry=0, skipped=True,
            skip_reason=f"No candle at {config.entry_time}",
        )

    entry_row = entry_candles.iloc[0]
    entry_price = entry_row["open"]
    absolute_strike = entry_row.get("absolute_strike", 0)
    spot_at_entry = entry_row.get("spot_price", 0)
    vix_at_entry = entry_row.get("india_vix", 0)

    # Calculate SL and target prices
    sl_pct = leg.sl_pct if leg.sl_pct is not None else config.sl_pct
    target_pct = leg.target_pct if leg.target_pct is not None else config.target_pct
    sl_type = config.sl_type
    target_type = config.target_type

    if sl_pct > 0:
        if leg.action == "SELL":
            sl_price = entry_price * (1 + sl_pct / 100)
        else:
            sl_price = entry_price * (1 - sl_pct / 100)
    else:
        sl_price = None

    if target_pct > 0:
        if leg.action == "SELL":
            target_price = entry_price * (1 - target_pct / 100)
        else:
            target_price = entry_price * (1 + target_pct / 100)
    else:
        target_price = None

    # Walk through candles after entry to find exit
    entry_ts = entry_row["timestamp"]
    post_entry = strike_data[strike_data["timestamp"] > entry_ts]

    exit_price = entry_price
    exit_time = config.exit_time
    exit_reason = "time_exit"

    for _, candle in post_entry.iterrows():
        candle_time = candle["timestamp"]

        # Time exit check
        if candle_time.hour > exit_h or (candle_time.hour == exit_h and candle_time.minute >= exit_m):
            exit_price = candle["open"]  # Rule B: exit at OPEN of exit candle
            exit_time = candle_time.strftime("%H:%M")
            exit_reason = "time_exit"
            break

        # SL check
        if sl_price is not None:
            if leg.action == "SELL":
                # For SELL: SL triggers when price goes UP
                if sl_type == "hard" and candle["high"] >= sl_price:
                    exit_price = sl_price  # Hard SL: exit at SL price exactly
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "sl_hard"
                    break
                elif sl_type == "close" and candle["close"] >= sl_price:
                    exit_price = candle["close"]  # Close SL: exit at candle close
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "sl_close"
                    break
            else:
                # For BUY: SL triggers when price goes DOWN
                if sl_type == "hard" and candle["low"] <= sl_price:
                    exit_price = sl_price
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "sl_hard"
                    break
                elif sl_type == "close" and candle["close"] <= sl_price:
                    exit_price = candle["close"]
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "sl_close"
                    break

        # Target check
        if target_price is not None:
            if leg.action == "SELL":
                # For SELL: target when price goes DOWN
                if target_type == "hard" and candle["low"] <= target_price:
                    exit_price = target_price
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "target_hard"
                    break
                elif target_type == "close" and candle["close"] <= target_price:
                    exit_price = candle["close"]
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "target_close"
                    break
            else:
                # For BUY: target when price goes UP
                if target_type == "hard" and candle["high"] >= target_price:
                    exit_price = target_price
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "target_hard"
                    break
                elif target_type == "close" and candle["close"] >= target_price:
                    exit_price = candle["close"]
                    exit_time = candle_time.strftime("%H:%M")
                    exit_reason = "target_close"
                    break

    # Calculate P&L
    quantity = leg.lots * config.lot_size
    if leg.action == "SELL":
        gross_pnl = (entry_price - exit_price) * quantity
    else:
        gross_pnl = (exit_price - entry_price) * quantity

    # Calculate costs
    trade_cost = cost_model.calculate(
        trade_date=trade_date,
        action=leg.action,
        premium=entry_price,
        exit_premium=exit_price,
        quantity=quantity,
        num_legs=1,
    )
    net_pnl = gross_pnl - trade_cost.total

    return OptionTrade(
        trade_date=trade_date,
        leg_id=0,
        action=leg.action,
        strike=leg.strike,
        option_type=leg.option_type,
        absolute_strike=absolute_strike,
        entry_time=config.entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        exit_reason=exit_reason,
        quantity=quantity,
        gross_pnl=gross_pnl,
        dte=dte,
        spot_at_entry=spot_at_entry,
        vix_at_entry=vix_at_entry,
        cost=trade_cost,
        net_pnl=net_pnl,
    )


# =========================================================================
# Main Backtester
# =========================================================================

class OptionsBacktester:
    """
    NIFTY options backtester.

    Usage:
        config = StrategyConfig(
            name="ATM Straddle Sell",
            legs=[LegConfig("SELL","ATM","CE"), LegConfig("SELL","ATM","PE")],
            entry_time="09:20", exit_time="15:15",
            sl_pct=25, sl_type="hard",
        )
        bt = OptionsBacktester()
        result = bt.run(config, from_date=date(2023,1,1), to_date=date(2024,12,31))
        print(result.summary())
    """

    def __init__(self, cost_config: Optional[CostConfig] = None):
        self.cost_model = CostModel(cost_config or CostConfig())
        self.cost_config = cost_config or CostConfig()

    def run(
        self,
        config: StrategyConfig,
        from_date: date,
        to_date: date,
        progress_callback=None,
    ) -> BacktestResult:
        """Run backtest across date range."""
        # Validate config
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid strategy config: {errors}")

        result = BacktestResult(
            strategy=config,
            cost_config=self.cost_config,
            started_at=datetime.now(),
        )

        # Preload data files for the entire range (Fix #1 — Speed)
        _data_loader.preload_range(from_date, to_date)

        # Load expiry calendar
        expiry_df = load_expiry_calendar()

        # Generate trading days (weekdays only)
        current = from_date
        total_days = (to_date - from_date).days
        processed = 0

        while current <= to_date:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            processed += 1
            if progress_callback and processed % 50 == 0:
                progress_callback(processed, total_days)

            # Load day data
            day_data = _data_loader.load_day(current)
            if day_data is None or day_data.empty:
                current += timedelta(days=1)
                continue

            # Calculate DTE
            next_expiry = get_next_expiry(current, expiry_df, config.expiry_type)
            dte = (next_expiry - current).days if next_expiry else 0

            # Check DTE filters
            if config.dte_min is not None and dte < config.dte_min:
                current += timedelta(days=1)
                continue
            if config.dte_max is not None and dte > config.dte_max:
                current += timedelta(days=1)
                continue

            # Check VIX filter
            if config.vix_min is not None or config.vix_max is not None:
                vix_vals = day_data["india_vix"].dropna()
                if not vix_vals.empty:
                    avg_vix = vix_vals.iloc[0]
                    if config.vix_min and avg_vix < config.vix_min:
                        current += timedelta(days=1)
                        continue
                    if config.vix_max and avg_vix > config.vix_max:
                        current += timedelta(days=1)
                        continue

            # Rule G: Check data boundary
            is_valid, reason = check_data_boundary(day_data, config)
            if not is_valid:
                result.skipped_days.append({"date": current, "reason": reason})
                current += timedelta(days=1)
                continue

            # Execute each leg
            for i, leg in enumerate(config.legs):
                trade = execute_leg(
                    day_data, leg, config, current, dte, self.cost_model,
                )
                trade.leg_id = i + 1

                if trade.skipped:
                    result.skipped_days.append({
                        "date": current,
                        "reason": trade.skip_reason,
                        "leg": i + 1,
                    })
                else:
                    result.trades.append(trade)

            current += timedelta(days=1)

        result.completed_at = datetime.now()
        return result


# =========================================================================
# Demo
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("OPTIONS BACKTESTER DEMO")
    print("=" * 60)

    config = StrategyConfig(
        name="ATM Straddle Sell (Hard SL)",
        legs=[
            LegConfig("SELL", "ATM", "CE"),
            LegConfig("SELL", "ATM", "PE"),
        ],
        entry_time="09:20",
        exit_time="15:15",
        sl_pct=25.0,
        sl_type="hard",
        lot_size=25,
    )
    print(config.summary())
    print()

    bt = OptionsBacktester()

    def on_progress(done, total):
        print(f"  Progress: {done}/{total} days...")

    result = bt.run(
        config,
        from_date=date(2024, 1, 1),
        to_date=date(2024, 3, 31),
        progress_callback=on_progress,
    )

    print(result.summary())
