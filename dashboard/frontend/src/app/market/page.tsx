"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { ArrowUpRight, ArrowDownRight, TrendingUp, Activity } from "lucide-react";

const indices = [
    { name: "NIFTY 50", value: 25454.35, change: 82.15, changePct: 0.32 },
    { name: "BANKNIFTY", value: 60739.55, change: -124.40, changePct: -0.20 },
    { name: "FINNIFTY", value: 24312.80, change: 45.60, changePct: 0.19 },
    { name: "INDIA VIX", value: 14.23, change: -0.45, changePct: -3.07 },
];

const watchlist = [
    { symbol: "NIFTY 25500 CE", ltp: 245.80, change: 12.40, changePct: 5.31, oi: "12.4L", volume: "8.2L", iv: 14.2, bid: 245.50, ask: 246.10 },
    { symbol: "NIFTY 25500 PE", ltp: 178.35, change: -8.20, changePct: -4.39, oi: "15.1L", volume: "6.8L", iv: 15.8, bid: 178.00, ask: 178.70 },
    { symbol: "NIFTY 25400 CE", ltp: 312.40, change: 18.60, changePct: 6.33, oi: "9.2L", volume: "5.4L", iv: 13.6, bid: 312.10, ask: 312.70 },
    { symbol: "NIFTY 25400 PE", ltp: 135.60, change: -6.80, changePct: -4.77, oi: "11.8L", volume: "4.2L", iv: 16.1, bid: 135.30, ask: 135.90 },
    { symbol: "BANKNIFTY 61000 CE", ltp: 420.50, change: -15.30, changePct: -3.51, oi: "4.6L", volume: "3.1L", iv: 16.4, bid: 420.20, ask: 420.80 },
    { symbol: "BANKNIFTY 61000 PE", ltp: 295.20, change: 22.40, changePct: 8.21, oi: "6.2L", volume: "4.8L", iv: 17.2, bid: 294.90, ask: 295.50 },
    { symbol: "NIFTY MAR FUT", ltp: 25512.30, change: 94.80, changePct: 0.37, oi: "82.3L", volume: "24.6L", iv: 0, bid: 25511.80, ask: 25512.80 },
    { symbol: "BANKNIFTY MAR FUT", ltp: 60845.60, change: -108.20, changePct: -0.18, oi: "34.5L", volume: "12.8L", iv: 0, bid: 60845.10, ask: 60846.10 },
];

const optionChain = [
    { strike: 25300, ceOi: "8.2L", ceLtp: 398.40, ceChange: 24.10, peOi: "6.1L", peLtp: 82.50, peChange: -12.30 },
    { strike: 25400, ceOi: "9.2L", ceLtp: 312.40, ceChange: 18.60, peOi: "11.8L", peLtp: 135.60, peChange: -6.80 },
    { strike: 25500, ceOi: "12.4L", ceLtp: 245.80, ceChange: 12.40, peOi: "15.1L", peLtp: 178.35, peChange: -8.20 },
    { strike: 25600, ceOi: "14.8L", ceLtp: 186.20, ceChange: 6.80, peOi: "8.4L", peLtp: 232.50, peChange: 14.60 },
    { strike: 25700, ceOi: "18.2L", ceLtp: 138.60, ceChange: 2.40, peOi: "5.6L", peLtp: 298.70, peChange: 28.40 },
];

