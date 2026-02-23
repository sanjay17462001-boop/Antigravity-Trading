"""
Antigravity Trading — AI Code Generation Backtester
=====================================================
Sends user prompt to Gemini → receives Python strategy code → executes it
day-by-day across the date range using the Strategy SDK.

This enables unlimited strategy features — trailing SL, Rs-based global SL,
profit locking, or literally any logic the user describes in English.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from datetime import date, time, datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd

from engine.strategy_sdk import StrategyContext, StrategyResult, TradeRecord
from engine.cost_model import CostModel, CostConfig
from engine.options_backtester import (
    DataLoader, _data_loader, load_expiry_calendar, get_next_expiry,
)

logger = logging.getLogger("antigravity.codegen")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


# =========================================================================
# System prompt for code generation
# =========================================================================

CODEGEN_SYSTEM_PROMPT = '''You are a Python code generator for NIFTY options backtesting.

The user will describe a trading strategy in plain English. You must write a Python function called `strategy(ctx)` that implements it.

## STRATEGY SDK REFERENCE

`ctx` is a StrategyContext object with these methods and properties:

### Properties (read-only)
- `ctx.date` → current trading date (datetime.date)
- `ctx.dte` → days to expiry (int)
- `ctx.spot` → NIFTY spot price at day start (float)
- `ctx.vix` → India VIX (float)
- `ctx.lot_size` → lot size, e.g. 75 or 65 (int)
- `ctx.entry_time` → configured entry time string e.g. "09:20"
- `ctx.exit_time` → configured exit time string e.g. "15:15"

### Data Access
- `ctx.get_candles(strike, option_type)` → DataFrame of 1-min OHLC candles
  - strike: "ATM", "ATM+1", "ATM+2", ..., "ATM+10", "ATM-1", ..., "ATM-10"
  - option_type: "CE" or "PE"
  - Returns columns: timestamp, open, high, low, close, volume, oi, spot_price, absolute_strike
- `ctx.get_option_price_at(strike, option_type, time_obj)` → float, option open price at specific time
- `ctx.get_spot_price_at(time_obj)` → float, spot price at specific time
- `ctx.get_available_strikes()` → list of available strike strings

### Position Management
- `ctx.open_position(strike, option_type, action, lots=1, label="", price=None, at_time=None)` → position_id (int)
  - action: "BUY" or "SELL"
  - Returns -1 if no price data available
- `ctx.close_position(position_id, price=None, reason="", at_time=None)` → bool
- `ctx.close_all(reason="", at_time=None)` → closes all open positions
- `ctx.get_open_positions()` → list of Position objects
- `ctx.get_position(position_id)` → Position or None
- `ctx.update_prices(candle_time)` → updates current_price on all open positions from candle data

### Position object properties
- `pos.id`, `pos.strike`, `pos.option_type`, `pos.action`, `pos.lots`, `pos.quantity`
- `pos.entry_price`, `pos.current_price`, `pos.is_open`
- `pos.unrealized_pnl` → current unrealized P&L

### P&L
- `ctx.get_total_pnl()` → float, total P&L (realized + unrealized)
- `ctx.get_realized_pnl()` → float, P&L from closed positions only
- `ctx.get_unrealized_pnl()` → float, P&L from open positions only

### Logging
- `ctx.log(message)` → add a log entry

## RULES
1. Your function signature MUST be: `def strategy(ctx):`
2. Available imports: `from datetime import time, date, timedelta` and `import math`
3. DO NOT import os, sys, subprocess, or any file/network modules
4. The function is called ONCE PER TRADING DAY
5. Any positions still open at day end are auto-closed at exit_time
6. Use `ctx.update_prices(t)` before checking P&L during candle walk
7. For minute-by-minute logic, iterate candles with a for loop
8. Use time objects for comparisons: `time(9, 21)` not string "09:21"

## COMMON PATTERNS

### Basic straddle sell:
```python
def strategy(ctx):
    entry_t = time(9, 20)
    p1 = ctx.open_position("ATM", "CE", "SELL", 1, "CE leg", at_time=entry_t)
    p2 = ctx.open_position("ATM", "PE", "SELL", 1, "PE leg", at_time=entry_t)
    if p1 == -1 or p2 == -1:
        ctx.close_all("no_data")
        return
```

### Minute-by-minute monitoring:
```python
    ce_candles = ctx.get_candles("ATM", "CE")
    for _, row in ce_candles.iterrows():
        t = row["timestamp"].time()
        if t <= entry_t:
            continue
        if t >= time(15, 15):
            ctx.close_all("time_exit", at_time="15:15")
            return
        ctx.update_prices(t)
        total_pnl = ctx.get_total_pnl()
        # ... your logic here
```

### Hard SL on individual leg (percentage-based):
```python
        for pos in ctx.get_open_positions():
            if pos.action == "SELL":
                sl_price = pos.entry_price * (1 + sl_pct / 100)
                if pos.current_price >= sl_price:
                    ctx.close_position(pos.id, price=sl_price, reason="sl_hit", at_time=str(t))
```

### Global Rs-based SL:
```python
        if ctx.get_total_pnl() <= -2000:
            ctx.close_all("global_sl", at_time=str(t))
            return
```

### Trailing SL:
```python
    peak_pnl = 0
    trail_sl = initial_sl
    # inside candle loop:
        total_pnl = ctx.get_total_pnl()
        if total_pnl > peak_pnl:
            peak_pnl = total_pnl
            trail_sl = peak_pnl * trail_pct  # or tighten the %
        if total_pnl < peak_pnl - trail_sl:
            ctx.close_all("trailing_sl")
            return
```

### Profit locking:
```python
    locked_profit = None
    # inside candle loop:
        total_pnl = ctx.get_total_pnl()
        if total_pnl >= lock_trigger and locked_profit is None:
            locked_profit = lock_amount
            ctx.log(f"Locked profit at Rs.{lock_amount}")
        if locked_profit is not None and total_pnl <= locked_profit:
            ctx.close_all("profit_lock")
            return
```

## OUTPUT FORMAT
Return ONLY the Python function. No markdown, no explanation, no code fences.
Start with `def strategy(ctx):` directly.
'''


# =========================================================================
# Code Generator
# =========================================================================

class CodegenBacktester:
    """
    AI Code Generation Backtester.
    1. Sends user prompt to Gemini → gets Python code
    2. Executes the code day-by-day using StrategyContext
    3. Collects results into StrategyResult
    """

    def __init__(
        self,
        api_key: str = "",
        cost_config: Optional[CostConfig] = None,
    ):
        self.api_key = api_key or GEMINI_API_KEY
        self.cost_model = CostModel(cost_config or CostConfig())
        self.cost_config = cost_config or CostConfig()

    def generate_code(self, user_prompt: str, max_retries: int = 3) -> tuple[str, str]:
        """
        Call Gemini to generate strategy code from user prompt.
        Validates the code and retries if it's incomplete.

        Returns:
            (code_string, strategy_name)
        """
        for attempt in range(max_retries):
            code, name = self._call_gemini(user_prompt, attempt)
            # Validate: code must contain essential SDK calls
            if "open_position" in code and "get_candles" in code and "def strategy" in code:
                logger.info("Code validation passed (attempt %d)", attempt + 1)
                return code, name
            logger.warning("Generated code missing essential SDK calls (attempt %d/%d)", attempt + 1, max_retries)

        # Return whatever we got on final attempt
        logger.error("All %d code generation attempts produced invalid code", max_retries)
        return code, name

    def _call_gemini(self, user_prompt: str, attempt: int = 0) -> tuple[str, str]:
        """Single Gemini API call for code generation."""
        extra_instruction = ""
        if attempt > 0:
            extra_instruction = (
                "\n\nIMPORTANT: Your previous code was incomplete. You MUST include:\n"
                "1. ctx.open_position() calls to enter trades\n"
                "2. ctx.get_candles() to get price data\n"
                "3. A candle-by-candle for loop for monitoring\n"
                "4. ctx.close_position() or ctx.close_all() for exits\n"
                "Make sure the function is COMPLETE and not truncated.\n"
            )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{
                        "text": f"{CODEGEN_SYSTEM_PROMPT}\n\n"
                                f"Generate a strategy function for this:\n{user_prompt}"
                                f"{extra_instruction}"
                    }],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 8192,
            },
        }

        resp = httpx.post(
            f"{GEMINI_URL}?key={self.api_key}",
            json=payload,
            timeout=60,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:300]}")

        result = resp.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]

        # Clean up — remove markdown code fences if present
        text = text.strip()
        if text.startswith("```python"):
            text = text[len("```python"):].strip()
        if text.startswith("```"):
            text = text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        # Extract strategy name from code comments or generate one
        strategy_name = "AI Strategy"
        for line in text.split("\n")[:5]:
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                name_line = line.strip().strip("\"'").strip()
                if name_line:
                    strategy_name = name_line[:50]
                break

        return text, strategy_name

    def _preprocess_code(self, code: str) -> str:
        """
        Strip import statements from generated code.
        We pre-inject time, date, timedelta, math into the execution context,
        so imports are unnecessary and would fail in the sandbox.
        """
        lines = code.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # Skip import lines — these are already injected
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def execute(
        self,
        code: str,
        user_prompt: str,
        strategy_name: str,
        from_date: date,
        to_date: date,
        lot_size: int = 75,
        entry_time: str = "09:20",
        exit_time: str = "15:15",
    ) -> StrategyResult:
        """
        Execute generated strategy code across date range.
        """
        # Pre-process: strip imports
        code = self._preprocess_code(code)

        # Compile the code
        allowed_builtins = {
            'abs': abs, 'min': min, 'max': max, 'round': round,
            'len': len, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'sorted': sorted, 'reversed': reversed,
            'sum': sum, 'any': any, 'all': all,
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
            'isinstance': isinstance, 'type': type,
            'print': lambda *a, **kw: None,  # suppress prints
            'True': True, 'False': False, 'None': None,
            'map': map, 'filter': filter,
        }

        import math
        from datetime import time as dt_time, date as dt_date, timedelta as dt_timedelta

        exec_globals = {
            '__builtins__': allowed_builtins,
            'math': math,
            'time': dt_time,
            'date': dt_date,
            'timedelta': dt_timedelta,
        }

        try:
            exec(code, exec_globals)
        except Exception as e:
            raise RuntimeError(f"Code compilation failed: {e}")

        strategy_fn = exec_globals.get("strategy")
        if strategy_fn is None:
            raise RuntimeError("Generated code does not define a `strategy(ctx)` function")

        # Preload data
        _data_loader.preload_range(from_date, to_date)
        expiry_df = load_expiry_calendar()

        # Run day-by-day
        result = StrategyResult(
            strategy_name=strategy_name,
            generated_code=code,
            user_prompt=user_prompt,
            from_date=from_date,
            to_date=to_date,
            lot_size=lot_size,
        )

        current = from_date
        while current <= to_date:
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            day_data = _data_loader.load_day(current)
            if day_data is None or day_data.empty:
                current += timedelta(days=1)
                continue

            # Calculate DTE
            next_expiry = get_next_expiry(current, expiry_df)
            dte = (next_expiry - current).days if next_expiry else 0

            # Create context for this day
            ctx = StrategyContext(
                day_data=day_data,
                trade_date=current,
                dte=dte,
                lot_size=lot_size,
                cost_model=self.cost_model,
                entry_time_str=entry_time,
                exit_time_str=exit_time,
            )

            # Execute strategy
            try:
                strategy_fn(ctx)
            except Exception as e:
                error_msg = f"[{current}] Execution error: {e}"
                result.execution_errors.append(error_msg)
                logger.warning(error_msg)

            # Collect day results
            day_result = ctx._collect_day_result()

            if day_result.trades:
                result.trades.extend(day_result.trades)
                result.daily_pnl[current] = day_result.daily_pnl
            result.logs.extend(day_result.logs)

            current += timedelta(days=1)

        return result

    def run(
        self,
        user_prompt: str,
        from_date: date,
        to_date: date,
        lot_size: int = 75,
        entry_time: str = "09:20",
        exit_time: str = "15:15",
    ) -> StrategyResult:
        """
        Full pipeline: generate code from prompt → execute → return results.
        """
        # 1. Generate code
        code, strategy_name = self.generate_code(user_prompt)
        logger.info("Generated strategy code (%d chars): %s", len(code), strategy_name)

        # 2. Execute
        result = self.execute(
            code=code,
            user_prompt=user_prompt,
            strategy_name=strategy_name,
            from_date=from_date,
            to_date=to_date,
            lot_size=lot_size,
            entry_time=entry_time,
            exit_time=exit_time,
        )

        logger.info(
            "Codegen backtest done: %d trades, Net P&L: Rs.%.0f",
            result.total_trades, result.net_pnl,
        )
        return result
