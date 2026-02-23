"""
Strategy: ATM Straddle Sell with Re-entry on SL + Trailing Features
====================================================================
Written by Antigravity AI (not Gemini-generated).

Rules:
  - Entry 9:16, Exit 14:30
  - Sell 1 ATM CE + 1 ATM PE with 30% hard SL per leg
  - Re-entry: If CE SL triggers, sell 1 more ATM CE with 30% SL
    BUT only when ATM CE price has increased by 10% from SL price
  - Re-entry: If PE SL triggers, sell 1 more ATM PE with 30% SL
    BUT only when ATM PE price has increased by 10% from SL price
  - Global hard SL: Rs 9000 combined loss
  - Profit lock: When profit reaches Rs 1500, lock at Rs 200
  - Lot size: 65
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from datetime import date, time
from collections import defaultdict
from engine.strategy_sdk import StrategyContext, StrategyResult, TradeRecord
from engine.cost_model import CostModel, CostConfig
from engine.options_backtester import _data_loader, load_expiry_calendar, get_next_expiry
from datetime import timedelta


def strategy(ctx: StrategyContext):
    """ATM Straddle + Re-entry on SL hit."""
    entry_t = time(9, 16)
    exit_t = time(14, 30)

    # --- Parameters ---
    sl_pct = 30       # 30% hard SL per leg
    global_sl = -9000  # Rs 9000 global stop loss
    profit_lock_trigger = 1500  # Lock when profit reaches this
    profit_lock_level = 200     # Lock profit at this
    reentry_price_increase = 0.10  # 10% price increase required for re-entry

    # --- Open initial straddle ---
    ce_id = ctx.open_position("ATM", "CE", "SELL", 1, "CE leg 1", at_time=entry_t)
    pe_id = ctx.open_position("ATM", "PE", "SELL", 1, "PE leg 1", at_time=entry_t)

    if ce_id == -1 or pe_id == -1:
        ctx.close_all("no_data")
        return

    # Track SL prices and re-entry state
    ce_pos = ctx.get_position(ce_id)
    pe_pos = ctx.get_position(pe_id)

    ce_sl_price = ce_pos.entry_price * (1 + sl_pct / 100)
    pe_sl_price = pe_pos.entry_price * (1 + sl_pct / 100)

    ce_sl_hit = False
    pe_sl_hit = False
    ce_reentry_done = False
    pe_reentry_done = False
    ce_sl_exit_price = 0.0  # Price at which CE SL triggered
    pe_sl_exit_price = 0.0  # Price at which PE SL triggered

    # Re-entry position tracking
    ce2_id = None
    pe2_id = None
    ce2_sl_price = None
    pe2_sl_price = None

    locked_profit = None
    peak_pnl = 0

    # --- Walk candles minute by minute ---
    ce_candles = ctx.get_candles("ATM", "CE")
    if ce_candles.empty:
        ctx.close_all("no_candle_data")
        return

    for _, row in ce_candles.iterrows():
        t = row["timestamp"].time()

        # Skip candles before entry
        if t <= entry_t:
            continue

        # Time exit
        if t >= exit_t:
            ctx.close_all("time_exit", at_time=f"{exit_t.hour:02d}:{exit_t.minute:02d}")
            return

        # Update all position prices
        ctx.update_prices(t)
        total_pnl = ctx.get_total_pnl()

        # --- Global SL check ---
        if total_pnl <= global_sl:
            ctx.close_all("global_sl", at_time=f"{t.hour:02d}:{t.minute:02d}")
            ctx.log(f"Global SL hit at Rs.{total_pnl:.0f}")
            return

        # --- Profit lock check ---
        if total_pnl >= profit_lock_trigger and locked_profit is None:
            locked_profit = profit_lock_level
            ctx.log(f"Profit locked at Rs.{profit_lock_level} (P&L reached Rs.{total_pnl:.0f})")

        if locked_profit is not None and total_pnl <= locked_profit:
            ctx.close_all("profit_lock", at_time=f"{t.hour:02d}:{t.minute:02d}")
            ctx.log(f"Profit lock exit at Rs.{total_pnl:.0f}")
            return

        # --- Check SL on initial CE leg ---
        if not ce_sl_hit:
            ce_p = ctx.get_position(ce_id)
            if ce_p and ce_p.is_open and ce_p.current_price >= ce_sl_price:
                ctx.close_position(ce_id, price=ce_sl_price, reason="sl_hit",
                                   at_time=f"{t.hour:02d}:{t.minute:02d}")
                ce_sl_hit = True
                ce_sl_exit_price = ce_sl_price
                ctx.log(f"CE SL hit at {t}, exit price: {ce_sl_price:.1f}")

        # --- Check SL on initial PE leg ---
        if not pe_sl_hit:
            pe_p = ctx.get_position(pe_id)
            if pe_p and pe_p.is_open and pe_p.current_price >= pe_sl_price:
                ctx.close_position(pe_id, price=pe_sl_price, reason="sl_hit",
                                   at_time=f"{t.hour:02d}:{t.minute:02d}")
                pe_sl_hit = True
                pe_sl_exit_price = pe_sl_price
                ctx.log(f"PE SL hit at {t}, exit price: {pe_sl_price:.1f}")

        # --- CE Re-entry: only when ATM CE price increased 10% from SL exit ---
        if ce_sl_hit and not ce_reentry_done:
            current_ce_price = ctx.get_option_price_at("ATM", "CE", t)
            if current_ce_price > 0 and current_ce_price >= ce_sl_exit_price * (1 + reentry_price_increase):
                ce2_id = ctx.open_position("ATM", "CE", "SELL", 1, "CE leg 2 (re-entry)",
                                           price=current_ce_price,
                                           at_time=t)
                if ce2_id != -1:
                    ce2_sl_price = current_ce_price * (1 + sl_pct / 100)
                    ce_reentry_done = True
                    ctx.log(f"CE re-entry at {t}, price: {current_ce_price:.1f} (10% above SL)")

        # --- PE Re-entry: only when ATM PE price increased 10% from SL exit ---
        if pe_sl_hit and not pe_reentry_done:
            current_pe_price = ctx.get_option_price_at("ATM", "PE", t)
            if current_pe_price > 0 and current_pe_price >= pe_sl_exit_price * (1 + reentry_price_increase):
                pe2_id = ctx.open_position("ATM", "PE", "SELL", 1, "PE leg 2 (re-entry)",
                                           price=current_pe_price,
                                           at_time=t)
                if pe2_id != -1:
                    pe2_sl_price = current_pe_price * (1 + sl_pct / 100)
                    pe_reentry_done = True
                    ctx.log(f"PE re-entry at {t}, price: {current_pe_price:.1f} (10% above SL)")

        # --- Check SL on CE re-entry leg ---
        if ce2_id and ce2_sl_price:
            ce2_p = ctx.get_position(ce2_id)
            if ce2_p and ce2_p.is_open and ce2_p.current_price >= ce2_sl_price:
                ctx.close_position(ce2_id, price=ce2_sl_price, reason="reentry_sl",
                                   at_time=f"{t.hour:02d}:{t.minute:02d}")
                ctx.log(f"CE re-entry SL hit at {t}")
                ce2_id = None

        # --- Check SL on PE re-entry leg ---
        if pe2_id and pe2_sl_price:
            pe2_p = ctx.get_position(pe2_id)
            if pe2_p and pe2_p.is_open and pe2_p.current_price >= pe2_sl_price:
                ctx.close_position(pe2_id, price=pe2_sl_price, reason="reentry_sl",
                                   at_time=f"{t.hour:02d}:{t.minute:02d}")
                ctx.log(f"PE re-entry SL hit at {t}")
                pe2_id = None

    # Close anything remaining at end of day
    ctx.close_all("time_exit", at_time=f"{exit_t.hour:02d}:{exit_t.minute:02d}")


# ======================================================================
# Run the backtest
# ======================================================================

if __name__ == "__main__":
    cost_model = CostModel(CostConfig(slippage_pts=0.5, brokerage_per_order=20))
    lot_size = 65
    from_date = date(2024, 1, 1)
    to_date = date(2024, 12, 31)

    _data_loader.preload_range(from_date, to_date)
    expiry_df = load_expiry_calendar()

    result = StrategyResult(
        strategy_name="ATM Straddle + Re-entry on SL",
        generated_code="Hand-written by Antigravity AI",
        user_prompt="Sell straddle, 30% SL, re-entry on 10% price increase, global SL 9000, lock 200@1500",
        from_date=from_date,
        to_date=to_date,
        lot_size=lot_size,
    )

    current = from_date
    while current <= to_date:
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        day_data = _data_loader.load_day(current)
        if day_data is None or day_data.empty:
            current += timedelta(days=1)
            continue

        next_expiry = get_next_expiry(current, expiry_df)
        dte = (next_expiry - current).days if next_expiry else 0

        ctx = StrategyContext(
            day_data=day_data,
            trade_date=current,
            dte=dte,
            lot_size=lot_size,
            cost_model=cost_model,
            entry_time_str="09:16",
            exit_time_str="14:30",
        )

        try:
            strategy(ctx)
        except Exception as e:
            result.execution_errors.append(f"[{current}] {e}")

        day_result = ctx._collect_day_result()
        if day_result.trades:
            result.trades.extend(day_result.trades)
            result.daily_pnl[current] = day_result.daily_pnl
        result.logs.extend(day_result.logs)

        current += timedelta(days=1)

    # ── Print Results ──
    s = result
    print("=" * 65)
    print("  ATM STRADDLE + RE-ENTRY ON SL (FULL YEAR 2024)")
    print("  Entry 9:16 | Exit 14:30 | 30% SL | Re-entry +10% | Lot 65")
    print("=" * 65)
    print(f"  Trades:            {s.total_trades}")
    print(f"  Trading Days:      {len(s.daily_pnl)}")
    print(f"  Winners:           {s.winning_trades}")
    print(f"  Losers:            {s.losing_trades}")
    print(f"  Win Rate:          {s.win_rate:.1f}%")
    print(f"  Gross P&L:         Rs.{s.gross_pnl:,.0f}")
    print(f"  Total Cost:        Rs.{s.total_cost:,.0f}")
    print(f"  Net P&L:           Rs.{s.net_pnl:,.0f}")
    print(f"  Max Drawdown:      Rs.{s.max_drawdown:,.0f}")
    pf = s.profit_factor if s.profit_factor != float('inf') else 999
    pr = s.payoff_ratio if s.payoff_ratio != float('inf') else 999
    print(f"  Profit Factor:     {pf:.2f}")
    print(f"  Payoff Ratio:      {pr:.2f}")
    print(f"  Expectancy:        Rs.{s.expectancy:,.0f} /trade")
    print(f"  Avg Win:           Rs.{s.avg_win:,.0f}")
    print(f"  Avg Loss:          Rs.{s.avg_loss:,.0f}")
    print(f"  Max Win:           Rs.{s.max_win:,.0f}")
    print(f"  Max Loss:          Rs.{s.max_loss:,.0f}")
    print(f"  Sharpe:            {s.sharpe_ratio:.2f}")
    print(f"  Calmar:            {s.calmar_ratio:.2f}")
    print(f"  Max Consec Wins:   {s.max_consecutive_wins}")
    print(f"  Max Consec Losses: {s.max_consecutive_losses}")
    print(f"  Exec Errors:       {len(s.execution_errors)}")
    print()

    # Monthly breakdown
    monthly = defaultdict(lambda: {"pnl": 0, "trades": 0, "wins": 0})
    for t in s.trades:
        m = t.trade_date.month
        monthly[m]["pnl"] += t.net_pnl
        monthly[m]["trades"] += 1
        if t.net_pnl > 0:
            monthly[m]["wins"] += 1

    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    print("  MONTHLY BREAKDOWN:")
    print(f"  {'Mon':>4s}  {'Trades':>7s}  {'WR':>6s}  {'Net PnL':>12s}")
    print("  " + "-" * 35)
    for m in range(1, 13):
        d = monthly[m]
        wr = (d["wins"] / d["trades"] * 100) if d["trades"] > 0 else 0
        sign = "+" if d["pnl"] >= 0 else ""
        print(f"  {months[m]:>4s}  {d['trades']:7d}  {wr:5.1f}%  {sign}Rs.{d['pnl']:>10,.0f}")
    print("=" * 65)

    if s.execution_errors:
        print(f"\n  ERRORS ({len(s.execution_errors)}):")
        for e in s.execution_errors[:10]:
            print(f"    {e}")

    # Show some key logs
    reentry_logs = [l for l in s.logs if "re-entry" in l.lower() or "lock" in l.lower() or "global" in l.lower()]
    if reentry_logs:
        print(f"\n  KEY EVENTS ({len(reentry_logs)} re-entries/locks/globals):")
        for l in reentry_logs[:20]:
            print(f"    {l}")
