"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useState } from "react";
import {
    Play, Pause, RotateCcw, ArrowUpRight, ArrowDownRight,
    Clock, Radio, Activity, TrendingUp, Shield, Zap, ChevronDown, ChevronUp,
} from "lucide-react";

// ── 10 Sample strategies tied to seed_strategies.py ──
const STRATEGIES = [
    { id: "strad-25h", name: "ATM Straddle 25% Hard SL", status: "RUNNING", pnl: 3088, trades: 8, wins: 5 },
    { id: "strad-30c", name: "ATM Straddle 30% Close SL", status: "RUNNING", pnl: 1542, trades: 6, wins: 4 },
    { id: "strang-1", name: "ATM+1 Strangle Sell", status: "RUNNING", pnl: -480, trades: 7, wins: 3 },
    { id: "deep-otm", name: "Deep OTM Strangle (ATM+3)", status: "PAUSED", pnl: 2215, trades: 10, wins: 7 },
    { id: "ic-2-5", name: "Iron Condor (ATM+2/+5)", status: "RUNNING", pnl: 690, trades: 4, wins: 3 },
    { id: "tight-15", name: "Tight SL Straddle (15%)", status: "RUNNING", pnl: -1320, trades: 12, wins: 5 },
    { id: "late-10", name: "Late Entry Straddle (10:00)", status: "RUNNING", pnl: 2750, trades: 5, wins: 4 },
    { id: "sl-tgt", name: "Straddle SL+Target (25/50)", status: "PAUSED", pnl: 4180, trades: 9, wins: 6 },
    { id: "bull-put", name: "Bull Put Spread (ATM/ATM-3)", status: "RUNNING", pnl: 1105, trades: 6, wins: 4 },
    { id: "2lot-25c", name: "2-Lot Straddle (25% Close)", status: "RUNNING", pnl: 5640, trades: 8, wins: 5 },
];

// ── Realistic virtual trades across strategies ──
const virtualTrades = [
    // ATM Straddle 25% Hard SL
    { time: "09:20:00", strategy: "ATM Straddle 25% Hard", symbol: "NIFTY 24400 CE", side: "SELL", qty: 25, entry: 228.40, current: 195.60, status: "OPEN", pnl: 820 },
    { time: "09:20:00", strategy: "ATM Straddle 25% Hard", symbol: "NIFTY 24400 PE", side: "SELL", qty: 25, entry: 215.30, current: 188.70, status: "OPEN", pnl: 665 },
    // ATM Straddle 30% Close SL
    { time: "09:30:00", strategy: "ATM Straddle 30% Close", symbol: "NIFTY 24400 CE", side: "SELL", qty: 25, entry: 235.60, current: 210.40, status: "OPEN", pnl: 630 },
    { time: "09:30:00", strategy: "ATM Straddle 30% Close", symbol: "NIFTY 24400 PE", side: "SELL", qty: 25, entry: 208.20, current: 195.80, status: "OPEN", pnl: 310 },
    // ATM+1 Strangle — hit SL on one leg
    { time: "09:20:00", strategy: "ATM+1 Strangle", symbol: "NIFTY 24450 CE", side: "SELL", qty: 25, entry: 175.40, current: 228.00, status: "SL HIT", pnl: -1315 },
    { time: "09:20:00", strategy: "ATM+1 Strangle", symbol: "NIFTY 24350 PE", side: "SELL", qty: 25, entry: 162.80, current: 128.30, status: "OPEN", pnl: 863 },
    // Deep OTM Strangle
    { time: "09:20:00", strategy: "Deep OTM Strangle", symbol: "NIFTY 24550 CE", side: "SELL", qty: 25, entry: 78.40, current: 42.10, status: "OPEN", pnl: 908 },
    { time: "09:20:00", strategy: "Deep OTM Strangle", symbol: "NIFTY 24250 PE", side: "SELL", qty: 25, entry: 85.60, current: 48.20, status: "OPEN", pnl: 935 },
    // Iron Condor
    { time: "09:20:00", strategy: "Iron Condor", symbol: "NIFTY 24500 CE", side: "SELL", qty: 25, entry: 125.80, current: 98.40, status: "OPEN", pnl: 685 },
    { time: "09:20:00", strategy: "Iron Condor", symbol: "NIFTY 24300 PE", side: "SELL", qty: 25, entry: 118.60, current: 95.20, status: "OPEN", pnl: 585 },
    { time: "09:20:00", strategy: "Iron Condor", symbol: "NIFTY 24650 CE", side: "BUY", qty: 25, entry: 52.40, current: 38.80, status: "OPEN", pnl: -340 },
    { time: "09:20:00", strategy: "Iron Condor", symbol: "NIFTY 24150 PE", side: "BUY", qty: 25, entry: 48.20, current: 35.60, status: "OPEN", pnl: -315 },
    // Late Entry Straddle
    { time: "10:00:00", strategy: "Late Entry Straddle", symbol: "NIFTY 24400 CE", side: "SELL", qty: 25, entry: 198.40, current: 158.60, status: "OPEN", pnl: 995 },
    { time: "10:00:00", strategy: "Late Entry Straddle", symbol: "NIFTY 24400 PE", side: "SELL", qty: 25, entry: 185.20, current: 148.80, status: "OPEN", pnl: 910 },
    // Straddle SL+Target — target hit
    { time: "09:20:00", strategy: "SL+Target Straddle", symbol: "NIFTY 24400 CE", side: "SELL", qty: 25, entry: 228.40, current: 114.20, status: "TARGET", pnl: 2855 },
    { time: "09:20:00", strategy: "SL+Target Straddle", symbol: "NIFTY 24400 PE", side: "SELL", qty: 25, entry: 215.30, current: 165.40, status: "OPEN", pnl: 1248 },
    // Bull Put Spread
    { time: "09:20:00", strategy: "Bull Put Spread", symbol: "NIFTY 24400 PE", side: "SELL", qty: 25, entry: 215.30, current: 188.70, status: "OPEN", pnl: 665 },
    { time: "09:20:00", strategy: "Bull Put Spread", symbol: "NIFTY 24250 PE", side: "BUY", qty: 25, entry: 85.60, current: 72.40, status: "OPEN", pnl: -330 },
    // 2-Lot Straddle
    { time: "09:20:00", strategy: "2-Lot Straddle", symbol: "NIFTY 24400 CE", side: "SELL", qty: 50, entry: 228.40, current: 195.60, status: "OPEN", pnl: 1640 },
    { time: "09:20:00", strategy: "2-Lot Straddle", symbol: "NIFTY 24400 PE", side: "SELL", qty: 50, entry: 215.30, current: 188.70, status: "OPEN", pnl: 1330 },
];

