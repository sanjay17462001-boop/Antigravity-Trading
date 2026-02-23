"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { Zap, Shield, AlertTriangle, ArrowUpRight, ArrowDownRight, Power, PauseCircle } from "lucide-react";

const liveStrategies = [
    { name: "Iron Condor VIX", instrument: "NIFTY Options", status: "running", pnlToday: 4120, trades: 3, riskUsed: 32 },
];

const openPositions = [
    { symbol: "NIFTY 25500 CE", side: "SHORT", qty: -50, avgPrice: 280.40, ltp: 245.80, pnl: 1730, mtm: 12290 },
    { symbol: "NIFTY 25300 CE", side: "LONG", qty: 50, avgPrice: 380.20, ltp: 398.40, pnl: 910, mtm: 19920 },
    { symbol: "NIFTY 25700 PE", side: "SHORT", qty: -50, avgPrice: 320.10, ltp: 298.70, pnl: 1070, mtm: 14935 },
    { symbol: "NIFTY 25500 PE", side: "LONG", qty: 50, avgPrice: 160.80, ltp: 178.35, pnl: 877.5, mtm: 8917.5 },
];

const orderLog = [
    { time: "09:15:32", type: "ENTRY", symbol: "NIFTY 25500 CE", side: "SELL", qty: 50, price: 280.40, status: "FILLED" },
    { time: "09:15:33", type: "ENTRY", symbol: "NIFTY 25300 CE", side: "BUY", qty: 50, price: 380.20, status: "FILLED" },
    { time: "09:15:34", type: "ENTRY", symbol: "NIFTY 25700 PE", side: "SELL", qty: 50, price: 320.10, status: "FILLED" },
    { time: "09:15:35", type: "ENTRY", symbol: "NIFTY 25500 PE", side: "BUY", qty: 50, price: 160.80, status: "FILLED" },
    { time: "11:42:18", type: "SL-MOD", symbol: "NIFTY 25500 CE", side: "BUY", qty: 50, price: 310.00, status: "OPEN" },
];

const riskMetrics = [
    { label: "Day Loss Limit", used: 4587.5, max: 50000 },
    { label: "Strategy Loss Limit", used: 0, max: 20000 },
    { label: "Max Position Value", used: 56062.5, max: 500000 },
    { label: "Open Positions", used: 4, max: 10 },
];

