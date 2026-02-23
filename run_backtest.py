"""
Antigravity Trading — Quick Backtest Runner
Run this script to execute a backtest from the command line.

Usage:
    python run_backtest.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np

from core.config import load_settings
from core.models import Exchange, Instrument, Interval, Segment, Candle
from data.storage import DataStorage
from engine.backtester import Backtester
from strategy.examples.simple_ma_crossover import MACrossoverStrategy


def generate_sample_data(
    instrument: Instrument,
    interval: Interval,
    days: int = 252,
    candles_per_day: int = 75,  # 5-min candles per trading day
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data for testing.
    Uses random walk with drift to simulate realistic price movement.
    """
    np.random.seed(42)
    total_candles = days * candles_per_day
    
    # Start at realistic price
    price = 22000.0  # Nifty-like
    timestamps = pd.date_range(
        start="2024-01-01 09:15",
        periods=total_candles,
        freq="5min",
    )
    
    data = []
    for ts in timestamps:
        # Skip non-market hours
        if ts.hour < 9 or ts.hour >= 16:
            continue
        if ts.hour == 9 and ts.minute < 15:
            continue
        if ts.hour == 15 and ts.minute > 30:
            continue
            
        # Random walk
        change = np.random.normal(0, 0.001) * price  # ~0.1% per candle
        trend = 0.00002 * price  # Slight upward drift
        
        open_price = price
        close_price = price + change + trend
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 0.0005) * price)
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 0.0005) * price)
        volume = int(np.random.lognormal(10, 1))
        
        data.append({
            "timestamp": ts,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume,
            "oi": 0,
        })
        
        price = close_price
    
    return pd.DataFrame(data)


def main():
    print("\n" + "=" * 60)
    print("  ANTIGRAVITY TRADING — Backtest Runner")
    print("=" * 60)
    
    # Load settings
    settings = load_settings()
    
    # Define instrument
    instrument = Instrument(
        symbol="NIFTY",
        exchange=Exchange.NFO,
        segment=Segment.FUTURES,
        lot_size=50,
        tick_size=0.05,
    )
    
    interval = Interval.M5
    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2024, 12, 31)
    
    # Check if real data exists
    storage = DataStorage()
    df = storage.load_candles(instrument, interval, from_dt, to_dt)
    
    if df.empty:
        print("\n[!] No real data found. Generating synthetic data for demo...")
        print("   (To use real data, fetch from Dhan first)\n")
        df = generate_sample_data(instrument, interval)
        storage.save_candles(
            [Candle(
                timestamp=row["timestamp"],
                open=row["open"], high=row["high"],
                low=row["low"], close=row["close"],
                volume=row["volume"], oi=row["oi"],
                instrument=instrument, interval=interval,
            ) for _, row in df.iterrows()],
            instrument, interval,
        )
        # Reload
        df = storage.load_candles(instrument, interval, from_dt, to_dt)
    
    print(f"  Instrument : {instrument.display_name}")
    print(f"  Interval   : {interval.value}")
    print(f"  Period     : {from_dt.date()} -> {to_dt.date()}")
    print(f"  Data points: {len(df)}")
    
    # Create strategy
    strategy = MACrossoverStrategy(
        params={"fast_period": 9, "slow_period": 21, "quantity": 50}
    )
    
    # Run backtest
    backtester = Backtester(
        initial_capital=settings.initial_capital,
        slippage_pct=0.01,
        commission_per_order=20.0,
        storage=storage,
    )
    
    result = backtester.run(
        strategy=strategy,
        instruments=[instrument],
        interval=interval,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    
    print(result.summary())
    
    # Print first 5 trades
    if result.trades:
        print("\n  First 5 Trades:")
        print("  " + "-" * 80)
        for trade in result.trades[:5]:
            print(
                f"  {trade.entry_time.strftime('%Y-%m-%d %H:%M')} -> "
                f"{trade.exit_time.strftime('%Y-%m-%d %H:%M')} | "
                f"{trade.side.value:4s} | "
                f"Entry: Rs.{trade.entry_price:,.2f} | "
                f"Exit: Rs.{trade.exit_price:,.2f} | "
                f"P&L: Rs.{trade.pnl:+,.2f}"
            )
    
    print("\n[OK] Backtest complete! Results saved to storage/trades.db")
    print("   Start the dashboard to view full results:")
    print("   cd dashboard/api && uvicorn main:app --reload --port 8000\n")


if __name__ == "__main__":
    main()
