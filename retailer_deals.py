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
import re
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


RETAILER_SOURCE_DEFINITIONS = [
    {
        "key": "walmart",
        "merchant": "Walmart",
        "official_source_url": "https://www.walmart.com/shop/deals/shop-advertised-deals",
        "source_type": "official deals and weekly-ad source",
        "allowed_hosts": {"walmart.com", "www.walmart.com"},
        "enabled": 1,
        "hold_reason": None,
    },
    {
        "key": "target",
        "merchant": "Target",
        "official_source_url": "https://www.target.com/c/top-deals/-/N-4xw74",
        "source_type": "official deals and digital-promotions source",
        "allowed_hosts": {"target.com", "www.target.com"},
        "enabled": 0,
        "hold_reason": "Target item-level promotion evidence is on hold pending clean verification.",
    },
    {
        "key": "fred-meyer",
        "merchant": "Fred Meyer",
        "official_source_url": "https://www.fredmeyer.com/savingsoverview/weekly-ad-info",
        "source_type": "official weekly-ad and digital-promotions source",
        "allowed_hosts": {"fredmeyer.com", "www.fredmeyer.com"},
        "enabled": 1,
        "hold_reason": None,
    },
]

SOURCE_BY_KEY = {item["key"]: item for item in RETAILER_SOURCE_DEFINITIONS}


class SourceHoldError(ValueError):
    """Raised when an operator tries to use a held retailer source."""


