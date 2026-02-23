"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { Search, Download, HardDrive, FileSpreadsheet, Calendar } from "lucide-react";

const dataFiles = [
    { instrument: "NIFTY 50", exchange: "NSE", type: "Spot", interval: "daily", from: "2021-01-01", to: "2026-02-19", candles: 1268, size: "142 KB", file: "NIFTY_50_daily.parquet" },
    { instrument: "NIFTY 50", exchange: "NSE", type: "Spot", interval: "5min", from: "2024-12-01", to: "2026-02-19", candles: 47340, size: "4.2 MB", file: "NIFTY_50_5min.parquet" },
    { instrument: "BANKNIFTY", exchange: "NSE", type: "Spot", interval: "daily", from: "2021-01-01", to: "2026-02-19", candles: 1268, size: "138 KB", file: "BANKNIFTY_daily.parquet" },
    { instrument: "BANKNIFTY", exchange: "NSE", type: "Spot", interval: "5min", from: "2024-12-01", to: "2026-02-19", candles: 46280, size: "4.1 MB", file: "BANKNIFTY_5min.parquet" },
    { instrument: "INDIA VIX", exchange: "NSE", type: "Index", interval: "daily", from: "2021-01-01", to: "2026-02-19", candles: 1268, size: "98 KB", file: "VIX_daily.parquet" },
];

const dbStats = [
    { label: "Total Candles", value: "97,424" },
    { label: "Instruments", value: "5" },
    { label: "Parquet Files", value: "5" },
    { label: "Total Size", value: "8.7 MB" },
    { label: "Trades in DB", value: "439" },
    { label: "Strategies Saved", value: "3" },
];

export default function DataPage() {
    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Data Explorer" />
                <div className="page-content fade-in">

                    {/* Stats */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "var(--space-sm)", marginBottom: "var(--space-xl)" }} className="stagger">
                        {dbStats.map((s) => (
                            <div key={s.label} style={{
                                background: "var(--gradient-card)",
                                border: "1px solid var(--border-subtle)",
                                borderRadius: "var(--radius-sm)",
                                padding: "12px 14px",
                            }}>
                                <div style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-dim)", marginBottom: 4 }}>{s.label}</div>
                                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'JetBrains Mono'" }}>{s.value}</div>
                            </div>
                        ))}
                    </div>

                    {/* Search and fetch */}
                    <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="card-header">
                            <span className="card-title">Fetch Historical Data</span>
                        </div>
                        <div style={{ display: "flex", gap: "var(--space-md)", alignItems: "flex-end", flexWrap: "wrap" }}>
                            <div style={{ flex: 1, minWidth: 180 }}>
                                <label style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 4 }}>Instrument</label>
                                <div style={{
                                    display: "flex", alignItems: "center", gap: 8,
                                    background: "var(--bg-tertiary)", border: "1px solid var(--border-default)",
                                    borderRadius: "var(--radius-sm)", padding: "8px 12px",
                                }}>
                                    <Search style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
                                    <input type="text" placeholder="Search NIFTY, BANKNIFTY..." style={{
                                        background: "transparent", border: "none", outline: "none",
                                        color: "var(--text-primary)", fontSize: 13, width: "100%", fontFamily: "inherit",
                                    }} />
                                </div>
                            </div>
                            <div style={{ minWidth: 120 }}>
                                <label style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 4 }}>Interval</label>
                                <select style={{
                                    background: "var(--bg-tertiary)", border: "1px solid var(--border-default)",
                                    borderRadius: "var(--radius-sm)", padding: "8px 12px",
                                    color: "var(--text-primary)", fontSize: 13, width: "100%", fontFamily: "inherit",
                                }}>
                                    <option>1min</option>
                                    <option selected>5min</option>
                                    <option>15min</option>
                                    <option>1hour</option>
                                    <option>daily</option>
                                </select>
                            </div>
                            <div style={{ minWidth: 130 }}>
                                <label style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 4 }}>From</label>
                                <input type="date" defaultValue="2024-12-01" style={{
                                    background: "var(--bg-tertiary)", border: "1px solid var(--border-default)",
                                    borderRadius: "var(--radius-sm)", padding: "8px 12px",
                                    color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                                }} />
                            </div>
                            <div style={{ minWidth: 130 }}>
                                <label style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 4 }}>To</label>
                                <input type="date" defaultValue="2026-02-19" style={{
                                    background: "var(--bg-tertiary)", border: "1px solid var(--border-default)",
                                    borderRadius: "var(--radius-sm)", padding: "8px 12px",
                                    color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                                }} />
                            </div>
                            <button className="btn btn-primary" style={{ height: 38 }}>
                                <Download style={{ width: 14, height: 14 }} /> Fetch Data
                            </button>
                        </div>
                    </div>

                    {/* Data files table */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Stored Data Files</span>
                            <span className="tag tag-accent"><HardDrive style={{ width: 12, height: 12 }} /> 8.7 MB total</span>
                        </div>
                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Instrument</th>
                                        <th>Exchange</th>
                                        <th>Type</th>
                                        <th>Interval</th>
                                        <th>Date Range</th>
                                        <th>Candles</th>
                                        <th>Size</th>
                                        <th>File</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {dataFiles.map((d, i) => (
                                        <tr key={i}>
                                            <td style={{ color: "var(--text-primary)", fontWeight: 600 }}>{d.instrument}</td>
                                            <td><span className="tag tag-accent">{d.exchange}</span></td>
                                            <td className="text-muted">{d.type}</td>
                                            <td className="text-mono">{d.interval}</td>
                                            <td style={{ fontSize: 12 }}>
                                                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                                    <Calendar style={{ width: 12, height: 12, color: "var(--text-dim)" }} />
                                                    {d.from} → {d.to}
                                                </span>
                                            </td>
                                            <td className="text-mono">{d.candles.toLocaleString()}</td>
                                            <td className="text-mono text-muted">{d.size}</td>
                                            <td>
                                                <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--accent)", cursor: "pointer", fontSize: 12 }}>
                                                    <FileSpreadsheet style={{ width: 12, height: 12 }} />
                                                    {d.file}
                                                </span>
                                            </td>
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