export default function MarketPage() {
    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Market Data" />
                <div className="page-content fade-in">
                    {/* Index cards */}
                    <div className="metric-grid stagger" style={{ marginBottom: "var(--space-xl)" }}>
                        {indices.map((idx) => (
                            <div key={idx.name} className="metric-card">
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                                    <span className="metric-label">{idx.name}</span>
                                    {idx.name === "INDIA VIX" ? (
                                        <Activity style={{ width: 14, height: 14, color: "var(--purple)" }} />
                                    ) : (
                                        <TrendingUp style={{ width: 14, height: 14, color: "var(--accent)" }} />
                                    )}
                                </div>
                                <div className="metric-value" style={{ fontSize: 22 }}>
                                    {idx.value.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </div>
                                <div className={`metric-change ${idx.change >= 0 ? "positive" : "negative"}`}>
                                    {idx.change >= 0 ? <ArrowUpRight style={{ width: 12, height: 12 }} /> : <ArrowDownRight style={{ width: 12, height: 12 }} />}
                                    {idx.change >= 0 ? "+" : ""}{idx.change.toFixed(2)} ({idx.changePct >= 0 ? "+" : ""}{idx.changePct.toFixed(2)}%)
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Option Chain */}
                    <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="card-header">
                            <span className="card-title">NIFTY Option Chain — 27 Feb 2026</span>
                            <div style={{ display: "flex", gap: 8 }}>
                                <span className="tag tag-accent">ATM: 25500</span>
                                <span className="tag tag-purple">IV: 14.2%</span>
                            </div>
                        </div>
                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th style={{ textAlign: "right" }}>OI</th>
                                        <th style={{ textAlign: "right" }}>Chg</th>
                                        <th style={{ textAlign: "right" }}>CE LTP</th>
                                        <th style={{ textAlign: "center", background: "var(--bg-card)", color: "var(--accent)", fontWeight: 700 }}>STRIKE</th>
                                        <th>PE LTP</th>
                                        <th>Chg</th>
                                        <th>OI</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {optionChain.map((row) => {
                                        const isAtm = row.strike === 25500;
                                        return (
                                            <tr key={row.strike} style={isAtm ? { background: "var(--accent-dim)" } : undefined}>
                                                <td style={{ textAlign: "right" }} className="text-mono text-muted">{row.ceOi}</td>
                                                <td style={{ textAlign: "right" }} className={`text-mono ${row.ceChange >= 0 ? "text-green" : "text-red"}`}>
                                                    {row.ceChange >= 0 ? "+" : ""}{row.ceChange.toFixed(2)}
                                                </td>
                                                <td style={{ textAlign: "right", fontWeight: 600 }} className="text-mono">{row.ceLtp.toFixed(2)}</td>
                                                <td style={{ textAlign: "center", fontWeight: 700, color: isAtm ? "var(--accent)" : "var(--text-primary)", background: "var(--bg-card)" }} className="text-mono">
                                                    {row.strike}
                                                </td>
                                                <td className="text-mono" style={{ fontWeight: 600 }}>{row.peLtp.toFixed(2)}</td>
                                                <td className={`text-mono ${row.peChange >= 0 ? "text-green" : "text-red"}`}>
                                                    {row.peChange >= 0 ? "+" : ""}{row.peChange.toFixed(2)}
                                                </td>
                                                <td className="text-mono text-muted">{row.peOi}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Watchlist */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Watchlist</span>
                            <button className="btn btn-sm btn-secondary">+ Add Symbol</button>
                        </div>
                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Symbol</th>
                                        <th>LTP</th>
                                        <th>Change</th>
                                        <th>OI</th>
                                        <th>Volume</th>
                                        <th>IV</th>
                                        <th>Bid</th>
                                        <th>Ask</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {watchlist.map((w) => (
                                        <tr key={w.symbol}>
                                            <td style={{ color: "var(--text-primary)", fontWeight: 600 }}>{w.symbol}</td>
                                            <td className="text-mono" style={{ fontWeight: 600 }}>{w.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                                            <td className={`text-mono ${w.change >= 0 ? "text-green" : "text-red"}`}>
                                                {w.change >= 0 ? "+" : ""}{w.change.toFixed(2)} ({w.changePct >= 0 ? "+" : ""}{w.changePct.toFixed(2)}%)
                                            </td>
                                            <td className="text-mono text-muted">{w.oi}</td>
                                            <td className="text-mono text-muted">{w.volume}</td>
                                            <td className="text-mono">{w.iv > 0 ? `${w.iv}%` : "—"}</td>
                                            <td className="text-mono text-muted">{w.bid.toFixed(2)}</td>
                                            <td className="text-mono text-muted">{w.ask.toFixed(2)}</td>
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
