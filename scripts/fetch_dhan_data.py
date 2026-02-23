"""
Antigravity Trading — Dhan Bulk Data Fetcher
=============================================
Downloads 1-minute OHLCV data from Dhan API for:
  NIFTY, BANKNIFTY, Crude Oil, Natural Gas, Gold, Silver, India VIX
  across Spot, Futures, and Options.

Saves to CSV files in storage/candles/ directory.

Usage:
    python scripts/fetch_dhan_data.py                        # full 5-year fetch
    python scripts/fetch_dhan_data.py --instrument NIFTY     # single instrument
    python scripts/fetch_dhan_data.py --days 30              # last 30 days only
    python scripts/fetch_dhan_data.py --skip-futures --skip-options  # spot only
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Configuration
# =============================================================================

DHAN_CLIENT_ID = "1110311427"
DHAN_ACCESS_TOKEN = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9."
    "eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzcxNjQ0NDkyLCJ"
    "pYXQiOjE3NzE1NTgwOTIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYm"
    "hvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTEwMzExNDI3In0."
    "9o98J2d7Ih59kqx66OU9bvpJrKJBKOl-AB8n_wtnF1sPBGhSojl69BrvmPq8z1R"
    "eR6228fotMBEF7Xiv4k69GQ"
)

STORAGE_DIR = PROJECT_ROOT / "storage" / "candles"
CHUNK_DAYS = 85       # max 90 per Dhan, use 85 for safety
RATE_LIMIT_SLEEP = 0.4
MAX_HISTORY_DAYS = 365 * 5  # 5 years


# =============================================================================
# Instrument Definitions — Dhan Security IDs
# =============================================================================

SPOT_INSTRUMENTS = {
    "NIFTY_50": {
        "security_id": "13",
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX",
        "display_name": "NIFTY_50",
    },
    "BANKNIFTY": {
        "security_id": "25",
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX",
        "display_name": "BANKNIFTY",
    },
    "INDIA_VIX": {
        "security_id": "26",
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX",
        "display_name": "INDIA_VIX",
    },
}

# Futures lookup config: underlying symbol → (exchange_segment, instrument_type)
FUTURES_CONFIG = {
    "NIFTY":      ("NIFTY",      "NSE_FNO", "FUTIDX"),
    "BANKNIFTY":  ("BANKNIFTY",  "NSE_FNO", "FUTIDX"),
    "CRUDE":      ("CRUDEOIL",   "MCX_COMM", "FUTCOM"),
    "NATURALGAS": ("NATURALGAS", "MCX_COMM", "FUTCOM"),
    "GOLD":       ("GOLD",       "MCX_COMM", "FUTCOM"),
    "SILVER":     ("SILVER",     "MCX_COMM", "FUTCOM"),
}

# Options lookup config
OPTIONS_CONFIG = {
    "NIFTY":     ("NIFTY",     "NSE_FNO", "OPTIDX", 25450, 50, 5),
    "BANKNIFTY": ("BANKNIFTY", "NSE_FNO", "OPTIDX", 60750, 100, 5),
}


# =============================================================================
# Dhan Client
# =============================================================================

class DhanClient:
    def __init__(self):
        from dhanhq import dhanhq
        self.client = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        print(f"  [OK] Dhan connected (client={DHAN_CLIENT_ID})")

    def fetch_intraday(self, security_id, exchange_segment, instrument_type,
                       from_date, to_date, interval=1):
        try:
            return self.client.intraday_minute_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
                instrument_type=instrument_type,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
            )
        except Exception as e:
            return {"status": "error", "remarks": str(e)}

    def fetch_daily(self, security_id, exchange_segment, instrument_type,
                    from_date, to_date):
        try:
            return self.client.historical_daily_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
                instrument_type=instrument_type,
                from_date=from_date,
                to_date=to_date,
            )
        except Exception as e:
            return {"status": "error", "remarks": str(e)}

    def get_instrument_master(self):
        import httpx
        print("  Downloading instrument master CSV...")
        resp = httpx.get(
            "https://images.dhan.co/api-data/api-scrip-master.csv",
            timeout=120, follow_redirects=True,
        )
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), low_memory=False)
        print(f"  [OK] {len(df):,} instruments loaded")
        return df


# =============================================================================
# Response Parser
# =============================================================================

def parse_response(resp, name=""):
    if not resp or resp.get("status") != "success":
        return pd.DataFrame()
    data = resp.get("data", {})
    if not data:
        return pd.DataFrame()

    timestamps = data.get("timestamp", data.get("start_Time", []))
    if not timestamps:
        return pd.DataFrame()

    records = []
    opens = data.get("open", [])
    highs = data.get("high", [])
    lows = data.get("low", [])
    closes = data.get("close", [])
    volumes = data.get("volume", [])
    oi = data.get("open_interest", [])

    for i in range(len(timestamps)):
        ts = timestamps[i]
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(ts)
        elif isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

        records.append({
            "timestamp": ts,
            "open": float(opens[i]) if i < len(opens) else 0,
            "high": float(highs[i]) if i < len(highs) else 0,
            "low": float(lows[i]) if i < len(lows) else 0,
            "close": float(closes[i]) if i < len(closes) else 0,
            "volume": int(volumes[i]) if i < len(volumes) else 0,
            "oi": int(oi[i]) if i < len(oi) else 0,
        })

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


# =============================================================================
# Futures / Options Lookup from Instrument Master
# =============================================================================

def find_futures(master, symbol, exchange_segment, instrument_type):
    today = datetime.now().strftime("%Y-%m-%d")
    mask = (
        master["SEM_TRADING_SYMBOL"].str.contains(symbol, case=False, na=False)
        & (master["SEM_INSTRUMENT_NAME"] == instrument_type)
        & (master["SEM_EXPIRY_DATE"] >= today)
    )
    df = master[mask].sort_values("SEM_EXPIRY_DATE")
    results = []
    for _, row in df.head(3).iterrows():
        results.append({
            "security_id": str(row["SEM_SMST_SECURITY_ID"]),
            "exchange_segment": exchange_segment,
            "instrument_type": instrument_type,
            "display_name": str(row["SEM_TRADING_SYMBOL"]),
            "expiry": str(row["SEM_EXPIRY_DATE"]),
        })
    return results


def find_options(master, symbol, exchange_segment, instrument_type,
                 atm_strike, interval, num_strikes):
    today = datetime.now().strftime("%Y-%m-%d")
    mask = (
        master["SEM_TRADING_SYMBOL"].str.contains(symbol, case=False, na=False)
        & (master["SEM_INSTRUMENT_NAME"] == instrument_type)
        & (master["SEM_EXPIRY_DATE"] >= today)
    )
    df = master[mask].sort_values("SEM_EXPIRY_DATE")
    if df.empty:
        return []

    nearest_expiry = df["SEM_EXPIRY_DATE"].iloc[0]
    df = df[df["SEM_EXPIRY_DATE"] == nearest_expiry]

    atm = round(atm_strike / interval) * interval
    targets = [atm + (i - num_strikes // 2) * interval for i in range(num_strikes)]

    results = []
    for _, row in df.iterrows():
        strike = row.get("SEM_STRIKE_PRICE", 0)
        try:
            strike = float(strike)
        except (ValueError, TypeError):
            continue
        if strike in targets:
            results.append({
                "security_id": str(row["SEM_SMST_SECURITY_ID"]),
                "exchange_segment": exchange_segment,
                "instrument_type": instrument_type,
                "display_name": str(row["SEM_TRADING_SYMBOL"]),
                "expiry": str(row["SEM_EXPIRY_DATE"]),
                "strike": strike,
            })
    return results


# =============================================================================
# Core Fetcher — 85-day Chunked Download
# =============================================================================

def fetch_and_save(client, security_id, exchange_segment, instrument_type,
                   display_name, days=MAX_HISTORY_DAYS, save_dir=STORAGE_DIR):
    save_dir.mkdir(parents=True, exist_ok=True)
    safe_name = display_name.replace(" ", "_").replace("/", "_").replace("-", "_")
    filepath = save_dir / f"{safe_name}_1min.csv"

    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=days)

    all_dfs = []
    chunk_start = from_dt
    total_chunks = (days // CHUNK_DAYS) + 1
    chunk_num = 0

    print(f"\n  >> {display_name} [{security_id}] @ {exchange_segment} ({instrument_type})")
    print(f"     {from_dt.strftime('%Y-%m-%d')} to {to_dt.strftime('%Y-%m-%d')} ({total_chunks} chunks)")

    while chunk_start < to_dt:
        chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS), to_dt)
        chunk_num += 1

        resp = client.fetch_intraday(
            security_id, exchange_segment, instrument_type,
            chunk_start.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d"),
            interval=1,
        )

        df = parse_response(resp, display_name)
        n = len(df)

        if n > 0:
            all_dfs.append(df)
            print(f"     [{chunk_num}/{total_chunks}] "
                  f"{chunk_start.strftime('%Y-%m-%d')} -> {chunk_end.strftime('%Y-%m-%d')}: "
                  f"{n:,} candles")
        else:
            remarks = resp.get("remarks", "") if resp else ""
            if resp and resp.get("status") != "success":
                print(f"     [{chunk_num}/{total_chunks}] "
                      f"{chunk_start.strftime('%Y-%m-%d')} -> {chunk_end.strftime('%Y-%m-%d')}: "
                      f"FAILED ({remarks})")
            else:
                print(f"     [{chunk_num}/{total_chunks}] "
                      f"{chunk_start.strftime('%Y-%m-%d')} -> {chunk_end.strftime('%Y-%m-%d')}: "
                      f"no data")

        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(RATE_LIMIT_SLEEP)

    if not all_dfs:
        print(f"     [WARN] No data for {display_name}")
        return 0

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    combined.to_csv(filepath, index=False)

    total = len(combined)
    size_mb = filepath.stat().st_size / (1024 * 1024)
    first = combined["timestamp"].iloc[0]
    last = combined["timestamp"].iloc[-1]
    print(f"     [SAVED] {filepath.name}: {total:,} candles, {size_mb:.1f} MB")
    print(f"     Range: {first} to {last}")
    return total


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Dhan Bulk Data Fetcher")
    parser.add_argument("--instrument", type=str, default=None,
                        help="Fetch specific asset only (NIFTY/BANKNIFTY/CRUDE/GOLD/SILVER/GAS/VIX)")
    parser.add_argument("--days", type=int, default=MAX_HISTORY_DAYS,
                        help=f"Days of history (default: {MAX_HISTORY_DAYS})")
    parser.add_argument("--skip-futures", action="store_true")
    parser.add_argument("--skip-options", action="store_true")
    parser.add_argument("--skip-master", action="store_true")
    args = parser.parse_args()

    print("=" * 70)
    print("ANTIGRAVITY TRADING - DHAN DATA FETCHER")
    print("=" * 70)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  History: {args.days} days")
    if args.instrument:
        print(f"  Filter: {args.instrument.upper()}")
    print()

    client = DhanClient()
    grand_total = 0
    master = None

    # Download instrument master for FUT/OPT lookup
    if not (args.skip_futures and args.skip_options) and not args.skip_master:
        try:
            master = client.get_instrument_master()
            master_path = STORAGE_DIR / "dhan_instrument_master.csv"
            master_path.parent.mkdir(parents=True, exist_ok=True)
            master.to_csv(master_path, index=False)
            print(f"  Master saved: {master_path.name}")
        except Exception as e:
            print(f"  [WARN] Master download failed: {e}")

    # ---- SPOT / INDEX ----
    print("\n" + "-" * 70)
    print("SPOT / INDEX DATA (1-min)")
    print("-" * 70)

    filt = args.instrument.upper() if args.instrument else None
    for key, inst in SPOT_INSTRUMENTS.items():
        if filt and filt not in key:
            continue
        grand_total += fetch_and_save(
            client, inst["security_id"], inst["exchange_segment"],
            inst["instrument_type"], inst["display_name"], args.days,
        )

    # ---- FUTURES ----
    if not args.skip_futures and master is not None:
        print("\n" + "-" * 70)
        print("FUTURES DATA (1-min)")
        print("-" * 70)

        for name, (symbol, ex_seg, inst_type) in FUTURES_CONFIG.items():
            if filt and filt not in name:
                continue

            print(f"\n  Looking up {name} futures ({symbol})...")
            futures = find_futures(master, symbol, ex_seg, inst_type)

            if not futures:
                print(f"  [WARN] No active futures for {symbol}")
                continue

            for fut in futures[:2]:
                grand_total += fetch_and_save(
                    client, fut["security_id"], fut["exchange_segment"],
                    fut["instrument_type"], fut["display_name"],
                    min(args.days, 90),
                )

    # ---- OPTIONS ----
    if not args.skip_options and master is not None:
        print("\n" + "-" * 70)
        print("OPTIONS DATA (1-min, ATM +/- strikes)")
        print("-" * 70)

        for name, (symbol, ex_seg, inst_type, atm, interval, n_strikes) in OPTIONS_CONFIG.items():
            if filt and filt not in name:
                continue

            print(f"\n  Looking up {name} options (ATM~{atm}, interval={interval})...")
            options = find_options(master, symbol, ex_seg, inst_type, atm, interval, n_strikes)

            if not options:
                print(f"  [WARN] No options found for {symbol}")
                continue

            print(f"  Found {len(options)} contracts")
            for opt in options:
                grand_total += fetch_and_save(
                    client, opt["security_id"], opt["exchange_segment"],
                    opt["instrument_type"], opt["display_name"],
                    min(args.days, 60),
                )

    # ---- SUMMARY ----
    print("\n" + "=" * 70)
    print("FETCH COMPLETE")
    print("=" * 70)
    print(f"  Total candles: {grand_total:,}")
    print(f"  Storage: {STORAGE_DIR}")

    csv_files = sorted(STORAGE_DIR.glob("*_1min.csv"))
    if csv_files:
        print(f"\n  Files:")
        total_size = 0
        for f in csv_files:
            size = f.stat().st_size
            total_size += size
            # Read first/last line for date range
            try:
                df_peek = pd.read_csv(f, usecols=["timestamp"], nrows=1)
                first = df_peek["timestamp"].iloc[0]
                df_tail = pd.read_csv(f, usecols=["timestamp"])
                last = df_tail["timestamp"].iloc[-1]
                print(f"    {f.name:<45s} {size/1024:>8,.0f} KB  [{first[:10]}..{last[:10]}]")
            except Exception:
                print(f"    {f.name:<45s} {size/1024:>8,.0f} KB")

        print(f"\n  Total size: {total_size / (1024*1024):.1f} MB")
    print()


if __name__ == "__main__":
    main()
