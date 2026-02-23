"use client";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useState, useCallback, useEffect, useMemo } from "react";
import { Sparkles, Play, BarChart3, TrendingUp, Clock, Target, Shield, Sliders, Loader2, CheckCircle2, ChevronDown, ChevronUp, Save, Trash2, History, DollarSign, Plus, ToggleLeft, ToggleRight, GitCompare, Calendar, Layers, Code, AlertTriangle, Zap } from "lucide-react";
import { getApiUrl } from "@/lib/api";

const API = typeof window !== "undefined" ? getApiUrl() : "";
interface LegConfig { action: string; strike: string; option_type: string; lots: number; sl_pct: number | null; target_pct: number | null; sl_type?: string; target_type?: string; }
interface SavedStrategy { id: string; name: string; description: string; legs: LegConfig[]; entry_time: string; exit_time: string; sl_pct: number; sl_type: string; target_pct: number; target_type: string; lot_size: number; created_at: string; }

function fmtRs(v: number) { return `${v >= 0 ? "+" : "-"}Rs.${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`; }
function StatCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
    return (<div style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: "10px 12px", textAlign: "center", minWidth: 0 }}>
        <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-dim)", marginBottom: 3 }}>{label}</div>
        <div className="text-mono" style={{ fontSize: 15, fontWeight: 700, color: color || "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{value}</div>
        {sub && <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 2 }}>{sub}</div>}
    </div>);
}
async function safeFetch(url: string, opts?: RequestInit, timeoutMs = 8000) {
    const ctrl = new AbortController(); const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    const headers = { ...((opts?.headers as Record<string, string>) || {}), "ngrok-skip-browser-warning": "1" };
    try { const r = await fetch(url, { ...opts, headers, signal: ctrl.signal }); clearTimeout(timer); return r; } catch { clearTimeout(timer); return null; }
}

