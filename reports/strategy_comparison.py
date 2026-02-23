"""
Antigravity Trading — Strategy Comparison
==========================================
Side-by-side comparison of multiple strategy backtest results.
Generates comparison tables, rankings, and HTML comparison reports.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import json

from reports.report_generator import ReportData, generate_report


@dataclass
class StrategyResult:
    """Single strategy's backtest results for comparison."""
    name: str
    instrument: str = "NIFTY 50"
    timeframe: str = "5min"
    date_range: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    equity_curve: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of comparing multiple strategies."""
    strategies: List[StrategyResult]
    rankings: Dict[str, List[str]] = field(default_factory=dict)
    best_overall: str = ""
    summary_table: List[Dict] = field(default_factory=list)


# =============================================================================
# Comparison Engine
# =============================================================================

# Metrics where higher is better
_HIGHER_BETTER = {
    "total_return_pct", "sharpe_ratio", "win_rate_pct", "profit_factor",
    "sortino_ratio", "calmar_ratio", "avg_win", "best_trade",
    "expectancy",
}

# Metrics where lower magnitude is better
_LOWER_BETTER = {
    "max_drawdown_pct", "avg_loss", "worst_trade",
}


def compare_strategies(strategies: List[StrategyResult]) -> ComparisonResult:
    """
    Compare multiple strategies and rank them across all metrics.

    Args:
        strategies: List of StrategyResult objects

    Returns:
        ComparisonResult with rankings and summary
    """
    if not strategies:
        raise ValueError("Need at least 1 strategy to compare")

    # Collect all metric keys
    all_keys: set = set()
    for strat in strategies:
        all_keys.update(strat.metrics.keys())

    # Rank each metric
    rankings: Dict[str, List[str]] = {}
    scores: Dict[str, float] = {s.name: 0 for s in strategies}

    for key in sorted(all_keys):
        # Get values for each strategy
        vals = []
        for s in strategies:
            val = s.metrics.get(key)
            if val is not None:
                vals.append((s.name, val))

        if not vals:
            continue

        # Sort
        if key in _HIGHER_BETTER:
            sorted_vals = sorted(vals, key=lambda x: x[1], reverse=True)
        elif key in _LOWER_BETTER:
            sorted_vals = sorted(vals, key=lambda x: abs(x[1]))
        else:
            sorted_vals = sorted(vals, key=lambda x: x[1], reverse=True)

        rankings[key] = [name for name, _ in sorted_vals]

        # Award points (1st = N points, 2nd = N-1, etc.)
        for rank, (name, _) in enumerate(sorted_vals):
            scores[name] += len(sorted_vals) - rank

    # Best overall
    best_overall = max(scores, key=lambda k: scores[k]) if scores else ""

    # Build summary table
    summary_table = []
    for strat in strategies:
        row = {
            "name": strat.name,
            "instrument": strat.instrument,
            "timeframe": strat.timeframe,
            "score": scores.get(strat.name, 0),
            "rank": 0,
        }
        row.update(strat.metrics)
        summary_table.append(row)

    # Assign ranks
    summary_table.sort(key=lambda x: x["score"], reverse=True)
    for i, row in enumerate(summary_table):
        row["rank"] = i + 1

    return ComparisonResult(
        strategies=strategies,
        rankings=rankings,
        best_overall=best_overall,
        summary_table=summary_table,
    )


# =============================================================================
# Console Output
# =============================================================================

def print_comparison(result: ComparisonResult) -> None:
    """Print comparison results to console."""
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON")
    print("=" * 80)

    # Summary table
    headers = ["Rank", "Strategy", "Return", "Sharpe", "MaxDD", "Win%", "PF", "Trades", "Score"]
    widths = [4, 20, 8, 7, 7, 6, 5, 6, 5]
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(f"\n{header_line}")
    print("-" * len(header_line))

    for row in result.summary_table:
        vals = [
            f"#{row['rank']}",
            row["name"][:20],
            f"{row.get('total_return_pct', 0):+.1f}%",
            f"{row.get('sharpe_ratio', 0):.2f}",
            f"{row.get('max_drawdown_pct', 0):.1f}%",
            f"{row.get('win_rate_pct', 0):.0f}%",
            f"{row.get('profit_factor', 0):.2f}",
            str(int(row.get("total_trades", 0))),
            f"{row['score']:.0f}",
        ]
        print(" | ".join(v.ljust(w) for v, w in zip(vals, widths)))

    print(f"\n* Best Overall: {result.best_overall}")

    # Per-metric rankings
    print(f"\n--- Metric Rankings ---")
    for key, names in sorted(result.rankings.items()):
        ranking_str = " > ".join(names)
        print(f"  {key:.<30s} {ranking_str}")


# =============================================================================
# HTML Comparison Report
# =============================================================================

def generate_comparison_report(
    result: ComparisonResult,
    output_path: Optional[str] = None,
) -> str:
    """Generate an HTML comparison report."""

    # Build metrics comparison table
    compare_metrics = [
        "total_return_pct", "sharpe_ratio", "max_drawdown_pct",
        "win_rate_pct", "profit_factor", "total_trades",
        "avg_win", "avg_loss", "sortino_ratio", "calmar_ratio",
    ]
    metric_labels = {
        "total_return_pct": "Total Return",
        "sharpe_ratio": "Sharpe Ratio",
        "max_drawdown_pct": "Max Drawdown",
        "win_rate_pct": "Win Rate",
        "profit_factor": "Profit Factor",
        "total_trades": "Total Trades",
        "avg_win": "Avg Win",
        "avg_loss": "Avg Loss",
        "sortino_ratio": "Sortino Ratio",
        "calmar_ratio": "Calmar Ratio",
    }

    # Table header
    strat_names = [s.name for s in result.strategies]
    th_cols = "".join(f"<th>{name}</th>" for name in strat_names)

    # Table rows
    rows_html = ""
    for key in compare_metrics:
        label = metric_labels.get(key, key)
        ranking = result.rankings.get(key, [])
        cells = ""
        for strat in result.strategies:
            val = strat.metrics.get(key)
            if val is None:
                cells += "<td>—</td>"
                continue

            is_best = ranking and ranking[0] == strat.name
            style = ' style="color:var(--accent);font-weight:700"' if is_best else ""

            if "pct" in key or "rate" in key:
                text = f"{val:+.2f}%" if val >= 0 else f"{val:.2f}%"
            elif key in ("avg_win", "avg_loss", "best_trade", "worst_trade"):
                text = f"₹{abs(val):,.0f}"
            elif key == "total_trades":
                text = str(int(val))
            else:
                text = f"{val:.2f}"

            cells += f"<td class=\"text-mono\"{style}>{text}</td>"

        rows_html += f"<tr><td style='color:var(--text2)'>{label}</td>{cells}</tr>"

    # Equity curves chart data
    chart_js = ""
    if any(s.equity_curve for s in result.strategies):
        colors = ["#38bdf8", "#a78bfa", "#22c55e", "#eab308", "#f87171"]
        datasets = []
        max_len = max((len(s.equity_curve) for s in result.strategies), default=0)
        labels = json.dumps([f"Day {i+1}" for i in range(max_len)])

        for i, strat in enumerate(result.strategies):
            values = json.dumps([e.get("equity", 0) for e in strat.equity_curve])
            color = colors[i % len(colors)]
            datasets.append(f"""{{
                label: '{strat.name}',
                data: {values},
                borderColor: '{color}',
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointRadius: 0,
            }}""")

        chart_js = f"""
