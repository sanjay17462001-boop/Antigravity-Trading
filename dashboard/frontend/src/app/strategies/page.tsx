"use client";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useState, useMemo } from "react";
import { BarChart3, TrendingUp, Shield, Sliders, ChevronDown, ChevronUp, Calendar, Zap, ToggleLeft, ToggleRight } from "lucide-react";

// ════════════════════════════════════════════════════════════════
// HARDCODED STRATEGY DATA
// ════════════════════════════════════════════════════════════════

interface TradeRow {
    date: string; year: number; month: number; dte: number;
    option_type: string; label: string; action: string;
    entry_price: number; exit_price: number; entry_time: string; exit_time: string;
    exit_reason: string; gross_pnl: number; lots: number; quantity: number;
}

interface StrategyData {
    id: string; name: string; description: string;
    period: string; lot_size: number; entry_time: string; exit_time: string;
    hard: ModeData; close: ModeData;
}

interface ModeData {
    trades: number; trading_days: number; winners: number; losers: number;
    win_rate: number; gross_pnl: number; max_drawdown: number;
    profit_factor: number; payoff_ratio: number; expectancy: number;
    avg_win: number; avg_loss: number; max_win: number; max_loss: number;
    sharpe: number; calmar: number; max_consec_wins: number; max_consec_losses: number;
    yearly: Record<number, { trades: number; pnl: number; wins: number }>;
    monthly: Record<string, { trades: number; pnl: number; wins: number }>;
    dte_matrix: Record<number, Record<string, number>>;
    trade_data: TradeRow[];
}

