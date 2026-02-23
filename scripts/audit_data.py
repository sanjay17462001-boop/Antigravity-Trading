"""Audit NIFTY options data month-by-month."""
import pandas as pd
from pathlib import Path
from collections import defaultdict

opts_dir = Path(r"C:\Users\sanja\Desktop\Reset\Antigravity Trading\storage\candles\nifty_options")
files = sorted(opts_dir.glob("*.csv"))

print("Loading all options files...")
monthly = defaultdict(lambda: {
    "candles": 0, "strikes": set(), "types": set(),
    "has_spot": False, "has_vix": False, "has_oi": False,
    "ce_count": 0, "pe_count": 0,
})

for i, f in enumerate(files):
    df = pd.read_csv(f)

    # Handle timestamp - could be epoch or string
    if df["timestamp"].dtype in ("int64", "float64"):
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")

    df["month"] = df["timestamp"].dt.to_period("M")

    for month, grp in df.groupby("month"):
        m = str(month)
        info = monthly[m]
        info["candles"] += len(grp)

        if "strike_rel" in grp.columns:
            info["strikes"].update(grp["strike_rel"].unique())
        if "type" in grp.columns:
            info["types"].update(grp["type"].unique())
            info["ce_count"] += len(grp[grp["type"] == "CALL"])
            info["pe_count"] += len(grp[grp["type"] == "PUT"])
        if "spot_price" in grp.columns:
            if grp["spot_price"].notna().sum() > 0:
                info["has_spot"] = True
        if "india_vix" in grp.columns:
            if grp["india_vix"].notna().sum() > 0:
                info["has_vix"] = True
        if "oi" in grp.columns:
            if (grp["oi"] > 0).sum() > 0:
                info["has_oi"] = True

    if (i + 1) % 100 == 0:
        print(f"  Processed {i+1}/{len(files)} files...")

print(f"  Done: {len(files)} files.\n")

# Print report
print("=" * 97)
print(f"{'Month':<10} {'Candles':>10} {'CE':>9} {'PE':>9} {'#Strikes':>8} {'Strike Range':<25} {'Spot':>5} {'VIX':>5} {'OI':>5}")
print("-" * 97)

for m in sorted(monthly.keys()):
    info = monthly[m]
    strikes = sorted(info["strikes"])
    s_range = f"{strikes[0]}..{strikes[-1]}" if strikes else "N/A"
    n_strikes = len(strikes)
    spot = "YES" if info["has_spot"] else "NO"
    vix = "YES" if info["has_vix"] else "NO"
    oi = "YES" if info["has_oi"] else "NO"
    print(f"{m:<10} {info['candles']:>10,} {info['ce_count']:>9,} {info['pe_count']:>9,} {n_strikes:>8} {s_range:<25} {spot:>5} {vix:>5} {oi:>5}")

print("-" * 97)
total_candles = sum(v["candles"] for v in monthly.values())
total_ce = sum(v["ce_count"] for v in monthly.values())
total_pe = sum(v["pe_count"] for v in monthly.values())
print(f"{'TOTAL':<10} {total_candles:>10,} {total_ce:>9,} {total_pe:>9,}")
print("=" * 97)

# All strikes seen
all_strikes = set()
for v in monthly.values():
    all_strikes.update(v["strikes"])
print(f"\nAll strike labels seen: {sorted(all_strikes)}")
