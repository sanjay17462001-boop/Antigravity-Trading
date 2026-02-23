"""
Antigravity Trading — Dhan Expired Options Data Fetcher
=======================================================
Downloads 5 years of 1-minute expired options data using Dhan's
Rolling Options API (/v2/charts/rollingoption).

Features:
- ATM and ATM+/-1 to ATM+/-10 strikes
- OHLC + IV + OI + Spot + Strike
- Weekly and Monthly expiry
- NIFTY + BANKNIFTY
- 30-day chunks (API limit)

Usage:
    python scripts/fetch_expired_options.py
    python scripts/fetch_expired_options.py --instrument NIFTY --strikes 5
    python scripts/fetch_expired_options.py --from-year 2023
"""

import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# Config
# =============================================================================

DHAN_ACCESS_TOKEN = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9."
    "eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzcxNjQ0NDkyLCJ"
    "pYXQiOjE3NzE1NTgwOTIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYm"
    "hvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTEwMzExNDI3In0."
    "9o98J2d7Ih59kqx66OU9bvpJrKJBKOl-AB8n_wtnF1sPBGhSojl69BrvmPq8z1R"
    "eR6228fotMBEF7Xiv4k69GQ"
)

API_URL = "https://api.dhan.co/v2/charts/rollingoption"
STORAGE_DIR = PROJECT_ROOT / "storage" / "candles" / "options_historical"
CHUNK_DAYS = 28  # max 30, use 28 for safety
RATE_LIMIT = 0.5  # seconds between calls

# Instruments
INSTRUMENTS = {
    "NIFTY": {"security_id": 13, "exchange_segment": "NSE_FNO", "instrument": "OPTIDX"},
    "BANKNIFTY": {"security_id": 25, "exchange_segment": "NSE_FNO", "instrument": "OPTIDX"},
}

# Strike offsets to fetch: ATM, ATM+1..ATM+N, ATM-1..ATM-N
STRIKE_LABELS = ["ATM"]
for i in range(1, 11):
    STRIKE_LABELS.append(f"ATM+{i}")
    STRIKE_LABELS.append(f"ATM-{i}")

# Data fields to request
REQUIRED_DATA = ["open", "high", "low", "close", "iv", "volume", "oi", "strike", "spot"]


# =============================================================================
# API Call
# =============================================================================

def fetch_rolling_options(
    security_id: int,
    exchange_segment: str,
    instrument: str,
    expiry_flag: str,  # "WEEK" or "MONTH"
    expiry_code: int,  # 1=nearest, 2=next, etc.
    strike: str,       # "ATM", "ATM+1", "ATM-1", etc.
    option_type: str,  # "CALL" or "PUT"
    from_date: str,
    to_date: str,
    interval: str = "1",
) -> dict:
    """Call Dhan Rolling Options API."""
    payload = {
        "exchangeSegment": exchange_segment,
        "interval": interval,
        "securityId": security_id,
        "instrument": instrument,
        "expiryFlag": expiry_flag,
        "expiryCode": expiry_code,
        "strike": strike,
        "drvOptionType": option_type,
        "requiredData": REQUIRED_DATA,
        "fromDate": from_date,
        "toDate": to_date,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "access-token": DHAN_ACCESS_TOKEN,
    }

    try:
        resp = httpx.post(API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "body": resp.text[:200]}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Response Parser
# =============================================================================

def parse_rolling_response(resp: dict, option_type: str) -> pd.DataFrame:
    """Parse rolling options API response into DataFrame."""
    if "error" in resp:
        return pd.DataFrame()

    data = resp.get("data", {})
    if not data:
        return pd.DataFrame()

    # Response has 'ce' and 'pe' keys
    key = "ce" if option_type == "CALL" else "pe"
    side_data = data.get(key)
    if not side_data:
        return pd.DataFrame()

    timestamps = side_data.get("timestamp", [])
    if not timestamps:
        return pd.DataFrame()

    records = []
    opens = side_data.get("open", [])
    highs = side_data.get("high", [])
    lows = side_data.get("low", [])
    closes = side_data.get("close", [])
    volumes = side_data.get("volume", [])
    ivs = side_data.get("iv", [])
    ois = side_data.get("oi", [])
    strikes = side_data.get("strike", [])
    spots = side_data.get("spot", [])

    for i in range(len(timestamps)):
        ts = timestamps[i]
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(ts)

        records.append({
            "timestamp": ts,
            "open": float(opens[i]) if i < len(opens) else 0,
            "high": float(highs[i]) if i < len(highs) else 0,
            "low": float(lows[i]) if i < len(lows) else 0,
            "close": float(closes[i]) if i < len(closes) else 0,
            "volume": int(volumes[i]) if i < len(volumes) else 0,
            "iv": float(ivs[i]) if i < len(ivs) else 0,
            "oi": int(ois[i]) if i < len(ois) else 0,
            "strike": float(strikes[i]) if i < len(strikes) else 0,
            "spot": float(spots[i]) if i < len(spots) else 0,
        })

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


