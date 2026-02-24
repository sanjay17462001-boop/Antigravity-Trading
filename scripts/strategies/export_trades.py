"""Export trade data to JSON for frontend."""
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
h_trades, _, _, _, _ = run_backtest(FROM, TO, LOT, "hard")
print(f"HARD: {len(h_trades)} trades")

print("Running CLOSE...")
c_trades, _, _, _, _ = run_backtest(FROM, TO, LOT, "close")
print(f"CLOSE: {len(c_trades)} trades")

# Convert dates to strings
for t in h_trades + c_trades:
    t["date"] = str(t["date"])

# Save trade data
out = {"hard": h_trades, "close": c_trades}
out_path = Path(__file__).parent.parent.parent / "dashboard" / "frontend" / "public" / "strat_01_trades.json"
with open(out_path, "w") as f:
    json.dump(out, f)
print(f"Saved to {out_path} ({out_path.stat().st_size // 1024}KB)")

# Print DTE trade counts
for mode, trades in [("hard", h_trades), ("close", c_trades)]:
    dte_counts = defaultdict(lambda: defaultdict(int))
    for t in trades:
        y = int(t["date"][:4])
        bucket = str(t["dte"]) if t["dte"] <= 6 else "7+"
        dte_counts[y][bucket] += 1
    print(f"\n{mode.upper()} DTE COUNTS:")
    for y in sorted(dte_counts.keys()):
        print(f"  {y}: {dict(dte_counts[y])}")
