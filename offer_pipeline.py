"""Authorized product-feed ingestion for Mak3Deals.

This module only publishes records supplied by an authorized product feed. It
does not scrape retailer pages, infer a discount from a sale-page URL, or
invent coupon codes. Feed URLs and credentials are supplied through Render
environment variables and are never committed to the repository.
"""

from datetime import date, datetime, timezone
import csv
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SOURCE_DEFINITIONS = [
    {"key": "upper", "store": "UPPER Brand", "url": "https://upperbags.com/"},
    {"key": "yeloly", "store": "Yeloly", "url": "https://www.yeloly.com/"},
    {"key": "walmart", "store": "Walmart", "url": "https://www.walmart.com/shop/deals/shop-advertised-deals"},
    {"key": "best-buy", "store": "Best Buy", "url": "https://www.bestbuy.com/top-deals-b"},
    {"key": "amazon", "store": "Amazon", "url": "https://www.amazon.com/gp/goldbox"},
    {"key": "target", "store": "Target", "url": "https://www.target.com/c/deals/-/N-4xw74"},
    {"key": "home-depot", "store": "Home Depot", "url": "https://www.homedepot.com/daily-deals"},
]

DEAL_COLUMNS = {
    "merchant_product_id": "TEXT",
    "currency": "TEXT DEFAULT 'USD'",
    "discount_percent": "REAL",
    "availability_status": "TEXT",
    "last_checked_at": "TEXT",
    "source_key": "TEXT",
    "source_provider": "TEXT",
    "feed_updated_at": "TEXT",
    "status": "TEXT DEFAULT 'active'",
    "raw_payload_hash": "TEXT",
}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
            mode TEXT NOT NULL DEFAULT 'product-ingestion',
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
    source_columns = {row[1] for row in connection.execute("PRAGMA table_info(feed_sources)").fetchall()}
    for name, definition in {
        "last_imported_at": "TEXT",
        "last_error": "TEXT",
        "imported_count": "INTEGER NOT NULL DEFAULT 0",
        "retired_count": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        if name not in source_columns:
            connection.execute(f"ALTER TABLE feed_sources ADD COLUMN {name} {definition}")

    if connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deals'").fetchone():
        deal_columns = {row[1] for row in connection.execute("PRAGMA table_info(deals)").fetchall()}
        for name, definition in DEAL_COLUMNS.items():
            if name not in deal_columns:
                connection.execute(f"ALTER TABLE deals ADD COLUMN {name} {definition}")

    for source in SOURCE_DEFINITIONS:
        connection.execute(
            """
            INSERT INTO feed_sources (source_key, store, url, mode, enabled, message)
            VALUES (?, ?, ?, 'product-feed', 1, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                store=excluded.store, url=excluded.url, mode=excluded.mode, enabled=excluded.enabled
            """,
            (source["key"], source["store"], source["url"], "Awaiting an authorized product feed URL."),
        )


def load_feed_configs():
    """Load feed definitions from MAK3DEALS_FEED_CONFIG without exposing secrets."""
    raw = os.environ.get("MAK3DEALS_FEED_CONFIG", "").strip()
    configs = {}
    if raw:
        try:
            parsed = json.loads(raw)
            items = parsed.items() if isinstance(parsed, dict) else ((item.get("source_key"), item) for item in parsed)
            for key, item in items:
                if key and isinstance(item, dict) and item.get("url"):
                    config = dict(item)
                    config["source_key"] = key
                    configs[key] = config
        except (TypeError, ValueError):
            return {}
    for source in SOURCE_DEFINITIONS:
        env_key = "MAK3DEALS_FEED_URL_" + re.sub(r"[^A-Z0-9]", "_", source["key"].upper())
        url = os.environ.get(env_key, "").strip()
        if url and source["key"] not in configs:
            configs[source["key"]] = {"source_key": source["key"], "store": source["store"], "url": url}
    return configs


def _fetch_feed(config, timeout=90):
    request = Request(
        config["url"],
        headers={
            "User-Agent": "Mak3Deals-ProductFeed/1.0 (+https://mak3deals.com/about)",
            "Accept": "text/csv,application/json,application/gzip,*/*",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            content_encoding = response.headers.get("Content-Encoding", "")
            status = response.status
    except HTTPError as error:
        raise RuntimeError(f"feed HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise RuntimeError(f"feed request failed: {reason}") from error
    if "gzip" in content_encoding.lower() or config.get("compression") == "gzip" or config["url"].lower().endswith((".gz", ".gzip")):
        body = gzip.decompress(body)
    return body, content_type, status


def _parse_feed(body, content_type, config):
    forced = str(config.get("format", "")).lower()
    text = body.decode("utf-8-sig", errors="replace")
    if forced == "json" or (not forced and ("json" in content_type.lower() or text.lstrip().startswith(("{", "[")))):
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for key in ("products", "items", "results", "data"):
                if isinstance(parsed.get(key), list):
                    return parsed[key]
            return [parsed]
        if isinstance(parsed, list):
            return parsed
        return []
    if forced == "jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return list(csv.DictReader(io.StringIO(text)))


def _first(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return ""


def _money(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
    try:
        number = float(cleaned)
    except (TypeError, ValueError):
        return None
    return round(number, 2) if number > 0 else None


def _date_only(value):
    if not value:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", str(value))
    return match.group(1) if match else None


def _available(row):
    value = _first(row, "availability_status", "availability", "stock_status", "in_stock", "is_for_sale")
    if not value:
        return "unknown"
    normalized = value.lower()
    if normalized in {"0", "false", "no", "out of stock", "out_of_stock", "unavailable", "sold out"}:
        return "unavailable"
    if normalized in {"1", "true", "yes", "in stock", "in_stock", "available", "for sale"}:
        return "available"
    return normalized[:80]


def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:160]


def normalize_product(row, config, checked_at=None):
    if not isinstance(row, dict):
        return None, "row is not an object"
    checked_at = checked_at or utc_now()
    title = _first(row, "title", "product_name", "name")
    product_url = _first(row, "product_url", "merchant_deep_link", "direct_url", "link", "url")
    image_url = _first(row, "image_url", "image_link", "merchant_image_url", "large_image", "image", "aw_image_url")
    current = _money(_first(row, "sale_price", "current_price", "price", "search_price", "store_price"))
    reference = _money(_first(row, "reference_price", "regular_price", "compare_at", "rrp_price", "product_price_old", "original_price", "list_price"))
    if not title or not product_url or not image_url:
        return None, "missing title, direct product URL, or image URL"
    if not product_url.startswith(("https://", "http://")) or not image_url.startswith(("https://", "http://")):
        return None, "product and image URLs must be absolute HTTP(S) URLs"
    if current is None:
        return None, "missing current price"

    merchant_product_id = _first(row, "merchant_product_id", "product_id", "aw_product_id", "sku", "id", "gtin", "upc", "ean")
    gtin = _first(row, "gtin", "product_gtin", "upc", "ean", "isbn")
    brand = _first(row, "brand", "brand_name")
    product_key = f"gtin:{gtin}" if gtin else f"title:{_slug((brand + ' ' + title).strip())}"
    expires_on = _date_only(_first(row, "expires_on", "valid_to", "expiration", "expiration_date", "end_date", "sale_end"))
    if expires_on and expires_on < date.today().isoformat():
        return None, "feed row is expired"
    availability = _available(row)
    if availability == "unknown":
        return None, "missing availability status"
    if availability == "unavailable":
        return None, "feed row is unavailable"
    if reference is not None and reference < current:
        return None, "reference price is lower than current price"
    discount = round((reference - current) / reference * 100, 1) if reference and reference > current else None
    verified_reference = f"${reference:.2f}" if discount and discount > 0 else None
    affiliate_url = _first(row, "affiliate_url", "aw_deep_link", "tracking_url", "tracking_link", "basket_link")
    payload_hash = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    category = _first(row, "category", "merchant_category", "category_name", "product_type", "google_product_category") or "Other"
    if ">" in category:
        category = category.split(">", 1)[0].strip() or "Other"
    return {
        "merchant_product_id": merchant_product_id or _slug(title),
        "store": config.get("store") or config.get("merchant") or config["source_key"],
        "title": title[:240],
        "description": _first(row, "description", "product_short_description", "promotional_text")[:2000],
        "category": category[:120],
        "link": product_url[:2000],
        "affiliate_url": affiliate_url[:2000] if affiliate_url else None,
        "image_url": image_url[:2000],
        "image_source": config.get("provider", "authorized product feed"),
        "sale_price": f"${current:.2f}",
        "regular_price": verified_reference,
        "currency": _first(row, "currency") or "USD",
        "discount_percent": discount,
        "expires_on": expires_on,
        "availability_status": availability,
        "last_checked_at": checked_at,
        "checked_on": checked_at[:10],
        "feed_updated_at": _first(row, "last_updated", "updated_at", "feed_updated_at") or None,
        "product_key": product_key,
        "source_key": config["source_key"],
        "source_provider": config.get("provider", "authorized product feed"),
        "raw_payload_hash": payload_hash,
    }, None


def normalize_awin_product(row, config, checked_at=None):
    """Normalize an Awin publisher product-feed row.

    Awin's standard columns include product_name, search_price, rrp_price,
    merchant_deep_link, merchant_image_url, merchant_product_id, and
    aw_deep_link. The common normalizer maps those fields. A row with no
    sale_price is still a valid Shop Product when it has a current price,
    direct tracked link, image, and availability; it simply has no discount.
    """
    # Awin's newer Google/Retail format uses `price` as the reference price
    # and `sale_price` as the current price. The older Awin format exposes
    # `search_price` and `rrp_price`; preserve support for both.
    mapped = dict(row)
    if _first(row, "sale_price") and not _first(row, "reference_price", "regular_price", "compare_at", "rrp_price", "product_price_old", "original_price", "list_price"):
        mapped["reference_price"] = _first(row, "price")
    return normalize_product(mapped, {**config, "provider": "awin"}, checked_at)


def _upsert_product(connection, product):
    existing = connection.execute(
        "SELECT id FROM deals WHERE source_key=? AND merchant_product_id=?",
        (product["source_key"], product["merchant_product_id"]),
    ).fetchone()
    values = (
        product["store"], product["title"], product["description"], "Online", product["category"],
        product["link"], product["expires_on"], 1, product["last_checked_at"], "product",
        product["sale_price"], product["regular_price"], None, "Imported from an authorized product feed.",
        product["checked_on"], product["product_key"], product["image_url"], product["image_source"],
        product["affiliate_url"], product["merchant_product_id"], product["currency"], product["discount_percent"],
        product["availability_status"], product["last_checked_at"], product["source_key"], product["source_provider"],
        product["feed_updated_at"], "active", product["raw_payload_hash"],
    )
    columns = ("store,title,description,city,category,link,expires_on,verified,created_at,deal_kind,sale_price,"
               "regular_price,coupon_code,offer_terms,checked_on,product_key,image_url,image_source,affiliate_url,"
               "merchant_product_id,currency,discount_percent,availability_status,last_checked_at,source_key,"
               "source_provider,feed_updated_at,status,raw_payload_hash")
    if existing:
        assignments = ", ".join(f"{column}=?" for column in columns.split(","))
        connection.execute(f"UPDATE deals SET {assignments} WHERE id=?", values + (existing["id"],))
        return "updated"
    connection.execute(f"INSERT INTO deals ({columns}) VALUES ({','.join('?' for _ in values)})", values)
    return "inserted"


def _ingest_config(connection, config, dry_run=False):
    checked_at = utc_now()
    body, content_type, http_status = _fetch_feed(config)
    rows = _parse_feed(body, content_type, config)
    seen_ids = set()
    imported = 0
    skipped = 0
    reasons = {}
    for row in rows:
        normalizer = normalize_awin_product if str(config.get("provider", "")).lower() == "awin" else normalize_product
        product, reason = normalizer(row, config, checked_at)
        if not product:
            skipped += 1
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        seen_ids.add(product["merchant_product_id"])
        imported += 1
        if not dry_run:
            _upsert_product(connection, product)
    retired = 0
    if not dry_run and imported:
        placeholders = ",".join("?" for _ in seen_ids)
        retired = connection.execute(
            f"""UPDATE deals SET verified=0, status='retired', availability_status='retired'
                WHERE source_key=? AND deal_kind='product' AND verified=1
                AND merchant_product_id NOT IN ({placeholders})""",
            [config["source_key"], *seen_ids],
        ).rowcount
    return {
        "source_key": config["source_key"],
        "store": config.get("store") or config.get("merchant") or config["source_key"],
        "http_status": http_status,
        "status": "reachable" if imported else "empty",
        "imported_count": imported,
        "retired_count": retired,
        "skipped_count": skipped,
        "skip_reasons": reasons,
        "checked_at": checked_at,
    }


def refresh_sources(connection, check_urls=True, dry_run=False):
    """Run every configured authorized product feed and retire stale products."""
    ensure_feed_schema(connection)
    started_at = utc_now()
    configs = load_feed_configs()
    source_results = []
    imported_total = retired_total = errors = 0
    for source in SOURCE_DEFINITIONS:
        config = configs.get(source["key"])
        if not config:
            result = {
                "source_key": source["key"], "store": source["store"], "status": "pending",
                "http_status": None, "imported_count": 0, "retired_count": 0,
                "message": "No authorized product feed configured.",
            }
        else:
            try:
                result = _ingest_config(connection, {**config, "source_key": source["key"], "store": config.get("store", source["store"])}, dry_run)
                result["message"] = "Feed imported and active products synchronized."
                imported_total += result["imported_count"]
                retired_total += result["retired_count"]
            except Exception as error:
                errors += 1
                result = {
                    "source_key": source["key"], "store": config.get("store", source["store"]),
                    "status": "error", "http_status": None, "imported_count": 0, "retired_count": 0,
                    "message": str(error)[:240],
                }
        source_results.append(result)
        if not dry_run:
            count = connection.execute(
                "SELECT COUNT(*) FROM deals WHERE source_key=? AND deal_kind='product' AND verified=1 AND status='active'",
                (source["key"],),
            ).fetchone()[0]
            connection.execute(
                """UPDATE feed_sources SET http_status=?, status=?, checked_at=?, offer_count=?,
                   message=?, last_imported_at=?, last_error=?, imported_count=?, retired_count=?
                   WHERE source_key=?""",
                (
                    result.get("http_status"), result["status"], result.get("checked_at", started_at), count,
                    result.get("message"), result.get("checked_at") if result["status"] in {"reachable", "empty"} else None,
                    result.get("message") if result["status"] == "error" else None,
                    result.get("imported_count", 0), result.get("retired_count", 0), source["key"],
                ),
            )
    completed_at = utc_now()
    result = {
        "started_at": started_at, "completed_at": completed_at, "published_count": imported_total,
        "retired_count": retired_total, "error_count": errors, "mode": "dry-run" if dry_run else "product-ingestion",
        "configured_feed_count": len(configs), "sources": source_results,
    }
    if not dry_run:
        message = "Authorized product feeds imported." if imported_total else "No authorized product feeds are connected yet."
        connection.execute(
            """INSERT INTO feed_runs (started_at, completed_at, published_count, retired_count, error_count, mode, message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (started_at, completed_at, imported_total, retired_total, errors, "product-ingestion", message),
        )
        connection.commit()
    return result
