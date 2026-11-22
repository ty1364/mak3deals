"""Fail unless the live/local database meets the Phase 1 product milestone."""

import json
import sqlite3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SOURCES = {"walmart", "best-buy", "amazon", "target", "home-depot"}


def main():
    connection = sqlite3.connect(ROOT / "deals.db")
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """SELECT source_key, store, title, sale_price, regular_price, discount_percent,
                  link, image_url, last_checked_at, availability_status
           FROM deals WHERE deal_kind='product' AND verified=1 AND status='active'"""
    ).fetchall()
    connected = {row["source_key"] for row in rows if row["source_key"]}
    invalid = []
    for row in rows:
        missing = [
            field for field in ("store", "title", "sale_price", "regular_price", "discount_percent",
                                "link", "image_url", "last_checked_at", "availability_status")
            if not row[field]
        ]
        if missing or not str(row["link"]).startswith(("http://", "https://")):
            invalid.append({"store": row["store"], "title": row["title"], "missing": missing or ["direct product URL"]})
    latest_run = connection.execute(
        "SELECT mode, published_count, completed_at FROM feed_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    result = {
        "pass": len(connected) >= 5 and len(rows) >= 100 and not invalid,
        "connected_merchants": len(connected),
        "required_merchants": sorted(REQUIRED_SOURCES),
        "active_product_records": len(rows),
        "invalid_records": invalid[:10],
        "latest_run": dict(latest_run) if latest_run else None,
    }
    print(json.dumps(result, indent=2))
    connection.close()
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
