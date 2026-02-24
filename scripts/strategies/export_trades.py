"""Export trade data + equity curve to JSON for frontend."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from scripts.strategies.strat_01_straddle_reentry import run_backtest
from datetime import date
from collections import defaultdict
import json

FROM, TO, LOT = date(2021, 1, 1), date(2026, 2, 18), 65

print("Running HARD...")
h_trades, h_dpnl, h_err, h_time, h_days = run_backtest(FROM, TO, LOT, "hard")
print(f"HARD: {len(h_trades)} trades, {h_time:.0f}s")

print("Running CLOSE...")
c_trades, c_dpnl, c_err, c_time, c_days = run_backtest(FROM, TO, LOT, "close")
print(f"CLOSE: {len(c_trades)} trades, {c_time:.0f}s")


def build_equity_curve(trades):
    """Build daily equity curve from trades."""
    daily = defaultdict(float)
    for t in trades:
        daily[t["date"]] += t["gross_pnl"]

    curve = []
    cumulative = 0
    peak = 0
    for d in sorted(daily.keys()):
        cumulative += daily[d]
        peak = max(peak, cumulative)
        dd = peak - cumulative
        curve.append({
            "date": str(d),
            "daily_pnl": round(daily[d], 2),
            "cumulative": round(cumulative, 2),
            "drawdown": round(dd, 2),
        })
    return curve


# Convert dates to strings
for t in h_trades + c_trades:
    t["date"] = str(t["date"])

# Build equity curves
h_equity = build_equity_curve(h_trades)
c_equity = build_equity_curve(c_trades)

# VIX stats
h_vix = [t.get("vix", 0) for t in h_trades if t.get("vix", 0) > 0]
c_vix = [t.get("vix", 0) for t in c_trades if t.get("vix", 0) > 0]
print(f"\nHARD VIX: {len(h_vix)} trades with VIX, range {min(h_vix):.1f}-{max(h_vix):.1f}" if h_vix else "No VIX data")
print(f"CLOSE VIX: {len(c_vix)} trades with VIX, range {min(c_vix):.1f}-{max(c_vix):.1f}" if c_vix else "No VIX data")

# Save
out = {
    "hard": h_trades,
    "close": c_trades,
    "hard_equity": h_equity,
    "close_equity": c_equity,
}
out_path = Path(__file__).parent.parent.parent / "dashboard" / "frontend" / "public" / "strat_01_trades.json"
with open(out_path, "w") as f:
    json.dump(out, f)
print(f"\nSaved to {out_path} ({out_path.stat().st_size // 1024}KB)")

# Print DTE trade counts for hardcoding
for mode, trades in [("hard", h_trades), ("close", c_trades)]:
    dte_counts = defaultdict(lambda: defaultdict(int))
    for t in trades:
        y = int(t["date"][:4])
        bucket = str(t["dte"]) if t["dte"] <= 6 else "7+"
        dte_counts[y][bucket] += 1
    print(f"\n{mode.upper()} DTE COUNTS:")
    for y in sorted(dte_counts.keys()):
        print(f"  {y}: {dict(dte_counts[y])}")
