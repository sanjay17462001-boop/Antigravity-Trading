"use client";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useState, useMemo, useEffect, useCallback } from "react";
import { BarChart3, TrendingUp, Sliders, ChevronDown, ChevronUp, Calendar, Zap, ToggleLeft, ToggleRight, Layers, Activity, Maximize2, X } from "lucide-react";
import { STRATEGIES, StrategyData, ModeData } from "./strategyData";

interface TradeRow { date: string; dte: number; option_type: string; label: string; action: string; entry_price: number; exit_price: number; entry_time: string; exit_time: string; exit_reason: string; gross_pnl: number; lots: number; quantity: number; strike: string; absolute_strike: number; vix: number; }
interface EquityPoint { date: string; daily_pnl: number; cumulative: number; drawdown: number; }

function fmtRs(v: number) { return `${v >= 0 ? "+" : ""}Rs.${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`; }

function StatCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
    return (<div style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: "10px 12px", textAlign: "center", minWidth: 0 }}>
        <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-dim)", marginBottom: 3 }}>{label}</div>
        <div className="text-mono" style={{ fontSize: 15, fontWeight: 700, color: color || "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{value}</div>
        {sub && <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 2 }}>{sub}</div>}
    </div>);
}

function Section({ title, icon, open, onToggle, onEnlarge, children }: { title: string; icon: React.ReactNode; open: boolean; onToggle: () => void; onEnlarge: () => void; children: React.ReactNode }) {
    return (<div className="card" style={{ marginBottom: 14, padding: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div onClick={onToggle} style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer", flex: 1 }}>
                {icon}<h4 style={{ fontSize: 12, fontWeight: 700, flex: 1 }}>{title}</h4>
                {open ? <ChevronUp style={{ width: 13, height: 13 }} /> : <ChevronDown style={{ width: 13, height: 13 }} />}
            </div>
            {open && <Maximize2 onClick={onEnlarge} style={{ width: 13, height: 13, cursor: "pointer", color: "var(--text-dim)", marginLeft: 4 }} title="Enlarge" />}
        </div>
        {open && <div style={{ marginTop: 8 }}>{children}</div>}
    </div>);
}

function FullscreenModal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
    return (<div style={{ position: "fixed", inset: 0, zIndex: 9999, background: "rgba(0,0,0,0.85)", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", padding: "12px 20px", borderBottom: "1px solid var(--border-subtle)", background: "var(--bg-secondary)" }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, flex: 1 }}>{title}</h3>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-primary)", padding: 4 }}><X style={{ width: 18, height: 18 }} /></button>
        </div>
        <div style={{ flex: 1, overflow: "auto", padding: 20, background: "var(--bg-primary)" }}>{children}</div>
    </div>);
}

function EquityCurve({ data, height = 120, ddHeight = 60 }: { data: EquityPoint[]; height?: number; ddHeight?: number }) {
    if (!data.length) return null;
    const mx = Math.max(...data.map(p => p.cumulative)); const mn = Math.min(...data.map(p => p.cumulative), 0);
    const rg = mx - mn || 1; const mxDD = Math.max(...data.map(p => p.drawdown), 1);
    // Build month labels
    const labels: { idx: number; label: string }[] = [];
    let lastLabel = "";
    data.forEach((p, i) => {
        const d = p.date; const ym = d.substring(0, 7);
        const m = parseInt(d.substring(5, 7)); const y = d.substring(2, 4);
        const lbl = m === 1 ? `'${y}` : ["", "J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"][m];
        if (ym !== lastLabel) { labels.push({ idx: i, label: lbl }); lastLabel = ym; }
    });
    const W = data.length; const padB = 18;
    return (<div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div><div style={{ fontSize: 9, color: "var(--text-dim)", marginBottom: 2 }}>EQUITY CURVE</div>
            <svg viewBox={`0 -2 ${W} ${100 + padB + 2}`} width="100%" height={height + 30} preserveAspectRatio="none" style={{ display: "block" }}>
                <polyline points={data.map((p, i) => `${i},${100 - ((p.cumulative - mn) / rg) * 100}`).join(" ")} fill="none" stroke="var(--accent)" strokeWidth="0.5" />
                <polygon points={`0,${100 - ((data[0].cumulative - mn) / rg) * 100} ${data.map((p, i) => `${i},${100 - ((p.cumulative - mn) / rg) * 100}`).join(" ")} ${W - 1},100 0,100`} fill="var(--accent)" opacity="0.08" />
                <line x1="0" y1="100" x2={W} y2="100" stroke="var(--border-subtle)" strokeWidth="0.3" />
                {labels.map((l, i) => (<g key={i}><line x1={l.idx} y1="100" x2={l.idx} y2="103" stroke="var(--text-dim)" strokeWidth="0.3" /><text x={l.idx + 1} y="112" fill="var(--text-dim)" fontSize="6" fontFamily="monospace">{l.label}</text></g>))}
            </svg>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 8, color: "var(--text-dim)", marginTop: -4 }}>
                <span>{data[0].date}</span><span>Peak: {fmtRs(mx)}</span><span>{data[data.length - 1].date}</span>
            </div>
        </div>
        <div><div style={{ fontSize: 9, color: "var(--text-dim)", marginBottom: 2 }}>DRAWDOWN</div>
            <svg viewBox={`0 -2 ${W} ${100 + padB + 2}`} width="100%" height={ddHeight + 30} preserveAspectRatio="none" style={{ display: "block" }}>
                <polyline points={data.map((p, i) => `${i},${(p.drawdown / mxDD) * 100}`).join(" ")} fill="none" stroke="var(--red-bright)" strokeWidth="0.5" />
                <polygon points={`0,0 ${data.map((p, i) => `${i},${(p.drawdown / mxDD) * 100}`).join(" ")} ${W - 1},0`} fill="var(--red-bright)" opacity="0.08" />
                <line x1="0" y1="100" x2={W} y2="100" stroke="var(--border-subtle)" strokeWidth="0.3" />
                {labels.map((l, i) => (<g key={i}><line x1={l.idx} y1="100" x2={l.idx} y2="103" stroke="var(--text-dim)" strokeWidth="0.3" /><text x={l.idx + 1} y="112" fill="var(--text-dim)" fontSize="6" fontFamily="monospace">{l.label}</text></g>))}
            </svg>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 8, color: "var(--text-dim)", marginTop: -4 }}>
                <span>0</span><span>Max DD: Rs.{mxDD.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>
            </div>
        </div>
    </div>);
}

