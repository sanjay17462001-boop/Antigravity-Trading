"""
Strategy 1: ATM Straddle Sell + Re-entry on SL — FAST ENGINE
=============================================================
Pre-caches all price data into dictionaries for O(1) lookups.
5-year backtest runs in ~60 seconds instead of 30+ minutes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from datetime import date, time, timedelta
from collections import defaultdict
import time as timer
from engine.cost_model import CostModel, CostConfig
from engine.options_backtester import _data_loader, load_expiry_calendar, get_next_expiry


# ══════════════════════════════════════════════════════════════
# FAST STRATEGY — works directly with price dicts, no SDK overhead
# ══════════════════════════════════════════════════════════════

def run_day(day_data, trade_date, dte, lot_size, exit_mode):
    """
    Run one day of strategy. Returns list of trade dicts, logs, daily_pnl, vix.
    All price lookups use pre-built dicts — no DataFrame filtering in loop.
    """
    entry_t = time(9, 16)
    exit_t = time(14, 30)
    sl_pct = 30
    global_sl = -9000
    profit_lock_trigger = 1500
    profit_lock_level = 200
    reentry_pct = 0.10

    # ── Extract VIX ──
    day_vix = 0.0
    if "india_vix" in day_data.columns:
        vix_vals = day_data["india_vix"].dropna()
        if not vix_vals.empty:
            day_vix = round(float(vix_vals.iloc[0]), 2)

    # ── Pre-build price caches (ONE DataFrame filter per strike/type) ──
    def build_cache(strike_rel, leg_type):
        """Returns {(hour,min): {open, high, low, close}} dict."""
        mask = (day_data["strike_rel"] == strike_rel) & (day_data["type"] == leg_type)
        df = day_data[mask]
        cache = {}
        abs_strike = 0
        for _, r in df.iterrows():
            ts = r["timestamp"]
            key = (ts.hour, ts.minute)
            cache[key] = {
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
            if abs_strike == 0:
                abs_strike = float(r.get("absolute_strike", 0))
        return cache, abs_strike

    ce_cache, ce_abs = build_cache("ATM", "CALL")
    pe_cache, pe_abs = build_cache("ATM", "PUT")

    if not ce_cache or not pe_cache:
        return [], [], 0, day_vix

    # ── Get entry prices ──
    entry_key = (entry_t.hour, entry_t.minute)
    if entry_key not in ce_cache or entry_key not in pe_cache:
        return [], [], 0, day_vix

    ce_entry = ce_cache[entry_key]["open"]
    pe_entry = pe_cache[entry_key]["open"]
    if ce_entry <= 0 or pe_entry <= 0:
        return [], [], 0

    # ── State ──
    trades = []
    logs = []
    qty = lot_size

    # Leg 1
    ce_open = True
    pe_open = True
    ce_sl = ce_entry * (1 + sl_pct / 100)
    pe_sl = pe_entry * (1 + sl_pct / 100)
    ce_exit_price = 0
    pe_exit_price = 0
    ce_exit_time = ""
    pe_exit_time = ""
    ce_exit_reason = "time_exit"
    pe_exit_reason = "time_exit"

    # Re-entry
    ce_sl_hit = False
    pe_sl_hit = False
    ce_reentry_done = False
    pe_reentry_done = False
    ce_sl_exit_price = 0
    pe_sl_exit_price = 0

    ce2_open = False
    pe2_open = False
    ce2_entry = 0
    pe2_entry = 0
    ce2_sl = 0
    pe2_sl = 0
    ce2_entry_time = ""
    pe2_entry_time = ""
    ce2_exit_price = 0
    pe2_exit_price = 0
    ce2_exit_time = ""
    pe2_exit_time = ""
    ce2_exit_reason = "time_exit"
    pe2_exit_reason = "time_exit"

    locked_profit = None
    all_closed = False

    # ── Walk through minutes ──
    sorted_times = sorted(set(ce_cache.keys()) | set(pe_cache.keys()))

    for hm in sorted_times:
        t = time(hm[0], hm[1])
        if t <= entry_t:
            continue
        if t >= exit_t:
            break

        ts = f"{hm[0]:02d}:{hm[1]:02d}"

        # Current prices (close for update_prices equivalent)
        ce_cur = ce_cache.get(hm, {}).get("close", ce_entry)
        pe_cur = pe_cache.get(hm, {}).get("close", pe_entry)
        ce_high = ce_cache.get(hm, {}).get("high", ce_cur)
        pe_high = pe_cache.get(hm, {}).get("high", pe_cur)

        # ── Compute total PnL ──
        total_pnl = 0
        if ce_open:
            total_pnl += (ce_entry - ce_cur) * qty  # SELL PnL
        if pe_open:
            total_pnl += (pe_entry - pe_cur) * qty
        if ce2_open:
            total_pnl += (ce2_entry - ce_cur) * qty
        if pe2_open:
            total_pnl += (pe2_entry - pe_cur) * qty
        # Add realized PnL from closed positions
        for tr in trades:
            total_pnl += tr["gross_pnl"]

        # ── Global SL ──
        if total_pnl <= global_sl:
            if ce_open:
                ce_exit_price = ce_cur; ce_exit_time = ts; ce_exit_reason = "global_sl"; ce_open = False
            if pe_open:
                pe_exit_price = pe_cur; pe_exit_time = ts; pe_exit_reason = "global_sl"; pe_open = False
            if ce2_open:
                ce2_exit_price = ce_cur; ce2_exit_time = ts; ce2_exit_reason = "global_sl"; ce2_open = False
            if pe2_open:
                pe2_exit_price = pe_cur; pe2_exit_time = ts; pe2_exit_reason = "global_sl"; pe2_open = False
            all_closed = True
            break

        # ── Profit lock ──
        if total_pnl >= profit_lock_trigger and locked_profit is None:
            locked_profit = profit_lock_level
        if locked_profit is not None and total_pnl <= locked_profit:
            if ce_open:
                ce_exit_price = ce_cur; ce_exit_time = ts; ce_exit_reason = "profit_lock"; ce_open = False
            if pe_open:
                pe_exit_price = pe_cur; pe_exit_time = ts; pe_exit_reason = "profit_lock"; pe_open = False
            if ce2_open:
                ce2_exit_price = ce_cur; ce2_exit_time = ts; ce2_exit_reason = "profit_lock"; ce2_open = False
            if pe2_open:
                pe2_exit_price = pe_cur; pe2_exit_time = ts; pe2_exit_reason = "profit_lock"; pe2_open = False
            all_closed = True
            break

        # ── CE Leg 1 SL ──
        if ce_open and not ce_sl_hit:
            if exit_mode == "hard":
                if ce_high >= ce_sl:
                    ce_exit_price = ce_sl; ce_exit_time = ts; ce_exit_reason = "sl_hit"; ce_open = False; ce_sl_hit = True; ce_sl_exit_price = ce_sl
            else:
                if ce_cur >= ce_sl:
                    ce_exit_price = ce_cur; ce_exit_time = ts; ce_exit_reason = "sl_hit"; ce_open = False; ce_sl_hit = True; ce_sl_exit_price = ce_cur

        # ── PE Leg 1 SL ──
        if pe_open and not pe_sl_hit:
            if exit_mode == "hard":
                if pe_high >= pe_sl:
                    pe_exit_price = pe_sl; pe_exit_time = ts; pe_exit_reason = "sl_hit"; pe_open = False; pe_sl_hit = True; pe_sl_exit_price = pe_sl
            else:
                if pe_cur >= pe_sl:
                    pe_exit_price = pe_cur; pe_exit_time = ts; pe_exit_reason = "sl_hit"; pe_open = False; pe_sl_hit = True; pe_sl_exit_price = pe_cur

        # ── CE Re-entry ──
        if ce_sl_hit and not ce_reentry_done:
            ce_reentry_price = ce_cache.get(hm, {}).get("open", 0)
            if ce_reentry_price > 0 and ce_reentry_price >= ce_sl_exit_price * (1 + reentry_pct):
                ce2_entry = ce_reentry_price; ce2_sl = ce2_entry * (1 + sl_pct / 100)
                ce2_open = True; ce_reentry_done = True; ce2_entry_time = ts

        # ── PE Re-entry ──
        if pe_sl_hit and not pe_reentry_done:
            pe_reentry_price = pe_cache.get(hm, {}).get("open", 0)
            if pe_reentry_price > 0 and pe_reentry_price >= pe_sl_exit_price * (1 + reentry_pct):
                pe2_entry = pe_reentry_price; pe2_sl = pe2_entry * (1 + sl_pct / 100)
                pe2_open = True; pe_reentry_done = True; pe2_entry_time = ts

        # ── CE2 SL ──
        if ce2_open:
            if exit_mode == "hard":
                if ce_high >= ce2_sl:
                    ce2_exit_price = ce2_sl; ce2_exit_time = ts; ce2_exit_reason = "reentry_sl"; ce2_open = False
            else:
                if ce_cur >= ce2_sl:
                    ce2_exit_price = ce_cur; ce2_exit_time = ts; ce2_exit_reason = "reentry_sl"; ce2_open = False

        # ── PE2 SL ──
        if pe2_open:
            if exit_mode == "hard":
                if pe_high >= pe2_sl:
                    pe2_exit_price = pe2_sl; pe2_exit_time = ts; pe2_exit_reason = "reentry_sl"; pe2_open = False
            else:
                if pe_cur >= pe2_sl:
                    pe2_exit_price = pe_cur; pe2_exit_time = ts; pe2_exit_reason = "reentry_sl"; pe2_open = False

    # ── Time exit for anything still open ──
    exit_key = (exit_t.hour, exit_t.minute)
    ce_close_price = ce_cache.get(exit_key, {}).get("open", list(ce_cache.values())[-1]["close"] if ce_cache else 0)
    pe_close_price = pe_cache.get(exit_key, {}).get("open", list(pe_cache.values())[-1]["close"] if pe_cache else 0)

    if ce_open:
        ce_exit_price = ce_close_price; ce_exit_time = f"{exit_t.hour:02d}:{exit_t.minute:02d}"
    if pe_open:
        pe_exit_price = pe_close_price; pe_exit_time = f"{exit_t.hour:02d}:{exit_t.minute:02d}"
    if ce2_open:
        ce2_exit_price = ce_close_price; ce2_exit_time = f"{exit_t.hour:02d}:{exit_t.minute:02d}"
    if pe2_open:
        pe2_exit_price = pe_close_price; pe2_exit_time = f"{exit_t.hour:02d}:{exit_t.minute:02d}"

    # ── Build trade records ──
    def make_trade(label, entry_p, exit_p, e_time, x_time, x_reason, opt_type, abs_s):
        gpnl = (entry_p - exit_p) * qty  # SELL PnL
        return {
            "date": trade_date, "strike": "ATM", "option_type": opt_type,
            "absolute_strike": abs_s, "action": "SELL", "lots": 1, "quantity": qty,
            "entry_price": round(entry_p, 2), "exit_price": round(exit_p, 2),
            "entry_time": e_time, "exit_time": x_time, "exit_reason": x_reason,
            "gross_pnl": round(gpnl, 2), "net_pnl": round(gpnl, 2),
            "dte": dte, "label": label, "vix": day_vix,
        }

    result_trades = []
    entry_ts = f"{entry_t.hour:02d}:{entry_t.minute:02d}"

    if ce_exit_price > 0:
        result_trades.append(make_trade("CE leg 1", ce_entry, ce_exit_price, entry_ts, ce_exit_time, ce_exit_reason, "CE", ce_abs))
    if pe_exit_price > 0:
        result_trades.append(make_trade("PE leg 1", pe_entry, pe_exit_price, entry_ts, pe_exit_time, pe_exit_reason, "PE", pe_abs))
    if ce2_entry > 0 and (ce2_exit_price > 0 or not ce2_open):
        if ce2_exit_price == 0:
            ce2_exit_price = ce_close_price
        result_trades.append(make_trade("CE leg 2 (re-entry)", ce2_entry, ce2_exit_price, ce2_entry_time, ce2_exit_time or f"{exit_t.hour:02d}:{exit_t.minute:02d}", ce2_exit_reason, "CE", ce_abs))
    if pe2_entry > 0 and (pe2_exit_price > 0 or not pe2_open):
        if pe2_exit_price == 0:
            pe2_exit_price = pe_close_price
        result_trades.append(make_trade("PE leg 2 (re-entry)", pe2_entry, pe2_exit_price, pe2_entry_time, pe2_exit_time or f"{exit_t.hour:02d}:{exit_t.minute:02d}", pe2_exit_reason, "PE", pe_abs))

    daily_pnl = sum(t["gross_pnl"] for t in result_trades)
    return result_trades, logs, daily_pnl, day_vix


def run_backtest(from_date, to_date, lot_size, exit_mode):
    """Run full backtest — fast version."""
    start = timer.time()
    _data_loader.preload_range(from_date, to_date)
    expiry_df = load_expiry_calendar()

    all_trades = []
    daily_pnl = {}
    errors = []

    current = from_date
    day_count = 0
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

        try:
            trades, logs, dpnl, vix = run_day(day_data, current, dte, lot_size, exit_mode)
            if trades:
                all_trades.extend(trades)
                daily_pnl[current] = dpnl
        except Exception as e:
            errors.append(f"[{current}] {e}")

        day_count += 1
        current += timedelta(days=1)

    elapsed = timer.time() - start
    return all_trades, daily_pnl, errors, elapsed, day_count


def print_results(all_trades, daily_pnl, errors, elapsed, day_count, mode_label):
    """Print comprehensive results."""
    total = len(all_trades)
    winners = len([t for t in all_trades if t["gross_pnl"] > 0])
    losers = len([t for t in all_trades if t["gross_pnl"] < 0])
    wr = (winners / total * 100) if total > 0 else 0
    gross = sum(t["gross_pnl"] for t in all_trades)

    # Drawdown
    equity = 0; peak = 0; max_dd = 0
    for t in all_trades:
        equity += t["gross_pnl"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    wins = [t["gross_pnl"] for t in all_trades if t["gross_pnl"] > 0]
    losses = [t["gross_pnl"] for t in all_trades if t["gross_pnl"] < 0]
    avg_w = sum(wins) / len(wins) if wins else 0
    avg_l = sum(losses) / len(losses) if losses else 0
    max_w = max(wins) if wins else 0
    max_l = min(losses) if losses else 0
    pf = (sum(wins) / abs(sum(losses))) if losses else 999
    pr = (avg_w / abs(avg_l)) if avg_l != 0 else 999
    exp = (wr / 100 * avg_w) - ((1 - wr / 100) * abs(avg_l))

    import numpy as np
    vals = list(daily_pnl.values())
    sharpe = float(np.mean(vals) / np.std(vals) * (252 ** 0.5)) if len(vals) > 1 and np.std(vals) > 0 else 0
    calmar = (gross * 252 / len(vals) / max_dd) if max_dd > 0 and vals else 0

    # Consecutive
    def max_consec(positive):
        c = 0; mx = 0
        for t in all_trades:
            if (positive and t["gross_pnl"] > 0) or (not positive and t["gross_pnl"] < 0):
                c += 1; mx = max(mx, c)
            else:
                c = 0
        return mx

    print(f"\n{'=' * 65}")
    print(f"  {mode_label}")
    print(f"  Entry 9:16 | Exit 14:30 | 30% SL | Re-entry +10% | Lot 65")
    print(f"  ZERO costs | Ran in {elapsed:.1f}s")
    print(f"{'=' * 65}")
    print(f"  Trades:            {total}")
    print(f"  Trading Days:      {len(daily_pnl)}")
    print(f"  Winners:           {winners}")
    print(f"  Losers:            {losers}")
    print(f"  Win Rate:          {wr:.1f}%")
    print(f"  Gross P&L:         Rs.{gross:,.0f}")
    print(f"  Max Drawdown:      Rs.{max_dd:,.0f}")
    print(f"  Profit Factor:     {pf:.2f}")
    print(f"  Payoff Ratio:      {pr:.2f}")
    print(f"  Expectancy:        Rs.{exp:,.0f} /trade")
    print(f"  Avg Win:           Rs.{avg_w:,.0f}")
    print(f"  Avg Loss:          Rs.{avg_l:,.0f}")
    print(f"  Max Win:           Rs.{max_w:,.0f}")
    print(f"  Max Loss:          Rs.{max_l:,.0f}")
    print(f"  Sharpe:            {sharpe:.2f}")
    print(f"  Calmar:            {calmar:.2f}")
    print(f"  Max Consec Wins:   {max_consec(True)}")
    print(f"  Max Consec Losses: {max_consec(False)}")
    print(f"  Exec Errors:       {len(errors)}")

    # Monthly
    months_name = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = defaultdict(lambda: {"pnl": 0, "trades": 0, "wins": 0})
    for t in all_trades:
        y = t["date"].year
        m = t["date"].month
        key = (y, m)
        monthly[key]["pnl"] += t["gross_pnl"]
        monthly[key]["trades"] += 1
        if t["gross_pnl"] > 0:
            monthly[key]["wins"] += 1

    years = sorted(set(t["date"].year for t in all_trades))
    print(f"\n  MONTHLY BREAKDOWN:")
    print(f"  {'Year':>5s} {'Mon':>4s}  {'Trades':>7s}  {'WR':>6s}  {'Gross PnL':>12s}")
    print(f"  {'-' * 40}")
    for y in years:
        for m in range(1, 13):
            d = monthly.get((y, m))
            if not d or d["trades"] == 0:
                continue
            wr_m = (d["wins"] / d["trades"] * 100) if d["trades"] > 0 else 0
            sign = "+" if d["pnl"] >= 0 else ""
            print(f"  {y:>5d} {months_name[m]:>4s}  {d['trades']:7d}  {wr_m:5.1f}%  {sign}Rs.{d['pnl']:>10,.0f}")
        # Year total
        yr_pnl = sum(monthly[(y, m)]["pnl"] for m in range(1, 13) if (y, m) in monthly)
        yr_trades = sum(monthly[(y, m)]["trades"] for m in range(1, 13) if (y, m) in monthly)
        print(f"  {y:>5d} {'TOTAL':>4s}  {yr_trades:7d}          Rs.{yr_pnl:>10,.0f}")
        print(f"  {'-' * 40}")

    # Year x DTE matrix
    dte_matrix = defaultdict(lambda: defaultdict(float))
    dte_counts = defaultdict(lambda: defaultdict(int))
    for t in all_trades:
        y = t["date"].year
        bucket = str(t["dte"]) if t["dte"] <= 6 else "7+"
        dte_matrix[y][bucket] += t["gross_pnl"]
        dte_counts[y][bucket] += 1

    all_buckets = sorted(set(b for yr in dte_matrix.values() for b in yr.keys()),
                         key=lambda x: int(x.replace("+", "")) if "+" not in x else 99)

    print(f"\n  YEAR x DTE MATRIX (Gross P&L):")
    header = f"  {'Year':>5s}"
    for b in all_buckets:
        header += f"  {'DTE'+b:>9s}"
    header += f"  {'TOTAL':>10s}"
    print(header)
    print(f"  {'-' * (7 + 11 * (len(all_buckets) + 1))}")
    for y in sorted(dte_matrix.keys()):
        row = f"  {y:>5d}"
        total_yr = 0
        for b in all_buckets:
            val = dte_matrix[y].get(b, 0)
            total_yr += val
            row += f"  {val:>9,.0f}"
        row += f"  {total_yr:>10,.0f}"
        print(row)

    print(f"{'=' * 65}")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors[:5]:
            print(f"    {e}")


if __name__ == "__main__":
    FROM = date(2021, 1, 1)
    TO = date(2026, 2, 18)
    LOT = 65

    print("\nRunning HARD exit backtest (5 years)...")
    h_trades, h_dpnl, h_err, h_time, h_days = run_backtest(FROM, TO, LOT, "hard")
    print_results(h_trades, h_dpnl, h_err, h_time, h_days, "MODE A: HARD EXITS (2021-2026)")

    print("\n\nRunning CLOSE exit backtest (5 years)...")
    c_trades, c_dpnl, c_err, c_time, c_days = run_backtest(FROM, TO, LOT, "close")
    print_results(c_trades, c_dpnl, c_err, c_time, c_days, "MODE B: CLOSE EXITS (2021-2026)")
