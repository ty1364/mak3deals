"""Verified offer-feed plumbing for Mak3Deals.

This module deliberately does not scrape prices or invent coupon codes. It checks
that configured official retailer pages are reachable and records feed health.
Actual offer ingestion can be added when an approved affiliate API/feed is
available for a retailer.
"""

from datetime import date, datetime
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SOURCE_DEFINITIONS = [
    {
        "key": "walmart",
        "store": "Walmart",
        "url": "https://www.walmart.com/shop/deals/shop-advertised-deals",
        "mode": "official-page",
        "enabled": True,
        "note": "Reachability only until an approved feed is connected.",
    },
    {
        "key": "best-buy",
        "store": "Best Buy",
        "url": "https://www.bestbuy.com/top-deals-b",
        "mode": "official-page",
        "enabled": True,
        "note": "Reachability only until an approved feed is connected.",
    },
    {
        "key": "amazon",
        "store": "Amazon",
        "url": "https://www.amazon.com/gp/goldbox",
        "mode": "affiliate-pending",
        "enabled": False,
        "note": "Enable after Amazon Associates approval and feed credentials.",
    },
    {
        "key": "target",
        "store": "Target",
        "url": "https://www.target.com/c/deals/-/N-4xw74",
        "mode": "affiliate-pending",
        "enabled": False,
        "note": "Enable after an approved partner/feed is connected.",
    },
    {
        "key": "home-depot",
        "store": "Home Depot",
        "url": "https://www.homedepot.com/SpecialBuy",
        "mode": "affiliate-pending",
        "enabled": False,
        "note": "Enable after an approved partner/feed is connected.",
    },
]


def ensure_feed_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS feed_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            published_count INTEGER NOT NULL DEFAULT 0,
            retired_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            mode TEXT NOT NULL DEFAULT 'source-health',
            message TEXT
        );
        CREATE TABLE IF NOT EXISTS feed_sources (
            source_key TEXT PRIMARY KEY,
            store TEXT NOT NULL,
            url TEXT NOT NULL,
            mode TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            http_status INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            checked_at TEXT,
            offer_count INTEGER NOT NULL DEFAULT 0,
            message TEXT
        );
        """
    )
    for source in SOURCE_DEFINITIONS:
        connection.execute(
            """
            INSERT INTO feed_sources
                (source_key, store, url, mode, enabled, message)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                store=excluded.store,
                url=excluded.url,
                mode=excluded.mode,
                enabled=excluded.enabled
            """,
            (
                source["key"], source["store"], source["url"], source["mode"],
                1 if source["enabled"] else 0, source["note"],
            ),
        )


def _check_url(url, timeout=15):
    request = Request(
        url,
        headers={
            "User-Agent": "Mak3Deals-OfferHealth/1.0 (+https://mak3deals.com/about)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, "reachable"
    except HTTPError as error:
        return error.code, f"HTTP {error.code}"
    except (URLError, TimeoutError, OSError) as error:
        return None, str(error.reason if isinstance(error, URLError) else error)[:240]


def refresh_sources(connection, check_urls=True, dry_run=False):
    """Check enabled sources and retire expired verified rows.

    This is intentionally conservative: it never creates an offer from page
    markup and never changes a price. A future affiliate adapter can increment
    published_count when it imports a signed/official feed row.
    """
    ensure_feed_schema(connection)
    started_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    errors = 0
    source_results = []

    for source in SOURCE_DEFINITIONS:
        if not source["enabled"]:
            status, http_status, message = "pending", None, source["note"]
        elif not check_urls:
            status, http_status, message = "skipped", None, "URL check disabled"
        else:
            http_status, message = _check_url(source["url"])
            status = "reachable" if http_status and 200 <= http_status < 400 else "error"
            errors += status == "error"

        offer_count = connection.execute(
            "SELECT COUNT(*) FROM deals WHERE lower(store)=lower(?) AND verified=1 AND expires_on >= ?",
            (source["store"], date.today().isoformat()),
        ).fetchone()[0]
        source_results.append({
            "key": source["key"],
            "store": source["store"],
            "url": source["url"],
            "mode": source["mode"],
            "enabled": source["enabled"],
            "status": status,
            "http_status": http_status,
            "offer_count": offer_count,
            "message": message,
        })
        if not dry_run:
            connection.execute(
                """
                UPDATE feed_sources SET http_status=?, status=?, checked_at=?,
                    offer_count=?, message=? WHERE source_key=?
                """,
                (http_status, status, datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                 offer_count, message, source["key"]),
            )

    expired_count = connection.execute(
        "SELECT COUNT(*) FROM deals WHERE verified=1 AND expires_on < ?",
        (date.today().isoformat(),),
    ).fetchone()[0]
    if not dry_run and expired_count:
        connection.execute(
            "UPDATE deals SET verified=0 WHERE verified=1 AND expires_on < ?",
            (date.today().isoformat(),),
        )

    completed_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    result = {
        "started_at": started_at,
        "completed_at": completed_at,
        "published_count": 0,
        "retired_count": expired_count,
        "error_count": errors,
        "mode": "dry-run" if dry_run else "source-health",
        "sources": source_results,
    }
    if not dry_run:
        connection.execute(
            """
            INSERT INTO feed_runs
                (started_at, completed_at, published_count, retired_count, error_count, mode, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (started_at, completed_at, 0, expired_count, errors, "source-health",
             "No new offers imported; affiliate feeds are not connected yet."),
        )
        connection.commit()
    return result
