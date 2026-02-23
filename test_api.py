"""
Fetch real NIFTY and BANKNIFTY data from Dhan API.
Stores daily and 5-min intraday data into the platform storage.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from dhanhq import dhanhq

from core.config import load_settings
from core.models import Candle, Exchange, Instrument, Interval, Segment
from data.storage import DataStorage

settings = load_settings()
dhan = dhanhq(settings.brokers.dhan.client_id, settings.brokers.dhan.access_token)
storage = DataStorage()

# Dhan security IDs for indices
INSTRUMENTS = {
    "NIFTY": {
        "security_id": "13",
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX",
        "instrument": Instrument(symbol="NIFTY", exchange=Exchange.NSE, segment=Segment.INDEX, lot_size=50, tick_size=0.05),
    },
    "BANKNIFTY": {
        "security_id": "25",
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX",
        "instrument": Instrument(symbol="BANKNIFTY", exchange=Exchange.NSE, segment=Segment.INDEX, lot_size=15, tick_size=0.05),
    },
}

def parse_candles(data: dict, instrument: Instrument, interval: Interval) -> list[Candle]:
    """Parse Dhan API response into Candle objects."""
    candles = []
    if not isinstance(data, dict):
        return candles
    
    timestamps = data.get("timestamp", [])
    opens = data.get("open", [])
    highs = data.get("high", [])
    lows = data.get("low", [])
    closes = data.get("close", [])
    volumes = data.get("volume", [])
    
    for j in range(len(closes)):
        try:
            ts = datetime.fromtimestamp(timestamps[j])
            candles.append(Candle(
                timestamp=ts,
                open=opens[j], high=highs[j], low=lows[j], close=closes[j],
                volume=int(volumes[j]) if j < len(volumes) else 0,
                oi=0, instrument=instrument, interval=interval,
            ))
        except Exception:
            pass
    
    return candles

def fetch_daily(name: str, config: dict, years: int = 2):
    """Fetch daily data in 90-day chunks."""
    print(f"\n  [{name}] Fetching daily data ({years} years)...")
    to_date = datetime.now()
    all_candles = []
    
    total_chunks = (years * 365) // 90 + 1
    for i in range(total_chunks):
        chunk_end = to_date - timedelta(days=i * 90)
        chunk_start = chunk_end - timedelta(days=89)
        
        try:
            result = dhan.historical_daily_data(
                security_id=config["security_id"],
                exchange_segment=config["exchange_segment"],
                instrument_type=config["instrument_type"],
                from_date=chunk_start.strftime("%Y-%m-%d"),
                to_date=chunk_end.strftime("%Y-%m-%d"),
            )
            
            if result and result.get("status") == "success":
                candles = parse_candles(result.get("data", {}), config["instrument"], Interval.D1)
                all_candles.extend(candles)
                if candles:
                    print(f"    Chunk {i+1}/{total_chunks}: {len(candles)} candles [{chunk_start.date()} -> {chunk_end.date()}]")
            
            time.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f"    Chunk {i+1} error: {e}")
    
    if all_candles:
        storage.save_candles(all_candles, config["instrument"], Interval.D1)
        sorted_c = sorted(all_candles, key=lambda c: c.timestamp)
        print(f"  [{name}] Saved {len(all_candles)} daily candles: {sorted_c[0].timestamp.date()} -> {sorted_c[-1].timestamp.date()}")
        print(f"  [{name}] Latest close: Rs.{sorted_c[-1].close:,.2f}")
    else:
        print(f"  [{name}] No daily data fetched")
    
    return all_candles

def fetch_intraday(name: str, config: dict, days: int = 90):
    """Fetch intraday 5-min data in 5-day chunks."""
    print(f"\n  [{name}] Fetching intraday 5-min data ({days} days)...")
    to_date = datetime.now()
    all_candles = []
    
    total_chunks = days // 5
    for i in range(total_chunks):
        chunk_end = to_date - timedelta(days=i * 5)
        chunk_start = chunk_end - timedelta(days=4)
        
        try:
            result = dhan.intraday_minute_data(
                security_id=config["security_id"],
                exchange_segment=config["exchange_segment"],
                instrument_type=config["instrument_type"],
                from_date=chunk_start.strftime("%Y-%m-%d"),
                to_date=chunk_end.strftime("%Y-%m-%d"),
            )
            
            if result and result.get("status") == "success":
                candles = parse_candles(result.get("data", {}), config["instrument"], Interval.M5)
                all_candles.extend(candles)
                if candles:
                    print(f"    Chunk {i+1}/{total_chunks}: {len(candles)} bars [{chunk_start.date()} -> {chunk_end.date()}]")
            
            time.sleep(0.3)
        except Exception as e:
            if "No data" not in str(e):
                print(f"    Chunk {i+1} error: {e}")
    
    if all_candles:
        storage.save_candles(all_candles, config["instrument"], Interval.M5)
        sorted_c = sorted(all_candles, key=lambda c: c.timestamp)
        print(f"  [{name}] Saved {len(all_candles)} 5min candles: {sorted_c[0].timestamp} -> {sorted_c[-1].timestamp}")
    else:
        print(f"  [{name}] No intraday data fetched")
    
    return all_candles

# ====== MAIN ======
print("=" * 60)
print("  ANTIGRAVITY -- Real Data Fetch from Dhan API")
print("=" * 60)

total_daily = 0
total_intraday = 0

for name, config in INSTRUMENTS.items():
    daily = fetch_daily(name, config, years=2)
    total_daily += len(daily)
    
    intraday = fetch_intraday(name, config, days=90)
    total_intraday += len(intraday)

print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print(f"  Total daily candles   : {total_daily}")
print(f"  Total intraday candles: {total_intraday}")
print(f"  Storage               : {storage._candles_dir}")
print()

# Show what's in storage
import os
for root, dirs, files in os.walk(storage._candles_dir):
    for f in files:
        fpath = Path(root) / f
        size_kb = fpath.stat().st_size / 1024
        print(f"  {fpath.relative_to(storage._candles_dir)} ({size_kb:.1f} KB)")

print("\n  [OK] Done!")
