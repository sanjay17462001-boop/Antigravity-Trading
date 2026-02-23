"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { ArrowUpRight, ArrowDownRight, Clock, DollarSign, AlertCircle } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const positions = [
    { symbol: "NIFTY 25500 CE", type: "OPTIONS", side: "LONG", qty: 50, avgPrice: 218.40, ltp: 245.80, pnl: 1370, pnlPct: 12.53, mtm: 12290 },
    { symbol: "NIFTY MAR FUT", type: "FUTURES", side: "SHORT", qty: 50, avgPrice: 25580.00, ltp: 25512.30, pnl: 3385, pnlPct: 0.26, mtm: 127561.5 },
    { symbol: "BANKNIFTY 60800 CE", type: "OPTIONS", side: "LONG", qty: 15, avgPrice: 380.00, ltp: 420.50, pnl: 607.5, pnlPct: 10.66, mtm: 6307.5 },
    { symbol: "NIFTY 25400 PE", type: "OPTIONS", side: "SHORT", qty: 50, avgPrice: 180.40, ltp: 135.60, pnl: 2240, pnlPct: 24.83, mtm: 6780 },
];

const closedToday = [
    { symbol: "NIFTY 25600 CE", side: "LONG", qty: 50, entry: 165.20, exit: 186.40, pnl: 1060, exitTime: "14:32" },
    { symbol: "BANKNIFTY 61000 PE", side: "SHORT", qty: 15, entry: 320.00, exit: 295.20, pnl: 372, exitTime: "13:45" },
];

const pnlTimeline = Array.from({ length: 24 }, (_, i) => ({
    time: `${9 + Math.floor(i * 0.27)}:${String((i * 16) % 60).padStart(2, "0")}`,
    pnl: Math.round(Math.sin(i * 0.3) * 2000 + i * 200 + Math.random() * 500),
}));

export default function PositionsPage() {
    const openPnl = positions.reduce((s, p) => s + p.pnl, 0);
    const closedPnl = closedToday.reduce((s, t) => s + t.pnl, 0);
    const totalPnl = openPnl + closedPnl;

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Positions" />
                <div className="page-content fade-in">

                    {/* Summary cards */}
                    <div className="metric-grid stagger" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="metric-card">
                            <div className="metric-label">Total P&amp;L</div>
                            <div className="metric-value" style={{ color: "var(--green-bright)" }}>+Rs.{totalPnl.toLocaleString("en-IN")}</div>
                            <div className="metric-change positive"><ArrowUpRight style={{ width: 12, height: 12 }} /> Open + Closed</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Open P&amp;L</div>
                            <div className="metric-value" style={{ fontSize: 22, color: "var(--green-bright)" }}>+Rs.{openPnl.toLocaleString("en-IN")}</div>
                            <div className="metric-change positive"><DollarSign style={{ width: 12, height: 12 }} /> 4 positions</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Realized P&amp;L</div>
                            <div className="metric-value" style={{ fontSize: 22, color: "var(--green-bright)" }}>+Rs.{closedPnl.toLocaleString("en-IN")}</div>
                            <div className="metric-change positive"><Clock style={{ width: 12, height: 12 }} /> 2 trades closed</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Margin Used</div>
                            <div className="metric-value" style={{ fontSize: 22 }}>Rs.1,52,939</div>
                            <div className="metric-change" style={{ color: "var(--accent)", background: "var(--accent-dim)" }}>
                                <AlertCircle style={{ width: 12, height: 12 }} /> 15.3% utilized
                            </div>
                        </div>
                    </div>

                    {/* P&L timeline */}
                    <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="card-header">
                            <span className="card-title">Intraday P&amp;L Timeline</span>
                        </div>
                        <div style={{ height: 200 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={pnlTimeline}>
                                    <defs>
                                        <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                    <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} interval={4} />
                                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`} />
                                    <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-sm)", fontSize: 12 }} />
                                    <Area type="monotone" dataKey="pnl" stroke="#22c55e" strokeWidth={2} fill="url(#pnlGrad)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Open positions */}
                    <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="card-header">
                            <span className="card-title">Open Positions</span>
                            <button className="btn btn-sm btn-danger">Square Off All</button>
                        </div>
                        <div className="table-wrapper">
                            <table>
                                <thead><tr><th>Symbol</th><th>Type</th><th>Side</th><th>Qty</th><th>Avg Price</th><th>LTP</th><th>P&amp;L</th><th>P&amp;L %</th></tr></thead>
                                <tbody>
                                    {positions.map((p) => (
                                        <tr key={p.symbol}>
                                            <td style={{ color: "var(--text-primary)", fontWeight: 600 }}>{p.symbol}</td>
                                            <td><span className="tag tag-purple">{p.type}</span></td>
                                            <td><span className={`tag ${p.side === "LONG" ? "tag-green" : "tag-red"}`}>{p.side}</span></td>
                                            <td className="text-mono">{Math.abs(p.qty)}</td>
                                            <td className="text-mono">{p.avgPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                                            <td className="text-mono" style={{ fontWeight: 600 }}>{p.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                                            <td className={`text-mono ${p.pnl >= 0 ? "text-green" : "text-red"}`}>
                                                {p.pnl >= 0 ? <ArrowUpRight style={{ width: 12, height: 12, display: "inline" }} /> : <ArrowDownRight style={{ width: 12, height: 12, display: "inline" }} />}
                                                {p.pnl >= 0 ? "+" : ""}Rs.{Math.abs(p.pnl).toLocaleString("en-IN")}
                                            </td>
                                            <td className={`text-mono ${p.pnlPct >= 0 ? "text-green" : "text-red"}`}>{p.pnlPct >= 0 ? "+" : ""}{p.pnlPct.toFixed(2)}%</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Closed today */}
                    <div className="card">
                        <div className="card-header"><span className="card-title">Closed Today</span></div>
                        <div className="table-wrapper">
                            <table>
                                <thead><tr><th>Exit Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&amp;L</th></tr></thead>
                                <tbody>
                                    {closedToday.map((t, i) => (
                                        <tr key={i}>
                                            <td className="text-mono text-muted">{t.exitTime}</td>
                                            <td style={{ fontWeight: 500 }}>{t.symbol}</td>
                                            <td><span className={`tag ${t.side === "LONG" ? "tag-green" : "tag-red"}`}>{t.side}</span></td>
                                            <td className="text-mono">{t.qty}</td>
                                            <td className="text-mono">{t.entry.toFixed(2)}</td>
                                            <td className="text-mono">{t.exit.toFixed(2)}</td>
                                            <td className={`text-mono ${t.pnl >= 0 ? "text-green" : "text-red"}`}>+Rs.{t.pnl.toLocaleString("en-IN")}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
