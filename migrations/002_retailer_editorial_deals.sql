-- Additive-only preparation for the daily retailer editorial workflow.
-- This stores source checks and manually reviewed link-outs; it does not
-- copy retailer catalogs or claim affiliate attribution.

CREATE TABLE IF NOT EXISTS retailer_sources (
    source_key TEXT PRIMARY KEY,
    merchant TEXT NOT NULL,
    official_source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at TIMESTAMPTZ,
    http_status INTEGER,
    status TEXT NOT NULL DEFAULT 'registered',
    last_error TEXT,
    last_candidate_count INTEGER NOT NULL DEFAULT 0,
    hold_reason TEXT,
    source_check_state TEXT NOT NULL DEFAULT 'not_checked',
    feed_state TEXT NOT NULL DEFAULT 'unconfigured',
    feed_last_error TEXT,
    last_feed_attempt_at TIMESTAMPTZ,
    last_feed_success_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS retailer_schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS retailer_discovery_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    candidate_count INTEGER NOT NULL DEFAULT 0,
    approved_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    expired_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    source_check_failure_count INTEGER NOT NULL DEFAULT 0,
    feed_error_count INTEGER NOT NULL DEFAULT 0,
    held_count INTEGER NOT NULL DEFAULT 0,
    message TEXT
);

CREATE TABLE IF NOT EXISTS retailer_deal_candidates (
    id BIGSERIAL PRIMARY KEY,
    source_key TEXT NOT NULL REFERENCES retailer_sources(source_key),
    merchant TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retailer_url TEXT NOT NULL,
    checked_on DATE NOT NULL,
    promotion_type TEXT NOT NULL DEFAULT 'editorial link-out',
    promotion_terms TEXT,
    expires_on DATE,
    recheck_on DATE,
    evidence_reference TEXT,
    evidence_scope TEXT NOT NULL DEFAULT 'landing-page',
    location_restrictions TEXT,
    membership_restrictions TEXT,
    link_scope TEXT NOT NULL DEFAULT 'editorial',
    status TEXT NOT NULL DEFAULT 'candidate',
    dedupe_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    review_note TEXT,
    published_at TIMESTAMPTZ,
    affiliate_claimed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_retailer_candidates_status_expiry
    ON retailer_deal_candidates (status, expires_on, merchant);
CREATE INDEX IF NOT EXISTS idx_retailer_candidates_source
    ON retailer_deal_candidates (source_key, last_seen_at);

-- Additive upgrades for databases created by the earlier workflow revision.
ALTER TABLE retailer_sources ADD COLUMN IF NOT EXISTS hold_reason TEXT;
ALTER TABLE retailer_sources ADD COLUMN IF NOT EXISTS source_check_state TEXT NOT NULL DEFAULT 'not_checked';
ALTER TABLE retailer_sources ADD COLUMN IF NOT EXISTS feed_state TEXT NOT NULL DEFAULT 'unconfigured';
ALTER TABLE retailer_sources ADD COLUMN IF NOT EXISTS feed_last_error TEXT;
ALTER TABLE retailer_sources ADD COLUMN IF NOT EXISTS last_feed_attempt_at TIMESTAMPTZ;
ALTER TABLE retailer_sources ADD COLUMN IF NOT EXISTS last_feed_success_at TIMESTAMPTZ;
ALTER TABLE retailer_discovery_runs ADD COLUMN IF NOT EXISTS source_check_failure_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE retailer_discovery_runs ADD COLUMN IF NOT EXISTS feed_error_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE retailer_discovery_runs ADD COLUMN IF NOT EXISTS held_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE retailer_deal_candidates ADD COLUMN IF NOT EXISTS recheck_on DATE;
ALTER TABLE retailer_deal_candidates ADD COLUMN IF NOT EXISTS evidence_reference TEXT;
ALTER TABLE retailer_deal_candidates ADD COLUMN IF NOT EXISTS evidence_scope TEXT NOT NULL DEFAULT 'landing-page';
