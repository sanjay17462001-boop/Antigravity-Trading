"""
Antigravity Trading — Report Generator
=======================================
Generates rich HTML reports for backtest results, trading sessions,
and strategy comparisons. Reports can be opened in any browser.
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


# =============================================================================
# Report Data Types
# =============================================================================

class ReportData:
    """Container for report data."""

    def __init__(
        self,
        title: str = "Antigravity Trading Report",
        strategy_name: str = "Unknown",
        instrument: str = "NIFTY 50",
        timeframe: str = "5min",
        date_range: str = "",
        metrics: Optional[Dict[str, Any]] = None,
        equity_curve: Optional[List[Dict]] = None,
        trades: Optional[List[Dict]] = None,
        monthly_returns: Optional[List[Dict]] = None,
        drawdown_series: Optional[List[Dict]] = None,
    ):
        self.title = title
        self.strategy_name = strategy_name
        self.instrument = instrument
        self.timeframe = timeframe
        self.date_range = date_range
        self.metrics = metrics or {}
        self.equity_curve = equity_curve or []
        self.trades = trades or []
        self.monthly_returns = monthly_returns or []
        self.drawdown_series = drawdown_series or []
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")


# =============================================================================
# HTML Template Engine
# =============================================================================

_CSS = """
:root {
  --bg: #0a0e17;
  --bg2: #111827;
  --bg3: #1a2236;
  --card: #151d2e;
  --border: rgba(255,255,255,0.08);
  --text: #f1f5f9;
  --text2: #94a3b8;
  --text3: #64748b;
  --accent: #38bdf8;
  --green: #22c55e;
  --red: #ef4444;
  --yellow: #eab308;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', -apple-system, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  line-height: 1.5;
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
}
.header {
  text-align: center;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
}
.header h1 {
  font-size: 24px;
  font-weight: 800;
  background: linear-gradient(135deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}
.header .subtitle {
  color: var(--text3);
  font-size: 13px;
}
.section { margin-bottom: 32px; }
.section-title {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text3);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.metric-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.metric-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text3);
  margin-bottom: 4px;
}
.metric-value {
  font-size: 20px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}