// ── Signal log ──
const signals = [
    { time: "09:15", strategy: "ATM Straddle 25%", signal: "SELL", strength: 92, symbol: "NIFTY 24400 CE+PE", reason: "Market open — ATM straddle entry triggered at 09:20" },
    { time: "09:20", strategy: "ATM+1 Strangle", signal: "SELL", strength: 78, symbol: "NIFTY 24450CE / 24350PE", reason: "OTM strangle entry — IV rank above 60" },
    { time: "09:30", strategy: "ATM Straddle 30%", signal: "SELL", strength: 85, symbol: "NIFTY 24400 CE+PE", reason: "Delayed entry straddle — opening range established" },
    { time: "10:00", strategy: "Late Entry Straddle", signal: "SELL", strength: 80, symbol: "NIFTY 24400 CE+PE", reason: "ORB complete — entering after initial vol crush" },
    { time: "10:45", strategy: "ATM+1 Strangle", signal: "SL", strength: 95, symbol: "NIFTY 24450 CE", reason: "CE leg SL triggered at 228.00 (30% above entry 175.40)" },
    { time: "11:30", strategy: "SL+Target Straddle", signal: "TARGET", strength: 100, symbol: "NIFTY 24400 CE", reason: "CE leg target hit at 114.20 (50% decay from 228.40)" },
    { time: "12:15", strategy: "Iron Condor", signal: "HOLD", strength: 65, symbol: "All 4 legs", reason: "Spot within ±100 of ATM — all legs safe, theta decaying" },
    { time: "13:00", strategy: "Deep OTM Strangle", signal: "HOLD", strength: 88, symbol: "NIFTY 24550CE / 24250PE", reason: "Both legs decayed >40% — comfortable profit zone" },
];

// ── Intraday P&L curve ──
const equityCurve = (() => {
    const points = [];
    let equity = 0;
    const base = Date.now();
    for (let m = 0; m <= 360; m += 5) {
        const h = 9 + Math.floor((m + 15) / 60);
        const min = (m + 15) % 60;
        if (h > 15 || (h === 15 && min > 30)) break;
        // Simulate realistic P&L growth with some volatility
        const trend = m * 12 + Math.sin(m * 0.03) * 2000;
        const noise = (Math.random() - 0.45) * 800;
        equity = Math.round(trend + noise);
        points.push({
            time: `${h}:${String(min).padStart(2, "0")}`,
            equity: equity,
        });
    }
    return points;
})();

