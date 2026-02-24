"""
Antigravity Trading — Dashboard API
FastAPI backend for the web dashboard.
Provides REST endpoints and WebSocket for real-time updates.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Load .env BEFORE any project imports so env vars are available
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from dashboard.api.routes import strategies, backtest, data as data_routes, strategy_ai

logger = logging.getLogger("antigravity.dashboard")

# Initialize settings
settings = load_settings()

# Create FastAPI app
app = FastAPI(
    title="Antigravity Trading Platform",
    description="Strategy Backtester, Forward Tester & Live Executor for Indian Markets",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(strategies.router, prefix="/api/strategies", tags=["Strategies"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
app.include_router(data_routes.router, prefix="/api/data", tags=["Data"])
app.include_router(strategy_ai.router, prefix="/api/strategy-ai", tags=["Strategy AI"])


# WebSocket connections for real-time updates
active_connections: list[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)
    logger.info("WebSocket client connected (%d total)", len(active_connections))
    try:
        while True:
            data = await ws.receive_text()
            # Handle incoming messages (subscriptions, etc.)
    except WebSocketDisconnect:
        active_connections.remove(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(active_connections))


async def broadcast(message: dict):
    """Broadcast message to all WebSocket clients."""
    text = json.dumps(message, default=str)
    for conn in active_connections:
        try:
            await conn.send_text(text)
        except Exception:
            pass


@app.get("/")
async def root():
    return {
        "name": "Antigravity Trading Platform",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "strategies": "/api/strategies",
            "backtest": "/api/backtest",
            "data": "/api/data",
            "websocket": "/ws",
            "docs": "/docs",
        },
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
