"""Load clearly labeled product fixtures into an isolated staging database.

This script never touches production unless the caller explicitly points
MAK3DEALS_DATABASE at a production file. Use the default staging-deals.db.
Fixture links use example.invalid and are never real shopping offers.
"""

import csv
import os
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from offer_pipeline import _upsert_product, ensure_feed_schema, normalize_product, utc_now  # noqa: E402


def ensure_deals_table(connection):
    connection.execute(
        """CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, store TEXT, title TEXT,
        description TEXT, city TEXT, category TEXT, link TEXT,
        expires_on TEXT, verified INTEGER DEFAULT 0, created_at TEXT,
        deal_kind TEXT, sale_price TEXT, regular_price TEXT, coupon_code TEXT,
        offer_terms TEXT, checked_on TEXT, affiliate_url TEXT, product_key TEXT,
        image_url TEXT, image_source TEXT, merchant_product_id TEXT,
        currency TEXT DEFAULT 'USD', discount_percent REAL,
        availability_status TEXT, last_checked_at TEXT, source_key TEXT,
        source_provider TEXT, feed_updated_at TEXT, status TEXT DEFAULT 'active',
        raw_payload_hash TEXT)"""
    )


def main():
    database_path = os.environ.get("MAK3DEALS_DATABASE", str(ROOT / "staging-deals.db"))
    origin = os.environ.get("MAK3DEALS_STAGING_ORIGIN", "http://127.0.0.1:5001").rstrip("/")
    fixture_path = ROOT / "tests" / "fixtures" / "awin_staging.csv"
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_deals_table(connection)
        ensure_feed_schema(connection)
        connection.execute("DELETE FROM deals WHERE source_key='staging-fixtures'")
        checked_at = utc_now()
        imported = 0
        with fixture_path.open(newline='', encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                row = {key: value.strip() for key, value in row.items()}
                row["merchant_image_url"] = row["merchant_image_url"].replace("__STAGING_ORIGIN__", origin)
                product, reason = normalize_product(
                    row,
                    {"source_key": "staging-fixtures", "store": row["brand"], "provider": "staging-fixture"},
                    checked_at,
                )
                if not product:
                    raise RuntimeError(f"fixture rejected: {row.get('id')}: {reason}")
                _upsert_product(connection, product)
                imported += 1
        connection.execute(
            """INSERT INTO feed_sources
               (source_key, store, url, mode, enabled, http_status, status, checked_at,
                offer_count, message, last_imported_at, imported_count)
               VALUES ('staging-fixtures', 'Staging fixtures', 'local fixture file', 'fixture', 1, 200,
                       'reachable', ?, ?, 'TEST FIXTURES ONLY — never publish as real deals.', ?, ?) 
               ON CONFLICT(source_key) DO UPDATE SET checked_at=excluded.checked_at,
                 offer_count=excluded.offer_count, message=excluded.message,
                 last_imported_at=excluded.last_imported_at, imported_count=excluded.imported_count""",
            (checked_at, imported, checked_at, imported),
        )
        connection.execute(
            """INSERT INTO feed_runs
               (started_at, completed_at, published_count, retired_count, error_count, mode, message)
               VALUES (?, ?, ?, 0, 0, 'staging-fixture', 'TEST FIXTURES ONLY — not production inventory.')""",
            (checked_at, checked_at, imported),
        )
        connection.commit()
        print(f"Loaded {imported} clearly labeled staging fixtures into {database_path}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
