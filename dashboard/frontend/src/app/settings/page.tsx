"use client";

import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { Save, Shield, Bell, Database, Key, Wifi, WifiOff, Activity, CheckCircle, XCircle } from "lucide-react";

const brokers = [
    { name: "Dhan", status: "connected", clientId: "1110311427", host: "api.dhan.co", mode: "Historical Data" },
    { name: "Bigul XTS", status: "connected", clientId: "TRS06", host: "trading.bigul.co", mode: "Live Feed + Execution" },
    { name: "Bigul Connect", status: "error", clientId: "DHTR0S06", host: "capi.bigul.co", mode: "Low-latency (pending)" },
    { name: "Kotak Neo", status: "disconnected", clientId: "Y3MFR", host: "gw-napi.kotaksecurities.com", mode: "Standby" },
];

const riskConfig = [
    { label: "Max Loss Per Day", value: "Rs.50,000", key: "max_loss_per_day" },
    { label: "Max Loss Per Strategy", value: "Rs.20,000", key: "max_loss_per_strategy" },
    { label: "Max Position Value", value: "Rs.5,00,000", key: "max_position_value" },
    { label: "Max Open Positions", value: "10", key: "max_open_positions" },
    { label: "Circuit Breaker DD%", value: "5%", key: "circuit_breaker_drawdown_pct" },
    { label: "Auto Square-off NSE", value: "15:15", key: "auto_square_off_nse" },
    { label: "Auto Square-off MCX", value: "23:25", key: "auto_square_off_mcx" },
];

export default function SettingsPage() {
    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="Settings" />
                <div className="page-content fade-in">

                    {/* Broker connections */}
                    <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="card-header">
                            <span className="card-title"><Key style={{ width: 14, height: 14, display: "inline", marginRight: 6 }} />Broker Connections</span>
                            <button className="btn btn-sm btn-primary"><Save style={{ width: 12, height: 12 }} /> Save</button>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "var(--space-md)" }}>
                            {brokers.map((b) => (
                                <div key={b.name} style={{
                                    background: "var(--bg-tertiary)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "16px",
                                    border: `1px solid ${b.status === "connected" ? "rgba(34,197,94,0.2)" : b.status === "error" ? "rgba(239,68,68,0.2)" : "var(--border-subtle)"}`,
                                }}>
                                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                            {b.status === "connected" ? <Wifi style={{ width: 16, height: 16, color: "var(--green)" }} /> :
                                                b.status === "error" ? <XCircle style={{ width: 16, height: 16, color: "var(--red)" }} /> :
                                                    <WifiOff style={{ width: 16, height: 16, color: "var(--text-dim)" }} />}
                                            <span style={{ fontWeight: 700, fontSize: 15 }}>{b.name}</span>
                                        </div>
                                        <span className={`tag ${b.status === "connected" ? "tag-green" : b.status === "error" ? "tag-red" : "tag-yellow"}`}>
                                            {b.status === "connected" ? "Connected" : b.status === "error" ? "Error" : "Disconnected"}
                                        </span>
                                    </div>
                                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
                                        <div>
                                            <span style={{ color: "var(--text-dim)" }}>Client ID:</span>
                                            <span className="text-mono" style={{ marginLeft: 6 }}>{b.clientId}</span>
                                        </div>
                                        <div>
                                            <span style={{ color: "var(--text-dim)" }}>Host:</span>
                                            <span className="text-mono" style={{ marginLeft: 6, color: "var(--accent)" }}>{b.host}</span>
                                        </div>
                                        <div style={{ gridColumn: "1 / -1" }}>
                                            <span style={{ color: "var(--text-dim)" }}>Mode:</span>
                                            <span style={{ marginLeft: 6 }}>{b.mode}</span>
                                        </div>
                                    </div>
                                    <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                                        <button className="btn btn-sm btn-secondary">Test Connection</button>
                                        <button className="btn btn-sm btn-secondary">Edit Keys</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Risk config */}
                    <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                        <div className="card-header">
                            <span className="card-title"><Shield style={{ width: 14, height: 14, display: "inline", marginRight: 6 }} />Risk Management</span>
                            <button className="btn btn-sm btn-primary"><Save style={{ width: 12, height: 12 }} /> Save</button>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "var(--space-md)" }}>
                            {riskConfig.map((r) => (
                                <div key={r.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
                                    <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>{r.label}</span>
                                    <span className="text-mono" style={{ fontWeight: 600, fontSize: 14 }}>{r.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* System config */}
                    <div className="row">
                        <div className="card flex-1">
                            <div className="card-header">
                                <span className="card-title"><Database style={{ width: 14, height: 14, display: "inline", marginRight: 6 }} />Data Settings</span>
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                {[
                                    { label: "Default Interval", value: "5min" },
                                    { label: "History Years", value: "5" },
                                    { label: "Cache Enabled", value: "Yes" },
                                    { label: "Initial Capital", value: "Rs.10,00,000" },
                                ].map((s) => (
                                    <div key={s.label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border-subtle)", fontSize: 13 }}>
                                        <span style={{ color: "var(--text-muted)" }}>{s.label}</span>
                                        <span className="text-mono" style={{ fontWeight: 500 }}>{s.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="card flex-1">
                            <div className="card-header">
                                <span className="card-title"><Bell style={{ width: 14, height: 14, display: "inline", marginRight: 6 }} />Notifications</span>
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                {[
                                    { label: "Trade Executions", enabled: true },
                                    { label: "Risk Alerts", enabled: true },
                                    { label: "Strategy Signals", enabled: true },
                                    { label: "Daily P&L Report", enabled: false },
                                    { label: "System Errors", enabled: true },
                                ].map((n) => (
                                    <div key={n.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border-subtle)", fontSize: 13 }}>
                                        <span style={{ color: "var(--text-secondary)" }}>{n.label}</span>
                                        <div style={{
                                            width: 36, height: 20, borderRadius: 10,
                                            background: n.enabled ? "var(--green)" : "var(--bg-tertiary)",
                                            border: `1px solid ${n.enabled ? "var(--green)" : "var(--border-default)"}`,
                                            position: "relative", cursor: "pointer", transition: "all 0.2s",
                                        }}>
                                            <div style={{
                                                width: 16, height: 16, borderRadius: "50%",
                                                background: "white", position: "absolute", top: 1,
                                                left: n.enabled ? 18 : 1, transition: "left 0.2s",
                                            }} />
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
