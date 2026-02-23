"""
Run backtest on real Dhan NIFTY data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from core.config import load_settings
from core.models import Exchange, Instrument, Interval, Segment
from data.storage import DataStorage
from engine.backtester import Backtester
from strategy.examples.simple_ma_crossover import MACrossoverStrategy

settings = load_settings()
storage = DataStorage()

# Use real NIFTY index data
instrument = Instrument(
    symbol="NIFTY", exchange=Exchange.NSE, segment=Segment.INDEX,
    lot_size=50, tick_size=0.05,
)

interval = Interval.M5
from_dt = datetime(2025, 12, 1)
to_dt = datetime(2026, 2, 20)

df = storage.load_candles(instrument, interval, from_dt, to_dt)
print(f"Loaded {len(df)} real NIFTY 5-min candles")
print(f"Date range: {df['timestamp'].min()} -> {df['timestamp'].max()}")
print(f"Price range: Rs.{df['close'].min():,.2f} - Rs.{df['close'].max():,.2f}")
print()

strategy = MACrossoverStrategy(
    params={"fast_period": 9, "slow_period": 21, "quantity": 50}
)

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

if result.trades:
    print("  First 10 Trades:")
    print("  " + "-" * 90)
    for trade in result.trades[:10]:
        print(
            f"  {trade.entry_time.strftime('%Y-%m-%d %H:%M')} -> "
            f"{trade.exit_time.strftime('%Y-%m-%d %H:%M')} | "
            f"{trade.side.value:4s} | "
            f"Entry: Rs.{trade.entry_price:,.2f} | "
            f"Exit: Rs.{trade.exit_price:,.2f} | "
            f"P&L: Rs.{trade.pnl:+,.2f}"
        )
    print()
    print(f"  Total trades: {len(result.trades)}")
    
    wins = [t for t in result.trades if t.pnl > 0]
    losses = [t for t in result.trades if t.pnl <= 0]
    print(f"  Winners: {len(wins)} | Losers: {len(losses)}")

print("\n[OK] Backtest on REAL data complete!")
