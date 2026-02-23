"""
Antigravity Trading — Parameter Optimizer
==========================================
Run parameter sweeps on strategy configs and compare results.

Usage:
    optimizer = ParameterOptimizer()
    results = optimizer.sweep(
        config=base_config,
        param_name="sl_pct",
        values=[15, 20, 25, 30, 35],
        from_date=date(2023, 1, 1),
        to_date=date(2024, 12, 31),
    )
    optimizer.print_comparison(results)
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from strategy.strategy_config import StrategyConfig
from engine.options_backtester import OptionsBacktester, BacktestResult
from engine.cost_model import CostConfig

logger = logging.getLogger("antigravity.optimizer")


@dataclass
class OptimizationResult:
    """Result of a single parameter value backtest."""
    param_name: str
    param_value: Any
    label: str
    result: BacktestResult


@dataclass
class OptimizationReport:
    """Complete optimization sweep report."""
    base_config: StrategyConfig
    param_name: str
    results: list[OptimizationResult] = field(default_factory=list)

    def best_by_pnl(self) -> Optional[OptimizationResult]:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.result.total_pnl)

    def best_by_winrate(self) -> Optional[OptimizationResult]:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.result.win_rate)

    def best_by_sharpe(self) -> Optional[OptimizationResult]:
        # Approximate Sharpe using avg daily pnl / std daily pnl
        best = None
        best_sharpe = -999
        for r in self.results:
            daily = r.result.daily_pnl()
            if not daily:
                continue
            import numpy as np
            vals = list(daily.values())
            mean = np.mean(vals)
            std = np.std(vals) if len(vals) > 1 else 1
            sharpe = (mean / std * (252 ** 0.5)) if std > 0 else 0
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best = r
        return best

    def to_comparison_table(self) -> list[dict]:
        """Generate comparison table data."""
        rows = []
        for r in self.results:
            res = r.result
            daily = res.daily_pnl()
            import numpy as np
            vals = list(daily.values()) if daily else [0]
            std = np.std(vals) if len(vals) > 1 else 0
            mean = np.mean(vals) if vals else 0
            sharpe = (mean / std * (252 ** 0.5)) if std > 0 else 0

            rows.append({
                "param": r.param_name,
                "value": r.param_value,
                "label": r.label,
                "trades": res.total_trades,
                "win_rate": round(res.win_rate, 1),
                "gross_pnl": round(res.gross_pnl, 2),
                "costs": round(res.total_cost, 2),
                "net_pnl": round(res.total_pnl, 2),
                "max_dd": round(res.max_drawdown, 2),
                "avg_daily": round(mean, 2),
                "sharpe": round(sharpe, 2),
                "skipped": len(res.skipped_days),
            })
        return rows


class ParameterOptimizer:
    """
    Sweep a strategy parameter across values and compare results.

    Supports:
    - Internal params: entry_time, exit_time, sl_pct, target_pct, sl_type
    - General factors: slippage_pts, brokerage_per_order
    - Strike params: leg strike offsets
    """

    def __init__(self, cost_config: Optional[CostConfig] = None):
        self.cost_config = cost_config or CostConfig()

    def sweep(
        self,
        config: StrategyConfig,
        param_name: str,
        values: list[Any],
        from_date: date,
        to_date: date,
        progress_callback=None,
    ) -> OptimizationReport:
        """
        Run backtests for each parameter value.

        Args:
            config: Base strategy config
            param_name: Parameter to sweep (e.g., "sl_pct", "entry_time")
            values: List of values to test
            from_date: Backtest start date
            to_date: Backtest end date
        """
        report = OptimizationReport(
            base_config=config,
            param_name=param_name,
        )

        for i, value in enumerate(values):
            # Clone config and modify parameter
            modified = self._modify_config(config, param_name, value)
            label = f"{param_name}={value}"

            if progress_callback:
                progress_callback(i + 1, len(values), label)

            # Run backtest
            bt = OptionsBacktester(self.cost_config)
            result = bt.run(modified, from_date, to_date)

            report.results.append(OptimizationResult(
                param_name=param_name,
                param_value=value,
                label=label,
                result=result,
            ))

        return report

    def sweep_general_factor(
        self,
        config: StrategyConfig,
        factor_name: str,
        values: list[Any],
        from_date: date,
        to_date: date,
        progress_callback=None,
    ) -> OptimizationReport:
        """
        Sweep a general factor (cost model parameter).
        Runs the same backtest but with different cost configs.
        """
        report = OptimizationReport(
            base_config=config,
            param_name=factor_name,
        )

        for i, value in enumerate(values):
            cost_cfg = copy.deepcopy(self.cost_config)
            if factor_name == "slippage_pts":
                cost_cfg.slippage_pts = value
            elif factor_name == "brokerage_per_order":
                cost_cfg.brokerage_per_order = value
            elif factor_name == "use_taxes":
                cost_cfg.use_taxes = value

            label = f"{factor_name}={value}"
            if progress_callback:
                progress_callback(i + 1, len(values), label)

            bt = OptionsBacktester(cost_cfg)
            result = bt.run(config, from_date, to_date)

            report.results.append(OptimizationResult(
                param_name=factor_name,
                param_value=value,
                label=label,
                result=result,
            ))

        return report

    def _modify_config(self, config: StrategyConfig, param_name: str, value: Any) -> StrategyConfig:
        """Create a modified copy of config with one param changed."""
        d = config.to_dict()

        if param_name in ("entry_time", "exit_time", "sl_pct", "target_pct",
                          "sl_type", "target_type", "lot_size",
                          "vix_min", "vix_max", "dte_min", "dte_max"):
            d[param_name] = value
        elif param_name.startswith("leg_") and "_strike" in param_name:
            # e.g., "leg_1_strike" → modify legs[0].strike
            leg_idx = int(param_name.split("_")[1]) - 1
            if leg_idx < len(d["legs"]):
                d["legs"][leg_idx]["strike"] = value
        elif param_name.startswith("leg_") and "_sl_pct" in param_name:
            leg_idx = int(param_name.split("_")[1]) - 1
            if leg_idx < len(d["legs"]):
                d["legs"][leg_idx]["sl_pct"] = value
        else:
            # Try as a custom param
            d["params"][param_name] = value

        modified = StrategyConfig.from_dict(d)
        modified.name = f"{config.name} [{param_name}={value}]"
        return modified

    @staticmethod
    def print_comparison(report: OptimizationReport):
        """Print comparison table to console."""
        rows = report.to_comparison_table()
        if not rows:
            print("No results to compare.")
            return

        print(f"\nOptimization: {report.param_name}")
        print(f"Strategy: {report.base_config.name}")
        print("-" * 120)
        print(f"{'Value':<12} {'Trades':>7} {'WinRate':>8} {'GrossPnL':>12} {'Costs':>10} {'NetPnL':>12} {'MaxDD':>10} {'AvgDaily':>10} {'Sharpe':>8} {'Skip':>5}")
        print("-" * 120)

        for r in rows:
            print(f"{str(r['value']):<12} {r['trades']:>7} {r['win_rate']:>7.1f}% "
                  f"Rs.{r['gross_pnl']:>10,.0f} Rs.{r['costs']:>8,.0f} "
                  f"Rs.{r['net_pnl']:>10,.0f} Rs.{r['max_dd']:>8,.0f} "
                  f"Rs.{r['avg_daily']:>8,.0f} {r['sharpe']:>7.2f} {r['skipped']:>5}")

        best = report.best_by_pnl()
        if best:
            print(f"\nBest by Net P&L: {best.param_name}={best.param_value} -> Rs.{best.result.total_pnl:,.0f}")


# =========================================================================
# Demo
# =========================================================================

if __name__ == "__main__":
    from strategy.strategy_config import LegConfig

    print("=" * 60)
    print("PARAMETER OPTIMIZER DEMO")
    print("=" * 60)

    config = StrategyConfig(
        name="ATM Straddle Sell",
        legs=[
            LegConfig("SELL", "ATM", "CE"),
            LegConfig("SELL", "ATM", "PE"),
        ],
        entry_time="09:20",
        exit_time="15:15",
        sl_pct=25.0,
        sl_type="hard",
    )

    optimizer = ParameterOptimizer()

    print("\n--- Sweeping SL % ---")
    report = optimizer.sweep(
        config,
        param_name="sl_pct",
        values=[15, 20, 25, 30, 35],
        from_date=date(2024, 1, 1),
        to_date=date(2024, 3, 31),
        progress_callback=lambda i, n, l: print(f"  [{i}/{n}] {l}..."),
    )
    optimizer.print_comparison(report)
