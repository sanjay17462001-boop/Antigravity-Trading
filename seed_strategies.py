"""Insert 10 sample strategies into Supabase for testing."""
import os
os.environ["SUPABASE_URL"] = "https://uccxmwljjhpgfbizmrzg.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVjY3htd2xqamhwZ2ZiaXptcnpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4MzA5NjksImV4cCI6MjA4NzQwNjk2OX0.1JsKf-yfmop8pqMwJc9zh3-b5r3WY0sMsPgCUNj-hD4"

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

strategies = [
    {
        "id": "strat001", "name": "ATM Straddle Sell",
        "description": "Sell ATM CE+PE at 9:20, exit 15:15",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1, "sl_pct": 25, "target_pct": None},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1, "sl_pct": 25, "target_pct": None},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 25.0, "sl_type": "hard", "target_pct": 0, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat002", "name": "Iron Condor",
        "description": "Sell OTM strangle + buy further OTM protection",
        "legs": [
            {"action": "SELL", "strike": "ATM+200", "option_type": "CE", "lots": 1, "sl_pct": 30, "target_pct": None},
            {"action": "SELL", "strike": "ATM-200", "option_type": "PE", "lots": 1, "sl_pct": 30, "target_pct": None},
            {"action": "BUY", "strike": "ATM+400", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
            {"action": "BUY", "strike": "ATM-400", "option_type": "PE", "lots": 1, "sl_pct": None, "target_pct": None},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 30.0, "sl_type": "hard", "target_pct": 0, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat003", "name": "Bull Call Spread",
        "description": "Buy ATM CE, sell OTM CE",
        "legs": [
            {"action": "BUY", "strike": "ATM", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
            {"action": "SELL", "strike": "ATM+300", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
        ],
        "entry_time": "09:30", "exit_time": "15:15",
        "sl_pct": 40.0, "sl_type": "hard", "target_pct": 50, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat004", "name": "Short Strangle",
        "description": "Sell OTM CE + OTM PE",
        "legs": [
            {"action": "SELL", "strike": "ATM+300", "option_type": "CE", "lots": 1, "sl_pct": 25, "target_pct": None},
            {"action": "SELL", "strike": "ATM-300", "option_type": "PE", "lots": 1, "sl_pct": 25, "target_pct": None},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 25.0, "sl_type": "close", "target_pct": 0, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat005", "name": "Ratio Call Spread",
        "description": "1:2 ratio call spread",
        "legs": [
            {"action": "BUY", "strike": "ATM", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
            {"action": "SELL", "strike": "ATM+200", "option_type": "CE", "lots": 2, "sl_pct": 30, "target_pct": None},
        ],
        "entry_time": "09:25", "exit_time": "15:10",
        "sl_pct": 35.0, "sl_type": "hard", "target_pct": 0, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat006", "name": "Jade Lizard",
        "description": "Short put + short call spread",
        "legs": [
            {"action": "SELL", "strike": "ATM-200", "option_type": "PE", "lots": 1, "sl_pct": 25, "target_pct": None},
            {"action": "SELL", "strike": "ATM+100", "option_type": "CE", "lots": 1, "sl_pct": 25, "target_pct": None},
            {"action": "BUY", "strike": "ATM+300", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 25.0, "sl_type": "hard", "target_pct": 0, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat007", "name": "Calendar Spread",
        "description": "Sell weekly ATM CE, hedge with monthly",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1, "sl_pct": 20, "target_pct": 15},
            {"action": "BUY", "strike": "ATM", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
        ],
        "entry_time": "09:30", "exit_time": "15:00",
        "sl_pct": 20.0, "sl_type": "close", "target_pct": 15, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat008", "name": "Butterfly Spread",
        "description": "ATM butterfly with CE",
        "legs": [
            {"action": "BUY", "strike": "ATM-200", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 2, "sl_pct": None, "target_pct": None},
            {"action": "BUY", "strike": "ATM+200", "option_type": "CE", "lots": 1, "sl_pct": None, "target_pct": None},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 50.0, "sl_type": "hard", "target_pct": 80, "target_type": "hard", "lot_size": 25,
    },
    {
        "id": "strat009", "name": "VIX-Filtered Straddle",
        "description": "Sell straddle only when VIX 12-18",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1, "sl_pct": 20, "target_pct": None},
            {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1, "sl_pct": 20, "target_pct": None},
        ],
        "entry_time": "09:25", "exit_time": "15:10",
        "sl_pct": 20.0, "sl_type": "close", "target_pct": 0, "target_type": "hard", "lot_size": 25,
        "vix_min": 12, "vix_max": 18,
    },
    {
        "id": "strat010", "name": "Aggressive CE Sell",
        "description": "Naked ATM CE sell with tight SL",
        "legs": [
            {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 2, "sl_pct": 15, "target_pct": None},
        ],
        "entry_time": "09:20", "exit_time": "15:15",
        "sl_pct": 15.0, "sl_type": "hard", "target_pct": 0, "target_type": "hard", "lot_size": 50,
    },
]

for s in strategies:
    res = sb.table("ai_strategies").upsert(s).execute()
    print(f"  Inserted: {s['name']}")

print(f"\nDone! {len(strategies)} strategies inserted into Supabase.")
