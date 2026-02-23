-- =========================================================================
-- Antigravity Trading — Supabase Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- =========================================================================

-- 1. Strategies (CRUD for registered strategies)
CREATE TABLE IF NOT EXISTS strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    code TEXT DEFAULT '',
    params JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. Backtest runs (execution history)
CREATE TABLE IF NOT EXISTS backtest_runs (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    params JSONB DEFAULT '{}',
    result_summary JSONB DEFAULT '{}',
    status TEXT DEFAULT 'running'
);

-- 3. Trades (individual trade records)
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    strategy_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION,
    quantity INTEGER NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    pnl DOUBLE PRECISION DEFAULT 0,
    charges DOUBLE PRECISION DEFAULT 0,
    slippage DOUBLE PRECISION DEFAULT 0,
    meta JSONB DEFAULT '{}',
    mode TEXT DEFAULT 'backtest'
);

-- 4. Signals log (audit trail)
CREATE TABLE IF NOT EXISTS signals_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    strategy_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    strength DOUBLE PRECISION DEFAULT 100,
    reason TEXT DEFAULT '',
    mode TEXT DEFAULT 'backtest'
);

-- 5. Data catalog (available data inventory)
CREATE TABLE IF NOT EXISTS data_catalog (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    segment TEXT NOT NULL,
    interval TEXT NOT NULL,
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    file_path TEXT NOT NULL,
    row_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(symbol, exchange, segment, interval, from_date, to_date)
);

-- 6. AI strategies (parsed strategy configs — replaces JSON file storage)
CREATE TABLE IF NOT EXISTS ai_strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    legs JSONB NOT NULL DEFAULT '[]',
    entry_time TEXT DEFAULT '09:20',
    exit_time TEXT DEFAULT '15:15',
    sl_pct DOUBLE PRECISION DEFAULT 25.0,
    sl_type TEXT DEFAULT 'hard',
    target_pct DOUBLE PRECISION DEFAULT 0.0,
    target_type TEXT DEFAULT 'hard',
    lot_size INTEGER DEFAULT 25,
    vix_min DOUBLE PRECISION,
    vix_max DOUBLE PRECISION,
    dte_min INTEGER,
    dte_max INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. Backtest history (for AI strategy comparison)
CREATE TABLE IF NOT EXISTS ai_backtest_history (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    config JSONB DEFAULT '{}',
    summary JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trades_run ON trades(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals_log(strategy_id);
CREATE INDEX IF NOT EXISTS idx_catalog_symbol ON data_catalog(symbol, exchange);
CREATE INDEX IF NOT EXISTS idx_ai_strategies_name ON ai_strategies(name);

-- Enable Row Level Security (allow all for anon key — single-user app)
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_backtest_history ENABLE ROW LEVEL SECURITY;

-- Policies: allow full access for anon (single-user app)
CREATE POLICY "Allow all" ON strategies FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON backtest_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON trades FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON signals_log FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON data_catalog FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON ai_strategies FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON ai_backtest_history FOR ALL USING (true) WITH CHECK (true);
