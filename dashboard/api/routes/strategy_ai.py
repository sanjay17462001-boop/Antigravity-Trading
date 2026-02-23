"""
Dashboard API — Strategy AI Routes
AI-powered strategy parsing, options backtesting, parameter optimization,
and strategy persistence (save/load/compare).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from strategy.ai_strategy_parser import AIStrategyParser
from strategy.strategy_config import StrategyConfig, LegConfig
from engine.options_backtester import OptionsBacktester, BacktestResult
from engine.optimizer import ParameterOptimizer, OptimizationReport
from engine.cost_model import CostConfig
from data.supabase_storage import get_storage

router = APIRouter()
logger = logging.getLogger("antigravity.dashboard.strategy_ai")
ai_parser = AIStrategyParser()

# Cloud or local storage
_storage = get_storage()

# Fallback: local file persistence (used only if Supabase unavailable)
STRATEGIES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "strategies"
STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)

# In-memory fallback for backtest history
_backtest_history: list[dict] = []


# =========================================================================
# Request / Response Models
# =========================================================================

class ParseRequest(BaseModel):
    description: str


class LegModel(BaseModel):
    action: str = "SELL"
    strike: str = "ATM"
    option_type: str = "CE"
    lots: int = 1
    sl_pct: Optional[float] = None
    target_pct: Optional[float] = None


class BacktestRequest(BaseModel):
    name: str = "Custom Strategy"
    legs: list[LegModel]
    entry_time: str = "09:20"
    exit_time: str = "15:15"
    sl_pct: float = 25.0
    sl_type: str = "hard"
    target_pct: float = 0.0
    target_type: str = "hard"
    lot_size: int = 25
    vix_min: Optional[float] = None
    vix_max: Optional[float] = None
    dte_min: Optional[int] = None
    dte_max: Optional[int] = None
    from_date: str = "2024-01-01"
    to_date: str = "2024-12-31"
    slippage_pts: float = 0.5
    brokerage_per_order: float = 20.0
    use_taxes: bool = True
    # Configurable DTE buckets (Fix #4)
    dte_buckets: Optional[list[list[int]]] = None


class OptimizeRequest(BaseModel):
    name: str = "Custom Strategy"
    legs: list[LegModel] = []
    entry_time: str = "09:20"
    exit_time: str = "15:15"
    sl_pct: float = 25.0
    sl_type: str = "hard"
    target_pct: float = 0.0
    target_type: str = "hard"
    lot_size: int = 25
    from_date: str = "2024-01-01"
    to_date: str = "2024-12-31"
    param_name: str = "sl_pct"
    values: list[float] = [15, 20, 25, 30, 35]
    slippage_pts: float = 0.5
    brokerage_per_order: float = 20.0


class SaveStrategyRequest(BaseModel):
    name: str
    description: str = ""
    legs: list[LegModel]
    entry_time: str = "09:20"
    exit_time: str = "15:15"
    sl_pct: float = 25.0
    sl_type: str = "hard"
    target_pct: float = 0.0
    target_type: str = "hard"
    lot_size: int = 25
    vix_min: Optional[float] = None
    vix_max: Optional[float] = None
    dte_min: Optional[int] = None
    dte_max: Optional[int] = None


# =========================================================================
# Helper
# =========================================================================

def _build_config(req) -> StrategyConfig:
    """Build StrategyConfig from request model."""
    legs = [
        LegConfig(
            action=l.action, strike=l.strike, option_type=l.option_type,
            lots=l.lots, sl_pct=l.sl_pct, target_pct=l.target_pct,
        )
        for l in req.legs
    ]
    return StrategyConfig(
        name=req.name, legs=legs,
        entry_time=req.entry_time, exit_time=req.exit_time,
        sl_pct=req.sl_pct, sl_type=req.sl_type,
        target_pct=req.target_pct, target_type=req.target_type,
        lot_size=req.lot_size,
        vix_min=getattr(req, "vix_min", None),
        vix_max=getattr(req, "vix_max", None),
        dte_min=getattr(req, "dte_min", None),
        dte_max=getattr(req, "dte_max", None),
    )


def _result_to_dict(result: BacktestResult, dte_buckets=None) -> dict:
    """Convert BacktestResult to JSON-serializable dict with all metrics."""
    trades = []
    for t in result.trades:
        if t.skipped:
            continue
        trades.append({
            "date": str(t.trade_date),
            "leg": t.leg_id,
            "action": t.action,
            "strike": t.strike,
            "option_type": t.option_type,
            "absolute_strike": t.absolute_strike,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "exit_reason": t.exit_reason,
            "quantity": t.quantity,
            "gross_pnl": round(t.gross_pnl, 2),
            "net_pnl": round(t.net_pnl, 2),
            "dte": t.dte,
            "spot": round(t.spot_at_entry, 2),
            "vix": round(t.vix_at_entry, 2) if t.vix_at_entry else 0,
            "costs": t.cost.to_dict() if t.cost else {},
        })

    # Daily P&L for equity curve
    daily = result.daily_pnl()
    equity_curve = []
    cumulative = 0
    for d in sorted(daily.keys()):
        cumulative += daily[d]
        equity_curve.append({
            "date": str(d),
            "daily_pnl": round(daily[d], 2),
            "cumulative": round(cumulative, 2),
        })

    # Parse DTE buckets — robust handling of malformed input
    parsed_buckets = None
    if dte_buckets:
        try:
            valid = [b for b in dte_buckets if isinstance(b, (list, tuple)) and len(b) >= 2]
            if valid:
                parsed_buckets = [(b[0], b[1]) for b in valid]
            # else: fall back to default buckets (None)
        except (TypeError, IndexError):
            parsed_buckets = None  # use defaults

    return {
        "strategy": result.strategy.to_dict() if result.strategy else {},
        "summary": {
            "total_trades": result.total_trades,
            "trading_days": len(set(t.trade_date for t in result.active_trades)),
            "winners": result.winning_trades,
            "losers": result.losing_trades,
            "breakeven": result.breakeven_trades,
            "win_rate": round(result.win_rate, 1),
            "gross_pnl": round(result.gross_pnl, 2),
            "total_cost": round(result.total_cost, 2),
            "net_pnl": round(result.total_pnl, 2),
            "max_drawdown": round(result.max_drawdown, 2),
            "skipped_days": len(result.skipped_days),
            # Fix #5 — Advanced ratios
            "profit_factor": round(result.profit_factor, 2) if result.profit_factor != float('inf') else 999,
            "payoff_ratio": round(result.payoff_ratio, 2) if result.payoff_ratio != float('inf') else 999,
            "expectancy": round(result.expectancy, 2),
            "avg_win": round(result.avg_win, 2),
            "avg_loss": round(result.avg_loss, 2),
            "max_win": round(result.max_win, 2),
            "max_loss": round(result.max_loss, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "calmar_ratio": round(result.calmar_ratio, 2),
            "avg_daily_pnl": round(result.avg_daily_pnl, 2),
            "max_consecutive_wins": result.max_consecutive_wins,
            "max_consecutive_losses": result.max_consecutive_losses,
        },
        # Fix #6 — Cost breakdown
        "cost_breakdown": result.cost_breakdown(),
        # Fix #4 — Configurable DTE
        "dte_breakdown": result.dte_breakdown(parsed_buckets),
        "trades": trades,
        "equity_curve": equity_curve,
    }


# =========================================================================
# Routes
# =========================================================================

@router.post("/parse")
async def parse_strategy(req: ParseRequest):
    """Parse plain-English strategy description into structured config using AI."""
    try:
        config, raw_json = ai_parser.parse_with_raw(req.description)
        if config is None:
            raise HTTPException(400, f"Failed to parse strategy: {raw_json}")

        errors = config.validate()
        return {
            "status": "success",
            "config": config.to_dict(),
            "raw_json": raw_json,
            "validation_errors": errors,
            "summary": config.summary(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Parse failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Parse failed: {str(e)}")


@router.post("/backtest")
async def run_options_backtest(req: BacktestRequest):
    """Run options backtest with given strategy config."""
    try:
        config = _build_config(req)
        errors = config.validate()
        if errors:
            raise HTTPException(400, f"Invalid config: {errors}")

        cost_cfg = CostConfig(
            slippage_pts=req.slippage_pts,
            brokerage_per_order=req.brokerage_per_order,
            use_taxes=req.use_taxes,
        )

        bt = OptionsBacktester(cost_cfg)
        result = bt.run(
            config,
            from_date=date.fromisoformat(req.from_date),
            to_date=date.fromisoformat(req.to_date),
        )

        response = _result_to_dict(result, req.dte_buckets)

        # Save to history for comparison (Fix #3)
        run_id = str(uuid.uuid4())[:8]
        history_entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "name": config.name,
            "from_date": req.from_date,
            "to_date": req.to_date,
            "summary": response["summary"],
            "config": config.to_dict(),
        }

        # Persist to Supabase if available, else in-memory
        if hasattr(_storage, 'save_ai_backtest'):
            try:
                _storage.save_ai_backtest(run_id, history_entry)
            except Exception as e:
                logger.warning("Supabase save failed, using memory: %s", e)
                _backtest_history.append(history_entry)
        else:
            _backtest_history.append(history_entry)

        response["run_id"] = run_id
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Backtest failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Backtest failed: {str(e)}")


@router.post("/optimize")
async def run_optimization(req: OptimizeRequest):
    """Run parameter optimization sweep."""
    try:
        config = _build_config(req)
        cost_cfg = CostConfig(
            slippage_pts=req.slippage_pts,
            brokerage_per_order=req.brokerage_per_order,
        )

        optimizer = ParameterOptimizer(cost_cfg)
        report = optimizer.sweep(
            config,
            param_name=req.param_name,
            values=req.values,
            from_date=date.fromisoformat(req.from_date),
            to_date=date.fromisoformat(req.to_date),
        )

        return {
            "param_name": report.param_name,
            "comparison": report.to_comparison_table(),
            "best_pnl": {
                "value": report.best_by_pnl().param_value if report.best_by_pnl() else None,
                "pnl": round(report.best_by_pnl().result.total_pnl, 2) if report.best_by_pnl() else 0,
            },
        }

    except Exception as e:
        logger.error("Optimization failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Optimization failed: {str(e)}")


# =========================================================================
# Strategy Persistence (Fix #2)
# =========================================================================

@router.post("/strategies/save")
async def save_strategy(req: SaveStrategyRequest):
    """Save a strategy configuration."""
    strat_id = str(uuid.uuid4())[:8]
    data = {
        "id": strat_id,
        "name": req.name,
        "description": req.description,
        "legs": [l.dict() for l in req.legs],
        "entry_time": req.entry_time,
        "exit_time": req.exit_time,
        "sl_pct": req.sl_pct,
        "sl_type": req.sl_type,
        "target_pct": req.target_pct,
        "target_type": req.target_type,
        "lot_size": req.lot_size,
        "vix_min": req.vix_min,
        "vix_max": req.vix_max,
        "dte_min": req.dte_min,
        "dte_max": req.dte_max,
        "created_at": datetime.now().isoformat(),
    }
    # Save to Supabase if available, else local JSON
    if hasattr(_storage, 'save_ai_strategy'):
        try:
            _storage.save_ai_strategy(strat_id, data)
        except Exception as e:
            logger.warning("Supabase save failed, using file: %s", e)
            filepath = STRATEGIES_DIR / f"{strat_id}.json"
            filepath.write_text(json.dumps(data, indent=2))
    else:
        filepath = STRATEGIES_DIR / f"{strat_id}.json"
        filepath.write_text(json.dumps(data, indent=2))
    return {"status": "saved", "id": strat_id, "strategy": data}


@router.get("/strategies/list")
async def list_saved_strategies():
    """List all saved strategies."""
    # Try Supabase first
    if hasattr(_storage, 'list_ai_strategies'):
        try:
            strategies = _storage.list_ai_strategies()
            return {"strategies": strategies, "count": len(strategies)}
        except Exception as e:
            logger.warning("Supabase list failed, falling back to files: %s", e)

    # Fallback to local JSON files
    strategies = []
    for f in sorted(STRATEGIES_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            strategies.append(data)
        except Exception:
            continue
    return {"strategies": strategies, "count": len(strategies)}


@router.get("/strategies/{strat_id}")
async def get_strategy(strat_id: str):
    """Get a saved strategy by ID."""
    if hasattr(_storage, 'get_ai_strategy'):
        try:
            data = _storage.get_ai_strategy(strat_id)
            if data:
                return data
        except Exception:
            pass
    # Fallback to file
    filepath = STRATEGIES_DIR / f"{strat_id}.json"
    if not filepath.exists():
        raise HTTPException(404, "Strategy not found")
    return json.loads(filepath.read_text())


@router.delete("/strategies/{strat_id}")
async def delete_strategy(strat_id: str):
    """Delete a saved strategy."""
    if hasattr(_storage, 'delete_ai_strategy'):
        try:
            _storage.delete_ai_strategy(strat_id)
        except Exception:
            pass
    # Also clean up local file if it exists
    filepath = STRATEGIES_DIR / f"{strat_id}.json"
    if filepath.exists():
        filepath.unlink()
    return {"status": "deleted", "id": strat_id}


# =========================================================================
# Backtest History / Comparison (Fix #3)
# =========================================================================

@router.get("/history")
async def backtest_history():
    """Get backtest run history for comparison."""
    if hasattr(_storage, 'list_ai_backtests'):
        try:
            runs = _storage.list_ai_backtests()
            return {"runs": runs, "count": len(runs)}
        except Exception as e:
            logger.warning("Supabase history failed: %s", e)
    return {"runs": list(reversed(_backtest_history[-50:])), "count": len(_backtest_history)}