const STRATEGY_1: StrategyData = {
    id: "strat_01",
    name: "ATM Straddle + Re-entry on SL",
    description: "Entry 9:16, exit 14:30. Sell 1 ATM CE + 1 ATM PE with 30% hard SL. Re-entry: On CE/PE SL hit, sell 1 more ATM CE/PE with 30% SL when price +10%. Global SL Rs 9000. Profit lock: Rs 200 when PnL reaches Rs 1500. Lot size 65. Weekly expiry. NIFTY.",
    period: "2021-01-01 to 2026-02-18",
    lot_size: 65,
    entry_time: "09:16",
    exit_time: "14:30",
    hard: {
        trades: 2605, trading_days: 1253, winners: 1565, losers: 1035,
        win_rate: 60.1, gross_pnl: 877108, max_drawdown: 20218,
        profit_factor: 1.80, payoff_ratio: 1.19, expectancy: 337,
        avg_win: 1265, avg_loss: -1065, max_win: 8612, max_loss: -9286,
        sharpe: 5.39, calmar: 14.68, max_consec_wins: 18, max_consec_losses: 5,
        yearly: {
            2021: { trades: 517, pnl: 162600, wins: 308 },
            2022: { trades: 511, pnl: 191606, wins: 318 },
            2023: { trades: 513, pnl: 122787, wins: 313 },
            2024: { trades: 507, pnl: 170884, wins: 305 },
            2025: { trades: 492, pnl: 198868, wins: 297 },
            2026: { trades: 65, pnl: 30362, wins: 38 },
        },
        monthly: {
            "2021-01": { trades: 42, pnl: 15073, wins: 24 }, "2021-02": { trades: 42, pnl: 16131, wins: 23 },
            "2021-03": { trades: 42, pnl: 16488, wins: 23 }, "2021-04": { trades: 38, pnl: 21455, wins: 26 },
            "2021-05": { trades: 44, pnl: 13023, wins: 26 }, "2021-06": { trades: 46, pnl: 3975, wins: 25 },
            "2021-07": { trades: 46, pnl: 1395, wins: 24 }, "2021-08": { trades: 44, pnl: 6770, wins: 23 },
            "2021-09": { trades: 44, pnl: 14488, wins: 27 }, "2021-10": { trades: 41, pnl: 18758, wins: 26 },
            "2021-11": { trades: 42, pnl: 17028, wins: 28 }, "2021-12": { trades: 46, pnl: 18016, wins: 28 },
            "2022-01": { trades: 42, pnl: 22497, wins: 24 }, "2022-02": { trades: 40, pnl: 29710, wins: 27 },
            "2022-03": { trades: 43, pnl: 10577, wins: 24 }, "2022-04": { trades: 39, pnl: 20497, wins: 24 },
            "2022-05": { trades: 42, pnl: 7024, wins: 24 }, "2022-06": { trades: 44, pnl: 25261, wins: 27 },
            "2022-07": { trades: 43, pnl: 16500, wins: 28 }, "2022-08": { trades: 42, pnl: 10244, wins: 27 },
            "2022-09": { trades: 44, pnl: 11858, wins: 26 }, "2022-10": { trades: 38, pnl: 13438, wins: 24 },
            "2022-11": { trades: 44, pnl: 14732, wins: 25 }, "2022-12": { trades: 50, pnl: 9268, wins: 33 },
            "2023-01": { trades: 43, pnl: 10776, wins: 26 }, "2023-02": { trades: 40, pnl: 19032, wins: 27 },
            "2023-03": { trades: 43, pnl: 8950, wins: 25 }, "2023-04": { trades: 35, pnl: 6708, wins: 19 },
            "2023-05": { trades: 47, pnl: 4575, wins: 24 }, "2023-06": { trades: 43, pnl: 5070, wins: 25 },
            "2023-07": { trades: 44, pnl: 9415, wins: 26 }, "2023-08": { trades: 46, pnl: 15261, wins: 31 },
            "2023-09": { trades: 44, pnl: 20432, wins: 28 }, "2023-10": { trades: 42, pnl: 9616, wins: 25 },
            "2023-11": { trades: 43, pnl: 8706, wins: 27 }, "2023-12": { trades: 42, pnl: 10406, wins: 28 },
            "2024-01": { trades: 45, pnl: 4559, wins: 23 }, "2024-02": { trades: 43, pnl: 23327, wins: 28 },
            "2024-03": { trades: 37, pnl: 19083, wins: 26 }, "2024-04": { trades: 43, pnl: 5664, wins: 22 },
            "2024-05": { trades: 42, pnl: 9916, wins: 25 }, "2024-06": { trades: 41, pnl: 13528, wins: 29 },
            "2024-07": { trades: 44, pnl: 6946, wins: 25 }, "2024-08": { trades: 44, pnl: 9648, wins: 25 },
            "2024-09": { trades: 43, pnl: 660, wins: 23 }, "2024-10": { trades: 44, pnl: 24644, wins: 27 },
            "2024-11": { trades: 38, pnl: 28917, wins: 28 }, "2024-12": { trades: 43, pnl: 23993, wins: 26 },
            "2025-01": { trades: 47, pnl: 15030, wins: 31 }, "2025-02": { trades: 39, pnl: 32690, wins: 29 },
            "2025-03": { trades: 40, pnl: 17293, wins: 26 }, "2025-04": { trades: 24, pnl: -1878, wins: 12 },
            "2025-05": { trades: 40, pnl: 24979, wins: 25 }, "2025-06": { trades: 45, pnl: 22222, wins: 27 },
            "2025-07": { trades: 48, pnl: 22043, wins: 33 }, "2025-08": { trades: 38, pnl: 6238, wins: 22 },
            "2025-09": { trades: 46, pnl: 3856, wins: 24 }, "2025-10": { trades: 41, pnl: 13780, wins: 25 },
            "2025-11": { trades: 38, pnl: 25338, wins: 26 }, "2025-12": { trades: 46, pnl: 17280, wins: 29 },
            "2026-01": { trades: 43, pnl: 16124, wins: 23 }, "2026-02": { trades: 22, pnl: 14238, wins: 14 },
        },
        dte_matrix: {
            2021: { "0": 59446, "1": 23778, "2": 33404, "3": 15736, "4": 0, "5": 3575, "6": 26660 },
            2022: { "0": 53332, "1": 19883, "2": 34673, "3": 36124, "4": 0, "5": 3198, "6": 44395 },
            2023: { "0": 27583, "1": 21563, "2": 17509, "3": 14109, "4": 0, "5": 1791, "6": 40232 },
            2024: { "0": 71447, "1": 39078, "2": 22921, "3": 14643, "4": 0, "5": 221, "6": 22574 },
            2025: { "0": 56487, "1": 40107, "2": 26446, "3": 17400, "4": 15347, "5": 8459, "6": 34622 },
            2026: { "0": 12975, "1": 6055, "2": 0, "3": 0, "4": 5295, "5": 557, "6": 5480 },
        },
        trade_data: [],
    },
    close: {
        trades: 2562, trading_days: 1253, winners: 1581, losers: 975,
        win_rate: 61.7, gross_pnl: 1004296, max_drawdown: 13452,
        profit_factor: 2.02, payoff_ratio: 1.25, expectancy: 390,
        avg_win: 1259, avg_loss: -1011, max_win: 8612, max_loss: -7504,
        sharpe: 6.58, calmar: 15.02, max_consec_wins: 15, max_consec_losses: 7,
        yearly: {
            2021: { trades: 505, pnl: 168779, wins: 309 },
            2022: { trades: 504, pnl: 194379, wins: 312 },
            2023: { trades: 502, pnl: 127910, wins: 305 },
            2024: { trades: 500, pnl: 238277, wins: 310 },
            2025: { trades: 487, pnl: 236899, wins: 311 },
            2026: { trades: 64, pnl: 38051, wins: 38 },
        },
        monthly: {
            "2021-01": { trades: 42, pnl: 10891, wins: 23 }, "2021-02": { trades: 41, pnl: 17069, wins: 24 },
            "2021-03": { trades: 42, pnl: 13322, wins: 23 }, "2021-04": { trades: 38, pnl: 23666, wins: 25 },
            "2021-05": { trades: 40, pnl: 12148, wins: 26 }, "2021-06": { trades: 46, pnl: 5324, wins: 26 },
            "2021-07": { trades: 44, pnl: -488, wins: 23 }, "2021-08": { trades: 44, pnl: 11411, wins: 23 },
            "2021-09": { trades: 43, pnl: 11625, wins: 26 }, "2021-10": { trades: 41, pnl: 22080, wins: 25 },
            "2021-11": { trades: 38, pnl: 21612, wins: 25 }, "2021-12": { trades: 46, pnl: 20118, wins: 29 },
            "2022-01": { trades: 42, pnl: 21976, wins: 22 }, "2022-02": { trades: 40, pnl: 33917, wins: 26 },
            "2022-03": { trades: 42, pnl: 10039, wins: 23 }, "2022-04": { trades: 39, pnl: 21170, wins: 24 },
            "2022-05": { trades: 42, pnl: 7641, wins: 24 }, "2022-06": { trades: 44, pnl: 23046, wins: 27 },
            "2022-07": { trades: 43, pnl: 18362, wins: 29 }, "2022-08": { trades: 41, pnl: 11908, wins: 26 },
            "2022-09": { trades: 45, pnl: 14358, wins: 26 }, "2022-10": { trades: 38, pnl: 19393, wins: 25 },
            "2022-11": { trades: 44, pnl: 3500, wins: 22 }, "2022-12": { trades: 44, pnl: 9068, wins: 29 },
            "2023-01": { trades: 43, pnl: 14882, wins: 27 }, "2023-02": { trades: 40, pnl: 21700, wins: 27 },
            "2023-03": { trades: 43, pnl: 10023, wins: 26 }, "2023-04": { trades: 35, pnl: 11073, wins: 20 },
            "2023-05": { trades: 45, pnl: -1004, wins: 22 }, "2023-06": { trades: 42, pnl: 2239, wins: 24 },
            "2023-07": { trades: 42, pnl: 4660, wins: 25 }, "2023-08": { trades: 45, pnl: 16016, wins: 31 },
            "2023-09": { trades: 42, pnl: 13367, wins: 25 }, "2023-10": { trades: 42, pnl: 17384, wins: 28 },
            "2023-11": { trades: 42, pnl: 9506, wins: 27 }, "2023-12": { trades: 41, pnl: 8063, wins: 27 },
            "2024-01": { trades: 43, pnl: 3078, wins: 22 }, "2024-02": { trades: 43, pnl: 25467, wins: 29 },
            "2024-03": { trades: 37, pnl: 21401, wins: 27 }, "2024-04": { trades: 42, pnl: 18392, wins: 24 },
            "2024-05": { trades: 42, pnl: 11235, wins: 26 }, "2024-06": { trades: 39, pnl: 32435, wins: 28 },
            "2024-07": { trades: 44, pnl: 28044, wins: 28 }, "2024-08": { trades: 44, pnl: 11742, wins: 26 },
            "2024-09": { trades: 42, pnl: 6009, wins: 22 }, "2024-10": { trades: 43, pnl: 22106, wins: 25 },
            "2024-11": { trades: 38, pnl: 29738, wins: 28 }, "2024-12": { trades: 43, pnl: 28629, wins: 28 },
            "2025-01": { trades: 47, pnl: 23592, wins: 32 }, "2025-02": { trades: 39, pnl: 35386, wins: 30 },
            "2025-03": { trades: 40, pnl: 24021, wins: 27 }, "2025-04": { trades: 24, pnl: 1758, wins: 12 },
            "2025-05": { trades: 40, pnl: 26478, wins: 25 }, "2025-06": { trades: 43, pnl: 16500, wins: 26 },
            "2025-07": { trades: 47, pnl: 20716, wins: 33 }, "2025-08": { trades: 38, pnl: 17270, wins: 25 },
            "2025-09": { trades: 46, pnl: 8541, wins: 27 }, "2025-10": { trades: 41, pnl: 19045, wins: 26 },
            "2025-11": { trades: 38, pnl: 28005, wins: 28 }, "2025-12": { trades: 44, pnl: 15587, wins: 29 },
            "2026-01": { trades: 42, pnl: 23813, wins: 24 }, "2026-02": { trades: 22, pnl: 14238, wins: 14 },
        },
        dte_matrix: {
            2021: { "0": 52686, "1": 30706, "2": 35415, "3": 21151, "4": 0, "5": 3575, "6": 25246 },
            2022: { "0": 54077, "1": 19331, "2": 37245, "3": 38974, "4": 0, "5": 3198, "6": 41554 },
            2023: { "0": 45572, "1": 8395, "2": 16802, "3": 15984, "4": 0, "5": 1791, "6": 39367 },
            2024: { "0": 90226, "1": 50807, "2": 51763, "3": 20550, "4": 0, "5": 221, "6": 24710 },
            2025: { "0": 64776, "1": 45952, "2": 32672, "3": 20378, "4": 18538, "5": 14648, "6": 39936 },
            2026: { "0": 11528, "1": 9474, "2": 0, "3": 0, "4": 3175, "5": 4176, "6": 9698 },
        },
        trade_data: [],
    },
};

