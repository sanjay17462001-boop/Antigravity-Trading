"""
Seed 10 sample strategies into the Antigravity Trading dashboard.
Run: python scripts/seed_strategies.py
"""

import json
import httpx
import time

API = "http://localhost:8000/api/strategy-ai"

# ═══════════════════════════════════════════════════════════════
# 10 Diverse NIFTY Options Strategies
# ═══════════════════════════════════════════════════════════════

STRATEGIES = [
    # 1. ATM Straddle Sell — The classic
    {
        "name": "ATM Straddle Sell (25% Hard SL)",
        "description": "Sell ATM CE + ATM PE at market open with 25% hard stop loss",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 25, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 2. ATM Straddle Sell — Close-based SL (wider)
    {
        "name": "ATM Straddle Close SL (30%)",
        "description": "Sell ATM straddle with 30% close-based stop loss, delayed entry at 9:30",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:30", "exit_time": "15:15",
        "sl_pct": 30, "sl_type": "close",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 3. ATM Strangle Sell — Wider strikes
    {
        "name": "ATM+1 Strangle Sell",
        "description": "Sell OTM strangle: ATM+1 CE and ATM-1 PE with 30% hard SL",
        "legs": [
            {"action": "SELL", "strike": "ATM+1", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM-1", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 30, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 4. Wide Strangle — Deep OTM
    {
        "name": "Deep OTM Strangle (ATM+3)",
        "description": "Sell deep OTM strangle: ATM+3 CE and ATM-3 PE with 50% hard SL",
        "legs": [
            {"action": "SELL", "strike": "ATM+3", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM-3", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 50, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 5. Iron Condor — Protected strangle
    {
        "name": "Iron Condor (ATM+2/+5)",
        "description": "Sell ATM+2 CE and ATM-2 PE, buy ATM+5 CE and ATM-5 PE for protection",
        "legs": [
            {"action": "SELL", "strike": "ATM+2", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM-2", "option_type": "PE", "lots": 1},
            {"action": "BUY", "strike": "ATM+5", "option_type": "CE", "lots": 1},
            {"action": "BUY", "strike": "ATM-5", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 0, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 6. Tight SL Straddle — Low risk, more trades
    {
        "name": "Tight SL Straddle (15% Hard)",
        "description": "ATM straddle sell with aggressive 15% hard SL for quick exits",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 15, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 7. Late Entry Straddle — Avoid opening volatility
    {
        "name": "Late Entry Straddle (10:00)",
        "description": "ATM straddle sell entering at 10:00 after opening range, 25% hard SL",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "10:00", "exit_time": "15:15",
        "sl_pct": 25, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 8. Straddle with Target
    {
        "name": "Straddle SL+Target (25/50)",
        "description": "ATM straddle sell with 25% SL and 50% profit target, both hard",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 25, "sl_type": "hard",
        "target_pct": 50, "target_type": "hard",
        "lot_size": 25,
    },
    # 9. Bull Put Spread
    {
        "name": "Bull Put Spread (ATM/ATM-3)",
        "description": "Sell ATM PE, buy ATM-3 PE for downside protection",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1},
            {"action": "BUY", "strike": "ATM-3", "option_type": "PE", "lots": 1},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 30, "sl_type": "hard",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
    # 10. 2-Lot Straddle — Higher position size
    {
        "name": "2-Lot Straddle (25% Close SL)",
        "description": "ATM straddle sell with 2 lots per leg and 25% close-based SL",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 2},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 2},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 25, "sl_type": "close",
        "target_pct": 0, "target_type": "hard",
        "lot_size": 25,
    },
]


def seed_strategies():
    """Save all 10 strategies via the API."""
    print("=" * 60)
    print("SEEDING 10 SAMPLE STRATEGIES")
    print("=" * 60)

    saved = []
    for i, s in enumerate(STRATEGIES, 1):
        print(f"\n[{i}/10] Saving: {s['name']}")
        try:
            r = httpx.post(f"{API}/strategies/save", json=s, timeout=10)
            if r.status_code == 200:
                data = r.json()
                print(f"  -> Saved as {data['id']}")
                saved.append(data)
            else:
                print(f"  -> Failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"  -> Error: {e}")

    print(f"\n{'=' * 60}")
    print(f"Saved {len(saved)}/10 strategies")
    return saved


def run_backtests():
    """Run backtest for each strategy (2024 full year)."""
    print("\n" + "=" * 60)
    print("RUNNING BACKTESTS FOR ALL STRATEGIES")
    print("=" * 60)

    results = []
    for i, s in enumerate(STRATEGIES, 1):
        print(f"\n[{i}/10] Backtesting: {s['name']}...")
        payload = {
            **s,
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "slippage_pts": 0.5,
            "brokerage_per_order": 20,
        }
        try:
            r = httpx.post(f"{API}/backtest", json=payload, timeout=120)
            if r.status_code == 200:
                data = r.json()
                summary = data["summary"]
                print(f"  Trades: {summary['total_trades']} | WR: {summary['win_rate']}%")
                print(f"  Net P&L: Rs.{summary['net_pnl']:,.0f} | Max DD: Rs.{summary['max_drawdown']:,.0f}")
                print(f"  Sharpe: {summary.get('sharpe_ratio', 'N/A')} | PF: {summary.get('profit_factor', 'N/A')}")
                results.append({"name": s["name"], "summary": summary})
            else:
                print(f"  -> Failed: {r.status_code}")
        except Exception as e:
            print(f"  -> Error: {e}")

    # Print comparison table
    if results:
        print("\n" + "=" * 80)
        print(f"{'Strategy':<35} {'Trades':>7} {'WR':>6} {'Net P&L':>12} {'Max DD':>10} {'Sharpe':>7} {'PF':>6}")
        print("-" * 80)
        for r in results:
            s = r["summary"]
            print(f"{r['name']:<35} {s['total_trades']:>7} {s['win_rate']:>5.1f}% "
                  f"Rs.{s['net_pnl']:>9,.0f} Rs.{s['max_drawdown']:>7,.0f} "
                  f"{s.get('sharpe_ratio', 0):>6.2f} {s.get('profit_factor', 0):>5.2f}")
        print("=" * 80)

    return results


if __name__ == "__main__":
    saved = seed_strategies()
    print("\nWaiting 2 seconds before backtests...")
    time.sleep(2)
    results = run_backtests()
    print(f"\n{'=' * 60}")
    print("DONE! Visit http://localhost:3000/strategies to see all strategies")
    print("=" * 60)