new Chart(document.getElementById('compChart'), {{
    type: 'line',
    data: {{ labels: {labels}, datasets: [{','.join(datasets)}] }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
            x: {{ ticks: {{ color: '#64748b', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
            y: {{ ticks: {{ color: '#64748b', callback: v => (v/100000).toFixed(1)+'L' }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
        }}
    }}
}});"""

    # Overall ranking
    ranking_html = ""
    for row in result.summary_table:
        medal = "🥇" if row["rank"] == 1 else "🥈" if row["rank"] == 2 else "🥉" if row["rank"] == 3 else f"#{row['rank']}"
        ranking_html += f"""<div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
            background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px">
            <span style="font-size:20px">{medal}</span>
            <span style="font-weight:700;flex:1">{row['name']}</span>
            <span style="color:var(--text3)">Score: {row['score']:.0f}</span>
        </div>"""

    css = """
:root{--bg:#0a0e17;--bg2:#111827;--bg3:#1a2236;--card:#151d2e;--border:rgba(255,255,255,0.08);--text:#f1f5f9;--text2:#94a3b8;--text3:#64748b;--accent:#38bdf8;--green:#22c55e;--red:#ef4444}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:13px;line-height:1.5;padding:32px;max-width:1200px;margin:0 auto}
.header{text-align:center;margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid var(--border)}
.header h1{font-size:24px;font-weight:800;background:linear-gradient(135deg,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.header .subtitle{color:var(--text3);font-size:13px}
.section{margin-bottom:32px}
.section-title{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text3);margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border)}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:8px;overflow:hidden;border:1px solid var(--border)}
th{padding:10px 14px;text-align:left;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text3);background:var(--bg3);border-bottom:1px solid var(--border)}
td{padding:8px 14px;font-size:12px;color:var(--text2);border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:none}
.text-mono{font-family:'JetBrains Mono',monospace}
.chart-container{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:20px}
canvas{width:100%!important;border-radius:8px}
.row{display:flex;gap:16px}
.flex-1{flex:1}.flex-2{flex:2}
.footer{text-align:center;padding-top:24px;border-top:1px solid var(--border);color:var(--text3);font-size:11px}
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Strategy Comparison</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>{css}</style>
</head>
<body>
<div class="header">
  <h1>Strategy Comparison Report</h1>
  <div class="subtitle">{len(result.strategies)} strategies compared &middot; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}</div>
</div>

<div class="section">
  <div class="section-title">Overall Ranking</div>
  {ranking_html}
</div>

<div class="section">
  <div class="section-title">Metrics Comparison</div>
  <table>
    <thead><tr><th>Metric</th>{th_cols}</tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>

{"<div class='section'><div class='section-title'>Equity Curves</div><div class='chart-container'><canvas id='compChart' height='100'></canvas></div></div>" if chart_js else ""}

<div class="footer">Antigravity Trading Platform &middot; Strategy Comparison Report</div>
<script>{chart_js}</script>
</body></html>"""

    if output_path is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(reports_dir / f"comparison_{ts}.html")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    import math

    print("Running strategy comparison demo...")

    # Create 3 mock strategies
    def make_equity(base, trend, volatility, length=100):
        return [{"date": f"Day {i+1}", "equity": round(base + i * trend + math.sin(i * 0.2) * volatility)}
                for i in range(length)]

    strats = [
        StrategyResult("MA Crossover", metrics={
            "total_return_pct": 12.4, "sharpe_ratio": 1.82, "max_drawdown_pct": -6.3,
            "win_rate_pct": 62.8, "profit_factor": 1.64, "total_trades": 439,
            "avg_win": 3240, "avg_loss": 1980, "sortino_ratio": 2.14, "calmar_ratio": 1.97,
        }, equity_curve=make_equity(1000000, 800, 18000)),
        StrategyResult("Iron Condor VIX", metrics={
            "total_return_pct": 18.2, "sharpe_ratio": 2.45, "max_drawdown_pct": -3.1,
            "win_rate_pct": 78.3, "profit_factor": 2.12, "total_trades": 156,
            "avg_win": 4120, "avg_loss": 2450, "sortino_ratio": 3.12, "calmar_ratio": 5.87,
        }, equity_curve=make_equity(1000000, 1200, 12000)),
        StrategyResult("ORB Breakout", metrics={
            "total_return_pct": -4.8, "sharpe_ratio": 0.62, "max_drawdown_pct": -12.4,
            "win_rate_pct": 45.2, "profit_factor": 0.88, "total_trades": 312,
            "avg_win": 2180, "avg_loss": 2400, "sortino_ratio": 0.45, "calmar_ratio": 0.39,
        }, equity_curve=make_equity(1000000, -300, 22000)),
    ]

    result = compare_strategies(strats)
    print_comparison(result)

    path = generate_comparison_report(result)
    print(f"\nComparison report saved: {path}")
    print("[OK] Strategy comparison ready!")