const STRATEGIES: StrategyData[] = [STRATEGY_1];

// ════════════════════════════════════════════════════════════════
// COMPONENTS
// ════════════════════════════════════════════════════════════════

function fmtRs(v: number) { return `${v >= 0 ? "+" : ""}Rs.${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`; }

function StatCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
    return (<div style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: "10px 12px", textAlign: "center", minWidth: 0 }}>
        <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-dim)", marginBottom: 3 }}>{label}</div>
        <div className="text-mono" style={{ fontSize: 15, fontWeight: 700, color: color || "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{value}</div>
        {sub && <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 2 }}>{sub}</div>}
    </div>);
}

// ════════════════════════════════════════════════════════════════
// MAIN PAGE
// ════════════════════════════════════════════════════════════════

export default function StrategiesPage() {
    const [activeStrat, setActiveStrat] = useState<StrategyData>(STRATEGIES[0]);
    const [exitMode, setExitMode] = useState<"hard" | "close">("close");
    const [slippage, setSlippage] = useState(0);
    const [brokeragePerOrder, setBrokeragePerOrder] = useState(0);
    const [useTaxes, setUseTaxes] = useState(false);
    const [vixMin, setVixMin] = useState(0);
    const [vixMax, setVixMax] = useState(100);
    const [showMonthly, setShowMonthly] = useState(true);
    const [showDteMatrix, setShowDteMatrix] = useState(true);

    const data = exitMode === "hard" ? activeStrat.hard : activeStrat.close;
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const DTE_COLS = ["0", "1", "2", "3", "4", "5", "6"];
    const years = Object.keys(data.yearly).map(Number).sort();

    // Cost adjustment factor — per trade
    const costPerTrade = useMemo(() => {
        let cost = 0;
        cost += slippage * activeStrat.lot_size;           // slippage_pts * qty
        cost += brokeragePerOrder * 2;                      // entry + exit brokerage
        if (useTaxes) {
            cost += activeStrat.lot_size * 100 * 0.0005;    // approx STT, CTT etc
        }
        return cost;
    }, [slippage, brokeragePerOrder, useTaxes, activeStrat.lot_size]);

    const totalCost = costPerTrade * data.trades;
    const netPnl = data.gross_pnl - totalCost;

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <Header title="AI Strategy Builder" />
                <div style={{ display: "flex", gap: 0, height: "calc(100vh - var(--header-height))" }}>

                    {/* ════════ LEFT: Strategy List + Cost Sidebar ════════ */}
                    <div style={{ width: 280, minWidth: 280, borderRight: "1px solid var(--border-subtle)", background: "var(--bg-secondary)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
                        {/* Strategy selector */}
                        <div style={{ padding: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 8 }}>Strategies</div>
                            {STRATEGIES.map(s => (
                                <div key={s.id} onClick={() => setActiveStrat(s)} style={{
                                    padding: "10px 12px", borderRadius: "var(--radius-sm)", cursor: "pointer", marginBottom: 4,
                                    background: activeStrat.id === s.id ? "var(--accent-dim)" : "transparent",
                                    borderLeft: activeStrat.id === s.id ? "3px solid var(--accent)" : "3px solid transparent",
                                }}>
                                    <div style={{ fontSize: 11, fontWeight: 700, color: activeStrat.id === s.id ? "var(--accent)" : "var(--text-primary)" }}>{s.name}</div>
                                    <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 2 }}>{s.period} · Lot {s.lot_size}</div>
                                </div>
                            ))}
                        </div>

                        {/* Exit Mode Toggle */}
                        <div style={{ padding: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 8 }}>Exit Mode</div>
                            <div style={{ display: "flex", gap: 4 }}>
                                <button onClick={() => setExitMode("hard")} style={{
                                    flex: 1, padding: "6px 8px", fontSize: 10, fontWeight: 600, borderRadius: "var(--radius-sm)", cursor: "pointer", border: "1px solid",
                                    background: exitMode === "hard" ? "var(--accent)" : "transparent",
                                    color: exitMode === "hard" ? "#000" : "var(--text-dim)",
                                    borderColor: exitMode === "hard" ? "var(--accent)" : "var(--border-subtle)",
                                }}>⚡ Hard SL</button>
                                <button onClick={() => setExitMode("close")} style={{
                                    flex: 1, padding: "6px 8px", fontSize: 10, fontWeight: 600, borderRadius: "var(--radius-sm)", cursor: "pointer", border: "1px solid",
                                    background: exitMode === "close" ? "var(--accent)" : "transparent",
                                    color: exitMode === "close" ? "#000" : "var(--text-dim)",
                                    borderColor: exitMode === "close" ? "var(--accent)" : "var(--border-subtle)",
                                }}>📊 Close SL</button>
                            </div>
                        </div>

                        {/* Cost Adjustment Sidebar */}
                        <div style={{ padding: "12px", flex: 1, overflowY: "auto" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 10, display: "flex", alignItems: "center", gap: 4 }}>
                                <Sliders style={{ width: 11, height: 11 }} /> Cost Parameters
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                                <label style={{ fontSize: 10 }}>
                                    <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Slippage (pts)</span>
                                    <input type="number" value={slippage} onChange={e => setSlippage(Number(e.target.value))} className="input-field" step="0.1" min="0" />
                                </label>
                                <label style={{ fontSize: 10 }}>
                                    <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Brokerage per Order (Rs)</span>
                                    <input type="number" value={brokeragePerOrder} onChange={e => setBrokeragePerOrder(Number(e.target.value))} className="input-field" min="0" />
                                </label>
                                <div style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }} onClick={() => setUseTaxes(!useTaxes)}>
                                    {useTaxes ? <ToggleRight style={{ width: 18, height: 18, color: "var(--accent)" }} /> : <ToggleLeft style={{ width: 18, height: 18, color: "var(--text-dim)" }} />}
                                    <span style={{ fontSize: 10, color: useTaxes ? "var(--accent)" : "var(--text-dim)", fontWeight: 600 }}>{useTaxes ? "Taxes ON" : "Taxes OFF"}</span>
                                </div>
                                <hr style={{ border: "none", borderTop: "1px solid var(--border-subtle)", margin: "4px 0" }} />
                                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: 2 }}>VIX Filter</div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                                    <label style={{ fontSize: 10 }}>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Min VIX</span>
                                        <input type="number" value={vixMin} onChange={e => setVixMin(Number(e.target.value))} className="input-field" min="0" step="1" />
                                    </label>
                                    <label style={{ fontSize: 10 }}>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 3 }}>Max VIX</span>
                                        <input type="number" value={vixMax} onChange={e => setVixMax(Number(e.target.value))} className="input-field" min="0" step="1" />
                                    </label>
                                </div>
                            </div>

                            {/* Cost Impact Summary */}
                            {(slippage > 0 || brokeragePerOrder > 0 || useTaxes) && (
                                <div style={{ marginTop: 14, padding: 10, background: "rgba(239,68,68,0.06)", borderRadius: "var(--radius-sm)", border: "1px solid rgba(239,68,68,0.15)" }}>
                                    <div style={{ fontSize: 9, color: "var(--text-dim)", marginBottom: 4, textTransform: "uppercase" }}>Cost Impact</div>
                                    <div style={{ fontSize: 10, color: "var(--red-bright)", marginBottom: 2 }}>Per trade: Rs.{costPerTrade.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
                                    <div style={{ fontSize: 10, color: "var(--red-bright)", marginBottom: 4 }}>Total: Rs.{totalCost.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: netPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>Net: {fmtRs(netPnl)}</div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* ════════ RIGHT: Results ════════ */}
                    <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

                        {/* Strategy Description */}
                        <div className="card" style={{ marginBottom: 14, padding: 14, border: "1px solid var(--accent-dim)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                                <Zap style={{ width: 15, height: 15, color: "var(--accent)" }} />
                                <span style={{ fontSize: 14, fontWeight: 700 }}>{activeStrat.name}</span>
                                <span style={{ fontSize: 9, color: "var(--text-dim)", marginLeft: "auto", background: exitMode === "hard" ? "rgba(239,154,26,0.15)" : "rgba(52,211,153,0.15)", padding: "2px 8px", borderRadius: 4, fontWeight: 600, color: exitMode === "hard" ? "var(--yellow)" : "var(--green-bright)" }}>
                                    {exitMode === "hard" ? "⚡ HARD SL (High-based)" : "📊 CLOSE SL (Candle close)"}
                                </span>
                            </div>
                            <div style={{ fontSize: 11, color: "var(--text-dim)", lineHeight: 1.6, background: "var(--bg-tertiary)", padding: "8px 12px", borderRadius: "var(--radius-sm)" }}>{activeStrat.description}</div>
                            <div style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 6 }}>Period: {activeStrat.period} · Entry {activeStrat.entry_time} · Exit {activeStrat.exit_time} · Lot {activeStrat.lot_size} · NIFTY Weekly</div>
                        </div>

                        {/* Stat Cards Row 1 */}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 8 }}>
                            <StatCard label="Trades" value={`${data.trades}`} sub={`${data.trading_days} days`} />
                            <StatCard label="Win Rate" value={`${data.win_rate}%`} color={data.win_rate >= 55 ? "var(--green-bright)" : "var(--red-bright)"} sub={`${data.winners}W / ${data.losers}L`} />
                            <StatCard label="Gross P&L" value={fmtRs(data.gross_pnl)} color={data.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)"} sub={totalCost > 0 ? `Net: ${fmtRs(netPnl)}` : "Zero costs"} />
                            <StatCard label="Max Drawdown" value={`Rs.${data.max_drawdown.toLocaleString("en-IN")}`} color="var(--red-bright)" />
                            <StatCard label="Profit Factor" value={`${data.profit_factor}`} color={data.profit_factor >= 1.5 ? "var(--green-bright)" : "var(--text-primary)"} />
                            <StatCard label="Sharpe" value={`${data.sharpe}`} color={data.sharpe >= 3 ? "var(--green-bright)" : "var(--text-primary)"} />
                        </div>
                        {/* Stat Cards Row 2 */}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 14 }}>
                            <StatCard label="Payoff" value={`${data.payoff_ratio}`} sub="AvgW/AvgL" />
                            <StatCard label="Expectancy" value={fmtRs(data.expectancy)} color={data.expectancy >= 0 ? "var(--green-bright)" : "var(--red-bright)"} sub="Per trade" />
                            <StatCard label="Avg Win" value={fmtRs(data.avg_win)} color="var(--green-bright)" />
                            <StatCard label="Avg Loss" value={fmtRs(data.avg_loss)} color="var(--red-bright)" />
                            <StatCard label="Max Win" value={fmtRs(data.max_win)} color="var(--green-bright)" sub={`Streak: ${data.max_consec_wins}`} />
                            <StatCard label="Max Loss" value={fmtRs(data.max_loss)} color="var(--red-bright)" sub={`Streak: ${data.max_consec_losses}`} />
                        </div>

                        {/* Yearly Summary */}
                        <div className="card" style={{ marginBottom: 14, padding: 14 }}>
                            <h4 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}>
                                <TrendingUp style={{ width: 13, height: 13, color: "var(--accent)" }} /> Yearly Summary
                            </h4>
                            <div style={{ overflowX: "auto" }}>
                                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                                    <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", fontSize: 9, color: "var(--text-dim)", textTransform: "uppercase" }}>
                                        <th style={{ padding: "6px 8px", textAlign: "left" }}>Year</th>
                                        <th style={{ padding: "6px 8px", textAlign: "right" }}>Trades</th>
                                        <th style={{ padding: "6px 8px", textAlign: "right" }}>Win Rate</th>
                                        <th style={{ padding: "6px 8px", textAlign: "right" }}>Gross P&L</th>
                                        {totalCost > 0 && <th style={{ padding: "6px 8px", textAlign: "right" }}>Net P&L</th>}
                                    </tr></thead>
                                    <tbody>{years.map(y => {
                                        const yd = data.yearly[y];
                                        const wr = yd.trades > 0 ? (yd.wins / yd.trades * 100) : 0;
                                        const yrCost = costPerTrade * yd.trades;
                                        return (<tr key={y} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                            <td style={{ padding: "6px 8px", fontWeight: 700 }}>{y}</td>
                                            <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right" }}>{yd.trades}</td>
                                            <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", color: wr >= 55 ? "var(--green-bright)" : "var(--text-primary)" }}>{wr.toFixed(1)}%</td>
                                            <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", fontWeight: 700, color: yd.pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(yd.pnl)}</td>
                                            {totalCost > 0 && <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", fontWeight: 700, color: yd.pnl - yrCost >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(yd.pnl - yrCost)}</td>}
                                        </tr>);
                                    })}</tbody>
                                    <tfoot><tr style={{ borderTop: "2px solid var(--border-subtle)", fontWeight: 700 }}>
                                        <td style={{ padding: "6px 8px" }}>TOTAL</td>
                                        <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right" }}>{data.trades}</td>
                                        <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right" }}>{data.win_rate}%</td>
                                        <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", color: data.gross_pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(data.gross_pnl)}</td>
                                        {totalCost > 0 && <td className="text-mono" style={{ padding: "6px 8px", textAlign: "right", color: netPnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(netPnl)}</td>}
                                    </tr></tfoot>
                                </table>
                            </div>
                        </div>

                        {/* Monthly Breakdown */}
                        <div className="card" style={{ marginBottom: 14, padding: 14 }}>
                            <div onClick={() => setShowMonthly(!showMonthly)} style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
                                <Calendar style={{ width: 13, height: 13, color: "var(--accent)" }} />
                                <h4 style={{ fontSize: 12, fontWeight: 700, flex: 1 }}>Monthly Breakdown</h4>
                                {showMonthly ? <ChevronUp style={{ width: 13, height: 13 }} /> : <ChevronDown style={{ width: 13, height: 13 }} />}
                            </div>
                            {showMonthly && (
                                <div style={{ overflowX: "auto", marginTop: 8 }}>
                                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                                        <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", fontSize: 8, color: "var(--text-dim)", textTransform: "uppercase" }}>
                                            <th style={{ padding: "4px 6px", textAlign: "left" }}>Year</th>
                                            {MONTHS.map(m => <th key={m} style={{ padding: "4px 4px", textAlign: "right", minWidth: 60 }}>{m}</th>)}
                                            <th style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700 }}>TOTAL</th>
                                        </tr></thead>
                                        <tbody>{years.map(y => (
                                            <tr key={y} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                                <td style={{ padding: "4px 6px", fontWeight: 700, fontSize: 10 }}>{y}</td>
                                                {MONTHS.map((_, mi) => {
                                                    const key = `${y}-${String(mi + 1).padStart(2, "0")}`;
                                                    const md = data.monthly[key];
                                                    if (!md || md.trades === 0) return <td key={mi} style={{ padding: "4px 4px", textAlign: "right", color: "var(--text-dim)" }}>—</td>;
                                                    const color = md.pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)";
                                                    return <td key={mi} className="text-mono" style={{ padding: "4px 4px", textAlign: "right", color, fontSize: 9 }}>{fmtRs(md.pnl)}</td>;
                                                })}
                                                <td className="text-mono" style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700, color: data.yearly[y].pnl >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(data.yearly[y].pnl)}</td>
                                            </tr>
                                        ))}</tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        {/* Year × DTE Matrix */}
                        <div className="card" style={{ marginBottom: 14, padding: 14 }}>
                            <div onClick={() => setShowDteMatrix(!showDteMatrix)} style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
                                <BarChart3 style={{ width: 13, height: 13, color: "var(--accent)" }} />
                                <h4 style={{ fontSize: 12, fontWeight: 700, flex: 1 }}>Year × DTE Matrix</h4>
                                {showDteMatrix ? <ChevronUp style={{ width: 13, height: 13 }} /> : <ChevronDown style={{ width: 13, height: 13 }} />}
                            </div>
                            {showDteMatrix && (
                                <div style={{ overflowX: "auto", marginTop: 8 }}>
                                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                                        <thead><tr style={{ borderBottom: "2px solid var(--border-subtle)", fontSize: 8, color: "var(--text-dim)", textTransform: "uppercase" }}>
                                            <th style={{ padding: "4px 6px", textAlign: "left" }}>Year</th>
                                            {DTE_COLS.map(d => <th key={d} style={{ padding: "4px 6px", textAlign: "right", minWidth: 70 }}>DTE {d}</th>)}
                                            <th style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700 }}>TOTAL</th>
                                        </tr></thead>
                                        <tbody>{years.map(y => {
                                            const ym = data.dte_matrix[y] || {};
                                            const total = DTE_COLS.reduce((s, d) => s + (ym[d] || 0), 0);
                                            return (<tr key={y} style={{ borderBottom: "1px solid var(--bg-tertiary)" }}>
                                                <td style={{ padding: "4px 6px", fontWeight: 700 }}>{y}</td>
                                                {DTE_COLS.map(d => {
                                                    const val = ym[d] || 0;
                                                    if (val === 0) return <td key={d} style={{ padding: "4px 6px", textAlign: "right", color: "var(--text-dim)" }}>—</td>;
                                                    return <td key={d} className="text-mono" style={{ padding: "4px 6px", textAlign: "right", color: val >= 0 ? "var(--green-bright)" : "var(--red-bright)", fontSize: 10 }}>
                                                        {fmtRs(val)}
                                                    </td>;
                                                })}
                                                <td className="text-mono" style={{ padding: "4px 6px", textAlign: "right", fontWeight: 700, color: total >= 0 ? "var(--green-bright)" : "var(--red-bright)" }}>{fmtRs(total)}</td>
                                            </tr>);
                                        })}</tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                    </div>
                </div>
            </main>
            <style jsx global>{`.input-field{padding:5px 8px;background:var(--bg-tertiary);border:1px solid var(--border-subtle);border-radius:var(--radius-sm);color:var(--text-primary);font-size:11px;font-family:inherit;outline:none;width:100%}.input-field:focus{border-color:var(--accent)}`}</style>
        </div>
    );
}