export default function PaperTradePage() {
    const totalPnl = virtualTrades.reduce((s, t) => s + t.pnl, 0);
    const openTrades = virtualTrades.filter(t => t.status === "OPEN").length;
    const totalTrades = virtualTrades.length;
    const slHits = virtualTrades.filter(t => t.status === "SL HIT").length;
    const targets = virtualTrades.filter(t => t.status === "TARGET").length;
    const activeStrategies = STRATEGIES.filter(s => s.status === "RUNNING").length;

    const [showAllTrades, setShowAllTrades] = useState(false);
    const displayedTrades = showAllTrades ? virtualTrades : virtualTrades.slice(0, 10);

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Paper Trading" />
                <div className="page-content fade-in">

                    {/* Status bar */}
                    <div style={{
                        background: "linear-gradient(135deg, rgba(56,189,248,0.1) 0%, rgba(167,139,250,0.05) 100%)",
                        border: "1px solid rgba(56,189,248,0.2)",
                        borderRadius: "var(--radius-md)", padding: "14px 20px",
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        marginBottom: "var(--space-lg)",
                    }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                            <Radio style={{ width: 16, height: 16, color: "var(--accent)" }} />
                            <div>
                                <div style={{ fontWeight: 700, fontSize: 14 }}>Multi-Strategy Paper Trading Session</div>
                                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                    {activeStrategies} strategies running — {openTrades} open positions — Virtual capital: Rs.10,00,000
                                </div>
                            </div>
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <button className="btn btn-secondary"><Pause style={{ width: 13, height: 13 }} /> Pause All</button>
                            <button className="btn btn-secondary"><RotateCcw style={{ width: 13, height: 13 }} /> Reset</button>
                            <button className="btn btn-primary"><Play style={{ width: 13, height: 13 }} /> Resume All</button>
                        </div>
                    </div>

                    {/* Metrics */}
                    <div className="metric-grid stagger" style={{ marginBottom: "var(--space-lg)" }}>
                        <div className="metric-card">
                            <div className="metric-label">Virtual P&amp;L</div>
                            <div className="metric-value" style={{ color: totalPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>
                                {totalPnl >= 0 ? "+" : ""}Rs.{Math.abs(totalPnl).toLocaleString("en-IN")}
                            </div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Positions</div>
                            <div className="metric-value" style={{ fontSize: 20 }}>{totalTrades}</div>
                            <div className="metric-change positive"><ArrowUpRight style={{ width: 12, height: 12 }} /> {openTrades} open</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">Strategies Active</div>
                            <div className="metric-value" style={{ fontSize: 20 }}>{activeStrategies}/10</div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-label">SL Hits / Targets</div>
                            <div className="metric-value" style={{ fontSize: 20 }}>
                                <span style={{ color: "var(--red-bright)" }}>{slHits}</span>
                                {" / "}
                                <span style={{ color: "var(--green-bright)" }}>{targets}</span>
                            </div>
                        </div>
                    </div>

                    {/* Strategy-wise P&L cards */}
                    <div className="card" style={{ marginBottom: "var(--space-lg)" }}>
                        <div className="card-header"><span className="card-title">Strategy Performance (Today)</span></div>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
                            {STRATEGIES.map(s => (
                                <div key={s.id} style={{
                                    background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)",
                                    padding: "10px 12px", border: `1px solid ${s.status === "PAUSED" ? "var(--border-subtle)" : "transparent"}`,
                                    opacity: s.status === "PAUSED" ? 0.6 : 1,
                                }}>
                                    <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                        {s.name}
                                    </div>
                                    <div className="text-mono" style={{
                                        fontSize: 15, fontWeight: 700,
                                        color: s.pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)",
                                    }}>
                                        {s.pnl >= 0 ? "+" : ""}Rs.{Math.abs(s.pnl).toLocaleString("en-IN")}
                                    </div>
                                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-dim)", marginTop: 3 }}>
                                        <span>{s.trades} trades</span>
                                        <span>WR: {Math.round(s.wins / s.trades * 100)}%</span>
                                        <span className={`tag ${s.status === "RUNNING" ? "tag-green" : "tag-accent"}`} style={{ fontSize: 8, padding: "1px 4px" }}>{s.status}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Equity curve */}
                    <div className="card" style={{ marginBottom: "var(--space-lg)" }}>
                        <div className="card-header"><span className="card-title">Combined Equity Curve (Intraday)</span></div>
                        <div style={{ height: 200, position: "relative", overflow: "hidden" }}>
                            {equityCurve.length > 0 && (() => {
                                const maxVal = Math.max(...equityCurve.map(d => d.equity));
                                const minVal = Math.min(...equityCurve.map(d => d.equity));
                                const range = maxVal - minVal || 1;
                                return (
                                    <svg viewBox={`0 0 ${equityCurve.length} 100`} width="100%" height="100%" preserveAspectRatio="none" style={{ display: "block" }}>
                                        <line x1="0" y1={100 - ((0 - minVal) / range) * 100} x2={equityCurve.length} y2={100 - ((0 - minVal) / range) * 100}
                                            stroke="var(--border-subtle)" strokeWidth="0.3" strokeDasharray="2,2" />
                                        <polyline points={equityCurve.map((d, i) => `${i},${100 - ((d.equity - minVal) / range) * 100}`).join(" ")}
                                            fill="none" stroke="var(--accent)" strokeWidth="0.8" />
                                        <polygon points={`0,${100 - ((equityCurve[0].equity - minVal) / range) * 100} ${equityCurve.map((d, i) => `${i},${100 - ((d.equity - minVal) / range) * 100}`).join(" ")} ${equityCurve.length - 1},100 0,100`}
                                            fill="var(--accent)" opacity="0.08" />
                                    </svg>
                                );
                            })()}
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-dim)", marginTop: 3 }}>
                            <span>{equityCurve[0]?.time}</span>
                            <span>{equityCurve[equityCurve.length - 1]?.time}</span>
                        </div>
                    </div>

                    <div className="row">
                        {/* Virtual trades */}
                        <div className="card flex-1">
                            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span className="card-title">Live Positions ({totalTrades})</span>
                                <button onClick={() => setShowAllTrades(!showAllTrades)}
                                    style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
                                    {showAllTrades ? "Collapse" : "Show All"}
                                    {showAllTrades ? <ChevronUp style={{ width: 12, height: 12 }} /> : <ChevronDown style={{ width: 12, height: 12 }} />}
                                </button>
                            </div>
                            <div className="table-wrapper">
                                <table>
                                    <thead><tr>
                                        <th>Time</th><th>Strategy</th><th>Symbol</th><th>Side</th>
                                        <th>Qty</th><th>Entry</th><th>CMP</th><th>Status</th><th>P&amp;L</th>
                                    </tr></thead>
                                    <tbody>
                                        {displayedTrades.map((t, i) => (
                                            <tr key={i}>
                                                <td className="text-mono text-muted" style={{ fontSize: 11 }}>{t.time}</td>
                                                <td style={{ fontSize: 11, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.strategy}</td>
                                                <td style={{ fontWeight: 500, fontSize: 12 }}>{t.symbol}</td>
                                                <td><span className={`tag ${t.side === "BUY" ? "tag-green" : "tag-red"}`}>{t.side}</span></td>
                                                <td className="text-mono">{t.qty}</td>
                                                <td className="text-mono">{t.entry.toFixed(2)}</td>
                                                <td className="text-mono">{t.current.toFixed(2)}</td>
                                                <td><span className={`tag ${t.status === "OPEN" ? "tag-accent" : t.status === "TARGET" ? "tag-green" : t.status === "SL HIT" ? "tag-red" : "tag-purple"}`} style={{ fontSize: 10 }}>{t.status}</span></td>
                                                <td className={`text-mono ${t.pnl >= 0 ? "text-green" : "text-red"}`}>
                                                    {t.pnl >= 0 ? "+" : ""}Rs.{Math.abs(t.pnl).toLocaleString("en-IN")}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Signal log */}
                        <div className="card flex-1">
                            <div className="card-header"><span className="card-title">Signal Log</span></div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                                {signals.map((s, i) => (
                                    <div key={i} style={{
                                        background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)",
                                        padding: "8px 12px", border: "1px solid var(--border-subtle)",
                                    }}>
                                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3 }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                                <Clock style={{ width: 11, height: 11, color: "var(--text-dim)" }} />
                                                <span className="text-mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>{s.time}</span>
                                                <span style={{ fontWeight: 600, fontSize: 12 }}>{s.strategy}</span>
                                            </div>
                                            <span className={`tag ${s.signal === "SELL" || s.signal === "SL" ? "tag-red" : s.signal === "TARGET" ? "tag-green" : s.signal === "HOLD" ? "tag-accent" : "tag-purple"}`} style={{ fontSize: 10 }}>{s.signal}</span>
                                        </div>
                                        <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 3 }}>{s.symbol} — {s.reason}</div>
                                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                            <div style={{ height: 3, flex: 1, background: "var(--bg-secondary)", borderRadius: 2, overflow: "hidden" }}>
                                                <div style={{ width: `${s.strength}%`, height: "100%", background: s.strength > 75 ? "var(--green)" : "var(--yellow)", borderRadius: 2 }} />
                                            </div>
                                            <span style={{ fontSize: 9, color: "var(--text-dim)", minWidth: 28 }}>{s.strength}%</span>
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
