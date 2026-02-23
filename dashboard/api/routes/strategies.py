"""
Dashboard API — Strategy Routes
CRUD for strategies and strategy management.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data.supabase_storage import get_storage

router = APIRouter()
logger = logging.getLogger("antigravity.dashboard.strategies")
storage = get_storage()


class StrategyCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    code: str = ""
    params: dict = {}


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    params: Optional[dict] = None


@router.get("/")
async def list_strategies():
    """Get all registered strategies."""
    strategies = storage.get_strategies()
    return {"strategies": strategies}


@router.post("/")
async def create_strategy(strategy: StrategyCreate):
    """Create or update a strategy."""
    storage.save_strategy(
        strategy.id,
        strategy.name,
        strategy.description,
        strategy.code,
        json.dumps(strategy.params),
    )
    return {"status": "created", "id": strategy.id}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get a specific strategy by ID."""
    strategies = storage.get_strategies()
    for s in strategies:
        if s["id"] == strategy_id:
            return s
    raise HTTPException(status_code=404, detail="Strategy not found")


@router.get("/{strategy_id}/trades")
async def get_strategy_trades(strategy_id: str, mode: str = ""):
    """Get all trades for a strategy."""
    trades = storage.get_trades(strategy_id=strategy_id, mode=mode)
    return {"trades": trades, "count": len(trades)}
