# Antigravity Trading Platform

**Strategy Backtester, Forward Tester & Live Executor for Indian Markets**

NSE (Nifty, BankNifty) • BSE (Sensex) • MCX (Crude Oil, Natural Gas, Gold, Silver)

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
# Edit config/settings.yaml with your broker credentials
# Or set environment variables: DHAN_ACCESS_TOKEN, BIGUL_API_KEY, etc.

# 4. Run the dashboard
cd dashboard/api
uvicorn main:app --reload --port 8000
# Open http://localhost:8000/docs for API documentation

# 5. Run a backtest (Python)
python run_backtest.py
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Web Dashboard (Next.js)             │
│   Strategy Builder • Backtest Results • Live Monitor │
├─────────────────────────────────────────────────────┤
│                FastAPI Backend + WebSocket            │
├──────────┬──────────┬───────────┬───────────────────┤
│ Strategy │ Backtest │  Forward  │  Live Executor     │
│  Engine  │  Engine  │  Tester   │  (Bigul primary)   │
├──────────┴──────────┴───────────┴───────────────────┤
│              Risk Manager + Portfolio Tracker         │
├─────────────────────────────────────────────────────┤
│          Data Layer (Parquet + SQLite + Cache)        │
├──────────┬──────────┬───────────────────────────────┤
│  Dhan    │  Bigul   │  Kotak Neo                     │
│ (History)│ (Feed +  │  (Hot Standby)                 │
│          │ Execute) │                                │
└──────────┴──────────┴───────────────────────────────┘
```

## Broker Roles

| Broker | Role | Capabilities |
|--------|------|-------------|
| **Dhan** | Historical Data | 5yr intraday, daily from inception, expired options |
| **Bigul** | Primary Broker | Live feed, order execution, positions |
| **Kotak Neo** | Hot Standby | Auto-failover for feed + execution |

## Writing Strategies

Strategies inherit from `strategy.base.Strategy`. Override the hooks you need:

```python
from strategy.base import Strategy
from core.models import Candle, Signal

class MyStrategy(Strategy):
    def on_candle(self, candle):
        data = self.ctx.get_data(candle.instrument)
        ema9 = self.get_indicator("ema", data, length=9)
        
        if some_condition:
            self.buy(candle.instrument, quantity=50)
        elif exit_condition:
            self.close_position(candle.instrument)
```

**No templates. No restrictions. Write any logic you want.**

## API Documentation

Start the server and visit: `http://localhost:8000/docs`

Key endpoints:
- `POST /api/backtest/run` — Run a backtest
- `GET /api/strategies` — List all strategies
- `GET /api/data/candles` — Get historical data
- `WS /ws` — Real-time updates