def source_is_held(connection, source_key):
    source = SOURCE_BY_KEY.get(source_key)
    if not source:
        return False
    if not source.get("enabled", 1):
        return True
    row = connection.execute(
        "SELECT enabled FROM retailer_sources WHERE source_key=?", (source_key,)
    ).fetchone()
    return bool(row is not None and not row[0])


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
            last_candidate_count INTEGER NOT NULL DEFAULT 0,
            hold_reason TEXT,
            source_check_state TEXT NOT NULL DEFAULT 'not_checked',
            feed_state TEXT NOT NULL DEFAULT 'unconfigured',
            feed_last_error TEXT,
            last_feed_attempt_at TEXT,
            last_feed_success_at TEXT
        );
        CREATE TABLE IF NOT EXISTS retailer_schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
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
            source_check_failure_count INTEGER NOT NULL DEFAULT 0,
            feed_error_count INTEGER NOT NULL DEFAULT 0,
            held_count INTEGER NOT NULL DEFAULT 0,
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
            recheck_on TEXT,
            evidence_reference TEXT,
            evidence_scope TEXT NOT NULL DEFAULT 'landing-page',
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
    source_columns = {row[1] for row in connection.execute("PRAGMA table_info(retailer_sources)").fetchall()}
    for column, definition in {
        "hold_reason": "TEXT",
        "source_check_state": "TEXT NOT NULL DEFAULT 'not_checked'",
        "feed_state": "TEXT NOT NULL DEFAULT 'unconfigured'",
        "feed_last_error": "TEXT",
        "last_feed_attempt_at": "TEXT",
        "last_feed_success_at": "TEXT",
    }.items():
        if column not in source_columns:
            connection.execute(f"ALTER TABLE retailer_sources ADD COLUMN {column} {definition}")
    run_columns = {row[1] for row in connection.execute("PRAGMA table_info(retailer_discovery_runs)").fetchall()}
    for column, definition in {
        "source_check_failure_count": "INTEGER NOT NULL DEFAULT 0",
        "feed_error_count": "INTEGER NOT NULL DEFAULT 0",
        "held_count": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        if column not in run_columns:
            connection.execute(f"ALTER TABLE retailer_discovery_runs ADD COLUMN {column} {definition}")
    candidate_columns = {row[1] for row in connection.execute("PRAGMA table_info(retailer_deal_candidates)").fetchall()}
    for column, definition in {
        "recheck_on": "TEXT",
        "evidence_reference": "TEXT",
        "evidence_scope": "TEXT NOT NULL DEFAULT 'landing-page'",
    }.items():
        if column not in candidate_columns:
            connection.execute(f"ALTER TABLE retailer_deal_candidates ADD COLUMN {column} {definition}")
    for source in RETAILER_SOURCE_DEFINITIONS:
        connection.execute(
            """
            INSERT INTO retailer_sources (source_key, merchant, official_source_url, source_type, enabled, hold_reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                merchant=excluded.merchant,
                official_source_url=excluded.official_source_url,
                source_type=excluded.source_type,
                enabled=excluded.enabled,
                hold_reason=excluded.hold_reason
            """,
            (source["key"], source["merchant"], source["official_source_url"], source["source_type"], source["enabled"], source["hold_reason"]),
        )
    migration = connection.execute(
        "SELECT value FROM retailer_schema_meta WHERE key='stable_dedupe_v1'"
    ).fetchone()
    if not migration:
        # Migrate the old expiration-sensitive key to a stable source/title/url
        # identity without deleting any data. Duplicate legacy rows are
        # retained but rejected so their history remains inspectable.
        rows = connection.execute(
            "SELECT id, source_key, title, retailer_url FROM retailer_deal_candidates ORDER BY id"
        ).fetchall()
        for row in rows:
            connection.execute("UPDATE retailer_deal_candidates SET dedupe_key=? WHERE id=?", (f"migrating:{row['id']}", row["id"]))
        seen = set()
        for row in rows:
            stable_key = _dedupe_key(row["source_key"], row["title"], row["retailer_url"])
            if stable_key in seen:
                connection.execute(
                    "UPDATE retailer_deal_candidates SET status='rejected', review_note='Superseded duplicate retained during stable-identity migration.', dedupe_key=? WHERE id=?",
                    (f"superseded:{row['id']}", row["id"]),
                )
            else:
                seen.add(stable_key)
                connection.execute("UPDATE retailer_deal_candidates SET dedupe_key=? WHERE id=?", (stable_key, row["id"]))
        connection.execute(
            "INSERT INTO retailer_schema_meta (key, value, updated_at) VALUES ('stable_dedupe_v1', 'complete', ?)",
            (utc_now(),),
        )
    connection.execute(
        "UPDATE retailer_sources SET enabled=0, hold_reason=? WHERE source_key='target'",
        (SOURCE_BY_KEY["target"]["hold_reason"],),
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
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{field} must be an https URL")
    return value


def _dedupe_key(source_key, title, retailer_url):
    material = "|".join([source_key, " ".join(title.lower().split()), retailer_url.rstrip("/")])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _validate_official_destination(source_key, value, field):
    value = _https_url(value, field)
    host = (urlparse(value).hostname or "").lower().rstrip(".")
    allowed = SOURCE_BY_KEY[source_key]["allowed_hosts"]
    if host not in allowed and not any(host.endswith("." + item) for item in allowed):
        raise ValueError(f"{field} must use the official {SOURCE_BY_KEY[source_key]['merchant']} domain")
    return value


def publication_issues(candidate):
    """Return explicit evidence/restriction gaps that block publication."""
    issues = []
    if not candidate["promotion_terms"]:
        issues.append("promotion terms are required")
    if not candidate["location_restrictions"]:
        issues.append("location restrictions or applicability must be stated")
    if not candidate["membership_restrictions"]:
        issues.append("membership or coupon requirements must be stated")
    if not candidate["evidence_reference"]:
        issues.append("a reviewed evidence reference is required")
    if candidate["evidence_scope"] not in {"landing-page", "individual-offer", "weekly-ad", "digital-promotion"}:
        issues.append("evidence scope is invalid")
    if not candidate["expires_on"] and not candidate["recheck_on"]:
        issues.append("an expiration or mandatory recheck date is required")
    if candidate["expires_on"] and candidate["expires_on"] < date.today().isoformat():
        issues.append("the promotion is expired")
    if candidate["recheck_on"] and candidate["recheck_on"] < date.today().isoformat():
        issues.append("the mandatory recheck date has passed")
    if candidate["link_scope"] == "individual-offer" and candidate["retailer_url"].rstrip("/") == candidate["source_url"].rstrip("/"):
        issues.append("an individual offer needs a distinct retailer destination")
    if candidate["evidence_scope"] == "landing-page" and re.search(r"(?:\$\s?\d|\b\d+(?:\.\d+)?\s?%|\b(?:was|off|discount|price)\b)", f"{candidate['title']} {candidate['summary']}", re.IGNORECASE):
        issues.append("landing-page evidence cannot support an individual numeric price or discount claim")
    if candidate["link_scope"] == "individual-offer" and candidate["evidence_scope"] != "individual-offer":
        issues.append("individual offers require individual-offer evidence scope")
    return issues


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
    source_url = _validate_official_destination(source_key, payload.get("source_url") or source["official_source_url"], "source_url")
    retailer_url = _validate_official_destination(source_key, payload.get("retailer_url"), "retailer_url")
    checked = _date_value(payload.get("checked_on") or checked_on or date.today().isoformat(), "checked_on", allow_blank=False)
    expires = _date_value(payload.get("expires_on"), "expires_on")
    recheck_on = _date_value(payload.get("recheck_on"), "recheck_on")
    promotion_type = " ".join(str(payload.get("promotion_type") or "editorial link-out").split())[:80]
    link_scope = str(payload.get("link_scope") or "editorial").strip().lower()
    if link_scope not in {"editorial", "individual-offer", "weekly-ad", "digital-promotion"}:
        raise ValueError("link_scope must be editorial, individual-offer, weekly-ad, or digital-promotion")
    evidence_reference = payload.get("evidence_reference")
    if evidence_reference:
        evidence_reference = _validate_official_destination(source_key, evidence_reference, "evidence_reference")
    evidence_scope = str(payload.get("evidence_scope") or ("individual-offer" if link_scope == "individual-offer" else link_scope if link_scope in {"weekly-ad", "digital-promotion"} else "landing-page")).strip().lower()
    if evidence_scope not in {"landing-page", "individual-offer", "weekly-ad", "digital-promotion"}:
        raise ValueError("evidence_scope must be landing-page, individual-offer, weekly-ad, or digital-promotion")
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
        "recheck_on": recheck_on,
        "evidence_reference": evidence_reference,
        "evidence_scope": evidence_scope,
        "location_restrictions": " ".join(str(payload.get("location_restrictions") or "").split())[:300] or None,
        "membership_restrictions": " ".join(str(payload.get("membership_restrictions") or "").split())[:300] or None,
        "link_scope": link_scope,
        "affiliate_claimed": affiliate_claimed,
    }


def upsert_candidate(connection, payload, checked_on=None):
    candidate = normalize_candidate(payload, checked_on=checked_on)
    if source_is_held(connection, candidate["source_key"]):
        raise SourceHoldError(f"{candidate['merchant']} is currently on hold")
    now = utc_now()
    dedupe_key = _dedupe_key(candidate["source_key"], candidate["title"], candidate["retailer_url"])
    existing = connection.execute("SELECT * FROM retailer_deal_candidates WHERE dedupe_key=?", (dedupe_key,)).fetchone()
    if existing:
        tracked_fields = ("summary", "source_url", "retailer_url", "checked_on", "promotion_type", "promotion_terms", "expires_on", "recheck_on", "evidence_reference", "evidence_scope", "location_restrictions", "membership_restrictions", "link_scope")
        changed = any(existing[field] != candidate[field] for field in tracked_fields)
        next_status = existing["status"]
        review_note = existing["review_note"]
        reviewed_at = existing["reviewed_at"]
        published_at = existing["published_at"]
        if changed and existing["status"] in {"approved", "published"}:
            next_status = "candidate"
            review_note = "Content changed since review; requires fresh editorial review."
            reviewed_at = None
            published_at = None
        if existing["status"] == "expired" and (candidate["expires_on"] or candidate["recheck_on"]):
            next_status = "candidate"
            review_note = "Fresh evidence received after expiry; requires editorial review."
        connection.execute(
            """UPDATE retailer_deal_candidates SET summary=?, source_url=?, checked_on=?,
               promotion_type=?, promotion_terms=?, expires_on=?, location_restrictions=?,
               membership_restrictions=?, link_scope=?, recheck_on=?, evidence_reference=?, evidence_scope=?, last_seen_at=?,
               status=?, reviewed_at=?, review_note=?, published_at=?, affiliate_claimed=0
               WHERE id=?""",
            (candidate["summary"], candidate["source_url"], candidate["checked_on"], candidate["promotion_type"],
             candidate["promotion_terms"], candidate["expires_on"], candidate["location_restrictions"],
             candidate["membership_restrictions"], candidate["link_scope"], candidate["recheck_on"], candidate["evidence_reference"], candidate["evidence_scope"], now,
             next_status, reviewed_at, review_note, published_at, existing["id"]),
        )
        return existing["id"], False
    cursor = connection.execute(
        """INSERT INTO retailer_deal_candidates
           (source_key, merchant, title, summary, source_url, retailer_url, checked_on,
            promotion_type, promotion_terms, expires_on, recheck_on, evidence_reference, evidence_scope, location_restrictions,
            membership_restrictions, link_scope, status, dedupe_key, created_at,
            last_seen_at, affiliate_claimed)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?, ?, ?, 0)""",
        (candidate["source_key"], candidate["merchant"], candidate["title"], candidate["summary"],
        candidate["source_url"], candidate["retailer_url"], candidate["checked_on"], candidate["promotion_type"],
        candidate["promotion_terms"], candidate["expires_on"], candidate["recheck_on"], candidate["evidence_reference"],
        candidate["evidence_scope"], candidate["location_restrictions"], candidate["membership_restrictions"], candidate["link_scope"], dedupe_key, now, now),
    )
    return cursor.lastrowid, True


def expire_candidates(connection, today=None):
    today = today or date.today().isoformat()
    cursor = connection.execute(
        "UPDATE retailer_deal_candidates SET status='expired', published_at=NULL WHERE status IN ('candidate','approved','published') AND expires_on IS NOT NULL AND expires_on < ?",
        (today,),
    )
    # A required recheck is a review reset, even when an old expiration date
    # is also overdue. Include the expired result so it remains visible to
    # editors as a fresh candidate instead of staying silently expired.
    connection.execute(
        """UPDATE retailer_deal_candidates
           SET status='candidate', reviewed_at=NULL, published_at=NULL,
               review_note='Mandatory recheck date passed; requires fresh review.'
           WHERE status IN ('approved','published','expired')
             AND recheck_on IS NOT NULL AND recheck_on < ?""",
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


def _source_check_state(status):
    if status is None:
        return "unreachable"
    if 200 <= status < 400:
        return "reachable"
    if status in {401, 403, 405, 408, 429}:
        return "inconclusive"
    return "unreachable"


def discover_retailer_deals(connection, check_urls=True, now=None):
    """Run the safe daily pass; only permitted JSON feeds create candidates."""
    ensure_retailer_deal_schema(connection)
    started = now or utc_now()
    expired_count = expire_candidates(connection)
    candidate_count = 0
    errors = []
    source_check_failure_count = 0
    feed_error_count = 0
    held_count = 0
    for source in RETAILER_SOURCE_DEFINITIONS:
        if source_is_held(connection, source["key"]):
            held_count += 1
            connection.execute(
                """UPDATE retailer_sources SET last_checked_at=?, status='held', hold_reason=?,
                   source_check_state='not_checked', feed_state='held', last_error=?, feed_last_error=NULL,
                   last_candidate_count=0 WHERE source_key=?""",
                (started, source["hold_reason"], source["hold_reason"], source["key"]),
            )
            continue
        status, error = (None, None)
        source_state = "not_checked"
        if check_urls:
            status, error = _check_official_source(source["official_source_url"])
            source_state = _source_check_state(status)
        if source_state == "unreachable":
            source_check_failure_count += 1
        feed_url = _configured_feed_url(source["key"])
        source_count = 0
        feed_state = "unconfigured"
        feed_error = None
        feed_attempt_at = utc_now() if feed_url else None
        if feed_url:
            feed_state = "configured"
            connection.execute("SAVEPOINT retailer_feed")
            try:
                for payload in _fetch_json_candidates(feed_url):
                    payload = dict(payload)
                    payload["source_key"] = source["key"]
                    _, created = upsert_candidate(connection, payload, checked_on=date.today().isoformat())
                    source_count += int(created)
                connection.execute("RELEASE SAVEPOINT retailer_feed")
                feed_state = "success"
            except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
                connection.execute("ROLLBACK TO SAVEPOINT retailer_feed")
                connection.execute("RELEASE SAVEPOINT retailer_feed")
                errors.append(f"{source['merchant']}: permitted feed error: {exc}")
                feed_error_count += 1
                feed_error = str(exc)
                feed_state = "error"
        candidate_count += source_count
        connection.execute(
            """UPDATE retailer_sources SET last_checked_at=?, http_status=?, status=?, last_error=?, last_candidate_count=?,
               source_check_state=?, feed_state=?, feed_last_error=?, last_feed_attempt_at=?,
               last_feed_success_at=CASE WHEN ?='success' THEN ? ELSE last_feed_success_at END
               WHERE source_key=?""",
            (started, status, "error" if feed_error or source_state == "unreachable" else ("checked" if source_state in {"reachable", "inconclusive"} else ("feed-only" if feed_url else "not_checked")),
             error or feed_error, source_count, source_state, feed_state, feed_error,
             feed_attempt_at, feed_state, utc_now(), source["key"]),
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
           (started_at, completed_at, candidate_count, approved_count, rejected_count, expired_count, error_count,
            source_check_failure_count, feed_error_count, held_count, message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (started, completed, candidate_count, status_counts.get("approved", 0), status_counts.get("rejected", 0), expired_count,
         source_check_failure_count + feed_error_count, source_check_failure_count, feed_error_count, held_count, message),
    )
    connection.commit()
    return {
        "started_at": started,
        "completed_at": completed,
        "candidate_count": candidate_count,
        "approved_count": status_counts.get("approved", 0),
        "rejected_count": status_counts.get("rejected", 0),
        "expired_count": expired_count,
        "error_count": source_check_failure_count + feed_error_count,
        "source_check_failure_count": source_check_failure_count,
        "feed_error_count": feed_error_count,
        "held_count": held_count,
        "message": message,
    }


def published_picks(connection, limit=None):
    query = """SELECT c.* FROM retailer_deal_candidates c
               JOIN retailer_sources s ON s.source_key=c.source_key AND s.enabled=1
               WHERE c.status='published' AND (c.expires_on IS NULL OR c.expires_on >= ?)
                 AND (c.recheck_on IS NULL OR c.recheck_on >= ?)
               ORDER BY c.expires_on IS NULL, c.expires_on ASC, c.published_at DESC, c.id DESC"""
    values = [date.today().isoformat(), date.today().isoformat()]
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
