"""Editorial retailer-deal discovery without unauthorized scraping.

The workflow records official source checks and accepts candidates only from a
configured permitted feed or an authenticated editor. It never treats a
retailer landing page as proof of a numerical discount and never claims an
affiliate relationship for an editorial pick.
"""

from datetime import date, datetime, timezone
import hashlib
import json
import os
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RETAILER_SOURCE_DEFINITIONS = [
    {
        "key": "walmart",
        "merchant": "Walmart",
        "official_source_url": "https://www.walmart.com/shop/deals/shop-advertised-deals",
        "source_type": "official deals and weekly-ad source",
    },
    {
        "key": "target",
        "merchant": "Target",
        "official_source_url": "https://www.target.com/c/top-deals/-/N-4xw74",
        "source_type": "official deals and digital-promotions source",
    },
    {
        "key": "fred-meyer",
        "merchant": "Fred Meyer",
        "official_source_url": "https://www.fredmeyer.com/savingsoverview/weekly-ad-info",
        "source_type": "official weekly-ad and digital-promotions source",
    },
]

SOURCE_BY_KEY = {item["key"]: item for item in RETAILER_SOURCE_DEFINITIONS}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_retailer_deal_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS retailer_sources (
            source_key TEXT PRIMARY KEY,
            merchant TEXT NOT NULL,
            official_source_url TEXT NOT NULL,
            source_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_checked_at TEXT,
            http_status INTEGER,
            status TEXT NOT NULL DEFAULT 'registered',
            last_error TEXT,
            last_candidate_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS retailer_discovery_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            candidate_count INTEGER NOT NULL DEFAULT 0,
            approved_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0,
            expired_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            message TEXT
        );
        CREATE TABLE IF NOT EXISTS retailer_deal_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_key TEXT NOT NULL,
            merchant TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            source_url TEXT NOT NULL,
            retailer_url TEXT NOT NULL,
            checked_on TEXT NOT NULL,
            promotion_type TEXT NOT NULL DEFAULT 'editorial link-out',
            promotion_terms TEXT,
            expires_on TEXT,
            location_restrictions TEXT,
            membership_restrictions TEXT,
            link_scope TEXT NOT NULL DEFAULT 'editorial',
            status TEXT NOT NULL DEFAULT 'candidate',
            dedupe_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            reviewed_at TEXT,
            review_note TEXT,
            published_at TEXT,
            affiliate_claimed INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_retailer_candidates_status_expiry
            ON retailer_deal_candidates (status, expires_on, merchant);
        CREATE INDEX IF NOT EXISTS idx_retailer_candidates_source
            ON retailer_deal_candidates (source_key, last_seen_at);
        """
    )
    for source in RETAILER_SOURCE_DEFINITIONS:
        connection.execute(
            """
            INSERT INTO retailer_sources (source_key, merchant, official_source_url, source_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                merchant=excluded.merchant,
                official_source_url=excluded.official_source_url,
                source_type=excluded.source_type
            """,
            (source["key"], source["merchant"], source["official_source_url"], source["source_type"]),
        )
    connection.commit()


def _date_value(value, field, allow_blank=True):
    value = (value or "").strip()
    if not value and allow_blank:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _https_url(value, field):
    value = (value or "").strip()
    if not value.startswith("https://"):
        raise ValueError(f"{field} must be an https URL")
    return value


def _dedupe_key(source_key, title, retailer_url, expires_on):
    material = "|".join([source_key, " ".join(title.lower().split()), retailer_url, expires_on or ""])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def normalize_candidate(payload, checked_on=None):
    if not isinstance(payload, dict):
        raise ValueError("candidate must be an object")
    source_key = str(payload.get("source_key") or "").strip().lower()
    source = SOURCE_BY_KEY.get(source_key)
    if not source:
        raise ValueError("source_key must be walmart, target, or fred-meyer")
    title = " ".join(str(payload.get("title") or "").split())
    summary = " ".join(str(payload.get("summary") or "").split())
    if not title or not summary:
        raise ValueError("title and original summary are required")
    source_url = _https_url(payload.get("source_url") or source["official_source_url"], "source_url")
    retailer_url = _https_url(payload.get("retailer_url"), "retailer_url")
    checked = _date_value(payload.get("checked_on") or checked_on or date.today().isoformat(), "checked_on", allow_blank=False)
    expires = _date_value(payload.get("expires_on"), "expires_on")
    promotion_type = " ".join(str(payload.get("promotion_type") or "editorial link-out").split())[:80]
    link_scope = str(payload.get("link_scope") or "editorial").strip().lower()
    if link_scope not in {"editorial", "individual-offer", "weekly-ad", "digital-promotion"}:
        raise ValueError("link_scope must be editorial, individual-offer, weekly-ad, or digital-promotion")
    # Editorial picks do not inherit affiliate claims from arbitrary input.
    affiliate_claimed = 0
    return {
        "source_key": source_key,
        "merchant": source["merchant"],
        "title": title[:240],
        "summary": summary[:600],
        "source_url": source_url,
        "retailer_url": retailer_url,
        "checked_on": checked,
        "promotion_type": promotion_type,
        "promotion_terms": " ".join(str(payload.get("promotion_terms") or "").split())[:500] or None,
        "expires_on": expires,
        "location_restrictions": " ".join(str(payload.get("location_restrictions") or "").split())[:300] or None,
        "membership_restrictions": " ".join(str(payload.get("membership_restrictions") or "").split())[:300] or None,
        "link_scope": link_scope,
        "affiliate_claimed": affiliate_claimed,
    }


def upsert_candidate(connection, payload, checked_on=None):
    candidate = normalize_candidate(payload, checked_on=checked_on)
    now = utc_now()
    dedupe_key = _dedupe_key(candidate["source_key"], candidate["title"], candidate["retailer_url"], candidate["expires_on"])
    existing = connection.execute("SELECT id, status FROM retailer_deal_candidates WHERE dedupe_key=?", (dedupe_key,)).fetchone()
    if existing:
        connection.execute(
            """UPDATE retailer_deal_candidates SET summary=?, source_url=?, checked_on=?,
               promotion_type=?, promotion_terms=?, expires_on=?, location_restrictions=?,
               membership_restrictions=?, link_scope=?, last_seen_at=?, affiliate_claimed=0
               WHERE id=?""",
            (candidate["summary"], candidate["source_url"], candidate["checked_on"], candidate["promotion_type"],
             candidate["promotion_terms"], candidate["expires_on"], candidate["location_restrictions"],
             candidate["membership_restrictions"], candidate["link_scope"], now, existing["id"]),
        )
        return existing["id"], False
    cursor = connection.execute(
        """INSERT INTO retailer_deal_candidates
           (source_key, merchant, title, summary, source_url, retailer_url, checked_on,
            promotion_type, promotion_terms, expires_on, location_restrictions,
            membership_restrictions, link_scope, status, dedupe_key, created_at,
            last_seen_at, affiliate_claimed)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?, ?, ?, 0)""",
        (candidate["source_key"], candidate["merchant"], candidate["title"], candidate["summary"],
         candidate["source_url"], candidate["retailer_url"], candidate["checked_on"], candidate["promotion_type"],
         candidate["promotion_terms"], candidate["expires_on"], candidate["location_restrictions"],
         candidate["membership_restrictions"], candidate["link_scope"], dedupe_key, now, now),
    )
    return cursor.lastrowid, True


def expire_candidates(connection, today=None):
    today = today or date.today().isoformat()
    cursor = connection.execute(
        "UPDATE retailer_deal_candidates SET status='expired' WHERE status IN ('candidate','approved') AND expires_on IS NOT NULL AND expires_on < ?",
        (today,),
    )
    connection.commit()
    return cursor.rowcount


def _configured_feed_url(source_key):
    return os.environ.get("MAK3DEALS_RETAILER_FEED_" + source_key.upper().replace("-", "_"), "").strip()


def _fetch_json_candidates(url):
    request = Request(url, headers={"User-Agent": "Mak3Deals-EditorialDiscovery/1.0 (+https://mak3deals.com/about)", "Accept": "application/json"})
    with urlopen(request, timeout=45) as response:
        body = response.read()
    payload = json.loads(body.decode("utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("candidates", payload.get("items", []))
    if not isinstance(payload, list):
        raise ValueError("permitted retailer discovery feed must return a candidate array")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("permitted retailer discovery feed candidates must be objects")
    return payload


def _check_official_source(url):
    request = Request(url, headers={"User-Agent": "Mak3Deals-EditorialDiscovery/1.0 (+https://mak3deals.com/about)"}, method="HEAD")
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, None
    except HTTPError as exc:
        return exc.code, str(exc)
    except (URLError, TimeoutError, OSError) as exc:
        return None, str(exc)


def discover_retailer_deals(connection, check_urls=True, now=None):
    """Run the safe daily pass; only permitted JSON feeds create candidates."""
    ensure_retailer_deal_schema(connection)
    started = now or utc_now()
    expired_count = expire_candidates(connection)
    candidate_count = 0
    errors = []
    for source in RETAILER_SOURCE_DEFINITIONS:
        status, error = (200, None)
        if check_urls:
            status, error = _check_official_source(source["official_source_url"])
        feed_url = _configured_feed_url(source["key"])
        source_count = 0
        if feed_url:
            try:
                for payload in _fetch_json_candidates(feed_url):
                    payload = dict(payload)
                    payload["source_key"] = source["key"]
                    _, created = upsert_candidate(connection, payload, checked_on=date.today().isoformat())
                    source_count += int(created)
            except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{source['merchant']}: permitted feed error: {exc}")
                error = str(exc)
        candidate_count += source_count
        connection.execute(
            """UPDATE retailer_sources SET last_checked_at=?, http_status=?, status=?, last_error=?, last_candidate_count=?
               WHERE source_key=?""",
            (started, status, "error" if error else "checked", error, source_count, source["key"]),
        )
    counts = connection.execute(
        "SELECT status, COUNT(*) AS count FROM retailer_deal_candidates GROUP BY status"
    ).fetchall()
    status_counts = {row["status"]: row["count"] for row in counts}
    completed = utc_now()
    message = "Official source checks completed; only configured permitted feeds or editor submissions create candidates."
    if errors:
        message = message + " " + " | ".join(errors)
    connection.execute(
        """INSERT INTO retailer_discovery_runs
           (started_at, completed_at, candidate_count, approved_count, rejected_count, expired_count, error_count, message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (started, completed, candidate_count, status_counts.get("approved", 0), status_counts.get("rejected", 0), expired_count, len(errors), message),
    )
    connection.commit()
    return {
        "started_at": started,
        "completed_at": completed,
        "candidate_count": candidate_count,
        "approved_count": status_counts.get("approved", 0),
        "rejected_count": status_counts.get("rejected", 0),
        "expired_count": expired_count,
        "error_count": len(errors),
        "message": message,
    }


def published_picks(connection, limit=None):
    query = """SELECT * FROM retailer_deal_candidates
               WHERE status='approved' AND (expires_on IS NULL OR expires_on >= ?)
               ORDER BY expires_on IS NULL, expires_on ASC, published_at DESC, id DESC"""
    values = [date.today().isoformat()]
    if limit:
        query += " LIMIT ?"
        values.append(limit)
    return connection.execute(query, values).fetchall()


def status_snapshot(connection):
    ensure_retailer_deal_schema(connection)
    expire_candidates(connection)
    latest = connection.execute("SELECT * FROM retailer_discovery_runs ORDER BY id DESC LIMIT 1").fetchone()
    counts = connection.execute("SELECT status, COUNT(*) AS count FROM retailer_deal_candidates GROUP BY status").fetchall()
    sources = connection.execute("SELECT * FROM retailer_sources ORDER BY merchant").fetchall()
    return {
        "latest_run": dict(latest) if latest else None,
        "counts": {row["status"]: row["count"] for row in counts},
        "sources": [dict(row) for row in sources],
    }