# =============================================================================
# Fetch a single strike/type combo across date range
# =============================================================================

def fetch_strike_history(
    instrument_name: str,
    config: dict,
    expiry_flag: str,
    expiry_code: int,
    strike: str,
    option_type: str,
    from_date: datetime,
    to_date: datetime,
) -> pd.DataFrame:
    """Fetch full history for one strike/type in 28-day chunks."""
    all_dfs = []
    chunk_start = from_date
    total_chunks = ((to_date - from_date).days // CHUNK_DAYS) + 1
    chunk_num = 0

    while chunk_start < to_date:
        chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS), to_date)
        chunk_num += 1

        resp = fetch_rolling_options(
            security_id=config["security_id"],
            exchange_segment=config["exchange_segment"],
            instrument=config["instrument"],
            expiry_flag=expiry_flag,
            expiry_code=expiry_code,
            strike=strike,
            option_type=option_type,
            from_date=chunk_start.strftime("%Y-%m-%d"),
            to_date=chunk_end.strftime("%Y-%m-%d"),
        )

        df = parse_rolling_response(resp, option_type)
        n = len(df)

        if n > 0:
            all_dfs.append(df)

        if chunk_num % 10 == 0 or chunk_num == total_chunks:
            total_so_far = sum(len(d) for d in all_dfs)
            print(f"       chunk {chunk_num}/{total_chunks}: {total_so_far:,} candles so far")

        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(RATE_LIMIT)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return combined


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fetch expired options data from Dhan")
    parser.add_argument("--instrument", type=str, default=None,
                        help="NIFTY or BANKNIFTY (default: both)")
    parser.add_argument("--strikes", type=int, default=5,
                        help="Number of strikes above/below ATM (default: 5, max: 10)")
    parser.add_argument("--from-year", type=int, default=2021,
                        help="Start year (default: 2021)")
    parser.add_argument("--expiry", type=str, default="MONTH",
                        help="WEEK or MONTH (default: MONTH)")
    args = parser.parse_args()

    print("=" * 70)
    print("DHAN EXPIRED OPTIONS DATA FETCHER")
    print("=" * 70)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  From: {args.from_year}-01-01")
    print(f"  Strikes: ATM +/- {args.strikes}")
    print(f"  Expiry: {args.expiry}")
    print()

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    from_date = datetime(args.from_year, 1, 1)
    to_date = datetime.now()
    grand_total = 0

    # Build strike list
    strikes_to_fetch = ["ATM"]
    for i in range(1, args.strikes + 1):
        strikes_to_fetch.append(f"ATM+{i}")
        strikes_to_fetch.append(f"ATM-{i}")

    instruments = {}
    if args.instrument:
        key = args.instrument.upper()
        if key in INSTRUMENTS:
            instruments[key] = INSTRUMENTS[key]
        else:
            print(f"  [ERROR] Unknown instrument: {key}")
            return
    else:
        instruments = INSTRUMENTS

    for inst_name, config in instruments.items():
        print(f"\n{'='*70}")
        print(f"  {inst_name} OPTIONS ({args.expiry} expiry)")
        print(f"{'='*70}")

        for strike in strikes_to_fetch:
            for opt_type in ["CALL", "PUT"]:
                label = f"{inst_name}_{strike}_{opt_type[0]}E_{args.expiry}"
                print(f"\n  >> {label}")

                df = fetch_strike_history(
                    inst_name, config, args.expiry, 1,
                    strike, opt_type, from_date, to_date,
                )

                if df.empty:
                    print(f"     [WARN] No data")
                    continue

                # Add metadata columns
                df["instrument"] = inst_name
                df["strike_label"] = strike
                df["option_type"] = opt_type[0] + "E"
                df["expiry_type"] = args.expiry

                filepath = STORAGE_DIR / f"{label}_1min.csv"
                df.to_csv(filepath, index=False)

                size_kb = filepath.stat().st_size / 1024
                first = df["timestamp"].iloc[0]
                last = df["timestamp"].iloc[-1]
                print(f"     [SAVED] {filepath.name}: {len(df):,} candles, {size_kb:.0f} KB")
                print(f"     Range: {first} to {last}")
                grand_total += len(df)

    # Summary
    print(f"\n{'='*70}")
    print("FETCH COMPLETE")
    print(f"{'='*70}")
    print(f"  Total candles: {grand_total:,}")
    print(f"  Storage: {STORAGE_DIR}")

    csv_files = sorted(STORAGE_DIR.glob("*_1min.csv"))
    if csv_files:
        total_size = sum(f.stat().st_size for f in csv_files)
        print(f"  Files: {len(csv_files)}")
        print(f"  Total size: {total_size / (1024*1024):.1f} MB")
    print()


if __name__ == "__main__":
    main()
