"""
Antigravity Trading — Performance Analytics
Computes all standard and advanced performance metrics.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd

from core.models import OrderSide, Trade

logger = logging.getLogger("antigravity.engine.analytics")


class PerformanceAnalytics:
    """
    Computes performance metrics from trades and equity curve.
    
    Metrics:
    - Net P&L and total return
    - Win rate, avg win/loss, profit factor
    - Sharpe ratio, Sortino ratio, Calmar ratio
    - Max drawdown (absolute and percentage)
    - CAGR
    - Expectancy
    - Consecutive wins/losses
    """

    def __init__(
        self,
        trades: list[Trade],
        equity_curve: list[dict],
        initial_capital: float = 1_000_000.0,
        risk_free_rate: float = 0.065,  # India: ~6.5% RBI repo rate
    ):
        self._trades = trades
        self._equity_curve = equity_curve
        self._initial_capital = initial_capital
        self._risk_free_rate = risk_free_rate

    def compute_all(self) -> dict[str, Any]:
        """Compute all metrics and return as a dictionary."""
        if not self._trades:
            return {"total_trades": 0, "net_pnl": 0, "message": "No trades executed"}

        pnls = [t.pnl for t in self._trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        net_pnl = sum(pnls)
        total_charges = sum(t.charges for t in self._trades)
        total_return_pct = (net_pnl / self._initial_capital) * 100

        # Win/Loss metrics
        total_trades = len(pnls)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        # Risk/Return ratios
        sharpe = self._sharpe_ratio(pnls)
        sortino = self._sortino_ratio(pnls)

        # Drawdown
        max_dd, max_dd_pct = self._max_drawdown()

        # CAGR
        cagr = self._cagr()

        # Calmar ratio
        calmar = (cagr / max_dd_pct) if max_dd_pct > 0 else 0

        # Consecutive wins/losses
        max_consec_wins, max_consec_losses = self._consecutive_streaks(pnls)

        # Average holding time
        holding_times = []
        for t in self._trades:
            if t.entry_time and t.exit_time:
                delta = (t.exit_time - t.entry_time).total_seconds() / 3600
                holding_times.append(delta)
        avg_holding_hours = np.mean(holding_times) if holding_times else 0

        # Long vs Short breakdown
        long_trades = [t for t in self._trades if t.side == OrderSide.BUY]
        short_trades = [t for t in self._trades if t.side == OrderSide.SELL]
        long_pnl = sum(t.pnl for t in long_trades)
        short_pnl = sum(t.pnl for t in short_trades)

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "net_pnl": round(net_pnl, 2),
            "total_charges": round(total_charges, 2),
            "total_return_pct": round(total_return_pct, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "cagr": round(cagr, 2),
            "max_consec_wins": max_consec_wins,
            "max_consec_losses": max_consec_losses,
            "avg_holding_hours": round(avg_holding_hours, 2),
            "long_trades": len(long_trades),
            "short_trades": len(short_trades),
            "long_pnl": round(long_pnl, 2),
            "short_pnl": round(short_pnl, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
        }

    def _sharpe_ratio(self, pnls: list[float]) -> float:
        """Annualized Sharpe ratio."""
        if len(pnls) < 2:
            return 0.0
        returns = np.array(pnls) / self._initial_capital
        excess_returns = returns - (self._risk_free_rate / 252)  # Daily risk-free
        if np.std(excess_returns) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))

    def _sortino_ratio(self, pnls: list[float]) -> float:
        """Sortino ratio (penalizes only downside volatility)."""
        if len(pnls) < 2:
            return 0.0
        returns = np.array(pnls) / self._initial_capital
        excess_returns = returns - (self._risk_free_rate / 252)
        downside = returns[returns < 0]
        if len(downside) == 0 or np.std(downside) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(downside) * np.sqrt(252))

    def _max_drawdown(self) -> tuple[float, float]:
        """Maximum drawdown in absolute ₹ and percentage."""
        if not self._equity_curve:
            return 0.0, 0.0

        equities = [e["equity"] for e in self._equity_curve]
        peak = equities[0]
        max_dd = 0.0
        max_dd_pct = 0.0

        for eq in equities:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            max_dd = max(max_dd, dd)
            max_dd_pct = max(max_dd_pct, dd_pct)

        return max_dd, max_dd_pct

    def _cagr(self) -> float:
        """Compound Annual Growth Rate."""
        if not self._equity_curve or len(self._equity_curve) < 2:
            return 0.0

        final_equity = self._equity_curve[-1]["equity"]
        if self._initial_capital <= 0 or final_equity <= 0:
            return 0.0

        # Estimate years from equity curve timestamps
        try:
            from datetime import datetime
            first = datetime.fromisoformat(self._equity_curve[0]["timestamp"])
            last = datetime.fromisoformat(self._equity_curve[-1]["timestamp"])
            years = max((last - first).days / 365.25, 0.01)
        except Exception:
            years = 1.0

        return ((final_equity / self._initial_capital) ** (1 / years) - 1) * 100

    def _consecutive_streaks(self, pnls: list[float]) -> tuple[int, int]:
        """Find max consecutive wins and losses."""
        max_wins = max_losses = 0
        current_wins = current_losses = 0

        for p in pnls:
            if p > 0:
                current_wins += 1
                current_losses = 0
            else:
                current_losses += 1
                current_wins = 0
            max_wins = max(max_wins, current_wins)
            max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def to_dataframe(self) -> pd.DataFrame:
        """Convert trades to DataFrame for further analysis."""
        if not self._trades:
            return pd.DataFrame()

        return pd.DataFrame([{
            "id": t.id,
            "instrument": t.instrument.display_name,
            "side": t.side.value,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "return_pct": t.return_pct,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "holding_hours": (t.exit_time - t.entry_time).total_seconds() / 3600 if t.exit_time and t.entry_time else 0,
        } for t in self._trades])
