"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Target,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";

/* ---------- Mock data ---------- */
const equityData = Array.from({ length: 60 }, (_, i) => {
  const base = 1000000;
  const noise = Math.sin(i * 0.3) * 25000 + Math.cos(i * 0.15) * 15000;
  const trend = i * 1200;
  return {
    day: `Day ${i + 1}`,
    equity: Math.round(base + trend + noise),
  };
});

const recentTrades = [
  { id: "T001", symbol: "NIFTY 25500 CE", side: "BUY", qty: 50, entry: 245.8, exit: 278.5, pnl: 1635, time: "14:32" },
  { id: "T002", symbol: "BANKNIFTY 61000 PE", side: "SELL", qty: 15, entry: 320.0, exit: 295.2, pnl: 372, time: "13:45" },
  { id: "T003", symbol: "NIFTY FUT MAR", side: "BUY", qty: 50, entry: 25410.5, exit: 25380.0, pnl: -1525, time: "12:20" },
  { id: "T004", symbol: "NIFTY 25400 PE", side: "SELL", qty: 50, entry: 180.4, exit: 155.6, pnl: 1240, time: "11:15" },
  { id: "T005", symbol: "BANKNIFTY 60800 CE", side: "BUY", qty: 15, entry: 410.0, exit: 445.3, pnl: 529.5, time: "10:30" },
];

const dailyPnl = [
  { date: "Mon", pnl: 4200 },
  { date: "Tue", pnl: -1800 },
  { date: "Wed", pnl: 6100 },
  { date: "Thu", pnl: 2400 },
  { date: "Fri", pnl: -900 },
  { date: "Sat", pnl: 0 },
  { date: "Sun", pnl: 0 },
];

const strategies = [
  { name: "MA Crossover", status: "Paper", winRate: "62%", pnl: "+Rs.24,350", trades: 47 },
  { name: "Iron Condor VIX", status: "Active", winRate: "78%", pnl: "+Rs.41,200", trades: 23 },
  { name: "Breakout Nifty", status: "Stopped", winRate: "45%", pnl: "-Rs.8,120", trades: 31 },
];

/* ---------- Custom tooltip ---------- */
function EquityTooltip({ active, payload }: { active?: boolean; payload?: Array<{ value: number }> }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-elevated)",
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-sm)",
      padding: "8px 12px",
      fontSize: 12,
    }}>
      <div style={{ color: "var(--text-muted)", marginBottom: 2 }}>Portfolio Value</div>
      <div style={{ color: "var(--accent)", fontWeight: 700, fontFamily: "'JetBrains Mono'" }}>
        Rs. {payload[0].value.toLocaleString("en-IN")}
      </div>
    </div>
  );
}