export default function StrategiesPage() {
    const [savedStrategies, setSavedStrategies] = useState<SavedStrategy[]>([]);
    const [activeStratId, setActiveStratId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    // ── AI Codegen Mode (primary) ──
    const [desc, setDesc] = useState("");
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [btError, setBtError] = useState("");
    const [generatedCode, setGeneratedCode] = useState("");
    const [showCode, setShowCode] = useState(false);
    const [executionErrors, setExecutionErrors] = useState<string[]>([]);
    const [stratLogs, setStratLogs] = useState<string[]>([]);
    const [showLogs, setShowLogs] = useState(false);

    // ── Settings ──
    const [lotSize, setLotSize] = useState(75);
    const [entryTime, setEntryTime] = useState("09:20");
    const [exitTime, setExitTime] = useState("15:15");
    const [fromDate, setFromDate] = useState("2024-01-01");
    const [toDate, setToDate] = useState("2024-12-31");
    const [slippage, setSlippage] = useState(0.5);
    const [brokerage, setBrokerage] = useState(20);

    // ── Results state ──
    const [showCostAdjusted, setShowCostAdjusted] = useState(false);
    const [showTrades, setShowTrades] = useState(false);
    const [activeTab, setActiveTab] = useState<"results" | "costs" | "history" | "pivot">("results");

    // ── Legacy manual mode ──
    const [manualMode, setManualMode] = useState(false);
    const [stratName, setStratName] = useState("");
    const [legs, setLegs] = useState<LegConfig[]>([]);
    const [slPct, setSlPct] = useState(25);
    const [slType, setSlType] = useState("hard");
    const [targetPct, setTargetPct] = useState(0);
    const [targetType, setTargetType] = useState("hard");
    const [dteBucketsStr, setDteBucketsStr] = useState("0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11+");

    // ── History ──
    const [history, setHistory] = useState<any[]>([]);

    useEffect(() => {
        setLoading(true);
        safeFetch(`${API}/api/strategy-ai/strategies/list`).then(r => r?.json()).then(d => { if (d) setSavedStrategies(d.strategies || []); }).catch(() => { }).finally(() => setLoading(false));
        safeFetch(`${API}/api/strategy-ai/history`).then(r => r?.json()).then(d => { if (d) setHistory(d.runs || []); }).catch(() => { });
    }, []);

    // ════════════════════════════════════════════════════
    // AI CODEGEN — main flow
    // ════════════════════════════════════════════════════

    const handleCodegen = useCallback(async () => {
        if (!desc.trim()) return;
        setRunning(true); setBtError(""); setResult(null); setGeneratedCode(""); setExecutionErrors([]); setStratLogs([]);
        try {
            const res = await safeFetch(`${API}/api/strategy-ai/codegen`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    description: desc,
                    from_date: fromDate,
                    to_date: toDate,
                    lot_size: lotSize,
                    entry_time: entryTime,
                    exit_time: exitTime,
                    slippage_pts: slippage,
                    brokerage_per_order: brokerage,
                }),
            }, 180000); // 3 min timeout
            if (!res) throw new Error("API not reachable");
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Codegen failed");
            setResult(data);
            setGeneratedCode(data.generated_code || "");
            setExecutionErrors(data.execution_errors || []);
            setStratLogs(data.logs || []);
            setActiveTab("results");
        } catch (e: any) { setBtError(e.message); } finally { setRunning(false); }
    }, [desc, fromDate, toDate, lotSize, entryTime, exitTime, slippage, brokerage]);

    // ════════════════════════════════════════════════════
    // Legacy manual mode handlers
    // ════════════════════════════════════════════════════

    const updateLeg = (idx: number, field: string, value: any) => {
        setLegs(prev => prev.map((l, i) => i === idx ? { ...l, [field]: value } : l));
    };

    const loadStrategy = (s: SavedStrategy) => {
        setActiveStratId(s.id); setStratName(s.name); setLegs(s.legs.map(l => ({ ...l, sl_pct: l.sl_pct ?? null, target_pct: l.target_pct ?? null, sl_type: l.sl_type || "hard", target_type: l.target_type || "hard" })));
        setEntryTime(s.entry_time); setExitTime(s.exit_time);
        setSlPct(s.sl_pct); setSlType(s.sl_type); setTargetPct(s.target_pct); setTargetType(s.target_type);
        setLotSize(s.lot_size || 25); setResult(null); setBtError(""); setManualMode(true);
    };

    const handleNewStrategy = () => {
        setActiveStratId(null); setStratName(""); setLegs([]); setResult(null); setDesc(""); setBtError(""); setManualMode(false);
    };

    function parseDteBuckets(): number[][] | null {
        try {
            const buckets = dteBucketsStr.split(",").map(s => s.trim()).filter(s => s.length > 0)
                .map(p => {
                    if (p.endsWith("+")) return [parseInt(p), 999];
                    if (p.includes("-")) return p.split("-").map(Number);
                    const n = parseInt(p); return isNaN(n) ? [] : [n, n];
                })
                .filter(b => b.length === 2 && b.every(n => !isNaN(n)));
            return buckets.length > 0 ? buckets : null;
        } catch { return null; }
    }

    const buildLegsPayload = () => legs.map((l) => ({ action: l.action, strike: l.strike, option_type: l.option_type, lots: l.lots, sl_pct: l.sl_pct, target_pct: l.target_pct }));

    const handleManualBacktest = useCallback(async () => {
        if (legs.length === 0) { setBtError("No legs"); return; }
        setRunning(true); setBtError(""); setResult(null);
        try {
            const res = await safeFetch(`${API}/api/strategy-ai/backtest`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: stratName || "Custom", legs: buildLegsPayload(), entry_time: entryTime, exit_time: exitTime, sl_pct: slPct, sl_type: slType, target_pct: targetPct, target_type: targetType, lot_size: lotSize, from_date: fromDate, to_date: toDate, slippage_pts: slippage, brokerage_per_order: brokerage, dte_buckets: parseDteBuckets() }),
            }, 120000);
            if (!res) throw new Error("API not reachable"); const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Backtest failed");
            setResult(data); setActiveTab("results");
        } catch (e: any) { setBtError(e.message); } finally { setRunning(false); }
    }, [legs, stratName, entryTime, exitTime, slPct, slType, targetPct, targetType, lotSize, fromDate, toDate, slippage, brokerage, dteBucketsStr]);

    const handleSave = useCallback(async () => {
        if (legs.length === 0 || !stratName) return;
        const res = await safeFetch(`${API}/api/strategy-ai/strategies/save`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: stratName, description: desc, legs: buildLegsPayload(), entry_time: entryTime, exit_time: exitTime, sl_pct: slPct, sl_type: slType, target_pct: targetPct, target_type: targetType, lot_size: lotSize }) });
        if (res?.ok) { safeFetch(`${API}/api/strategy-ai/strategies/list`).then(r => r?.json()).then(d => { if (d) setSavedStrategies(d.strategies || []); }); }
    }, [legs, stratName, desc, entryTime, exitTime, slPct, slType, targetPct, targetType, lotSize]);

    const deleteStrategy = async (id: string) => {
        await safeFetch(`${API}/api/strategy-ai/strategies/${id}`, { method: "DELETE" });
        setSavedStrategies(prev => prev.filter(s => s.id !== id)); if (activeStratId === id) handleNewStrategy();
    };

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="AI Strategy Builder" />
                <div style={{ display: "flex", gap: 0, height: "calc(100vh - var(--header-height))" }}>
                    {/* ════════ LEFT: Strategy List ════════ */}
                    <div style={{ width: 250, minWidth: 250, borderRight: "1px solid var(--border-subtle)", background: "var(--bg-secondary)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
                        <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)" }}>Saved ({savedStrategies.length})</span>
                            <button onClick={handleNewStrategy} className="btn-icon" style={{ width: 26, height: 26, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}><Plus style={{ width: 13, height: 13 }} /></button>
                        </div>
                        <div style={{ flex: 1, overflowY: "auto", padding: "4px 6px" }}>
                            {loading && <div style={{ padding: 16, textAlign: "center", color: "var(--text-dim)", fontSize: 11 }}>Loading...</div>}
                            {!loading && savedStrategies.length === 0 && <div style={{ padding: 16, textAlign: "center", color: "var(--text-dim)", fontSize: 11 }}>No strategies yet.</div>}
                            {savedStrategies.map(s => (
                                <div key={s.id} onClick={() => loadStrategy(s)} style={{ padding: "8px 10px", borderRadius: "var(--radius-sm)", cursor: "pointer", marginBottom: 2, background: activeStratId === s.id ? "var(--accent-dim)" : "transparent", borderLeft: activeStratId === s.id ? "3px solid var(--accent)" : "3px solid transparent" }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                        <span style={{ fontSize: 11, fontWeight: activeStratId === s.id ? 700 : 500, color: activeStratId === s.id ? "var(--accent)" : "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 170 }}>{s.name}</span>
                                        <button onClick={e => { e.stopPropagation(); deleteStrategy(s.id); }} style={{ background: "none", border: "none", cursor: "pointer", padding: 2, color: "var(--text-dim)" }}><Trash2 style={{ width: 10, height: 10 }} /></button>
                                    </div>
                                    <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 2 }}>{s.legs?.length || 0} legs · {s.sl_pct}% {s.sl_type} · {s.entry_time}→{s.exit_time}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* ════════ RIGHT: Builder ════════ */}
                    <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

                        {/* ══ AI INPUT — Primary ══ */}
                        <div className="card" style={{ marginBottom: 14, padding: 14, border: "1px solid var(--accent-dim)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                                <Zap style={{ width: 15, height: 15, color: "var(--accent)" }} />
                                <span style={{ fontSize: 14, fontWeight: 700 }}>Describe Your Strategy</span>
                                <span style={{ fontSize: 9, color: "var(--text-dim)", marginLeft: "auto", background: "var(--bg-tertiary)", padding: "2px 6px", borderRadius: 4 }}>AI Code Generation · Gemini 2.5 Flash</span>
                            </div>
                            <div style={{ fontSize: 10, color: "var(--text-dim)", marginBottom: 8, lineHeight: 1.5 }}>
                                Write in plain English — <b>any</b> features: trailing SL, Rs-based global SL, profit locking, time-based rules, VIX filters, multi-leg adjustments, literally anything.
                                The AI will write and execute custom Python code for your strategy.
                            </div>
                            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder='Example: Sell ATM straddle at 9:21 with 40% hard SL. Trailing SL from 3% to 1%. Global SL Rs 2000. Lock profit at Rs 500 when it reaches Rs 1500. Lot size 65.' style={{ width: "100%", minHeight: 80, padding: "8px 10px", background: "var(--bg-tertiary)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", color: "var(--text-primary)", fontSize: 12, fontFamily: "inherit", resize: "vertical", outline: "none", lineHeight: 1.6 }} />

                            {/* Settings row */}
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr 1fr 1fr", gap: 6, marginTop: 8, fontSize: 10 }}>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>From</span><input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>To</span><input type="date" value={toDate} onChange={e => setToDate(e.target.value)} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Lot Size</span><input type="number" value={lotSize} onChange={e => setLotSize(Number(e.target.value))} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Entry</span><input type="time" value={entryTime} onChange={e => setEntryTime(e.target.value)} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Exit</span><input type="time" value={exitTime} onChange={e => setExitTime(e.target.value)} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Slippage</span><input type="number" value={slippage} onChange={e => setSlippage(Number(e.target.value))} className="input-field" step="0.1" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Brokerage</span><input type="number" value={brokerage} onChange={e => setBrokerage(Number(e.target.value))} className="input-field" /></label>
                            </div>

                            <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
                                <button className="btn btn-primary" onClick={handleCodegen} disabled={running || !desc.trim()} style={{ fontSize: 12, padding: "7px 18px", display: "flex", alignItems: "center", gap: 5 }}>
                                    {running ? <Loader2 style={{ width: 14, height: 14, animation: "spin 1s linear infinite" }} /> : <Zap style={{ width: 14, height: 14 }} />}
                                    {running ? "Generating & Running..." : "Generate & Run"}
                                </button>
                                {btError && <span style={{ color: "var(--red-bright)", fontSize: 10, maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis" }}>{btError}</span>}
                                {result && !btError && <span style={{ color: "var(--green-bright)", fontSize: 10, display: "flex", alignItems: "center", gap: 3 }}><CheckCircle2 style={{ width: 12, height: 12 }} /> Done — {result.summary?.total_trades || 0} trades</span>}
                                <div style={{ marginLeft: "auto" }}>
                                    <button onClick={() => setManualMode(!manualMode)} style={{ background: "none", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "4px 10px", cursor: "pointer", color: "var(--text-dim)", fontSize: 10 }}>
                                        {manualMode ? "← AI Mode" : "Manual Mode →"}
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* ══ Generated Code (collapsible) ══ */}
                        {generatedCode && (
                            <div className="card" style={{ marginBottom: 12, padding: 0, overflow: "hidden" }}>
                                <div onClick={() => setShowCode(!showCode)} style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: 5, cursor: "pointer", background: "var(--bg-tertiary)", borderBottom: showCode ? "1px solid var(--border-subtle)" : "none" }}>
                                    <Code style={{ width: 12, height: 12, color: "var(--accent)" }} />
                                    <span style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)" }}>Generated Strategy Code</span>
                                    <span style={{ fontSize: 9, color: "var(--text-dim)", marginLeft: 4 }}>({generatedCode.split("\n").length} lines)</span>
                                    {showCode ? <ChevronUp style={{ width: 11, height: 11, marginLeft: "auto" }} /> : <ChevronDown style={{ width: 11, height: 11, marginLeft: "auto" }} />}
                                </div>
                                {showCode && (
                                    <pre style={{ margin: 0, padding: "12px 14px", fontSize: 11, lineHeight: 1.5, overflowX: "auto", maxHeight: 400, background: "var(--bg-primary)", color: "var(--text-primary)", fontFamily: "'Fira Code', 'JetBrains Mono', monospace" }}>{generatedCode}</pre>
                                )}
                            </div>
                        )}

                        {/* ══ Execution Errors ══ */}
                        {executionErrors.length > 0 && (
                            <div className="card" style={{ marginBottom: 12, padding: 10, border: "1px solid rgba(239,68,68,0.3)", background: "rgba(239,68,68,0.04)" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 4 }}>
                                    <AlertTriangle style={{ width: 12, height: 12, color: "var(--red-bright)" }} />
                                    <span style={{ fontSize: 10, fontWeight: 700, color: "var(--red-bright)" }}>Execution Warnings ({executionErrors.length})</span>
                                </div>
                                <div style={{ fontSize: 9, color: "var(--text-dim)", maxHeight: 100, overflowY: "auto" }}>
                                    {executionErrors.slice(0, 10).map((e, i) => <div key={i} style={{ marginBottom: 2 }}>{e}</div>)}
                                    {executionErrors.length > 10 && <div>...and {executionErrors.length - 10} more</div>}
                                </div>
                            </div>
                        )}

                        {/* ══ Strategy Logs ══ */}
                        {stratLogs.length > 0 && (
                            <div className="card" style={{ marginBottom: 12, padding: 0, overflow: "hidden" }}>
                                <div onClick={() => setShowLogs(!showLogs)} style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: 5, cursor: "pointer", background: "var(--bg-tertiary)" }}>
                                    <span style={{ fontSize: 10, fontWeight: 600, color: "var(--text-muted)" }}>Strategy Logs ({stratLogs.length})</span>
                                    {showLogs ? <ChevronUp style={{ width: 11, height: 11, marginLeft: "auto" }} /> : <ChevronDown style={{ width: 11, height: 11, marginLeft: "auto" }} />}
                                </div>
                                {showLogs && (
                                    <div style={{ padding: "8px 14px", fontSize: 9, color: "var(--text-dim)", maxHeight: 200, overflowY: "auto", fontFamily: "monospace" }}>
                                        {stratLogs.slice(0, 100).map((l, i) => <div key={i}>{l}</div>)}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* ══ MANUAL MODE (legacy leg builder) ══ */}
                        {manualMode && (<>
                            <div className="card" style={{ marginBottom: 12, padding: 14, borderLeft: "3px solid var(--yellow)" }}>
                                <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 4, color: "var(--yellow)" }}><Sliders style={{ width: 12, height: 12 }} /> Manual Leg Builder (Legacy)</h4>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr", gap: 6, marginBottom: 10, fontSize: 10 }}>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Name</span><input type="text" value={stratName} onChange={e => setStratName(e.target.value)} className="input-field" placeholder="Strategy name" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Global SL %</span><input type="number" value={slPct} onChange={e => setSlPct(Number(e.target.value))} className="input-field" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>SL Type</span><select value={slType} onChange={e => setSlType(e.target.value)} className="input-field"><option value="hard">Hard</option><option value="close">Close</option></select></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Target %</span><input type="number" value={targetPct} onChange={e => setTargetPct(Number(e.target.value))} className="input-field" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Target Type</span><select value={targetType} onChange={e => setTargetType(e.target.value)} className="input-field"><option value="hard">Hard</option><option value="close">Close</option></select></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>DTE Buckets</span><input type="text" value={dteBucketsStr} onChange={e => setDteBucketsStr(e.target.value)} className="input-field" /></label>
                                </div>

                                {legs.length > 0 && <div style={{ overflowX: "auto", marginBottom: 8 }}>
                                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                                        <thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", fontSize: 9, color: "var(--text-dim)" }}>
                                            <th style={{ padding: "5px 4px", textAlign: "left" }}>LEG</th><th style={{ padding: "5px 4px" }}>ACTION</th><th style={{ padding: "5px 4px" }}>STRIKE</th><th style={{ padding: "5px 4px" }}>TYPE</th><th style={{ padding: "5px 4px" }}>LOTS</th><th style={{ padding: "5px 4px" }}>SL %</th><th style={{ padding: "5px 4px" }}>TARGET %</th>
                                        </tr></thead>
                                        <tbody>{legs.map((leg, i) => (
                                            <tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                                <td style={{ padding: "4px", fontWeight: 700, color: "var(--text-muted)" }}>#{i + 1}</td>
                                                <td style={{ padding: "4px" }}><select value={leg.action} onChange={e => updateLeg(i, "action", e.target.value)} className="input-field" style={{ width: 60 }}><option value="SELL">SELL</option><option value="BUY">BUY</option></select></td>
                                                <td style={{ padding: "4px" }}><input type="text" value={leg.strike} onChange={e => updateLeg(i, "strike", e.target.value)} className="input-field" style={{ width: 60 }} /></td>
                                                <td style={{ padding: "4px" }}><select value={leg.option_type} onChange={e => updateLeg(i, "option_type", e.target.value)} className="input-field" style={{ width: 50 }}><option value="CE">CE</option><option value="PE">PE</option></select></td>
                                                <td style={{ padding: "4px" }}><input type="number" value={leg.lots} onChange={e => updateLeg(i, "lots", Number(e.target.value))} className="input-field" style={{ width: 40 }} min={1} /></td>
                                                <td style={{ padding: "4px" }}><input type="number" value={leg.sl_pct ?? ""} onChange={e => updateLeg(i, "sl_pct", e.target.value === "" ? null : Number(e.target.value))} className="input-field" style={{ width: 50 }} placeholder="Gbl" /></td>
                                                <td style={{ padding: "4px" }}><input type="number" value={leg.target_pct ?? ""} onChange={e => updateLeg(i, "target_pct", e.target.value === "" ? null : Number(e.target.value))} className="input-field" style={{ width: 50 }} placeholder="Gbl" /></td>
                                            </tr>
                                        ))}</tbody>
                                    </table>
                                </div>}
                                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                                    <button className="btn btn-primary" onClick={handleManualBacktest} disabled={running || legs.length === 0} style={{ fontSize: 11, padding: "5px 12px" }}>
                                        {running ? <Loader2 style={{ width: 12, height: 12, animation: "spin 1s linear infinite" }} /> : <Play style={{ width: 12, height: 12 }} />}
                                        {running ? "Running..." : "Run Backtest"}
                                    </button>
                                    <button className="btn btn-secondary" onClick={handleSave} disabled={!stratName || legs.length === 0} style={{ fontSize: 11, padding: "5px 10px" }}><Save style={{ width: 11, height: 11 }} /> Save</button>
                                    <button onClick={() => setLegs([...legs, { action: "SELL", strike: "ATM", option_type: "CE", lots: 1, sl_pct: null, target_pct: null }])} style={{ background: "none", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "4px 10px", cursor: "pointer", color: "var(--text-dim)", fontSize: 10 }}>+ Add Leg</button>
                                </div>
                            </div>
                        </>)}

                        {/* ════════ RESULTS ════════ */}
                        {result && result.summary && (<div>
                            <div style={{ display: "flex", gap: 0, marginBottom: 10, borderBottom: "1px solid var(--border-subtle)", alignItems: "center" }}>
                                {([{ key: "results", icon: <BarChart3 style={{ width: 11, height: 11 }} />, label: "Results" }, { key: "costs", icon: <DollarSign style={{ width: 11, height: 11 }} />, label: "Cost Breakdown" }, { key: "history", icon: <History style={{ width: 11, height: 11 }} />, label: "Run History" }] as const).map(tab => (
                                    <button key={tab.key} onClick={() => setActiveTab(tab.key as any)} style={{ padding: "6px 14px", background: "none", border: "none", borderBottom: activeTab === tab.key ? "2px solid var(--accent)" : "2px solid transparent", color: activeTab === tab.key ? "var(--accent)" : "var(--text-muted)", fontWeight: activeTab === tab.key ? 700 : 400, fontSize: 11, cursor: "pointer", display: "flex", alignItems: "center", gap: 3 }}>{tab.icon} {tab.label}</button>
                                ))}
                                {activeTab === "results" && <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, cursor: "pointer", fontSize: 10 }} onClick={() => setShowCostAdjusted(!showCostAdjusted)}>
                                    {showCostAdjusted ? <ToggleRight style={{ width: 16, height: 16, color: "var(--accent)" }} /> : <ToggleLeft style={{ width: 16, height: 16, color: "var(--text-dim)" }} />}
                                    <span style={{ color: showCostAdjusted ? "var(--accent)" : "var(--text-dim)", fontWeight: 600 }}>{showCostAdjusted ? "Net (after costs)" : "Gross (raw)"}</span>
                                </div>}
                            </div>

                            {activeTab === "results" && (<>
                                <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 8 }}>
                                    <StatCard label="Trades" value={`${result.summary.total_trades}`} sub={`${result.summary.trading_days} days`} />
                                    <StatCard label="Win Rate" value={`${result.summary.win_rate}%`} color={result.summary.win_rate >= 55 ? "var(--green-bright)" : "var(--red-bright)"} sub={`${result.summary.winners}W / ${result.summary.losers}L`} />
                                    <StatCard label={showCostAdjusted ? "Net P&L" : "Gross P&L"} value={fmtRs(showCostAdjusted ? result.summary.net_pnl : result.summary.gross_pnl)} color={(showCostAdjusted ? result.summary.net_pnl : result.summary.gross_pnl) >= 0 ? "var(--green-bright)" : "var(--red-bright)"} sub={showCostAdjusted ? `Gross: ${fmtRs(result.summary.gross_pnl)}` : `Net: ${fmtRs(result.summary.net_pnl)}`} />
                                    <StatCard label="Max Drawdown" value={`Rs.${result.summary.max_drawdown.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} color="var(--red-bright)" />
                                    <StatCard label="Profit Factor" value={`${result.summary.profit_factor}`} color={result.summary.profit_factor >= 1.5 ? "var(--green-bright)" : "var(--text-primary)"} />
                                    <StatCard label="Sharpe" value={`${result.summary.sharpe_ratio}`} />
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 12 }}>
                                    <StatCard label="Payoff" value={`${result.summary.payoff_ratio}`} sub="AvgW/AvgL" />
                                    <StatCard label="Expectancy" value={fmtRs(result.summary.expectancy)} color={result.summary.expectancy >= 0 ? "var(--green-bright)" : "var(--red-bright)"} sub="Per trade" />
                                    <StatCard label="Avg Win" value={fmtRs(result.summary.avg_win)} color="var(--green-bright)" />
                                    <StatCard label="Avg Loss" value={fmtRs(result.summary.avg_loss)} color="var(--red-bright)" />
                                    <StatCard label="Max Win" value={fmtRs(result.summary.max_win)} color="var(--green-bright)" sub={`Streak: ${result.summary.max_consecutive_wins}`} />
                                    <StatCard label="Max Loss" value={fmtRs(result.summary.max_loss)} color="var(--red-bright)" sub={`Streak: ${result.summary.max_consecutive_losses}`} />
                                </div>
                                {/* Equity */}
                                <div className="card" style={{ marginBottom: 12, padding: 12 }}>
                                    <h4 style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>Equity Curve</h4>
                                    <div style={{ height: 140 }}>
                                        {result.equity_curve && result.equity_curve.length > 0 && (() => { const d = result.equity_curve; const mx = Math.max(...d.map((p: any) => p.cumulative)); const mn = Math.min(...d.map((p: any) => p.cumulative)); const rg = mx - mn || 1; return (<svg viewBox={`0 0 ${d.length} 100`} width="100%" height="100%" preserveAspectRatio="none"><polyline points={d.map((p: any, i: number) => `${i},${100 - ((p.cumulative - mn) / rg) * 100}`).join(" ")} fill="none" stroke="var(--accent)" strokeWidth="0.8" /><polygon points={`0,${100 - ((d[0].cumulative - mn) / rg) * 100} ${d.map((p: any, i: number) => `${i},${100 - ((p.cumulative - mn) / rg) * 100}`).join(" ")} ${d.length - 1},100 0,100`} fill="var(--accent)" opacity="0.08" /></svg>); })()}
                                    </div>
                                </div>
                                {/* Trade log */}
                                <div className="card" style={{ padding: 12 }}>
                                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                                        <h4 style={{ fontSize: 11, fontWeight: 700 }}>Trade Log ({result.trades?.length || 0})</h4>
                                        <button className="btn-icon" onClick={() => setShowTrades(!showTrades)} style={{ width: 22, height: 22, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>{showTrades ? <ChevronUp style={{ width: 11, height: 11 }} /> : <ChevronDown style={{ width: 11, height: 11 }} />}</button>
                                    </div>
                                    {showTrades && <div style={{ overflowX: "auto", maxHeight: 280 }}><table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}><thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-dim)", fontSize: 8 }}>{["Date", "Label", "Action", "Strike", "Entry", "Exit", "Reason", "DTE", "Gross", "Net"].map(h => <th key={h} style={{ padding: "3px" }}>{h}</th>)}</tr></thead><tbody>{(result.trades || []).slice(0, 200).map((t: any, i: number) => (
                                        <tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}><td style={{ padding: "3px" }}>{t.date}</td><td style={{ padding: "3px", fontSize: 8, color: "var(--text-dim)" }}>{t.label || t.leg}</td><td style={{ padding: "3px" }}><span className={`tag ${t.action === "SELL" ? "tag-red" : "tag-green"}`} style={{ fontSize: 8, padding: "0 4px" }}>{t.action}</span></td><td className="text-mono" style={{ padding: "3px" }}>{t.strike} {t.option_type}</td><td className="text-mono" style={{ padding: "3px" }}>{t.entry_price?.toFixed(1)}</td><td className="text-mono" style={{ padding: "3px" }}>{t.exit_price?.toFixed(1)}</td><td style={{ padding: "3px", fontSize: 8 }}>{t.exit_reason?.replace("_", " ")}</td><td className="text-mono" style={{ padding: "3px" }}>{t.dte}</td><td className="text-mono" style={{ padding: "3px", color: t.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(t.gross_pnl)}</td><td className="text-mono" style={{ padding: "3px", fontWeight: 600, color: t.net_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(t.net_pnl)}</td></tr>
                                    ))}</tbody></table></div>}
                                </div>
                            </>)}

                            {activeTab === "costs" && result.summary && (<div className="card" style={{ padding: 14 }}>
                                <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Cost & Tax Breakdown</h4>
                                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 12 }}>
                                    {[{ l: "Gross P&L", v: result.summary.gross_pnl, c: result.summary.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }, { l: "Total Costs", v: result.summary.total_cost || 0, c: "var(--red-bright)" }, { l: "Net P&L", v: result.summary.net_pnl, c: result.summary.net_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }].map((item, i) => (<div key={i} style={{ background: i === 2 ? "rgba(52,211,153,0.06)" : "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: 12, textAlign: "center", border: i === 2 ? "1px solid rgba(52,211,153,0.15)" : "none" }}>
                                        <div style={{ fontSize: 9, textTransform: "uppercase", color: "var(--text-dim)", marginBottom: 3 }}>{item.l}</div>
                                        <div className="text-mono" style={{ fontSize: 16, fontWeight: 700, color: item.c }}>{fmtRs(item.v)}</div>
                                    </div>))}
                                </div>
                            </div>)}

                            {activeTab === "history" && (<div className="card" style={{ padding: 14 }}>
                                <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Backtest Run History</h4>
                                {history.length === 0 ? <p style={{ color: "var(--text-dim)", fontSize: 11 }}>No runs yet.</p> : <div style={{ overflowX: "auto" }}><table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}><thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-dim)", fontSize: 8 }}>{["RUN", "STRATEGY", "PERIOD", "TRADES", "WR", "GROSS", "NET", "MAX DD", "PF"].map(h => <th key={h} style={{ padding: "5px 3px" }}>{h}</th>)}</tr></thead><tbody>{history.map((run: any, i: number) => (<tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}><td style={{ padding: "4px 3px", fontFamily: "monospace", fontSize: 8 }}>{run.run_id?.slice(0, 6)}</td><td style={{ padding: "4px 3px", fontWeight: 600, maxWidth: 130, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.name}</td><td style={{ padding: "4px 3px", fontSize: 9, color: "var(--text-dim)" }}>{run.from_date}→{run.to_date}</td><td className="text-mono" style={{ padding: "4px 3px", textAlign: "right" }}>{run.summary?.total_trades}</td><td className="text-mono" style={{ padding: "4px 3px", textAlign: "right" }}>{run.summary?.win_rate}%</td><td className="text-mono" style={{ padding: "4px 3px", textAlign: "right", color: (run.summary?.gross_pnl || 0) >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(run.summary?.gross_pnl || 0)}</td><td className="text-mono" style={{ padding: "4px 3px", textAlign: "right", fontWeight: 700, color: (run.summary?.net_pnl || 0) >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(run.summary?.net_pnl || 0)}</td><td className="text-mono" style={{ padding: "4px 3px", textAlign: "right", color: "var(--red-bright)" }}>Rs.{(run.summary?.max_drawdown || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td><td className="text-mono" style={{ padding: "4px 3px", textAlign: "right" }}>{run.summary?.profit_factor || "—"}</td></tr>))}</tbody></table></div>}
                            </div>)}
                        </div>)}
                    </div>
                </div>
            </main>
            <style jsx global>{`.input-field{padding:4px 6px;background:var(--bg-tertiary);border:1px solid var(--border-subtle);border-radius:var(--radius-sm);color:var(--text-primary);font-size:11px;font-family:inherit;outline:none;width:100%}.input-field:focus{border-color:var(--accent)}@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
        </div>
    );
}