export default function LivePage() {
    const totalPnl = openPositions.reduce((s, p) => s + p.pnl, 0);

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Live Trading" />
                <div className="page-content fade-in">

                    {/* Status banner */}
                    <div style={{
                        background: "linear-gradient(135deg, rgba(34,197,94,0.1) 0%, rgba(56,189,248,0.05) 100%)",
                        border: "1px solid rgba(34,197,94,0.2)",
                        borderRadius: "var(--radius-md)",
                        padding: "16px 24px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "var(--space-xl)",
                    }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--green)", boxShadow: "0 0 12px var(--green)", animation: "pulse-green 2s infinite" }} />
                            <div>
                                <div style={{ fontWeight: 700, fontSize: 15 }}>Live Trading Active</div>
                                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>1 strategy running — Market hours: 09:15 - 15:30 IST</div>
                            </div>
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <button className="btn btn-secondary"><PauseCircle style={{ width: 14, height: 14 }} /> Pause All</button>
                            <button className="btn btn-danger"><Power style={{ width: 14, height: 14 }} /> Kill Switch</button>
                        </div>
                    </div>

                    {/* Metrics */}
                    <div className="metric-grid stagger" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="metric-card">
                            <div className="metric-label">Live P&amp;L</div>
                            <div className="metric-value" style={{ color: totalPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>
                                {totalPnl >= 0 ? "+" : ""}Rs.{Math.abs(totalPnl).toLocaleString("en-IN")}
                            </div>
                            <div className="metric-change positive"><ArrowUpRight style={{ width: 12, height: 12 }} /> 4 positions</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">MTM Exposure</div>
                            <div className="metric-value" style={{ fontSize: 22 }}>Rs.56,063</div>
                            <div className="metric-change" style={{ color: "var(--accent)", background: "var(--accent-dim)" }}>
                                <Shield style={{ width: 12, height: 12 }} /> 11.2% of limit
                            </div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Risk Used</div>
                            <div className="metric-value" style={{ fontSize: 22 }}>9.2%</div>
                            <div className="metric-change positive"><Zap style={{ width: 12, height: 12 }} /> Well within limits</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Orders Today</div>
                            <div className="metric-value" style={{ fontSize: 22 }}>5</div>
                            <div className="metric-change" style={{ color: "var(--yellow)", background: "var(--yellow-dim)" }}>
                                <AlertTriangle style={{ width: 12, height: 12 }} /> 1 SL pending
                            </div>
                        </div>
                    </div>

                    <div className="row" style={{ marginBottom: "var(--space-xl)" }}>
                        {/* Positions */}
                        <div className="card flex-2">
                            <div className="card-header">
                                <span className="card-title">Open Positions</span>
                                <button className="btn btn-sm btn-danger">Square Off All</button>
                            </div>
                            <div className="table-wrapper">
                                <table>
                                    <thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Price</th><th>LTP</th><th>P&amp;L</th><th>MTM</th></tr></thead>
                                    <tbody>
                                        {openPositions.map((p) => (
                                            <tr key={p.symbol}>
                                                <td style={{ color: "var(--text-primary)", fontWeight: 600 }}>{p.symbol}</td>
                                                <td><span className={`tag ${p.side === "LONG" ? "tag-green" : "tag-red"}`}>{p.side}</span></td>
                                                <td className="text-mono">{Math.abs(p.qty)}</td>
                                                <td className="text-mono">{p.avgPrice.toFixed(2)}</td>
                                                <td className="text-mono" style={{ fontWeight: 600 }}>{p.ltp.toFixed(2)}</td>
                                                <td className={`text-mono ${p.pnl >= 0 ? "text-green" : "text-red"}`}>
                                                    {p.pnl >= 0 ? "+" : ""}Rs.{Math.abs(p.pnl).toLocaleString("en-IN")}
                                                </td>
                                                <td className="text-mono text-muted">Rs.{p.mtm.toLocaleString("en-IN")}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Risk gauges */}
                        <div className="card flex-1">
                            <div className="card-header">
                                <span className="card-title">Risk Monitor</span>
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                                {riskMetrics.map((r) => {
                                    const pct = (r.used / r.max) * 100;
                                    const color = pct > 80 ? "var(--red)" : pct > 50 ? "var(--yellow)" : "var(--green)";
                                    return (
                                        <div key={r.label}>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                                                <span style={{ color: "var(--text-secondary)" }}>{r.label}</span>
                                                <span className="text-mono" style={{ color: "var(--text-muted)" }}>
                                                    {typeof r.used === "number" && r.used > 100
                                                        ? `Rs.${r.used.toLocaleString("en-IN")}`
                                                        : r.used} / {typeof r.max === "number" && r.max > 100 ? `Rs.${r.max.toLocaleString("en-IN")}` : r.max}
                                                </span>
                                            </div>
                                            <div style={{ height: 6, background: "var(--bg-tertiary)", borderRadius: 3, overflow: "hidden" }}>
                                                <div style={{ width: `${Math.min(pct, 100)}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.5s" }} />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {/* Order log */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Order Log</span>
                        </div>
                        <div className="table-wrapper">
                            <table>
                                <thead><tr><th>Time</th><th>Type</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Status</th></tr></thead>
                                <tbody>
                                    {orderLog.map((o, i) => (
                                        <tr key={i}>
                                            <td className="text-mono text-muted">{o.time}</td>
                                            <td><span className={`tag ${o.type === "ENTRY" ? "tag-accent" : "tag-yellow"}`}>{o.type}</span></td>
                                            <td style={{ fontWeight: 500 }}>{o.symbol}</td>
                                            <td><span className={`tag ${o.side === "BUY" ? "tag-green" : "tag-red"}`}>{o.side}</span></td>
                                            <td className="text-mono">{o.qty}</td>
                                            <td className="text-mono">{o.price.toFixed(2)}</td>
                                            <td><span className={`tag ${o.status === "FILLED" ? "tag-green" : "tag-yellow"}`}>{o.status}</span></td>
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
