-- Migration: 001_add_earnings_dividends_schema.sql
-- Database: helion_db

-- 1. Add earnings estimate & surprise columns to reports table
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS eps_actual NUMERIC;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS eps_estimate NUMERIC;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS eps_surprise_pct NUMERIC;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS revenue_actual NUMERIC;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS revenue_estimate NUMERIC;

-- 2. Create dividends table if not exists
CREATE TABLE IF NOT EXISTS public.dividends (
    id BIGSERIAL PRIMARY KEY,
    id_ticker BIGINT NOT NULL REFERENCES public.ticker(id) ON DELETE CASCADE,
    ex_date DATE NOT NULL,
    amount NUMERIC NOT NULL,
    pay_date DATE,
    record_date DATE,
    declaration_date DATE,
    yield NUMERIC,
    frequency TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_ticker_exdate UNIQUE (id_ticker, ex_date)
);

-- Index for fast retrieval of dividends by ticker and date
CREATE INDEX IF NOT EXISTS idx_dividends_ticker_exdate ON public.dividends(id_ticker, ex_date DESC);
CREATE INDEX IF NOT EXISTS idx_reports_ticker_date ON public.reports(id_ticker, date DESC);

-- 3. Add Russian description to company table
ALTER TABLE public.company ADD COLUMN IF NOT EXISTS description_ru TEXT;
ALTER TABLE public.company ADD COLUMN IF NOT EXISTS sector TEXT;
ALTER TABLE public.company ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE public.company ADD COLUMN IF NOT EXISTS peers TEXT[];