// ── Recompute all metrics from filtered trade array ──
function computeMetrics(trades: TradeRow[]): ModeData | null {
    if (!trades.length) return null;
    const total = trades.length;
    const winners = trades.filter(t => t.gross_pnl > 0).length;
    const losers = trades.filter(t => t.gross_pnl < 0).length;
    const gross = trades.reduce((s, t) => s + t.gross_pnl, 0);
    const wr = total > 0 ? +(winners / total * 100).toFixed(1) : 0;
    const wins = trades.filter(t => t.gross_pnl > 0).map(t => t.gross_pnl);
    const losses = trades.filter(t => t.gross_pnl < 0).map(t => t.gross_pnl);
    const avgW = wins.length ? Math.round(wins.reduce((a, b) => a + b, 0) / wins.length) : 0;
    const avgL = losses.length ? Math.round(losses.reduce((a, b) => a + b, 0) / losses.length) : 0;
    const maxW = wins.length ? Math.round(Math.max(...wins)) : 0;
    const maxL = losses.length ? Math.round(Math.min(...losses)) : 0;
    const pf = losses.length ? +((wins.reduce((a, b) => a + b, 0)) / Math.abs(losses.reduce((a, b) => a + b, 0))).toFixed(2) : 999;
    const pr = avgL !== 0 ? +(avgW / Math.abs(avgL)).toFixed(2) : 999;
    const exp = Math.round((wr / 100 * avgW) - ((1 - wr / 100) * Math.abs(avgL)));
    // Drawdown
    let eq = 0, peak = 0, mdd = 0;
    const dailyMap: Record<string, number> = {};
    trades.forEach(t => { eq += t.gross_pnl; peak = Math.max(peak, eq); mdd = Math.max(mdd, peak - eq); dailyMap[t.date] = (dailyMap[t.date] || 0) + t.gross_pnl; });
    const vals = Object.values(dailyMap);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    const std = Math.sqrt(vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length);
    const sharpe = std > 0 ? +((mean / std) * Math.sqrt(252)).toFixed(2) : 0;
    const calmar = mdd > 0 ? +((gross * 252 / vals.length / mdd)).toFixed(2) : 0;
    // Consec
    let cw = 0, mxcw = 0, cl = 0, mxcl = 0;
    trades.forEach(t => { if (t.gross_pnl > 0) { cw++; mxcw = Math.max(mxcw, cw); cl = 0; } else { cl++; mxcl = Math.max(mxcl, cl); cw = 0; } });
    // Yearly
    const yearly: Record<number, { trades: number; pnl: number; wins: number }> = {};
    const monthly: Record<string, { trades: number; pnl: number; wins: number }> = {};
    const dteMatrix: Record<number, Record<string, number>> = {};
    const dteCounts: Record<number, Record<string, number>> = {};
    trades.forEach(t => {
        const y = parseInt(t.date.substring(0, 4));
        const ym = t.date.substring(0, 7);
        const b = t.dte <= 6 ? String(t.dte) : "7+";
        if (!yearly[y]) yearly[y] = { trades: 0, pnl: 0, wins: 0 };
        yearly[y].trades++; yearly[y].pnl += t.gross_pnl; if (t.gross_pnl > 0) yearly[y].wins++;
        if (!monthly[ym]) monthly[ym] = { trades: 0, pnl: 0, wins: 0 };
        monthly[ym].trades++; monthly[ym].pnl += t.gross_pnl; if (t.gross_pnl > 0) monthly[ym].wins++;
        if (!dteMatrix[y]) { dteMatrix[y] = {}; dteCounts[y] = {}; }
        dteMatrix[y][b] = (dteMatrix[y][b] || 0) + t.gross_pnl;
        dteCounts[y][b] = (dteCounts[y][b] || 0) + 1;
    });
    return {
        trades: total, trading_days: Object.keys(dailyMap).length, winners, losers, win_rate: wr,
        gross_pnl: Math.round(gross), max_drawdown: Math.round(mdd), profit_factor: pf,
        payoff_ratio: pr, expectancy: exp, avg_win: avgW, avg_loss: avgL,
        max_win: maxW, max_loss: maxL, sharpe, calmar,
        max_consec_wins: mxcw, max_consec_losses: mxcl,
        yearly, monthly, dte_matrix: dteMatrix, dte_counts: dteCounts,
    };
}