.positive { color: var(--green); }
.negative { color: var(--red); }
.neutral { color: var(--text); }
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--card);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}
th {
  padding: 10px 14px;
  text-align: left;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text3);
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
}
td {
  padding: 8px 14px;
  font-size: 12px;
  color: var(--text2);
  border-bottom: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(255,255,255,0.02); }
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}
.tag-green { background: rgba(34,197,94,0.12); color: var(--green); }
.tag-red { background: rgba(239,68,68,0.12); color: var(--red); }
canvas { width: 100% !important; border-radius: 8px; }
.chart-container {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
}
.row { display: flex; gap: 16px; }
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }
.footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  color: var(--text3);
  font-size: 11px;
}
@media print {
  body { background: white; color: #1a1a1a; }
  .metric-card { border: 1px solid #ddd; }
  table { border: 1px solid #ddd; }
}
"""


def _metric_html(label: str, value: str, css_class: str = "neutral") -> str:
    return f"""<div class="metric-card">
  <div class="metric-label">{label}</div>
  <div class="metric-value {css_class}">{value}</div>
</div>"""


def _format_pnl(value: float) -> tuple:
    """Return (formatted_string, css_class)."""
    if value >= 0:
        return f"+₹{value:,.0f}", "positive"
    else:
        return f"-₹{abs(value):,.0f}", "negative"


def _format_pct(value: float) -> tuple:
    if value >= 0:
        return f"+{value:.2f}%", "positive"
    else:
        return f"{value:.2f}%", "negative"


# =============================================================================
# Chart.js Script Generation
# =============================================================================

def _equity_chart_js(data: List[Dict]) -> str:
    labels = json.dumps([d.get("date", d.get("day", str(i))) for i, d in enumerate(data)])
    values = json.dumps([d.get("equity", d.get("value", 0)) for d in data])
    benchmark = json.dumps([d.get("benchmark", None) for d in data])
    has_benchmark = any(d.get("benchmark") for d in data)

    datasets = f"""{{
        label: 'Strategy',
        data: {values},
        borderColor: '#38bdf8',
        backgroundColor: 'rgba(56,189,248,0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
    }}"""

    if has_benchmark:
        datasets += f""",{{
        label: 'Benchmark',
        data: {benchmark},
        borderColor: '#64748b',
        borderWidth: 1,
        borderDash: [5, 5],
        fill: false,
        tension: 0.3,
        pointRadius: 0,
    }}"""

    return f"""
new Chart(document.getElementById('equityChart'), {{
    type: 'line',
    data: {{
        labels: {labels},
        datasets: [{datasets}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: {str(has_benchmark).lower()}, labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
            x: {{ ticks: {{ color: '#64748b', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
            y: {{ ticks: {{ color: '#64748b', callback: v => (v/100000).toFixed(1)+'L' }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
        }}
    }}
}});"""


def _drawdown_chart_js(data: List[Dict]) -> str:
    labels = json.dumps([d.get("date", str(i)) for i, d in enumerate(data)])
    values = json.dumps([d.get("drawdown", 0) for d in data])

    return f"""
new Chart(document.getElementById('drawdownChart'), {{
    type: 'line',
    data: {{
        labels: {labels},
        datasets: [{{
            label: 'Drawdown %',
            data: {values},
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239,68,68,0.1)',
            borderWidth: 1.5,
            fill: true,
            tension: 0.3,
            pointRadius: 0,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ ticks: {{ color: '#64748b', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
            y: {{ ticks: {{ color: '#64748b', callback: v => v.toFixed(1)+'%' }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
        }}
    }}
}});"""


# =============================================================================
# HTML Report Builder
# =============================================================================

def generate_report(data: ReportData, output_path: Optional[str] = None) -> str:
    """
    Generate a complete HTML report from ReportData.

    Args:
        data: ReportData with metrics, equity curve, trades, etc.
        output_path: Where to save the HTML file. Auto-generated if None.

    Returns:
        Path to the generated HTML file.
    """

    # --- Metrics section ---
    metrics_html = ""
    metric_order = [
        ("total_return_pct", "Total Return", "pct"),
        ("sharpe_ratio", "Sharpe Ratio", "num"),
        ("max_drawdown_pct", "Max Drawdown", "pct_neg"),
        ("total_trades", "Total Trades", "int"),
        ("win_rate_pct", "Win Rate", "pct"),
        ("profit_factor", "Profit Factor", "num"),
        ("avg_win", "Avg Win", "money"),
        ("avg_loss", "Avg Loss", "money_neg"),
        ("sortino_ratio", "Sortino Ratio", "num"),
        ("calmar_ratio", "Calmar Ratio", "num"),
        ("best_trade", "Best Trade", "money"),
        ("worst_trade", "Worst Trade", "money_neg"),
    ]

    for key, label, fmt in metric_order:
        val = data.metrics.get(key)
        if val is None:
            continue
        if fmt == "pct":
            text, cls = _format_pct(val)
        elif fmt == "pct_neg":
            text = f"{val:.2f}%"
            cls = "negative" if val < 0 else "positive"
        elif fmt == "money":
            text, cls = _format_pnl(val)
        elif fmt == "money_neg":
            text = f"₹{abs(val):,.0f}"
            cls = "negative"
        elif fmt == "int":
            text, cls = str(int(val)), "neutral"
        else:
            text = f"{val:.2f}"
            cls = "positive" if val > 1 else "negative" if val < 1 else "neutral"
        metrics_html += _metric_html(label, text, cls)

    # --- Trades table ---
    trades_html = ""
    if data.trades:
        rows = ""
        for t in data.trades[:50]:  # limit to 50
            side = t.get("side", "BUY")
            side_tag = f'<span class="tag tag-{"green" if side == "BUY" else "red"}">{side}</span>'
            pnl = t.get("pnl", 0)
            pnl_str, pnl_cls = _format_pnl(pnl)
            rows += f"""<tr>
              <td>{t.get('date', '')}</td>
              <td style="color:var(--text);font-weight:500">{t.get('symbol', '')}</td>
              <td>{side_tag}</td>
              <td>{t.get('qty', '')}</td>
              <td>{t.get('entry_price', '')}</td>
              <td>{t.get('exit_price', '')}</td>
              <td class="{pnl_cls}">{pnl_str}</td>
            </tr>"""

        trades_html = f"""
        <div class="section">
          <div class="section-title">Trade Log ({len(data.trades)} trades)</div>
          <table>
            <thead><tr><th>Date</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&L</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    # --- Charts ---
    chart_scripts = ""
    equity_chart_html = ""
    drawdown_chart_html = ""

    if data.equity_curve:
        equity_chart_html = f"""
        <div class="section">
          <div class="section-title">Equity Curve</div>
          <div class="chart-container">
            <canvas id="equityChart" height="100"></canvas>
          </div>
        </div>"""
        chart_scripts += _equity_chart_js(data.equity_curve)

    if data.drawdown_series:
        drawdown_chart_html = f"""
        <div class="section">
          <div class="section-title">Drawdown</div>
          <div class="chart-container">
            <canvas id="drawdownChart" height="60"></canvas>
          </div>
        </div>"""
        chart_scripts += _drawdown_chart_js(data.drawdown_series)

    # --- Monthly returns ---
    monthly_html = ""
    if data.monthly_returns:
        m_rows = ""
        for m in data.monthly_returns:
            ret = m.get("return_pct", 0)
            ret_str, ret_cls = _format_pct(ret)
            m_rows += f"""<tr>
              <td>{m.get('month', '')}</td>
              <td>{m.get('trades', '')}</td>
              <td class="{ret_cls}">{ret_str}</td>
            </tr>"""
        monthly_html = f"""
        <div class="section">
          <div class="section-title">Monthly Returns</div>
          <table>
            <thead><tr><th>Month</th><th>Trades</th><th>Return</th></tr></thead>
            <tbody>{m_rows}</tbody>
          </table>
        </div>"""

    # --- Assemble HTML ---
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.title}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <style>{_CSS}</style>
</head>
<body>
  <div class="header">
    <h1>{data.title}</h1>
    <div class="subtitle">
      {data.strategy_name} &middot; {data.instrument} &middot; {data.timeframe}
      {f' &middot; {data.date_range}' if data.date_range else ''}
    </div>
    <div class="subtitle" style="margin-top:4px">Generated: {data.generated_at}</div>
  </div>

  <div class="section">
    <div class="section-title">Performance Summary</div>
    <div class="metrics-grid">{metrics_html}</div>
  </div>

  {equity_chart_html}
  {drawdown_chart_html}
  {monthly_html}
  {trades_html}

  <div class="footer">
    Antigravity Trading Platform &middot; Report generated automatically &middot; {data.generated_at}
  </div>

  <script>{chart_scripts}</script>
</body>
</html>"""

    # Save
    if output_path is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(reports_dir / f"report_{data.strategy_name.replace(' ', '_')}_{timestamp}.html")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# =============================================================================
# Demo / Self-test
# =============================================================================

if __name__ == "__main__":
    import math

    print("Generating demo backtest report...")

    # Simulate equity curve
    equity = []
    base = 1000000
    for i in range(120):
        val = base + i * 800 + math.sin(i * 0.2) * 18000
        dd = -(i - 50) * 1200 if 50 < i < 70 else 0
        equity.append({
            "date": f"Day {i+1}",
            "equity": round(val + dd),
            "benchmark": round(base + i * 400),
        })

    # Simulate drawdown
    drawdowns = []
    peak = equity[0]["equity"]
    for e in equity:
        peak = max(peak, e["equity"])
        dd_pct = ((e["equity"] - peak) / peak) * 100
        drawdowns.append({"date": e["date"], "drawdown": round(dd_pct, 2)})

    # Simulate trades
    trades = [
        {"date": "2026-01-15", "symbol": "NIFTY 25500 CE", "side": "BUY", "qty": 50, "entry_price": 228.60, "exit_price": 278.50, "pnl": 2495},
        {"date": "2026-01-16", "symbol": "NIFTY 25400 PE", "side": "SELL", "qty": 50, "entry_price": 180.40, "exit_price": 155.60, "pnl": 1240},
        {"date": "2026-01-17", "symbol": "BANKNIFTY 61000 CE", "side": "BUY", "qty": 15, "entry_price": 410.00, "exit_price": 445.30, "pnl": 529.5},
        {"date": "2026-01-18", "symbol": "NIFTY FUT MAR", "side": "BUY", "qty": 50, "entry_price": 25410.50, "exit_price": 25380.00, "pnl": -1525},
        {"date": "2026-01-20", "symbol": "NIFTY 25600 PE", "side": "SELL", "qty": 50, "entry_price": 195.20, "exit_price": 210.40, "pnl": -760},
    ]

    data = ReportData(
        title="Backtest Report — MA Crossover",
        strategy_name="MA Crossover",
        instrument="NIFTY 50",
        timeframe="5min",
        date_range="Dec 2025 — Feb 2026",
        metrics={
            "total_return_pct": 12.4,
            "sharpe_ratio": 1.82,
            "max_drawdown_pct": -6.3,
            "total_trades": 439,
            "win_rate_pct": 62.8,
            "profit_factor": 1.64,
            "avg_win": 3240,
            "avg_loss": 1980,
            "sortino_ratio": 2.14,
            "calmar_ratio": 1.97,
            "best_trade": 14200,
            "worst_trade": -8700,
        },
        equity_curve=equity,
        trades=trades,
        monthly_returns=[
            {"month": "Dec 2025", "trades": 142, "return_pct": 2.1},
            {"month": "Jan 2026", "trades": 168, "return_pct": -1.3},
            {"month": "Feb 2026", "trades": 129, "return_pct": 3.8},
        ],
        drawdown_series=drawdowns,
    )

    path = generate_report(data)
    print(f"Report saved: {path}")
    print("[OK] Report generator ready!")
