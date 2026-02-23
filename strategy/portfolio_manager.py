"""
Antigravity Trading — Multi-Strategy Portfolio Manager
======================================================
Orchestrates multiple trading strategies with:
- Capital allocation (equal, risk-parity, custom weights)
- Portfolio-level risk aggregation
- Consolidated P&L and drawdown tracking
- Strategy lifecycle management (start/stop/pause)
- Correlation monitoring between strategies
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("antigravity.portfolio_manager")


# =============================================================================
# Enums
# =============================================================================

class StrategyState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class AllocationMethod(Enum):
    EQUAL = "equal"                      # Equal capital to each strategy
    RISK_PARITY = "risk_parity"          # Allocate inversely proportional to volatility
    FIXED_FRACTION = "fixed_fraction"    # Kelly-criterion inspired
    CUSTOM = "custom"                    # User-defined weights


class RiskAction(Enum):
    WARN = "warn"
    PAUSE_STRATEGY = "pause_strategy"
    STOP_ALL = "stop_all"
    SQUARE_OFF = "square_off"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StrategyAllocation:
    """Capital allocation for a single strategy."""
    strategy_id: str
    strategy_name: str
    weight: float                    # 0.0 to 1.0
    allocated_capital: float
    used_capital: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    max_drawdown_pct: float = 0.0
    total_trades: int = 0
    win_count: int = 0
    state: StrategyState = StrategyState.IDLE
    last_trade_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def return_pct(self) -> float:
        if self.allocated_capital == 0:
            return 0.0
        return (self.total_pnl / self.allocated_capital) * 100

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.win_count / self.total_trades) * 100

    @property
    def utilization_pct(self) -> float:
        if self.allocated_capital == 0:
            return 0.0
        return (self.used_capital / self.allocated_capital) * 100


@dataclass
class RiskLimit:
    """A risk limit with threshold and action."""
    name: str
    metric: str                      # e.g., "portfolio_drawdown_pct", "strategy_loss"
    threshold: float
    action: RiskAction
    strategy_id: Optional[str] = None  # None = portfolio-level
    triggered: bool = False
    triggered_at: Optional[datetime] = None


@dataclass
class PortfolioSnapshot:
    """Point-in-time portfolio state."""
    timestamp: datetime
    total_equity: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    drawdown_pct: float
    strategy_pnls: Dict[str, float]
    active_strategies: int
    open_positions: int


@dataclass
class RebalanceAction:
    """Describes a rebalancing action."""
    strategy_id: str
    strategy_name: str
    current_weight: float
    target_weight: float
    capital_change: float            # positive = add, negative = remove


# =============================================================================
# Multi-Strategy Portfolio Manager
# =============================================================================

class MultiStrategyPortfolioManager:
    """
    Manages a portfolio of multiple trading strategies.

    Features:
    - Capital allocation and rebalancing
    - Strategy lifecycle (run/pause/stop)
    - Portfolio-level risk monitoring
    - Consolidated P&L and drawdown
    - Correlation tracking between strategies
    - Snapshot history for analysis
    """

    def __init__(
        self,
        total_capital: float,
        allocation_method: AllocationMethod = AllocationMethod.EQUAL,
    ):
        self.total_capital = total_capital
        self.allocation_method = allocation_method
        self.strategies: Dict[str, StrategyAllocation] = {}
        self.risk_limits: List[RiskLimit] = []
        self.snapshots: List[PortfolioSnapshot] = []
        self._peak_equity = total_capital
        self._pnl_history: Dict[str, List[float]] = {}  # for correlation

        # Default risk limits
        self.add_risk_limit(RiskLimit(
            "Portfolio Max Drawdown",
            "portfolio_drawdown_pct",
            5.0,
            RiskAction.STOP_ALL,
        ))
        self.add_risk_limit(RiskLimit(
            "Daily Loss Limit",
            "daily_loss",
            50000,
            RiskAction.STOP_ALL,
        ))

        logger.info("Portfolio manager initialized: capital=Rs.%s, method=%s",
                     f"{total_capital:,.0f}", allocation_method.value)

    # -------------------------------------------------------------------------
    # Strategy Management
    # -------------------------------------------------------------------------

    def add_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        weight: Optional[float] = None,
        max_loss: float = 20000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StrategyAllocation:
        """Add a strategy to the portfolio."""
        if strategy_id in self.strategies:
            raise ValueError(f"Strategy {strategy_id} already exists")

        alloc = StrategyAllocation(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            weight=weight or 0.0,
            allocated_capital=0.0,
            metadata=metadata or {},
        )
        self.strategies[strategy_id] = alloc

        # Add per-strategy risk limit
        self.add_risk_limit(RiskLimit(
            f"{strategy_name} Max Loss",
            "strategy_loss",
            max_loss,
            RiskAction.PAUSE_STRATEGY,
            strategy_id=strategy_id,
        ))

        # Recalculate allocations
        self._recalculate_allocations()
        self._pnl_history[strategy_id] = []

        logger.info("Added strategy: %s (weight=%.2f, capital=Rs.%s)",
                     strategy_name, alloc.weight, f"{alloc.allocated_capital:,.0f}")
        return alloc

    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy from the portfolio."""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")

        strat = self.strategies.pop(strategy_id)
        self.risk_limits = [r for r in self.risk_limits if r.strategy_id != strategy_id]
        self._pnl_history.pop(strategy_id, None)
        self._recalculate_allocations()

        logger.info("Removed strategy: %s", strat.strategy_name)

    def set_strategy_state(self, strategy_id: str, state: StrategyState) -> None:
        """Change a strategy's state."""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")

        old_state = self.strategies[strategy_id].state
        self.strategies[strategy_id].state = state
        logger.info("Strategy %s: %s -> %s",
                     self.strategies[strategy_id].strategy_name,
                     old_state.value, state.value)

    def start_strategy(self, strategy_id: str) -> None:
        self.set_strategy_state(strategy_id, StrategyState.RUNNING)

    def pause_strategy(self, strategy_id: str) -> None:
        self.set_strategy_state(strategy_id, StrategyState.PAUSED)

    def stop_strategy(self, strategy_id: str) -> None:
        self.set_strategy_state(strategy_id, StrategyState.STOPPED)

    def start_all(self) -> None:
        for sid in self.strategies:
            self.start_strategy(sid)

    def stop_all(self) -> None:
        for sid in self.strategies:
            self.stop_strategy(sid)

    # -------------------------------------------------------------------------
    # Capital Allocation
    # -------------------------------------------------------------------------

    def _recalculate_allocations(self) -> None:
        """Recalculate capital allocation based on current method."""
        n = len(self.strategies)
        if n == 0:
            return

        if self.allocation_method == AllocationMethod.EQUAL:
            weight = 1.0 / n
            for strat in self.strategies.values():
                strat.weight = weight
                strat.allocated_capital = self.total_capital * weight

        elif self.allocation_method == AllocationMethod.RISK_PARITY:
            # Use inverse of max drawdown as risk proxy
            inv_risks = {}
            for sid, strat in self.strategies.items():
                dd = abs(strat.max_drawdown_pct) if strat.max_drawdown_pct != 0 else 5.0
                inv_risks[sid] = 1.0 / dd

            total_inv = sum(inv_risks.values())
            for sid, strat in self.strategies.items():
                strat.weight = inv_risks[sid] / total_inv
                strat.allocated_capital = self.total_capital * strat.weight

        elif self.allocation_method == AllocationMethod.CUSTOM:
            # Use weights already set
            total_weight = sum(s.weight for s in self.strategies.values())
            if total_weight > 0:
                for strat in self.strategies.values():
                    strat.allocated_capital = self.total_capital * (strat.weight / total_weight)

        elif self.allocation_method == AllocationMethod.FIXED_FRACTION:
            # Kelly-inspired: weight = win_rate - (1 - win_rate) / payoff_ratio
            for strat in self.strategies.values():
                wr = strat.win_rate / 100 if strat.win_rate > 0 else 0.5
                payoff = 1.5  # default
                kelly = max(0.05, wr - (1 - wr) / payoff)
                strat.weight = min(kelly, 0.5)  # cap at 50%

            total_weight = sum(s.weight for s in self.strategies.values())
            if total_weight > 0:
                for strat in self.strategies.values():
                    strat.weight /= total_weight
                    strat.allocated_capital = self.total_capital * strat.weight

    def set_custom_weights(self, weights: Dict[str, float]) -> None:
        """Set custom weights for strategies. Weights are normalized to sum to 1."""
        for sid, weight in weights.items():
            if sid in self.strategies:
                self.strategies[sid].weight = weight
        self.allocation_method = AllocationMethod.CUSTOM
        self._recalculate_allocations()

    def get_rebalance_actions(self, target_weights: Optional[Dict[str, float]] = None) -> List[RebalanceAction]:
        """Calculate rebalancing actions needed to reach target weights."""
        actions = []
        if target_weights is None:
            target_weights = {sid: s.weight for sid, s in self.strategies.items()}

        total_w = sum(target_weights.values())
        for sid, strat in self.strategies.items():
            tw = target_weights.get(sid, 0) / total_w if total_w > 0 else 0
            current_capital = strat.allocated_capital
            target_capital = self.total_capital * tw
            delta = target_capital - current_capital

            if abs(delta) > 100:  # ignore tiny changes
                actions.append(RebalanceAction(
                    strategy_id=sid,
                    strategy_name=strat.strategy_name,
                    current_weight=strat.weight,
                    target_weight=tw,
                    capital_change=round(delta, 2),
                ))
        return actions

    # -------------------------------------------------------------------------
    # P&L and Trade Updates
    # -------------------------------------------------------------------------

    def record_trade(
        self,
        strategy_id: str,
        pnl: float,
        capital_used: float = 0,
        trade_time: Optional[datetime] = None,
    ) -> None:
        """Record a completed trade for a strategy."""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")

        strat = self.strategies[strategy_id]
        strat.realized_pnl += pnl
        strat.total_trades += 1
        if pnl > 0:
            strat.win_count += 1
        strat.last_trade_time = trade_time or datetime.now()

        # Track P&L history for correlation
        self._pnl_history[strategy_id].append(pnl)

        # Update drawdown
        equity = strat.allocated_capital + strat.total_pnl
        peak = strat.allocated_capital + max(0, strat.realized_pnl)
        if peak > 0:
            dd = ((peak - equity) / peak) * 100
            strat.max_drawdown_pct = max(strat.max_drawdown_pct, dd)

        self._check_risk_limits()

    def update_unrealized(self, strategy_id: str, unrealized_pnl: float, capital_used: float = 0) -> None:
        """Update unrealized P&L for a strategy."""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].unrealized_pnl = unrealized_pnl
            self.strategies[strategy_id].used_capital = capital_used

    # -------------------------------------------------------------------------
    # Risk Management
    # -------------------------------------------------------------------------

    def add_risk_limit(self, limit: RiskLimit) -> None:
        """Add a risk limit."""
        self.risk_limits.append(limit)

    def _check_risk_limits(self) -> List[RiskLimit]:
        """Check all risk limits and trigger actions."""
        triggered = []
        for limit in self.risk_limits:
            if limit.triggered:
                continue

            value = self._get_risk_metric(limit.metric, limit.strategy_id)
            if value is None:
                continue

            if value >= limit.threshold:
                limit.triggered = True
                limit.triggered_at = datetime.now()
                triggered.append(limit)
                self._handle_risk_breach(limit)

        return triggered

    def _get_risk_metric(self, metric: str, strategy_id: Optional[str] = None) -> Optional[float]:
        """Get current value of a risk metric."""
        if metric == "portfolio_drawdown_pct":
            return self.portfolio_drawdown_pct
        elif metric == "daily_loss":
            return abs(min(0, self.total_pnl))
        elif metric == "strategy_loss" and strategy_id:
            strat = self.strategies.get(strategy_id)
            return abs(min(0, strat.total_pnl)) if strat else None
        return None

    def _handle_risk_breach(self, limit: RiskLimit) -> None:
        """Handle a risk limit breach."""
        logger.warning("RISK LIMIT BREACHED: %s (threshold: %s, action: %s)",
                        limit.name, limit.threshold, limit.action.value)

        if limit.action == RiskAction.WARN:
            pass  # Just log
        elif limit.action == RiskAction.PAUSE_STRATEGY and limit.strategy_id:
            self.pause_strategy(limit.strategy_id)
        elif limit.action == RiskAction.STOP_ALL:
            self.stop_all()
        elif limit.action == RiskAction.SQUARE_OFF:
            self.stop_all()
            logger.warning("SQUARE OFF triggered — all strategies stopped")

    def reset_risk_limits(self) -> None:
        """Reset all triggered risk limits (e.g., at start of new day)."""
        for limit in self.risk_limits:
            limit.triggered = False
            limit.triggered_at = None

    # -------------------------------------------------------------------------
    # Portfolio Metrics
    # -------------------------------------------------------------------------

    @property
    def total_equity(self) -> float:
        return self.total_capital + self.total_pnl

    @property
    def total_pnl(self) -> float:
        return sum(s.total_pnl for s in self.strategies.values())

    @property
    def total_realized_pnl(self) -> float:
        return sum(s.realized_pnl for s in self.strategies.values())

    @property
    def total_unrealized_pnl(self) -> float:
        return sum(s.unrealized_pnl for s in self.strategies.values())

    @property
    def total_trades_count(self) -> int:
        return sum(s.total_trades for s in self.strategies.values())

    @property
    def portfolio_drawdown_pct(self) -> float:
        equity = self.total_equity
        if equity > self._peak_equity:
            self._peak_equity = equity
        if self._peak_equity == 0:
            return 0.0
        return ((self._peak_equity - equity) / self._peak_equity) * 100

    @property
    def portfolio_win_rate(self) -> float:
        total_trades = sum(s.total_trades for s in self.strategies.values())
        total_wins = sum(s.win_count for s in self.strategies.values())
        if total_trades == 0:
            return 0.0
        return (total_wins / total_trades) * 100

    @property
    def active_strategy_count(self) -> int:
        return sum(1 for s in self.strategies.values() if s.state == StrategyState.RUNNING)

    @property
    def capital_utilization_pct(self) -> float:
        total_used = sum(s.used_capital for s in self.strategies.values())
        if self.total_capital == 0:
            return 0.0
        return (total_used / self.total_capital) * 100

    # -------------------------------------------------------------------------
    # Correlation Analysis
    # -------------------------------------------------------------------------

    def strategy_correlation(self, sid1: str, sid2: str) -> Optional[float]:
        """Calculate Pearson correlation between two strategies' trade P&Ls."""
        h1 = self._pnl_history.get(sid1, [])
        h2 = self._pnl_history.get(sid2, [])

        n = min(len(h1), len(h2))
        if n < 5:
            return None

        x, y = h1[:n], h2[:n]
        mx = sum(x) / n
        my = sum(y) / n
        sx = math.sqrt(sum((xi - mx) ** 2 for xi in x) / n)
        sy = math.sqrt(sum((yi - my) ** 2 for yi in y) / n)

        if sx == 0 or sy == 0:
            return 0.0

        cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
        return round(cov / (sx * sy), 4)

    def correlation_matrix(self) -> Dict[Tuple[str, str], float]:
        """Compute pairwise correlation matrix."""
        sids = list(self.strategies.keys())
        matrix = {}
        for i, s1 in enumerate(sids):
            for s2 in sids[i + 1:]:
                corr = self.strategy_correlation(s1, s2)
                if corr is not None:
                    matrix[(s1, s2)] = corr
        return matrix

    # -------------------------------------------------------------------------
    # Snapshots
    # -------------------------------------------------------------------------

    def take_snapshot(self, timestamp: Optional[datetime] = None) -> PortfolioSnapshot:
        """Capture current portfolio state."""
        ts = timestamp or datetime.now()
        snapshot = PortfolioSnapshot(
            timestamp=ts,
            total_equity=self.total_equity,
            total_pnl=self.total_pnl,
            unrealized_pnl=self.total_unrealized_pnl,
            realized_pnl=self.total_realized_pnl,
            drawdown_pct=self.portfolio_drawdown_pct,
            strategy_pnls={sid: s.total_pnl for sid, s in self.strategies.items()},
            active_strategies=self.active_strategy_count,
            open_positions=sum(1 for s in self.strategies.values() if s.used_capital > 0),
        )
        self.snapshots.append(snapshot)
        return snapshot

    # -------------------------------------------------------------------------
    # Summary / Display
    # -------------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Get portfolio summary as dictionary."""
        return {
            "total_capital": self.total_capital,
            "total_equity": round(self.total_equity, 2),
            "total_pnl": round(self.total_pnl, 2),
            "realized_pnl": round(self.total_realized_pnl, 2),
            "unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "drawdown_pct": round(self.portfolio_drawdown_pct, 2),
            "win_rate": round(self.portfolio_win_rate, 1),
            "total_trades": self.total_trades_count,
            "active_strategies": self.active_strategy_count,
            "capital_utilization": round(self.capital_utilization_pct, 1),
            "strategies": {
                sid: {
                    "name": s.strategy_name,
                    "state": s.state.value,
                    "weight": round(s.weight, 4),
                    "allocated": round(s.allocated_capital, 2),
                    "used": round(s.used_capital, 2),
                    "pnl": round(s.total_pnl, 2),
                    "return_pct": round(s.return_pct, 2),
                    "trades": s.total_trades,
                    "win_rate": round(s.win_rate, 1),
                    "max_dd": round(s.max_drawdown_pct, 2),
                }
                for sid, s in self.strategies.items()
            },
        }

    def print_summary(self) -> None:
        """Print portfolio summary to console."""
        s = self.summary()
        print("\n" + "=" * 70)
        print("MULTI-STRATEGY PORTFOLIO SUMMARY")
        print("=" * 70)
        print(f"  Total Capital:    Rs.{s['total_capital']:>12,.0f}")
        print(f"  Total Equity:     Rs.{s['total_equity']:>12,.2f}")
        print(f"  Total P&L:        Rs.{s['total_pnl']:>12,.2f}  "
              f"({'+'if s['total_pnl']>=0 else ''}{(s['total_pnl']/s['total_capital'])*100:.2f}%)")
        print(f"  Realized P&L:     Rs.{s['realized_pnl']:>12,.2f}")
        print(f"  Unrealized P&L:   Rs.{s['unrealized_pnl']:>12,.2f}")
        print(f"  Drawdown:         {s['drawdown_pct']:>12.2f}%")
        print(f"  Win Rate:         {s['win_rate']:>12.1f}%")
        print(f"  Total Trades:     {s['total_trades']:>12d}")
        print(f"  Capital Used:     {s['capital_utilization']:>12.1f}%")
        print(f"  Active Strategies:{s['active_strategies']:>12d} / {len(self.strategies)}")

        print(f"\n{'Strategy':<20} {'State':<8} {'Weight':>7} {'Capital':>12} "
              f"{'P&L':>10} {'Return':>8} {'WR%':>6} {'Trades':>6} {'MaxDD':>7}")
        print("-" * 95)
        for sid, st in s["strategies"].items():
            pnl_color = "+" if st["pnl"] >= 0 else ""
            print(f"  {st['name']:<18} {st['state']:<8} {st['weight']:>6.1%} "
                  f"Rs.{st['allocated']:>9,.0f} "
                  f"{pnl_color}Rs.{st['pnl']:>7,.0f} "
                  f"{st['return_pct']:>+7.2f}% "
                  f"{st['win_rate']:>5.1f}% "
                  f"{st['trades']:>6d} "
                  f"{st['max_dd']:>6.2f}%")

        # Risk limits
        triggered = [r for r in self.risk_limits if r.triggered]
        if triggered:
            print(f"\n  !! TRIGGERED RISK LIMITS:")
            for r in triggered:
                print(f"     - {r.name}: threshold={r.threshold}, action={r.action.value}")


