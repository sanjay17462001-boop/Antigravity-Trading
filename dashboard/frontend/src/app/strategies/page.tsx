"use client";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useState, useCallback, useEffect } from "react";
import { Sparkles, Play, BarChart3, TrendingUp, Clock, Target, Shield, Sliders, Loader2, CheckCircle2, ChevronDown, ChevronUp, Save, Trash2, History, DollarSign, Plus, ToggleLeft, ToggleRight, GitCompare } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "";
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
    try { const r = await fetch(url, { ...opts, signal: ctrl.signal }); clearTimeout(timer); return r; } catch { clearTimeout(timer); return null; }
}

export default function StrategiesPage() {
    const [savedStrategies, setSavedStrategies] = useState<SavedStrategy[]>([]);
    const [activeStratId, setActiveStratId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    // AI
    const [desc, setDesc] = useState(""); const [parsing, setParsing] = useState(false); const [parsed, setParsed] = useState<any>(null); const [parseError, setParseError] = useState("");
    // Config
    const [stratName, setStratName] = useState(""); const [legs, setLegs] = useState<LegConfig[]>([]);
    const [entryTime, setEntryTime] = useState("09:20"); const [exitTime, setExitTime] = useState("15:15");
    const [slPct, setSlPct] = useState(25); const [slType, setSlType] = useState("hard");
    const [targetPct, setTargetPct] = useState(0); const [targetType, setTargetType] = useState("hard");
    const [lotSize, setLotSize] = useState(25);
    const [fromDate, setFromDate] = useState("2024-01-01"); const [toDate, setToDate] = useState("2024-12-31");
    const [slippage, setSlippage] = useState(0.5); const [brokerage, setBrokerage] = useState(20);
    const [dteBucketsStr, setDteBucketsStr] = useState("0-3, 4-7, 8-14, 15+");
    // Backtest
    const [running, setRunning] = useState(false); const [result, setResult] = useState<any>(null); const [btError, setBtError] = useState("");
    // Cost layer toggle
    const [showCostAdjusted, setShowCostAdjusted] = useState(false);
    // Optimize
    const [optParam, setOptParam] = useState("sl_pct"); const [optLegIdx, setOptLegIdx] = useState(-1); // -1 = global
    const [optValues, setOptValues] = useState("15,20,25,30,35");
    const [optimizing, setOptimizing] = useState(false); const [optResults, setOptResults] = useState<any[] | null>(null);
    // History
    const [history, setHistory] = useState<any[]>([]);
    const [showTrades, setShowTrades] = useState(false);
    const [activeTab, setActiveTab] = useState<"results" | "optimize" | "costs" | "history">("results");

    useEffect(() => {
        setLoading(true);
        safeFetch(`${API}/api/strategy-ai/strategies/list`).then(r => r?.json()).then(d => { if (d) setSavedStrategies(d.strategies || []); }).catch(() => { }).finally(() => setLoading(false));
        safeFetch(`${API}/api/strategy-ai/history`).then(r => r?.json()).then(d => { if (d) setHistory(d.runs || []); }).catch(() => { });
    }, []);

    function parseDteBuckets(): number[][] | null {
        try {
            const buckets = dteBucketsStr.split(",").map(s => s.trim()).filter(s => s.length > 0)
                .map(p => p.endsWith("+") ? [parseInt(p), 999] : p.split("-").map(Number))
                .filter(b => b.length === 2 && b.every(n => !isNaN(n)));
            return buckets.length > 0 ? buckets : null;
        } catch { return null; }
    }

    const updateLeg = (idx: number, field: string, value: any) => {
        setLegs(prev => prev.map((l, i) => i === idx ? { ...l, [field]: value } : l));
    };

    const loadStrategy = (s: SavedStrategy) => {
        setActiveStratId(s.id); setStratName(s.name); setLegs(s.legs.map(l => ({ ...l, sl_pct: l.sl_pct ?? null, target_pct: l.target_pct ?? null, sl_type: l.sl_type || "hard", target_type: l.target_type || "hard" })));
        setEntryTime(s.entry_time); setExitTime(s.exit_time);
        setSlPct(s.sl_pct); setSlType(s.sl_type); setTargetPct(s.target_pct); setTargetType(s.target_type);
        setLotSize(s.lot_size || 25); setParsed({ name: s.name }); setResult(null); setBtError("");
    };

    const handleNewStrategy = () => {
        setActiveStratId(null); setStratName(""); setLegs([]); setParsed(null); setResult(null); setDesc(""); setBtError("");
    };

    const handleParse = useCallback(async () => {
        if (!desc.trim()) return;
        setParsing(true); setParseError(""); setParsed(null);
        try {
            const res = await safeFetch(`${API}/api/strategy-ai/parse`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ description: desc }) }, 30000);
            if (!res) throw new Error("API not reachable"); const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Parse failed");
            setParsed(data.config); setEntryTime(data.config.entry_time || "09:20"); setExitTime(data.config.exit_time || "15:15");
            setSlPct(data.config.sl_pct || 25); setSlType(data.config.sl_type || "hard");
            setTargetPct(data.config.target_pct || 0); setTargetType(data.config.target_type || "hard");
            setLegs((data.config.legs || []).map((l: any) => ({ ...l, sl_pct: l.sl_pct ?? null, target_pct: l.target_pct ?? null }))); setStratName(data.config.name || "");
        } catch (e: any) { setParseError(e.message); } finally { setParsing(false); }
    }, [desc]);

    const buildLegsPayload = () => legs.map((l, i) => ({ action: l.action, strike: l.strike, option_type: l.option_type, lots: l.lots, sl_pct: l.sl_pct, target_pct: l.target_pct }));

    const handleBacktest = useCallback(async () => {
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
            safeFetch(`${API}/api/strategy-ai/history`).then(r => r?.json()).then(d => { if (d) setHistory(d.runs || []); }).catch(() => { });
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

    const handleOptimize = useCallback(async () => {
        if (legs.length === 0) return;
        setOptimizing(true); setOptResults(null);
        const vals = optValues.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
        const results: any[] = [];
        for (const val of vals) {
            try {
                // Build modified legs/config for this value
                const modLegs = legs.map((l, i) => {
                    const leg = { ...l };
                    if (optLegIdx === -1 || optLegIdx === i) {
                        if (optParam === "sl_pct") leg.sl_pct = val;
                        else if (optParam === "target_pct") leg.target_pct = val;
                    }
                    return leg;
                });
                const modConfig: any = { name: `${stratName} [${optParam}=${val}]`, legs: modLegs.map(l => ({ action: l.action, strike: l.strike, option_type: l.option_type, lots: l.lots, sl_pct: l.sl_pct, target_pct: l.target_pct })), entry_time: entryTime, exit_time: exitTime, sl_pct: optLegIdx === -1 && optParam === "sl_pct" ? val : slPct, sl_type: slType, target_pct: optLegIdx === -1 && optParam === "target_pct" ? val : targetPct, target_type: targetType, lot_size: lotSize, from_date: fromDate, to_date: toDate, slippage_pts: slippage, brokerage_per_order: brokerage };
                const res = await safeFetch(`${API}/api/strategy-ai/backtest`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(modConfig) }, 120000);
                if (res?.ok) { const data = await res.json(); results.push({ value: val, ...data.summary, gross_pnl: data.summary.gross_pnl, net_pnl: data.summary.net_pnl, cost_total: data.cost_breakdown?.total }); }
            } catch { }
        }
        setOptResults(results); setOptimizing(false);
    }, [legs, stratName, entryTime, exitTime, slPct, slType, targetPct, targetType, lotSize, fromDate, toDate, optParam, optLegIdx, optValues, slippage, brokerage]);

    // Compute display metrics based on cost toggle
    const getMetric = (key: string) => {
        if (!result) return 0;
        const s = result.summary;
        if (key === "pnl") return showCostAdjusted ? s.net_pnl : s.gross_pnl;
        return s[key] || 0;
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
                            <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)" }}>Strategies ({savedStrategies.length})</span>
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
                        {/* AI Input */}
                        <div className="card" style={{ marginBottom: 14, padding: 14, border: "1px solid var(--accent-dim)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                                <Sparkles style={{ width: 14, height: 14, color: "var(--accent)" }} />
                                <span style={{ fontSize: 13, fontWeight: 700 }}>Describe Your Strategy</span>
                                <span style={{ fontSize: 9, color: "var(--text-dim)", marginLeft: "auto" }}>Gemini 2.5 Flash</span>
                            </div>
                            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder='e.g. Sell ATM straddle at 9:20 with CE SL 25%, PE SL 30%, exit at 15:15' style={{ width: "100%", minHeight: 50, padding: "6px 8px", background: "var(--bg-tertiary)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", color: "var(--text-primary)", fontSize: 12, fontFamily: "inherit", resize: "vertical", outline: "none" }} />
                            <div style={{ display: "flex", gap: 6, marginTop: 5, alignItems: "center" }}>
                                <button className="btn btn-primary" onClick={handleParse} disabled={parsing || !desc.trim()} style={{ fontSize: 11, padding: "5px 12px" }}>
                                    {parsing ? <Loader2 style={{ width: 12, height: 12, animation: "spin 1s linear infinite" }} /> : <Sparkles style={{ width: 12, height: 12 }} />}
                                    {parsing ? "Parsing..." : "Parse"}
                                </button>
                                {parseError && <span style={{ color: "var(--red-bright)", fontSize: 10 }}>{parseError}</span>}
                                {parsed && !parseError && <span style={{ color: "var(--green-bright)", fontSize: 10, display: "flex", alignItems: "center", gap: 3 }}><CheckCircle2 style={{ width: 11, height: 11 }} /> Parsed</span>}
                            </div>
                        </div>

                        {/* ── PER-LEG CONFIG ── */}
                        {legs.length > 0 && (<>
                            <div className="card" style={{ marginBottom: 12, padding: 14 }}>
                                <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}><Target style={{ width: 12, height: 12, color: "var(--accent)" }} /> Legs — Per-Leg Parameters</h4>
                                <div style={{ overflowX: "auto" }}>
                                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                                        <thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", fontSize: 9, color: "var(--text-dim)" }}>
                                            <th style={{ padding: "5px 4px", textAlign: "left" }}>LEG</th>
                                            <th style={{ padding: "5px 4px" }}>ACTION</th>
                                            <th style={{ padding: "5px 4px" }}>STRIKE</th>
                                            <th style={{ padding: "5px 4px" }}>TYPE</th>
                                            <th style={{ padding: "5px 4px" }}>LOTS</th>
                                            <th style={{ padding: "5px 4px" }}>SL %</th>
                                            <th style={{ padding: "5px 4px" }}>SL TYPE</th>
                                            <th style={{ padding: "5px 4px" }}>TARGET %</th>
                                            <th style={{ padding: "5px 4px" }}>TGT TYPE</th>
                                        </tr></thead>
                                        <tbody>
                                            {legs.map((leg, i) => (
                                                <tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                                    <td style={{ padding: "4px", fontWeight: 700, color: "var(--text-muted)" }}>#{i + 1}</td>
                                                    <td style={{ padding: "4px" }}>
                                                        <select value={leg.action} onChange={e => updateLeg(i, "action", e.target.value)} className="input-field" style={{ width: 60 }}>
                                                            <option value="SELL">SELL</option><option value="BUY">BUY</option>
                                                        </select>
                                                    </td>
                                                    <td style={{ padding: "4px" }}>
                                                        <input type="text" value={leg.strike} onChange={e => updateLeg(i, "strike", e.target.value)} className="input-field" style={{ width: 60 }} />
                                                    </td>
                                                    <td style={{ padding: "4px" }}>
                                                        <select value={leg.option_type} onChange={e => updateLeg(i, "option_type", e.target.value)} className="input-field" style={{ width: 50 }}>
                                                            <option value="CE">CE</option><option value="PE">PE</option>
                                                        </select>
                                                    </td>
                                                    <td style={{ padding: "4px" }}><input type="number" value={leg.lots} onChange={e => updateLeg(i, "lots", Number(e.target.value))} className="input-field" style={{ width: 40 }} min={1} /></td>
                                                    <td style={{ padding: "4px" }}><input type="number" value={leg.sl_pct ?? ""} onChange={e => updateLeg(i, "sl_pct", e.target.value === "" ? null : Number(e.target.value))} className="input-field" style={{ width: 50 }} placeholder="Global" /></td>
                                                    <td style={{ padding: "4px" }}>
                                                        <select value={leg.sl_type || slType} onChange={e => updateLeg(i, "sl_type", e.target.value)} className="input-field" style={{ width: 60 }}>
                                                            <option value="hard">Hard</option><option value="close">Close</option>
                                                        </select>
                                                    </td>
                                                    <td style={{ padding: "4px" }}><input type="number" value={leg.target_pct ?? ""} onChange={e => updateLeg(i, "target_pct", e.target.value === "" ? null : Number(e.target.value))} className="input-field" style={{ width: 50 }} placeholder="Global" /></td>
                                                    <td style={{ padding: "4px" }}>
                                                        <select value={leg.target_type || targetType} onChange={e => updateLeg(i, "target_type", e.target.value)} className="input-field" style={{ width: 60 }}>
                                                            <option value="hard">Hard</option><option value="close">Close</option>
                                                        </select>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 6, fontStyle: "italic" }}>
                                    Leave SL/Target blank to use global defaults below. Per-leg values override global.
                                </div>
                            </div>

                            {/* Global defaults + timing */}
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr 1fr", gap: 6, marginBottom: 10, fontSize: 10 }}>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Entry</span><input type="time" value={entryTime} onChange={e => setEntryTime(e.target.value)} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Exit</span><input type="time" value={exitTime} onChange={e => setExitTime(e.target.value)} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Global SL %</span><input type="number" value={slPct} onChange={e => setSlPct(Number(e.target.value))} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>SL Type</span><select value={slType} onChange={e => setSlType(e.target.value)} className="input-field"><option value="hard">Hard</option><option value="close">Close</option></select></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Global Target %</span><input type="number" value={targetPct} onChange={e => setTargetPct(Number(e.target.value))} className="input-field" /></label>
                                <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Lot Size</span><input type="number" value={lotSize} onChange={e => setLotSize(Number(e.target.value))} className="input-field" /></label>
                            </div>

                            {/* Date + Cost params (clearly separated) */}
                            <div className="card" style={{ marginBottom: 14, padding: 12, borderLeft: "3px solid var(--yellow)" }}>
                                <div style={{ fontSize: 10, fontWeight: 700, color: "var(--yellow)", marginBottom: 6 }}>⚙ BACKTEST SETTINGS & COST LAYER</div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr", gap: 6, fontSize: 10 }}>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>From</span><input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="input-field" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>To</span><input type="date" value={toDate} onChange={e => setToDate(e.target.value)} className="input-field" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Slippage (pts)</span><input type="number" value={slippage} onChange={e => setSlippage(Number(e.target.value))} className="input-field" step="0.1" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Brokerage/order</span><input type="number" value={brokerage} onChange={e => setBrokerage(Number(e.target.value))} className="input-field" /></label>
                                    <label><span style={{ color: "var(--text-dim)", fontSize: 8 }}>DTE Buckets</span><input type="text" value={dteBucketsStr} onChange={e => setDteBucketsStr(e.target.value)} className="input-field" /></label>
                                </div>
                                <div style={{ fontSize: 8, color: "var(--text-dim)", marginTop: 4, fontStyle: "italic" }}>Slippage, brokerage, and taxes are applied as a <b>post-backtest overlay</b>. Toggle Gross/Net in results to see raw vs cost-adjusted.</div>
                            </div>

                            {/* Run + Save */}
                            <div style={{ display: "flex", gap: 6, marginBottom: 14, alignItems: "center" }}>
                                <button className="btn btn-primary" onClick={handleBacktest} disabled={running} style={{ fontSize: 11, padding: "6px 14px" }}>
                                    {running ? <Loader2 style={{ width: 12, height: 12, animation: "spin 1s linear infinite" }} /> : <Play style={{ width: 12, height: 12 }} />}
                                    {running ? "Running..." : "Run Backtest"}
                                </button>
                                <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
                                    <input type="text" value={stratName} onChange={e => setStratName(e.target.value)} placeholder="Strategy name" className="input-field" style={{ width: 160 }} />
                                    <button className="btn btn-secondary" onClick={handleSave} disabled={!stratName || legs.length === 0} style={{ fontSize: 11, padding: "5px 12px" }}><Save style={{ width: 11, height: 11 }} /> Save</button>
                                </div>
                                {btError && <span style={{ color: "var(--red-bright)", fontSize: 10 }}>{btError}</span>}
                            </div>
                        </>)}

                        {/* ════════ RESULTS ════════ */}
                        {result && (<div>
                            <div style={{ display: "flex", gap: 0, marginBottom: 10, borderBottom: "1px solid var(--border-subtle)", alignItems: "center" }}>
                                {([{ key: "results", icon: <BarChart3 style={{ width: 11, height: 11 }} />, label: "Results" }, { key: "costs", icon: <DollarSign style={{ width: 11, height: 11 }} />, label: "Cost Breakdown" }, { key: "optimize", icon: <GitCompare style={{ width: 11, height: 11 }} />, label: "Optimize & Compare" }, { key: "history", icon: <History style={{ width: 11, height: 11 }} />, label: "Run History" }] as const).map(tab => (
                                    <button key={tab.key} onClick={() => setActiveTab(tab.key as any)} style={{ padding: "6px 14px", background: "none", border: "none", borderBottom: activeTab === tab.key ? "2px solid var(--accent)" : "2px solid transparent", color: activeTab === tab.key ? "var(--accent)" : "var(--text-muted)", fontWeight: activeTab === tab.key ? 700 : 400, fontSize: 11, cursor: "pointer", display: "flex", alignItems: "center", gap: 3 }}>{tab.icon} {tab.label}</button>
                                ))}
                                {/* Gross/Net toggle */}
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
                                        {result.equity_curve.length > 0 && (() => { const d = result.equity_curve; const mx = Math.max(...d.map((p: any) => p.cumulative)); const mn = Math.min(...d.map((p: any) => p.cumulative)); const rg = mx - mn || 1; return (<svg viewBox={`0 0 ${d.length} 100`} width="100%" height="100%" preserveAspectRatio="none"><polyline points={d.map((p: any, i: number) => `${i},${100 - ((p.cumulative - mn) / rg) * 100}`).join(" ")} fill="none" stroke="var(--accent)" strokeWidth="0.8" /><polygon points={`0,${100 - ((d[0].cumulative - mn) / rg) * 100} ${d.map((p: any, i: number) => `${i},${100 - ((p.cumulative - mn) / rg) * 100}`).join(" ")} ${d.length - 1},100 0,100`} fill="var(--accent)" opacity="0.08" /></svg>); })()}
                                    </div>
                                </div>
                                {/* DTE */}
                                {result.dte_breakdown && Object.keys(result.dte_breakdown).length > 0 && (<div className="card" style={{ marginBottom: 12, padding: 12 }}>
                                    <h4 style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>DTE Breakdown</h4>
                                    <div style={{ display: "grid", gridTemplateColumns: `repeat(${Object.keys(result.dte_breakdown).length}, 1fr)`, gap: 6 }}>
                                        {Object.entries(result.dte_breakdown).map(([b, s]: any) => (<div key={b} style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: 8, textAlign: "center" }}>
                                            <div style={{ fontWeight: 700, fontSize: 12, color: "var(--accent)" }}>{b}</div>
                                            <div style={{ fontSize: 9, color: "var(--text-dim)" }}>{s.count} trades</div>
                                            <div className="text-mono" style={{ fontSize: 12, fontWeight: 600, color: s.total_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(s.total_pnl)}</div>
                                        </div>))}
                                    </div>
                                </div>)}
                                {/* Trade log */}
                                <div className="card" style={{ padding: 12 }}>
                                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                                        <h4 style={{ fontSize: 11, fontWeight: 700 }}>Trade Log ({result.trades.length})</h4>
                                        <button className="btn-icon" onClick={() => setShowTrades(!showTrades)} style={{ width: 22, height: 22, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>{showTrades ? <ChevronUp style={{ width: 11, height: 11 }} /> : <ChevronDown style={{ width: 11, height: 11 }} />}</button>
                                    </div>
                                    {showTrades && <div style={{ overflowX: "auto", maxHeight: 280 }}><table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}><thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-dim)", fontSize: 8 }}>{["Date", "Leg", "Action", "Strike", "Entry", "Exit", "Reason", "DTE", "Gross", "Net"].map(h => <th key={h} style={{ padding: "3px" }}>{h}</th>)}</tr></thead><tbody>{result.trades.slice(0, 100).map((t: any, i: number) => (<tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}><td style={{ padding: "3px" }}>{t.date}</td><td style={{ padding: "3px" }}>{t.leg}</td><td style={{ padding: "3px" }}><span className={`tag ${t.action === "SELL" ? "tag-red" : "tag-green"}`} style={{ fontSize: 8, padding: "0 4px" }}>{t.action}</span></td><td className="text-mono" style={{ padding: "3px" }}>{t.strike} {t.option_type}</td><td className="text-mono" style={{ padding: "3px" }}>{t.entry_price?.toFixed(1)}</td><td className="text-mono" style={{ padding: "3px" }}>{t.exit_price?.toFixed(1)}</td><td style={{ padding: "3px", fontSize: 8 }}>{t.exit_reason?.replace("_", " ")}</td><td className="text-mono" style={{ padding: "3px" }}>{t.dte}</td><td className="text-mono" style={{ padding: "3px", color: t.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(t.gross_pnl)}</td><td className="text-mono" style={{ padding: "3px", fontWeight: 600, color: t.net_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(t.net_pnl)}</td></tr>))}</tbody></table></div>}
                                </div>
                            </>)}

                            {activeTab === "costs" && result.cost_breakdown && (<div className="card" style={{ padding: 14 }}>
                                <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Cost & Tax Breakdown (Post-Backtest Overlay)</h4>
                                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 12 }}>
                                    {[{ l: "Gross P&L", v: result.summary.gross_pnl, c: result.summary.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }, { l: "Total Costs", v: result.cost_breakdown.total, c: "var(--red-bright)" }, { l: "Net P&L", v: result.summary.net_pnl, c: result.summary.net_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }, { l: "Cost/Trade", v: result.cost_breakdown.total / (result.summary.total_trades || 1), c: "var(--text-primary)" }].map((item, i) => (<div key={i} style={{ background: i === 2 ? "rgba(52,211,153,0.06)" : "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: 12, textAlign: "center", border: i === 2 ? "1px solid rgba(52,211,153,0.15)" : "none" }}>
                                        <div style={{ fontSize: 9, textTransform: "uppercase", color: "var(--text-dim)", marginBottom: 3 }}>{item.l}</div>
                                        <div className="text-mono" style={{ fontSize: 16, fontWeight: 700, color: item.c }}>{i === 3 ? `Rs.${item.v.toFixed(0)}` : fmtRs(item.v)}</div>
                                    </div>))}
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                                    {[{ l: "Brokerage", v: result.cost_breakdown.brokerage }, { l: "STT", v: result.cost_breakdown.stt }, { l: "Exchange", v: result.cost_breakdown.exchange_charges }, { l: "GST", v: result.cost_breakdown.gst }, { l: "SEBI Fees", v: result.cost_breakdown.sebi_fees }, { l: "Stamp Duty", v: result.cost_breakdown.stamp_duty }, { l: "Slippage", v: result.cost_breakdown.slippage }, { l: "Cost % of Gross", v: result.summary.gross_pnl ? (result.cost_breakdown.total / Math.abs(result.summary.gross_pnl) * 100) : 0 }].map((item, i) => (<div key={i} style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: 10, textAlign: "center" }}>
                                        <div style={{ fontSize: 8, textTransform: "uppercase", color: "var(--text-dim)", marginBottom: 3 }}>{item.l}</div>
                                        <div className="text-mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{i === 7 ? `${item.v.toFixed(1)}%` : `Rs.${item.v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`}</div>
                                    </div>))}
                                </div>
                            </div>)}

                            {activeTab === "optimize" && (<div className="card" style={{ padding: 14 }}>
                                <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, display: "flex", alignItems: "center", gap: 4 }}><GitCompare style={{ width: 13, height: 13, color: "var(--accent)" }} /> Parameter Optimization & Comparison</h4>
                                <div style={{ display: "grid", gridTemplateColumns: "120px 120px 1fr auto", gap: 6, alignItems: "end", marginBottom: 10 }}>
                                    <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Parameter</span><select value={optParam} onChange={e => setOptParam(e.target.value)} className="input-field"><option value="sl_pct">SL %</option><option value="target_pct">Target %</option></select></label>
                                    <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Apply To</span><select value={optLegIdx} onChange={e => setOptLegIdx(Number(e.target.value))} className="input-field"><option value={-1}>All Legs (Global)</option>{legs.map((l, i) => <option key={i} value={i}>Leg {i + 1}: {l.action} {l.strike} {l.option_type}</option>)}</select></label>
                                    <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", fontSize: 8 }}>Values to test (comma-separated)</span><input type="text" value={optValues} onChange={e => setOptValues(e.target.value)} className="input-field" /></label>
                                    <button className="btn btn-primary" onClick={handleOptimize} disabled={optimizing} style={{ fontSize: 10, padding: "5px 12px" }}>{optimizing ? <><Loader2 style={{ width: 11, height: 11, animation: "spin 1s linear infinite" }} /> Running...</> : "Run Optimization"}</button>
                                </div>
                                {optimizing && <div style={{ padding: 16, textAlign: "center", color: "var(--text-muted)", fontSize: 11 }}><Loader2 style={{ width: 16, height: 16, animation: "spin 1s linear infinite", margin: "0 auto 6px" }} /><br />Running {optValues.split(",").length} backtests...</div>}
                                {optResults && optResults.length > 0 && (<>
                                    <div style={{ overflowX: "auto" }}>
                                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                                            <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", color: "var(--text-dim)", fontSize: 9 }}>
                                                {[optParam.toUpperCase(), "TRADES", "WIN RATE", "GROSS P&L", "NET P&L", "COSTS", "MAX DD", "SHARPE", "PF", "EXPECTANCY"].map(h => <th key={h} style={{ padding: "5px 4px", textAlign: "right" }}>{h}</th>)}
                                            </tr></thead>
                                            <tbody>{optResults.map((r: any, i: number) => {
                                                const best = r.net_pnl === Math.max(...optResults.map((x: any) => x.net_pnl));
                                                return (<tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)", background: best ? "rgba(52,211,153,0.06)" : undefined }}>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", fontWeight: 700 }}>{r.value}%{best && <span style={{ color: "var(--green-bright)", fontSize: 8, marginLeft: 3 }}>★ BEST</span>}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right" }}>{r.total_trades}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", color: r.win_rate >= 55 ? "var(--green-bright)" : "var(--text-primary)" }}>{r.win_rate}%</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", color: r.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(r.gross_pnl)}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", fontWeight: 700, color: r.net_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(r.net_pnl)}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", color: "var(--text-dim)" }}>{r.cost_total ? `Rs.${r.cost_total.toLocaleString("en-IN", { maximumFractionDigits: 0 })}` : "—"}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", color: "var(--red-bright)" }}>Rs.{(r.max_drawdown || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right" }}>{(r.sharpe_ratio || 0).toFixed(2)}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right" }}>{(r.profit_factor || 0).toFixed(2)}</td>
                                                    <td className="text-mono" style={{ padding: "5px 4px", textAlign: "right", color: (r.expectancy || 0) >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(r.expectancy || 0)}</td>
                                                </tr>);
                                            })}</tbody>
                                        </table>
                                    </div>
                                </>)}
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
