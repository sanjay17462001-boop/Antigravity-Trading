"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import {
    Play,
    Download,
    ArrowUpRight,
    ArrowDownRight,
    Calendar,
    TrendingUp,
    TrendingDown,
    BarChart3,
} from "lucide-react";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
} from "recharts";

/* ---------- Mock backtest data ---------- */
const equityCurve = Array.from({ length: 120 }, (_, i) => {
    const base = 1000000;
    const trend = i * 800;
    const noise = Math.sin(i * 0.2) * 18000 + Math.cos(i * 0.08) * 12000;
    const drawdown = i > 50 && i < 70 ? -(i - 50) * 1500 : 0;
    return {
        candle: i + 1,
        equity: Math.round(base + trend + noise + drawdown),
        benchmark: Math.round(base + i * 400),
    };
});

const metrics = [
    { label: "Total Return", value: "+12.4%", positive: true },
    { label: "Sharpe Ratio", value: "1.82", positive: true },
    { label: "Max Drawdown", value: "-6.3%", positive: false },
    { label: "Total Trades", value: "439", positive: null },
    { label: "Win Rate", value: "62.8%", positive: true },
    { label: "Profit Factor", value: "1.64", positive: true },
    { label: "Avg Win", value: "Rs.3,240", positive: true },
    { label: "Avg Loss", value: "Rs.1,980", positive: false },
    { label: "Sortino Ratio", value: "2.14", positive: true },
    { label: "Calmar Ratio", value: "1.97", positive: true },
    { label: "Best Day", value: "+Rs.14,200", positive: true },
    { label: "Worst Day", value: "-Rs.8,700", positive: false },
];

const winLoss = [
    { name: "Wins", value: 276, color: "#22c55e" },
    { name: "Losses", value: 163, color: "#ef4444" },
];

const monthlyReturns = [
    { month: "Dec 25", ret: 2.1 },
    { month: "Jan 26", ret: -1.3 },
    { month: "Feb 26", ret: 3.8 },
];

export default function BacktestPage() {
    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Backtest Results" />

                <div className="page-content fade-in">
                    {/* Controls */}
                    <div style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "var(--space-xl)",
                    }}>
                        <div>
                            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
                                MA Crossover — NIFTY 5min
                            </h3>
                            <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--text-muted)" }}>
                                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                    <Calendar style={{ width: 12, height: 12 }} />
                                    Dec 2025 — Feb 2026
                                </span>
                                <span>21,385 candles</span>
                                <span>439 trades</span>
                            </div>
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <button className="btn btn-secondary">
                                <Download style={{ width: 14, height: 14 }} />
                                Export
                            </button>
                            <button className="btn btn-primary">
                                <Play style={{ width: 14, height: 14 }} />
                                Re-run
                            </button>
                        </div>
                    </div>

                    {/* Metric cards grid */}
                    <div className="stagger" style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(6, 1fr)",
                        gap: "var(--space-sm)",
                        marginBottom: "var(--space-xl)",
                    }}>
                        {metrics.map((m) => (
                            <div key={m.label} style={{
                                background: "var(--gradient-card)",
                                border: "1px solid var(--border-subtle)",
                                borderRadius: "var(--radius-sm)",
                                padding: "12px 14px",
                            }}>
                                <div style={{
                                    fontSize: 10,
                                    fontWeight: 600,
                                    textTransform: "uppercase" as const,
                                    letterSpacing: "0.5px",
                                    color: "var(--text-dim)",
                                    marginBottom: 4,
                                }}>
                                    {m.label}
                                </div>
                                <div style={{
                                    fontSize: 16,
                                    fontWeight: 700,
                                    fontFamily: "'JetBrains Mono'",
                                    color: m.positive === true ? "var(--green-bright)" :
                                        m.positive === false ? "var(--red-bright)" : "var(--text-primary)",
                                }}>
                                    {m.value}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Charts row */}
                    <div className="row" style={{ marginBottom: "var(--space-xl)" }}>
                        {/* Equity curve */}
                        <div className="card flex-2">
                            <div className="card-header">
                                <span className="card-title">Equity Curve vs Benchmark</span>
                                <div style={{ display: "flex", gap: 16, fontSize: 11 }}>
                                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                        <span style={{ width: 8, height: 3, background: "#38bdf8", borderRadius: 2 }} />
                                        Strategy
                                    </span>
                                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                        <span style={{ width: 8, height: 3, background: "#64748b", borderRadius: 2 }} />
                                        Buy &amp; Hold
                                    </span>
                                </div>
                            </div>
                            <div style={{ height: 320 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={equityCurve}>
                                        <defs>
                                            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.2} />
                                                <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                        <XAxis
                                            dataKey="candle"
                                            tick={{ fontSize: 10, fill: "#64748b" }}
                                            tickLine={false}
                                            axisLine={false}
                                            interval={19}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: "#64748b" }}
                                            tickLine={false}
                                            axisLine={false}
                                            tickFormatter={(v: number) => `${(v / 100000).toFixed(1)}L`}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                background: "var(--bg-elevated)",
                                                border: "1px solid var(--border-default)",
                                                borderRadius: "var(--radius-sm)",
                                                fontSize: 12,
                                            }}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="benchmark"
                                            stroke="#64748b"
                                            strokeWidth={1}
                                            strokeDasharray="4 4"
                                            fill="none"
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="equity"
                                            stroke="#38bdf8"
                                            strokeWidth={2}
                                            fill="url(#eqGrad)"
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Win/Loss + Monthly */}
                        <div className="flex-1" style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                            {/* Win/Loss donut */}
                            <div className="card">
                                <div className="card-header">
                                    <span className="card-title">Win / Loss</span>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                                    <div style={{ width: 120, height: 120 }}>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie
                                                    data={winLoss}
                                                    dataKey="value"
                                                    innerRadius={35}
                                                    outerRadius={55}
                                                    paddingAngle={3}
                                                    startAngle={90}
                                                    endAngle={-270}
                                                >
                                                    {winLoss.map((entry) => (
                                                        <Cell key={entry.name} fill={entry.color} />
                                                    ))}
                                                </Pie>
                                            </PieChart>
                                        </ResponsiveContainer>
                                    </div>
                                    <div style={{ fontSize: 13 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                                            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#22c55e" }} />
                                            <span>276 Wins</span>
                                            <span className="text-mono text-green" style={{ marginLeft: "auto" }}>62.8%</span>
                                        </div>
                                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444" }} />
                                            <span>163 Losses</span>
                                            <span className="text-mono text-red" style={{ marginLeft: "auto" }}>37.2%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Monthly returns */}
                            <div className="card">
                                <div className="card-header">
                                    <span className="card-title">Monthly Returns</span>
                                </div>
                                {monthlyReturns.map((m) => (
                                    <div key={m.month} style={{
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "space-between",
                                        padding: "8px 0",
                                        borderBottom: "1px solid var(--border-subtle)",
                                        fontSize: 13,
                                    }}>
                                        <span style={{ color: "var(--text-secondary)" }}>{m.month}</span>
                                        <span className={`text-mono ${m.ret >= 0 ? "text-green" : "text-red"}`}
                                            style={{ display: "flex", alignItems: "center", gap: 4 }}
                                        >
                                            {m.ret >= 0 ? (
                                                <ArrowUpRight style={{ width: 14, height: 14 }} />
                                            ) : (
                                                <ArrowDownRight style={{ width: 14, height: 14 }} />
                                            )}
                                            {m.ret >= 0 ? "+" : ""}{m.ret}%
                                        </span>
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
