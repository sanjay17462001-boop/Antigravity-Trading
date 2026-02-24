// Hardcoded Strategy 1 data — separated from page component for maintainability

export interface ModeData {
    trades: number; trading_days: number; winners: number; losers: number;
    win_rate: number; gross_pnl: number; max_drawdown: number;
    profit_factor: number; payoff_ratio: number; expectancy: number;
    avg_win: number; avg_loss: number; max_win: number; max_loss: number;
    sharpe: number; calmar: number; max_consec_wins: number; max_consec_losses: number;
    yearly: Record<number, { trades: number; pnl: number; wins: number }>;
    monthly: Record<string, { trades: number; pnl: number; wins: number }>;
    dte_matrix: Record<number, Record<string, number>>;
    dte_counts: Record<number, Record<string, number>>;
}

export interface StrategyData {
    id: string; name: string; description: string;
    period: string; lot_size: number; entry_time: string; exit_time: string;
    hard: ModeData; close: ModeData;
}

export const STRATEGY_1: StrategyData = {
    id: "strat_01", name: "ATM Straddle + Re-entry on SL",
    description: "Entry 9:16, exit 14:30. Sell 1 ATM CE + 1 ATM PE with 30% hard SL. Re-entry: On CE/PE SL hit, sell 1 more ATM CE/PE with 30% SL when price +10%. Global SL Rs 9000. Profit lock: Rs 200 when PnL reaches Rs 1500. Lot size 65. Weekly expiry. NIFTY.",
    period: "2021-01-01 to 2026-02-18", lot_size: 65, entry_time: "09:16", exit_time: "14:30",
    hard: {
        trades: 2605, trading_days: 1253, winners: 1565, losers: 1035,
        win_rate: 60.1, gross_pnl: 877108, max_drawdown: 20218,
        profit_factor: 1.80, payoff_ratio: 1.19, expectancy: 337,
        avg_win: 1265, avg_loss: -1065, max_win: 8612, max_loss: -9286,
        sharpe: 5.39, calmar: 14.68, max_consec_wins: 18, max_consec_losses: 5,
        yearly: {
            2021: { trades: 517, pnl: 162600, wins: 308 }, 2022: { trades: 511, pnl: 191606, wins: 318 },
            2023: { trades: 513, pnl: 122787, wins: 313 }, 2024: { trades: 507, pnl: 170884, wins: 305 },
            2025: { trades: 492, pnl: 198868, wins: 297 }, 2026: { trades: 65, pnl: 30362, wins: 38 },
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
        dte_counts: {
            2021: { "0": 112, "1": 105, "2": 104, "3": 97, "5": 8, "6": 91 },
            2022: { "0": 112, "1": 99, "2": 98, "3": 100, "5": 2, "6": 100 },
            2023: { "0": 111, "1": 113, "2": 94, "3": 93, "5": 4, "6": 98 },
            2024: { "0": 111, "1": 95, "2": 111, "3": 96, "5": 2, "6": 92 },
            2025: { "0": 112, "1": 98, "2": 63, "3": 63, "4": 37, "5": 35, "6": 84 },
            2026: { "0": 13, "1": 12, "4": 15, "5": 12, "6": 13 },
        },
    },
    close: {
        trades: 2562, trading_days: 1253, winners: 1581, losers: 975,
        win_rate: 61.7, gross_pnl: 1004296, max_drawdown: 13452,
        profit_factor: 2.02, payoff_ratio: 1.25, expectancy: 390,
        avg_win: 1259, avg_loss: -1011, max_win: 8612, max_loss: -7504,
        sharpe: 6.58, calmar: 15.02, max_consec_wins: 15, max_consec_losses: 7,
        yearly: {
            2021: { trades: 505, pnl: 168779, wins: 309 }, 2022: { trades: 504, pnl: 194379, wins: 312 },
            2023: { trades: 502, pnl: 127910, wins: 305 }, 2024: { trades: 500, pnl: 238277, wins: 310 },
            2025: { trades: 487, pnl: 236899, wins: 311 }, 2026: { trades: 64, pnl: 38051, wins: 38 },
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
        dte_counts: {
            2021: { "0": 108, "1": 101, "2": 102, "3": 96, "5": 8, "6": 90 },
            2022: { "0": 109, "1": 97, "2": 97, "3": 100, "5": 2, "6": 99 },
            2023: { "0": 108, "1": 107, "2": 93, "3": 93, "5": 4, "6": 97 },
            2024: { "0": 109, "1": 94, "2": 107, "3": 96, "5": 2, "6": 92 },
            2025: { "0": 108, "1": 98, "2": 62, "3": 63, "4": 37, "5": 35, "6": 84 },
            2026: { "0": 13, "1": 12, "4": 14, "5": 12, "6": 13 },
        },
    },
};

export const STRATEGIES: StrategyData[] = [STRATEGY_1];