# =============================================================================
# Demo / Self-test
# =============================================================================

if __name__ == "__main__":
    import random

    print("Multi-Strategy Portfolio Manager Demo")
    print("=" * 50)

    # Create portfolio
    pm = MultiStrategyPortfolioManager(
        total_capital=1_000_000,
        allocation_method=AllocationMethod.EQUAL,
    )

    # Add strategies
    pm.add_strategy("ma_cross", "MA Crossover", max_loss=25000,
                     metadata={"instrument": "NIFTY", "timeframe": "5min"})
    pm.add_strategy("iron_condor", "Iron Condor VIX", max_loss=15000,
                     metadata={"instrument": "NIFTY Options", "timeframe": "15min"})
    pm.add_strategy("orb", "ORB Breakout", max_loss=20000,
                     metadata={"instrument": "BANKNIFTY FUT", "timeframe": "15min"})

    # Start all
    pm.start_all()

    # Simulate 30 trades across strategies
    random.seed(42)
    for i in range(30):
        sid = random.choice(["ma_cross", "iron_condor", "orb"])

        if sid == "iron_condor":
            pnl = random.gauss(500, 800)
        elif sid == "ma_cross":
            pnl = random.gauss(200, 1200)
        else:
            pnl = random.gauss(-100, 1500)

        pm.record_trade(sid, round(pnl, 2), capital_used=random.randint(50000, 150000))

    # Update some unrealized P&L
    pm.update_unrealized("ma_cross", 2400, 120000)
    pm.update_unrealized("iron_condor", 1800, 80000)
    pm.update_unrealized("orb", -1200, 95000)

    # Take snapshot
    pm.take_snapshot()

    # Print summary
    pm.print_summary()

    # Correlation
    matrix = pm.correlation_matrix()
    if matrix:
        print(f"\n  Strategy Correlations:")
        for (s1, s2), corr in matrix.items():
            n1 = pm.strategies[s1].strategy_name
            n2 = pm.strategies[s2].strategy_name
            print(f"    {n1} <-> {n2}: {corr:+.4f}")

    # Rebalance check
    print(f"\n  Rebalancing to 50/30/20 split:")
    actions = pm.get_rebalance_actions({"ma_cross": 0.5, "iron_condor": 0.3, "orb": 0.2})
    for a in actions:
        direction = "ADD" if a.capital_change > 0 else "REMOVE"
        print(f"    {a.strategy_name}: {direction} Rs.{abs(a.capital_change):,.0f} "
              f"({a.current_weight:.1%} -> {a.target_weight:.1%})")

    print("\n[OK] Multi-strategy portfolio manager ready!")
