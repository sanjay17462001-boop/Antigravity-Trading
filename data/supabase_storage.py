"""
Antigravity Trading — Supabase Storage Engine
Cloud-native replacement for SQLite DataStorage.
Uses Supabase PostgreSQL via the supabase-py client.

Falls back to local SQLite DataStorage if SUPABASE_URL / SUPABASE_KEY
environment variables are not set.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("antigravity.data.supabase_storage")

# Try to load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_client():
    """Create a Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


class SupabaseStorage:
    """
    Cloud storage layer using Supabase PostgreSQL.
    Same interface as DataStorage for drop-in replacement.
    """

    def __init__(self):
        self._client = _get_client()
        if self._client:
            logger.info("SupabaseStorage connected to %s", os.getenv("SUPABASE_URL"))
        else:
            logger.warning("Supabase env vars not set — SupabaseStorage is inactive")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------
    # Strategy CRUD
    # ------------------------------------------------------------------

    def save_strategy(self, strategy_id: str, name: str, description: str = "",
                      code: str = "", params: str = "{}") -> None:
        if not self._client:
            return
        data = {
            "id": strategy_id,
            "name": name,
            "description": description,
            "code": code,
            "params": json.loads(params) if isinstance(params, str) else params,
            "updated_at": datetime.now().isoformat(),
        }
        self._client.table("strategies").upsert(data).execute()

    def get_strategies(self) -> list[dict]:
        if not self._client:
            return []
        result = self._client.table("strategies").select("*").order("updated_at", desc=True).execute()
        return result.data or []

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    def save_trade(self, trade, run_id: str = "", mode: str = "backtest") -> None:
        if not self._client:
            return
        data = {
            "id": trade.id,
            "run_id": run_id,
            "strategy_id": trade.strategy_id,
            "instrument": trade.instrument.display_name,
            "side": trade.side.value,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "quantity": trade.quantity,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat(),
            "pnl": trade.pnl,
            "charges": trade.charges,
            "slippage": trade.slippage,
            "meta": trade.meta,
            "mode": mode,
        }
        self._client.table("trades").upsert(data).execute()

    def get_trades(self, strategy_id: str = "", run_id: str = "", mode: str = "") -> list[dict]:
        if not self._client:
            return []
        query = self._client.table("trades").select("*")
        if strategy_id:
            query = query.eq("strategy_id", strategy_id)
        if run_id:
            query = query.eq("run_id", run_id)
        if mode:
            query = query.eq("mode", mode)
        result = query.order("entry_time").execute()
        return result.data or []

    # ------------------------------------------------------------------
    # Backtest runs
    # ------------------------------------------------------------------

    def save_backtest_run(self, run_id: str, strategy_id: str, params: str = "{}") -> None:
        if not self._client:
            return
        data = {
            "id": run_id,
            "strategy_id": strategy_id,
            "params": json.loads(params) if isinstance(params, str) else params,
        }
        self._client.table("backtest_runs").upsert(data).execute()

    def complete_backtest_run(self, run_id: str, result_summary: str) -> None:
        if not self._client:
            return
        self._client.table("backtest_runs").update({
            "completed_at": datetime.now().isoformat(),
            "result_summary": json.loads(result_summary) if isinstance(result_summary, str) else result_summary,
            "status": "completed",
        }).eq("id", run_id).execute()

    def get_backtest_runs(self, limit: int = 50) -> list[dict]:
        if not self._client:
            return []
        result = (
            self._client.table("backtest_runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    # ------------------------------------------------------------------
    # AI Strategies (replaces JSON file persistence)
    # ------------------------------------------------------------------

    def save_ai_strategy(self, strat_id: str, data: dict) -> None:
        if not self._client:
            return
        row = {
            "id": strat_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "legs": data.get("legs", []),
            "entry_time": data.get("entry_time", "09:20"),
            "exit_time": data.get("exit_time", "15:15"),
            "sl_pct": data.get("sl_pct", 25.0),
            "sl_type": data.get("sl_type", "hard"),
            "target_pct": data.get("target_pct", 0.0),
            "target_type": data.get("target_type", "hard"),
            "lot_size": data.get("lot_size", 25),
            "vix_min": data.get("vix_min"),
            "vix_max": data.get("vix_max"),
            "dte_min": data.get("dte_min"),
            "dte_max": data.get("dte_max"),
            "created_at": data.get("created_at", datetime.now().isoformat()),
        }
        self._client.table("ai_strategies").upsert(row).execute()

    def list_ai_strategies(self) -> list[dict]:
        if not self._client:
            return []
        result = (
            self._client.table("ai_strategies")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_ai_strategy(self, strat_id: str) -> Optional[dict]:
        if not self._client:
            return None
        result = (
            self._client.table("ai_strategies")
            .select("*")
            .eq("id", strat_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_ai_strategy(self, strat_id: str) -> None:
        if not self._client:
            return
        self._client.table("ai_strategies").delete().eq("id", strat_id).execute()

    # ------------------------------------------------------------------
    # AI Backtest History
    # ------------------------------------------------------------------

    def save_ai_backtest(self, run_id: str, data: dict) -> None:
        if not self._client:
            return
        row = {
            "id": run_id,
            "name": data.get("name", ""),
            "from_date": data.get("from_date", ""),
            "to_date": data.get("to_date", ""),
            "config": data.get("config", {}),
            "summary": data.get("summary", {}),
            "created_at": datetime.now().isoformat(),
        }
        self._client.table("ai_backtest_history").upsert(row).execute()

    def list_ai_backtests(self, limit: int = 50) -> list[dict]:
        if not self._client:
            return []
        result = (
            self._client.table("ai_backtest_history")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    # ------------------------------------------------------------------
    # Data catalog
    # ------------------------------------------------------------------

    def get_data_catalog(self) -> list[dict]:
        if not self._client:
            return []
        result = (
            self._client.table("data_catalog")
            .select("*")
            .order("symbol")
            .execute()
        )
        return result.data or []


# ---------------------------------------------------------------------------
# Smart factory — returns SupabaseStorage if available, else local DataStorage
# ---------------------------------------------------------------------------

def get_storage():
    """Get the best available storage backend."""
    supa = SupabaseStorage()
    if supa.is_connected:
        return supa

    # Fall back to local SQLite
    from data.storage import DataStorage
    return DataStorage()
