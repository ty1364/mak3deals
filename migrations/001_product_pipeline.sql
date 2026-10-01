-- Mak3Deals Phase 1 PostgreSQL schema preparation.
-- Additive only: no DROP, TRUNCATE, DELETE, or data rewrite.
-- Apply only after the app's PostgreSQL connection layer is enabled.

CREATE TABLE IF NOT EXISTS deals (
    id BIGSERIAL PRIMARY KEY,
    store TEXT,
    title TEXT,
    description TEXT,
    city TEXT,
    category TEXT,
    link TEXT,
    expires_on DATE,
    verified INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deal_kind TEXT NOT NULL DEFAULT 'deal',
    sale_price TEXT,
    regular_price TEXT,
    coupon_code TEXT,
    offer_terms TEXT,
    checked_on DATE,
    affiliate_url TEXT,
    product_key TEXT,
    image_url TEXT,
    image_source TEXT,
    merchant_product_id TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    discount_percent NUMERIC(6,2),
    availability_status TEXT,
    last_checked_at TIMESTAMPTZ,
    source_key TEXT,
    source_provider TEXT,
    feed_updated_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',
    raw_payload_hash TEXT
);

ALTER TABLE deals ADD COLUMN IF NOT EXISTS merchant_product_id TEXT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'USD';
ALTER TABLE deals ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(6,2);
ALTER TABLE deals ADD COLUMN IF NOT EXISTS availability_status TEXT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS source_key TEXT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS source_provider TEXT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS feed_updated_at TIMESTAMPTZ;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE deals ADD COLUMN IF NOT EXISTS raw_payload_hash TEXT;

CREATE TABLE IF NOT EXISTS feed_sources (
    source_key TEXT PRIMARY KEY,
    store TEXT NOT NULL,
    url TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'product-feed',
    enabled INTEGER NOT NULL DEFAULT 0,
    http_status INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    checked_at TIMESTAMPTZ,
    offer_count INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    last_imported_at TIMESTAMPTZ,
    last_error TEXT,
    imported_count INTEGER NOT NULL DEFAULT 0,
    retired_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS feed_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    published_count INTEGER NOT NULL DEFAULT 0,
    retired_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    mode TEXT NOT NULL DEFAULT 'product-ingestion',
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_deals_active_products
    ON deals (deal_kind, status, verified, source_key);
CREATE INDEX IF NOT EXISTS idx_deals_product_identity
    ON deals (source_key, merchant_product_id);
CREATE INDEX IF NOT EXISTS idx_feed_runs_completed
    ON feed_runs (completed_at DESC);
