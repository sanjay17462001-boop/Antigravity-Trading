---
description: Strategy backtesting workflow - from plain English to hardcoded frontend results
---

# Strategy Backtesting Workflow

// turbo-all

## Prerequisites
- Data range: 2021-01-01 to present (628 files, NIFTY options 1-min OHLC)
- NIFTY lot size: 65 (unless specified otherwise)
- Instrument: NIFTY only (unless specified otherwise)
- Expiry: Current weekly expiry only (unless specified otherwise)

## Process

### Step 1: Receive Strategy
- User describes strategy in plain English
- **DO NOT ASSUME** anything — ask questions if any parameter is unclear
- Confirm: entry time, exit time, SL%, SL type, target%, re-entry rules, global SL, profit locking, lot size, any other rules

### Step 2: Write Strategy Code
- Write the strategy code MYSELF (do NOT use Gemini/API)
- Use the Strategy SDK (`engine/strategy_sdk.py`) with `StrategyContext`
- Save as `scripts/strategies/strategy_<name>.py`
- Code must implement the exact rules from Step 1

### Step 3: Backtest — Two Modes
Run TWO separate backtests for the same strategy:

#### Mode A: Hard Exits
- All SL, target, profit lock, global SL exits happen at the EXACT trigger price
- SL triggers when high (for SELL) or low (for BUY) breaches the SL level
- This is the "best case" execution

#### Mode B: Candle Close Exits
- All SL, target, profit lock, global SL exits happen at the candle CLOSE price
- SL triggers only when the close price breaches the SL level
- This is the "realistic" execution

Both backtests run for **5 years: 2021-01-01 to 2026-02-18** (or latest available data).

### Step 4: Base Results (Zero Costs)
- Slippage: 0
- Brokerage: 0
- Taxes: 0
- These are the RAW gross results

### Step 5: Results to Display
For EACH mode (Hard / Close), show:
- Total trades, trading days, winners, losers, win rate
- Gross P&L (= Net P&L since zero costs)
- Max drawdown, profit factor, payoff ratio, expectancy
- Avg win, avg loss, max win, max loss
- Sharpe ratio, calmar ratio
- Max consecutive wins/losses
- Monthly breakdown (all months, all years)
- **Year vs DTE matrix** (rows = years, columns = DTE buckets 0,1,2,3,4,5,6,7+)

### Step 6: Hardcode in Frontend
After user approves the results:
1. Write strategy description in the "Describe Your Strategy" field
2. Hardcode BOTH backtest results (Hard + Close) in the results section
3. Add a **toggle** to switch between Hard and Close results
4. Add a **sidebar** with adjustable parameters:
   - Slippage (pts): default 0
   - Brokerage per order (Rs): default 0
   - Taxes: toggle on/off
   - VIX filter: min/max
5. When parameters change, recalculate Net P&L from stored gross results
6. Year vs DTE matrix must be visible

### Step 7: Strategy Reference
- The strategy description written in "Describe Your Strategy" field serves as the unique reference
- If user provides this description later, I can find and reference the exact same strategy
- Each strategy gets a unique slug/ID in the frontend

## Rules
- NIFTY only unless specified
- Lot size 65 unless specified
- Weekly expiry only unless specified
- 5-year backtest (2021-2026) unless specified
- Zero costs in base results (adjustable via sidebar)
- Always run BOTH Hard and Close backtests
- Never assume — ask questions
- Never use Gemini API for code generation — write code myself