/* ---------- Page ---------- */
export default function DashboardPage() {
  const totalPnl = recentTrades.reduce((sum, t) => sum + t.pnl, 0);
  const currentEquity = equityData[equityData.length - 1].equity;

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Header title="Dashboard" />

        <div className="page-content fade-in">
          {/* Metric cards */}
          <div className="metric-grid stagger" style={{ marginBottom: "var(--space-xl)" }}>
            <div className="metric-card">
              <div className="metric-label">Portfolio Value</div>
              <div className="metric-value">
                Rs.{currentEquity.toLocaleString("en-IN")}
              </div>
              <div className="metric-change positive">
                <ArrowUpRight style={{ width: 12, height: 12 }} />
                +7.2% all time
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Today&#39;s P&amp;L</div>
              <div className="metric-value" style={{ color: totalPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>
                {totalPnl >= 0 ? "+" : ""}Rs.{Math.abs(totalPnl).toLocaleString("en-IN")}
              </div>
              <div className={`metric-change ${totalPnl >= 0 ? "positive" : "negative"}`}>
                {totalPnl >= 0 ? <TrendingUp style={{ width: 12, height: 12 }} /> : <TrendingDown style={{ width: 12, height: 12 }} />}
                5 trades today
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Win Rate</div>
              <div className="metric-value">68.4%</div>
              <div className="metric-change positive">
                <Target style={{ width: 12, height: 12 }} />
                Above target (60%)
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Active Strategies</div>
              <div className="metric-value">3</div>
              <div className="metric-change" style={{
                color: "var(--accent)",
                background: "var(--accent-dim)",
              }}>
                <BarChart3 style={{ width: 12, height: 12 }} />
                1 live, 1 paper, 1 stopped
              </div>
            </div>
          </div>

          {/* Charts row */}
          <div className="row" style={{ marginBottom: "var(--space-xl)" }}>
            {/* Equity curve */}
            <div className="card flex-2">
              <div className="card-header">
                <span className="card-title">Equity Curve</span>
                <div style={{ display: "flex", gap: 8 }}>
                  {["1W", "1M", "3M", "ALL"].map((period) => (
                    <button
                      key={period}
                      className="btn btn-sm btn-secondary"
                      style={{
                        background: period === "1M" ? "var(--accent-dim)" : undefined,
                        color: period === "1M" ? "var(--accent)" : undefined,
                        borderColor: period === "1M" ? "var(--accent)" : undefined,
                      }}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityData}>
                    <defs>
                      <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 10, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                      interval={9}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `${(v / 100000).toFixed(1)}L`}
                    />
                    <Tooltip content={<EquityTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#38bdf8"
                      strokeWidth={2}
                      fill="url(#equityGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Daily P&L */}
            <div className="card flex-1">
              <div className="card-header">
                <span className="card-title">Daily P&amp;L</span>
                <span className="tag tag-green">This Week</span>
              </div>
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dailyPnl}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`}
                    />
                    <Bar
                      dataKey="pnl"
                      radius={[4, 4, 0, 0]}
                    >
                      {dailyPnl.map((entry, index) => (
                        <Cell key={`pnl-${index}`} fill={entry.pnl >= 0 ? "#22c55e" : "#ef4444"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Bottom row */}
          <div className="row">
            {/* Recent trades */}
            <div className="card flex-2">
              <div className="card-header">
                <span className="card-title">Recent Trades</span>
                <button className="btn btn-sm btn-secondary">View All</button>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>Side</th>
                      <th>Qty</th>
                      <th>Entry</th>
                      <th>Exit</th>
                      <th>P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentTrades.map((trade) => (
                      <tr key={trade.id}>
                        <td>
                          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <Clock style={{ width: 12, height: 12, color: "var(--text-dim)" }} />
                            <span className="text-mono">{trade.time}</span>
                          </span>
                        </td>
                        <td style={{ color: "var(--text-primary)", fontWeight: 500 }}>
                          {trade.symbol}
                        </td>
                        <td>
                          <span className={`tag ${trade.side === "BUY" ? "tag-green" : "tag-red"}`}>
                            {trade.side}
                          </span>
                        </td>
                        <td className="text-mono">{trade.qty}</td>
                        <td className="text-mono">{trade.entry.toLocaleString("en-IN")}</td>
                        <td className="text-mono">{trade.exit.toLocaleString("en-IN")}</td>
                        <td>
                          <span className={`text-mono ${trade.pnl >= 0 ? "text-green" : "text-red"}`}
                            style={{ display: "flex", alignItems: "center", gap: 4 }}
                          >
                            {trade.pnl >= 0 ? (
                              <ArrowUpRight style={{ width: 14, height: 14 }} />
                            ) : (
                              <ArrowDownRight style={{ width: 14, height: 14 }} />
                            )}
                            {trade.pnl >= 0 ? "+" : ""}Rs.{Math.abs(trade.pnl).toLocaleString("en-IN")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Strategies */}
            <div className="card flex-1">
              <div className="card-header">
                <span className="card-title">Strategies</span>
                <button className="btn btn-sm btn-primary">+ New</button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {strategies.map((strat) => (
                  <div
                    key={strat.name}
                    style={{
                      background: "var(--bg-tertiary)",
                      borderRadius: "var(--radius-sm)",
                      padding: "12px 16px",
                      border: "1px solid var(--border-subtle)",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 8,
                    }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{strat.name}</span>
                      <span className={`tag ${strat.status === "Active" ? "tag-green" :
                        strat.status === "Paper" ? "tag-accent" : "tag-red"
                        }`}>
                        {strat.status}
                      </span>
                    </div>
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: 12,
                      color: "var(--text-muted)",
                    }}>
                      <span>Win: {strat.winRate}</span>
                      <span className="text-mono" style={{
                        color: strat.pnl.startsWith("+") ? "var(--green-bright)" : "var(--red-bright)"
                      }}>
                        {strat.pnl}
                      </span>
                      <span>{strat.trades} trades</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