export default function StrategiesPage() {
    const [activeStrat, setActiveStrat] = useState<StrategyData>(STRATEGIES[0]);
    const [exitMode, setExitMode] = useState<"hard" | "close">("close");
    const [slippage, setSlippage] = useState(0);
    const [brokeragePerOrder, setBrokeragePerOrder] = useState(0);
    const [useTaxes, setUseTaxes] = useState(false);
    const [vixMin, setVixMin] = useState(0);
    const [vixMax, setVixMax] = useState(100);
    const [showYearly, setShowYearly] = useState(true);
    const [showMonthly, setShowMonthly] = useState(true);
    const [showDteMatrix, setShowDteMatrix] = useState(true);
    const [showEquity, setShowEquity] = useState(true);
    const [showTrades, setShowTrades] = useState(false);
    const [tradeView, setTradeView] = useState<"trades" | "daily">("trades");
    const [tradeData, setTradeData] = useState<TradeRow[]>([]);
    const [equityData, setEquityData] = useState<EquityPoint[]>([]);
    const [dataLoaded, setDataLoaded] = useState(false);
    const [enlarged, setEnlarged] = useState<string | null>(null);

    const baseData = exitMode === "hard" ? activeStrat.hard : activeStrat.close;
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const DTE_COLS = ["0", "1", "2", "3", "4", "5", "6"];

    useEffect(() => {
        setDataLoaded(false);
        fetch("/strat_01_trades.json").then(r => r.json()).then(d => {
            setTradeData(d[exitMode] || []); setEquityData(d[`${exitMode}_equity`] || []); setDataLoaded(true);
        }).catch(() => setDataLoaded(true));
    }, [exitMode]);

    const vixActive = vixMin > 0 || vixMax < 100;

    // VIX-filtered trades — treats vix=0 as "no data" and includes them if filter is default
    const filteredTrades = useMemo(() => {
        if (!vixActive) return tradeData;
        return tradeData.filter(t => {
            if (!t.vix || t.vix === 0) return false; // exclude trades without VIX data
            return t.vix >= vixMin && t.vix <= vixMax;
        });
    }, [tradeData, vixMin, vixMax, vixActive]);

    // When VIX active, recompute ALL metrics from filtered trades
    const data: ModeData = useMemo(() => {
        if (!vixActive) return baseData;
        const computed = computeMetrics(filteredTrades);
        return computed || baseData;
    }, [vixActive, filteredTrades, baseData]);

    // Recompute equity curve from filtered trades when VIX active
    const activeEquity = useMemo(() => {
        if (!vixActive) return equityData;
        const dailyMap: Record<string, number> = {};
        filteredTrades.forEach(t => { dailyMap[t.date] = (dailyMap[t.date] || 0) + t.gross_pnl; });
        let cum = 0, peak = 0;
        return Object.keys(dailyMap).sort().map(d => {
            cum += dailyMap[d]; peak = Math.max(peak, cum);
            return { date: d, daily_pnl: dailyMap[d], cumulative: cum, drawdown: peak - cum };
        });
    }, [vixActive, filteredTrades, equityData]);

    const dailySummary = useMemo(() => {
        const map: Record<string, { date: string; trades: number; pnl: number; wins: number; vix: number }> = {};
        filteredTrades.forEach(t => {
            if (!map[t.date]) map[t.date] = { date: t.date, trades: 0, pnl: 0, wins: 0, vix: t.vix || 0 };
            map[t.date].trades++; map[t.date].pnl += t.gross_pnl; if (t.gross_pnl > 0) map[t.date].wins++;
        });
        return Object.values(map).sort((a, b) => a.date.localeCompare(b.date));
    }, [filteredTrades]);

    const years = Object.keys(data.yearly).map(Number).sort();
    const costPerTrade = useMemo(() => { let c = slippage * activeStrat.lot_size; c += brokeragePerOrder * 2; if (useTaxes) c += 40; return c; }, [slippage, brokeragePerOrder, useTaxes, activeStrat.lot_size]);
    const totalCost = costPerTrade * data.trades;
    const netPnl = data.gross_pnl - totalCost;
    const hasCosts = costPerTrade > 0;

    // ── Render helpers (to reuse in both normal + enlarged view) ──
    const renderEquity = () => <EquityCurve data={activeEquity} height={enlarged === "equity" ? 250 : 120} ddHeight={enlarged === "equity" ? 120 : 60} />;

    const renderYearly = () => (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", fontSize: 9, color: "var(--text-dim)", textTransform: "uppercase" }}>
                <th style={{ padding: "6px 8px", textAlign: "left" }}>Year</th><th style={{ padding: "6px 8px", textAlign: "right" }}>Trades</th><th style={{ padding: "6px 8px", textAlign: "right" }}>Win Rate</th><th style={{ padding: "6px 8px", textAlign: "right" }}>Gross P&L</th>{hasCosts && <th style={{ padding: "6px 8px", textAlign: "right" }}>Net P&L</th>}
            </tr></thead>
            <tbody>{years.map(y => { const yd = data.yearly[y]; if (!yd) return null; const wr = yd.trades > 0 ? (yd.wins / yd.trades * 100) : 0; const yrNet = yd.pnl - costPerTrade * yd.trades; return (<tr key={y} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}><td style={{ padding: "6px 8px", fontWeight: 700 }}>{y}</td><td className="text-mono" style={{ padding: "6px 8px", textAlign: "right" }}>{yd.trades}</td><td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", color: wr >= 55 ? "var(--green-bright)" : "var(--text-primary)" }}>{wr.toFixed(1)}%</td><td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", fontWeight: 700, color: yd.pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(yd.pnl))}</td>{hasCosts && <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", fontWeight: 700, color: yrNet >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(yrNet))}</td>}</tr>); })}</tbody>
            <tfoot><tr style={{ borderTop: "2px solid var(--border-subtle)", fontWeight: 700 }}><td style={{ padding: "6px 8px" }}>TOTAL</td><td className="text-mono" style={{ padding: "6px 8px", textAlign: "right" }}>{data.trades}</td><td className="text-mono" style={{ padding: "6px 8px", textAlign: "right" }}>{data.win_rate}%</td><td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", color: data.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(data.gross_pnl)}</td>{hasCosts && <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", color: netPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(netPnl)}</td>}</tr></tfoot>
        </table>
    );

    const renderMonthly = () => (
        <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", fontSize: 8, color: "var(--text-dim)", textTransform: "uppercase" }}><th style={{ padding: "4px 6px", textAlign: "left" }}>Year</th>{MONTHS.map(m => <th key={m} style={{ padding: "4px 4px", textAlign: "right", minWidth: 60 }}>{m}</th>)}<th style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700 }}>TOTAL</th></tr></thead>
                <tbody>{years.map(y => (<tr key={y} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}><td style={{ padding: "4px 6px", fontWeight: 700, fontSize: 10 }}>{y}</td>{MONTHS.map((_, mi) => { const key = `${y}-${String(mi + 1).padStart(2, "0")}`; const md = data.monthly[key]; if (!md || md.trades === 0) return <td key={mi} style={{ padding: "4px 4px", textAlign: "right", color: "var(--text-dim)" }}>—</td>; const val = hasCosts ? md.pnl - costPerTrade * md.trades : md.pnl; return <td key={mi} className="text-mono" style={{ padding: "4px 4px", textAlign: "right", color: val >= 0 ? "var(--green-bright)" : "var(--red-bright)", fontSize: 9 }}>{fmtRs(Math.round(val))}</td>; })}{(() => { const yd = data.yearly[y]; if (!yd) return <td>—</td>; const val = hasCosts ? yd.pnl - costPerTrade * yd.trades : yd.pnl; return <td className="text-mono" style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700, color: val >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(val))}</td>; })()}</tr>))}</tbody>
                <tfoot><tr style={{ borderTop: "2px solid var(--border-subtle)", fontWeight: 700 }}><td style={{ padding: "4px 6px" }}>GRAND TOTAL</td>{MONTHS.map((_, mi) => { let c = 0; years.forEach(y => { const md = data.monthly[`${y}-${String(mi + 1).padStart(2, "0")}`]; if (md) c += hasCosts ? md.pnl - costPerTrade * md.trades : md.pnl; }); return <td key={mi} className="text-mono" style={{ padding: "4px 4px", textAlign: "right", color: c >= 0 ? "var(--green-bright)" : "var(--red-bright)", fontSize: 9, fontWeight: 700 }}>{fmtRs(Math.round(c))}</td>; })}<td className="text-mono" style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700, fontSize: 11, color: (hasCosts ? netPnl : data.gross_pnl) >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(hasCosts ? netPnl : data.gross_pnl)}</td></tr></tfoot>
            </table>
        </div>
    );

    const renderDte = () => (
        <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", fontSize: 8, color: "var(--text-dim)", textTransform: "uppercase" }}><th style={{ padding: "4px 6px", textAlign: "left" }}>Year</th>{DTE_COLS.map(d => <th key={d} style={{ padding: "4px 6px", textAlign: "right", minWidth: 70 }}>DTE {d}</th>)}<th style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700 }}>TOTAL</th></tr></thead>
                <tbody>{years.map(y => { const ym = data.dte_matrix[y] || {}; const yc = data.dte_counts[y] || {}; let rt = 0; return (<tr key={y} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}><td style={{ padding: "4px 6px", fontWeight: 700 }}>{y}</td>{DTE_COLS.map(d => { const g = ym[d] || 0; const c = yc[d] || 0; const v = hasCosts ? g - costPerTrade * c : g; rt += v; if (g === 0 && c === 0) return <td key={d} style={{ padding: "4px 6px", textAlign: "right", color: "var(--text-dim)" }}>—</td>; return <td key={d} className="text-mono" style={{ padding: "4px 6px", textAlign: "right", color: v >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(v))}</td>; })}<td className="text-mono" style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700, color: rt >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(rt))}</td></tr>); })}</tbody>
                <tfoot><tr style={{ borderTop: "2px solid var(--border-subtle)", fontWeight: 700 }}><td style={{ padding: "4px 6px" }}>GRAND TOTAL</td>{DTE_COLS.map(d => { let c = 0; years.forEach(y => { const g = (data.dte_matrix[y] || {})[d] || 0; const n = (data.dte_counts[y] || {})[d] || 0; c += hasCosts ? g - costPerTrade * n : g; }); return <td key={d} className="text-mono" style={{ padding: "4px 6px", textAlign: "right", color: c >= 0 ? "var(--green-bright)" : "var(--red-bright)", fontWeight: 700 }}>{fmtRs(Math.round(c))}</td>; })}<td className="text-mono" style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700, fontSize: 11, color: (hasCosts ? netPnl : data.gross_pnl) >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(hasCosts ? netPnl : data.gross_pnl)}</td></tr></tfoot>
            </table>
        </div>
    );

    const renderTradeLog = () => (
        <>
            <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
                {(["trades", "daily"] as const).map(v => (<button key={v} onClick={() => setTradeView(v)} style={{ padding: "4px 10px", fontSize: 9, fontWeight: 600, borderRadius: "var(--radius-sm)", cursor: "pointer", border: "1px solid", background: tradeView === v ? "var(--accent)" : "transparent", color: tradeView === v ? "#000" : "var(--text-dim)", borderColor: tradeView === v ? "var(--accent)" : "var(--border-subtle)" }}>{v === "trades" ? "All Trades" : "Day Summary"}</button>))}
            </div>
            {!dataLoaded ? <div style={{ padding: 16, textAlign: "center", color: "var(--text-dim)", fontSize: 11 }}>Loading...</div> :
                tradeView === "trades" ? (
                    <div style={{ overflowX: "auto", maxHeight: enlarged === "trades" ? undefined : 400 }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                            <thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", fontSize: 8, color: "var(--text-dim)", textTransform: "uppercase", position: "sticky", top: 0, background: "var(--bg-secondary)" }}>
                                {["Date", "Entry", "Exit", "Label", "Strike", "Type", "EntryPx", "ExitPx", "Reason", "DTE", "VIX", "Gross", hasCosts ? "Net" : ""].filter(Boolean).map(h => <th key={h} style={{ padding: "4px 5px", textAlign: ["Gross", "Net"].includes(h) ? "right" : "left" }}>{h}</th>)}
                            </tr></thead>
                            <tbody>{filteredTrades.slice(0, enlarged === "trades" ? 2000 : 500).map((t, i) => {
                                const net = t.gross_pnl - costPerTrade;
                                return (<tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                    <td style={{ padding: "3px 5px", whiteSpace: "nowrap" }}>{t.date}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", fontSize: 9 }}>{t.entry_time}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", fontSize: 9 }}>{t.exit_time}</td>
                                    <td style={{ padding: "3px 5px", fontSize: 9, color: "var(--text-dim)" }}>{t.label}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px" }}>{t.absolute_strike || "ATM"}</td>
                                    <td style={{ padding: "3px 5px" }}><span style={{ fontSize: 8, padding: "0 4px", borderRadius: 3, background: t.option_type === "CE" ? "rgba(59,130,246,0.12)" : "rgba(239,68,68,0.12)", color: t.option_type === "CE" ? "#60a5fa" : "#f87171" }}>{t.option_type}</span></td>
                                    <td className="text-mono" style={{ padding: "3px 5px" }}>{t.entry_price?.toFixed(1)}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px" }}>{t.exit_price?.toFixed(1)}</td>
                                    <td style={{ padding: "3px 5px", fontSize: 8 }}>{t.exit_reason?.replace(/_/g, " ")}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px" }}>{t.dte}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", fontSize: 9 }}>{t.vix || "—"}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", textAlign: "right", color: t.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(t.gross_pnl))}</td>
                                    {hasCosts && <td className="text-mono" style={{ padding: "3px 5px", textAlign: "right", fontWeight: 600, color: net >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(net))}</td>}
                                </tr>);
                            })}</tbody>
                        </table>
                    </div>
                ) : (
                    <div style={{ overflowX: "auto", maxHeight: enlarged === "trades" ? undefined : 400 }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                            <thead><tr style={{ borderBottom: "1px solid var(--border-subtle)", fontSize: 8, color: "var(--text-dim)", textTransform: "uppercase", position: "sticky", top: 0, background: "var(--bg-secondary)" }}>
                                {["Date", "Trades", "Winners", "Win Rate", "VIX", "Gross P&L", hasCosts ? "Net P&L" : ""].filter(Boolean).map(h => <th key={h} style={{ padding: "4px 5px", textAlign: ["Gross P&L", "Net P&L"].includes(h) ? "right" : "left" }}>{h}</th>)}
                            </tr></thead>
                            <tbody>{dailySummary.map((d, i) => {
                                const net = d.pnl - costPerTrade * d.trades; const wr = d.trades > 0 ? (d.wins / d.trades * 100) : 0;
                                return (<tr key={i} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                    <td style={{ padding: "3px 5px", whiteSpace: "nowrap", fontWeight: 600 }}>{d.date}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px" }}>{d.trades}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", color: "var(--green-bright)" }}>{d.wins}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", color: wr >= 50 ? "var(--green-bright)" : "var(--red-bright)" }}>{wr.toFixed(0)}%</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", fontSize: 9 }}>{d.vix || "—"}</td>
                                    <td className="text-mono" style={{ padding: "3px 5px", textAlign: "right", fontWeight: 600, color: d.pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(d.pnl))}</td>
                                    {hasCosts && <td className="text-mono" style={{ padding: "3px 5px", textAlign: "right", fontWeight: 600, color: net >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(Math.round(net))}</td>}
                                </tr>);
                            })}</tbody>
                        </table>
                    </div>
                )}
        </>
    );

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="AI Strategy Builder" />
                <div style={{ display: "flex", gap: 0, height: "calc(100vh - var(--header-height))" }}>
                    {/* LEFT SIDEBAR */}
                    <div style={{ width: 280, minWidth: 280, borderRight: "1px solid var(--border-subtle)", background: "var(--bg-secondary)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
                        <div style={{ padding: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 8 }}>Strategies</div>
                            {STRATEGIES.map(s => (<div key={s.id} onClick={() => setActiveStrat(s)} style={{ padding: "10px 12px", borderRadius: "var(--radius-sm)", cursor: "pointer", marginBottom: 4, background: activeStrat.id === s.id ? "var(--accent-dim)" : "transparent", borderLeft: activeStrat.id === s.id ? "3px solid var(--accent)" : "3px solid transparent" }}><div style={{ fontSize: 11, fontWeight: 700, color: activeStrat.id === s.id ? "var(--accent)" : "var(--text-primary)" }}>{s.name}</div><div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 2 }}>{s.period} · Lot {s.lot_size}</div></div>))}
                        </div>
                        <div style={{ padding: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 8 }}>Exit Mode</div>
                            <div style={{ display: "flex", gap: 4 }}>{(["hard", "close"] as const).map(m => (<button key={m} onClick={() => setExitMode(m)} style={{ flex: 1, padding: "6px 8px", fontSize: 10, fontWeight: 600, borderRadius: "var(--radius-sm)", cursor: "pointer", border: "1px solid", background: exitMode === m ? "var(--accent)" : "transparent", color: exitMode === m ? "#000" : "var(--text-dim)", borderColor: exitMode === m ? "var(--accent)" : "var(--border-subtle)" }}>{m === "hard" ? "⚡ Hard SL" : "📊 Close SL"}</button>))}</div>
                        </div>
                        <div style={{ padding: "12px", flex: 1, overflowY: "auto" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 10, display: "flex", alignItems: "center", gap: 4 }}><Sliders style={{ width: 11, height: 11 }} /> Cost Parameters</div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                                <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Slippage (pts per trade)</span><input type="number" value={slippage} onChange={e => setSlippage(Number(e.target.value))} className="input-field" step="0.1" min="0" /></label>
                                <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Brokerage per Order (Rs)</span><input type="number" value={brokeragePerOrder} onChange={e => setBrokeragePerOrder(Number(e.target.value))} className="input-field" min="0" /></label>
                                <div style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }} onClick={() => setUseTaxes(!useTaxes)}>
                                    {useTaxes ? <ToggleRight style={{ width: 18, height: 18, color: "var(--accent)" }} /> : <ToggleLeft style={{ width: 18, height: 18, color: "var(--text-dim)" }} />}
                                    <span style={{ fontSize: 10, color: useTaxes ? "var(--accent)" : "var(--text-dim)", fontWeight: 600 }}>{useTaxes ? "Taxes ON (~Rs.40/trade)" : "Taxes OFF"}</span>
                                </div>
                                <hr style={{ border: "none", borderTop: "1px solid var(--border-subtle)", margin: "4px 0" }} />
                                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 2 }}>VIX Filter {vixActive && <span style={{ color: "var(--accent)", fontSize: 8, marginLeft: 4 }}>● ACTIVE</span>}</div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                                    <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Min VIX</span><input type="number" value={vixMin} onChange={e => setVixMin(Number(e.target.value))} className="input-field" min="0" step="1" /></label>
                                    <label style={{ fontSize: 10 }}><span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Max VIX</span><input type="number" value={vixMax} onChange={e => setVixMax(Number(e.target.value))} className="input-field" min="0" step="1" /></label>
                                </div>
                                {vixActive && <div style={{ fontSize: 9, padding: "6px 8px", background: "rgba(52,211,153,0.08)", borderRadius: "var(--radius-sm)", border: "1px solid rgba(52,211,153,0.2)", color: "var(--accent)" }}>
                                    VIX {vixMin}–{vixMax}: <strong>{filteredTrades.length}</strong> / {tradeData.length} trades<br />
                                    <span style={{ fontSize: 8 }}>All metrics recalculated from filtered trades</span>
                                </div>}
                            </div>
                            {hasCosts && (<div style={{ marginTop: 14, padding: 10, background: "rgba(239,68,68,0.06)", borderRadius: "var(--radius-sm)", border: "1px solid rgba(239,68,68,0.15)" }}>
                                <div style={{ fontSize: 9, color: "var(--text-dim)", marginBottom: 4, textTransform: "uppercase" }}>Cost Impact</div>
                                <div style={{ fontSize: 10, color: "var(--red-bright)", marginBottom: 2 }}>Per trade: Rs.{costPerTrade.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
                                <div style={{ fontSize: 10, color: "var(--red-bright)", marginBottom: 4 }}>Total ({data.trades} trades): Rs.{totalCost.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
                                <div style={{ fontSize: 12, fontWeight: 700, color: netPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>Net: {fmtRs(netPnl)}</div>
                            </div>)}
                        </div>
                    </div>

                    {/* RIGHT: Results */}
                    <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
                        <div className="card" style={{ marginBottom: 14, padding: 14, border: "1px solid var(--accent-dim)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                                <Zap style={{ width: 15, height: 15, color: "var(--accent)" }} />
                                <span style={{ fontSize: 14, fontWeight: 700 }}>{activeStrat.name}</span>
                                <span style={{ fontSize: 9, marginLeft: "auto", background: exitMode === "hard" ? "rgba(239,154,26,0.15)" : "rgba(52,211,153,0.15)", padding: "2px 8px", borderRadius: 4, fontWeight: 600, color: exitMode === "hard" ? "var(--yellow)" : "var(--green-bright)" }}>{exitMode === "hard" ? "⚡ HARD SL" : "📊 CLOSE SL"}</span>
                            </div>
                            <div style={{ fontSize: 11, color: "var(--text-dim)", lineHeight: 1.6, background: "var(--bg-tertiary)", padding: "8px 12px", borderRadius: "var(--radius-sm)" }}>{activeStrat.description}</div>
                            <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 6 }}>Period: {activeStrat.period} · Entry {activeStrat.entry_time} · Exit {activeStrat.exit_time} · Lot {activeStrat.lot_size} · NIFTY Weekly</div>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 8 }}>
                            <StatCard label="Trades" value={`${data.trades}`} sub={`${data.trading_days} days`} />
                            <StatCard label="Win Rate" value={`${data.win_rate}%`} color={data.win_rate >= 55 ? "var(--green-bright)" : "var(--red-bright)"} sub={`${data.winners}W / ${data.losers}L`} />
                            <StatCard label={hasCosts ? "Gross P&L" : "P&L"} value={fmtRs(data.gross_pnl)} color={data.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)"} sub={hasCosts ? `Net: ${fmtRs(netPnl)}` : "Zero costs"} />
                            <StatCard label="Max Drawdown" value={`Rs.${data.max_drawdown.toLocaleString("en-IN")}`} color="var(--red-bright)" />
                            <StatCard label="Profit Factor" value={`${data.profit_factor}`} color={data.profit_factor >= 1.5 ? "var(--green-bright)" : "var(--text-primary)"} />
                            <StatCard label="Sharpe" value={`${data.sharpe}`} color={data.sharpe >= 3 ? "var(--green-bright)" : "var(--text-primary)"} />
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 14 }}>
                            <StatCard label="Payoff" value={`${data.payoff_ratio}`} sub="AvgW/AvgL" />
                            <StatCard label="Expectancy" value={fmtRs(data.expectancy)} color={data.expectancy >= 0 ? "var(--green-bright)" : "var(--red-bright)"} sub="Per trade" />
                            <StatCard label="Avg Win" value={fmtRs(data.avg_win)} color="var(--green-bright)" />
                            <StatCard label="Avg Loss" value={fmtRs(data.avg_loss)} color="var(--red-bright)" />
                            <StatCard label="Max Win" value={fmtRs(data.max_win)} color="var(--green-bright)" sub={`Streak: ${data.max_consec_wins}`} />
                            <StatCard label="Max Loss" value={fmtRs(data.max_loss)} color="var(--red-bright)" sub={`Streak: ${data.max_consec_losses}`} />
                        </div>

                        <Section title="Equity Curve & Drawdown" icon={<Activity style={{ width: 13, height: 13, color: "var(--accent)" }} />} open={showEquity} onToggle={() => setShowEquity(!showEquity)} onEnlarge={() => setEnlarged("equity")}>{renderEquity()}</Section>
                        <Section title="Yearly Summary" icon={<TrendingUp style={{ width: 13, height: 13, color: "var(--accent)" }} />} open={showYearly} onToggle={() => setShowYearly(!showYearly)} onEnlarge={() => setEnlarged("yearly")}>{renderYearly()}</Section>
                        <Section title="Monthly Breakdown" icon={<Calendar style={{ width: 13, height: 13, color: "var(--accent)" }} />} open={showMonthly} onToggle={() => setShowMonthly(!showMonthly)} onEnlarge={() => setEnlarged("monthly")}>{renderMonthly()}</Section>
                        <Section title={`Year × DTE Matrix ${hasCosts ? "(Net)" : "(Gross)"}`} icon={<BarChart3 style={{ width: 13, height: 13, color: "var(--accent)" }} />} open={showDteMatrix} onToggle={() => setShowDteMatrix(!showDteMatrix)} onEnlarge={() => setEnlarged("dte")}>{renderDte()}</Section>
                        <Section title={`Trade Log (${vixActive ? filteredTrades.length + "/" : ""}${data.trades} trades)`} icon={<Layers style={{ width: 13, height: 13, color: "var(--accent)" }} />} open={showTrades} onToggle={() => setShowTrades(!showTrades)} onEnlarge={() => setEnlarged("trades")}>{renderTradeLog()}</Section>
                    </div>
                </div>
            </main>

            {/* Fullscreen modal */}
            {enlarged && (
                <FullscreenModal title={enlarged === "equity" ? "Equity Curve & Drawdown" : enlarged === "yearly" ? "Yearly Summary" : enlarged === "monthly" ? "Monthly Breakdown" : enlarged === "dte" ? "Year × DTE Matrix" : "Trade Log"} onClose={() => setEnlarged(null)}>
                    {enlarged === "equity" && renderEquity()}
                    {enlarged === "yearly" && renderYearly()}
                    {enlarged === "monthly" && renderMonthly()}
                    {enlarged === "dte" && renderDte()}
                    {enlarged === "trades" && renderTradeLog()}
                </FullscreenModal>
            )}

            <style jsx global>{`.input-field{padding:5px 8px;background:var(--bg-tertiary);border:1px solid var(--border-subtle);border-radius:var(--radius-sm);color:var(--text-primary);font-size:11px;font-family:inherit;outline:none;width:100%}.input-field:focus{border-color:var(--accent)}`}</style>
        </div>
    );
}
