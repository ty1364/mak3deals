from datetime import date, datetime, timezone
import hmac
import os
import re
import sqlite3
from flask import Flask, abort, g, jsonify, redirect, render_template, request
from daily_game import daily_session, daily_hint, evaluate_guess, puzzle_date
from guides import GUIDE_BY_SLUG, GUIDES
from offer_pipeline import ensure_feed_schema, refresh_sources
from retailer_deals import (
    ensure_retailer_deal_schema,
    discover_retailer_deals,
    expire_candidates,
    SourceHoldError,
    publication_issues,
    published_picks,
    status_snapshot,
    upsert_candidate,
)

app = Flask(__name__)
# Staging can point at an isolated SQLite file without changing production's
# default database path. Render production keeps using its configured path.
DATABASE = os.environ.get("MAK3DEALS_DATABASE", "deals.db")

SITE_AD_TV = """
<style>
.site-ad-slot{max-width:1180px;margin:0 auto;padding:24px 8% 10px}.site-ad-tv{display:flex;flex-direction:column;width:100%;min-height:150px;padding:12px;border:1px solid rgba(255,211,111,.78);border-radius:16px;background:linear-gradient(135deg,#0d1730,#102a3d 62%,#133f4b);color:#f7f7ff;box-shadow:0 14px 30px rgba(6,25,44,.18);font:800 10px/1.3 system-ui,sans-serif;letter-spacing:.12em}.site-ad-tv-top,.site-ad-tv-foot{display:flex;justify-content:space-between;color:#bde0dd}.site-ad-live{color:#ffd36f}.site-ad-tv-screen{display:flex;align-items:center;min-height:98px;margin:8px 0;padding:16px 20px;border:1px solid rgba(92,238,255,.55);border-radius:9px;background:radial-gradient(circle at 65% 45%,#1d5571,#0b1b31 70%)}.site-ad-tv-screen strong{font-size:clamp(20px,2.5vw,32px);line-height:.9;color:#fff}.site-ad-tv-screen em{color:#ffd36f;font-style:normal}.ad-player-screen{gap:16px}.ad-player-copy{display:grid;gap:7px;min-width:0;letter-spacing:.02em}.ad-player-copy strong{font-size:clamp(18px,2.4vw,30px);line-height:1.02;letter-spacing:-.04em}.ad-player-copy.pink strong{color:#ffd36f}.ad-player-copy.blue strong{color:#8cecff}.ad-player-copy.gold strong{color:#ffd36f}.ad-player-copy.cyan strong{color:#a7f7ff}.ad-player-provider,.ad-player-detail{font-size:10px;line-height:1.35;letter-spacing:.04em;color:#bdefff}.ad-player-provider{color:#ffd36f;text-transform:uppercase}.ad-player-detail{color:#e1e6ff}.ad-player-image{width:82px;height:82px;flex:0 0 82px;object-fit:contain;border-radius:10px;border:1px solid rgba(115,244,255,.5);background:#fff}.ad-player-cta,.ad-player-disclosure{color:#8cecff;text-decoration:none;letter-spacing:.04em}.ad-player-cta{justify-self:start;padding:7px 10px;border:1px solid rgba(115,244,255,.55);border-radius:999px;font-size:10px}.ad-player-cta:hover,.ad-player-disclosure:hover{color:#fff;background:rgba(115,244,255,.12)}.ad-player-disclosure{font-size:9px}@media(max-width:700px){.site-ad-slot{padding:18px 6% 4px}.site-ad-tv-screen{min-height:112px;padding:14px}.ad-player-image{width:62px;height:62px;flex-basis:62px}}
</style>
<div class="site-ad-slot"><aside class="site-ad-tv" data-ad-player data-ad-channel="01" aria-label="Mak3Deals advertising channel 01"><div class="site-ad-tv-top"><span>AD CHANNEL 01</span><span class="site-ad-live">● PLACEMENT</span></div><div class="site-ad-tv-screen ad-player-screen"><div class="ad-player-copy"><strong>MAK3<br><em>DEALS</em></strong><span class="ad-player-detail">Loading verified placements…</span></div></div><div class="site-ad-tv-foot"><span class="ad-player-provider">Mak3Deals</span><a class="ad-player-disclosure" href="/affiliate-disclosure">Disclosure</a></div></aside></div>
<script src="/static/ad-player.js?v=b0283b4" defer></script>
"""

# The homepage uses the same player inside the hero's dedicated right column.
# Keeping the player markup shared prevents the desktop and in-flow placements
# from drifting apart as inventory changes.
SITE_AD_HERO = SITE_AD_TV.replace('<div class="site-ad-slot">', '<div class="site-ad-slot hero-ad-slot">', 1)

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def price_number(value):
    """Return a sortable price for display-only comparison groups."""
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d{1,2})?", value.replace(",", ""))
    return float(match.group()) if match else None

@app.teardown_appcontext
def close_db(error):
    connection = g.pop("db", None)
    if connection: connection.close()

@app.after_request
def add_site_ad_tv(response):
    # Submit is a utility form and should stay distraction-free. Game routes
    # have their own dedicated placements. Normal savings pages get one
    # clearly labeled channel, and the homepage puts it in the hero column.
    excluded_paths = {"/submit", "/daily", "/games", "/game", "/game/deal-dash", "/game/tile-shift", "/game/bubble-crush", "/game/cart-quest", "/game/vault-runner", "/game/dealway-drift", "/game/deal-dash-royale", "/game/deal-siege", "/about", "/privacy", "/terms", "/affiliate-disclosure", "/contact", "/sources", "/feed-status", "/retailer-deal-admin"}
    if request.path not in excluded_paths and response.content_type.startswith("text/html"):
        html = response.get_data(as_text=True)
        if "class=\"site-ad-tv\"" not in html:
            hero_match = re.search(r'<section class="hero(?:\s[^\"]*)?">', html)
            if request.path == "/" and hero_match:
                hero_start = hero_match.start()
                hero_end = html.find("</section>", hero_start)
                note = re.search(r'<div class="hero-note">.*?</div>', html[hero_start:hero_end], flags=re.S)
                if note:
                    note_start = hero_start + note.start()
                    note_end = hero_start + note.end()
                    hero_right = f'<div class="hero-right">{SITE_AD_HERO}{html[note_start:note_end]}</div>'
                    html = html[:note_start] + hero_right + html[note_end:]
                else:
                    html = html[:hero_end + len("</section>")] + SITE_AD_TV + html[hero_end + len("</section>"):]
            elif hero_match:
                hero_start = hero_match.start()
                hero_end = html.find("</section>", hero_start)
                html = html[:hero_end + len("</section>")] + SITE_AD_TV + html[hero_end + len("</section>"):]
            elif re.search(r'<section class="simple-hero[^\"]*">', html):
                hero_match = re.search(r'<section class="simple-hero[^\"]*">', html)
                hero_end = html.find("</section>", hero_match.end())
                hero_content = html[hero_match.end():hero_end]
                replacement = f'{html[hero_match.start():hero_match.end()]}<div class="simple-hero-copy">{hero_content}</div><div class="simple-hero-right">{SITE_AD_HERO}</div></section>'
                html = html[:hero_match.start()] + replacement + html[hero_end + len("</section>"):]
            else:
                main_match = re.search(r'<main[^>]*>', html)
                if main_match:
                    html = html[:main_match.end()] + SITE_AD_TV + html[main_match.end():]
                else:
                    html = html.replace("</body>", SITE_AD_TV + "</body>")
            response.set_data(html)
    return response

def _admin_request_allowed():
    """Allow feed diagnostics only to local operators or a server-side token."""
    configured = os.environ.get("MAK3DEALS_ADMIN_TOKEN", "").strip()
    supplied = request.headers.get("X-Mak3Deals-Admin", "").strip()
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if configured:
        return bool(supplied) and hmac.compare_digest(configured, supplied)
    host = (request.host or "").split(":", 1)[0].lower()
    return request.remote_addr in {"127.0.0.1", "::1"} and host in {"127.0.0.1", "localhost"}

@app.before_request
def protect_feed_diagnostics():
    admin_paths = {"/feed-status", "/sources", "/api/feed-status", "/retailer-deal-admin", "/api/retailer-deal-status", "/api/retailer-deals/candidates"}
    if (request.path in admin_paths or request.path.startswith("/api/retailer-deals/")) and not _admin_request_allowed():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return "Not found", 404

@app.before_request
def setup():
    database = db()
    database.executescript("""CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, store TEXT, title TEXT,
        description TEXT, city TEXT, category TEXT, link TEXT,
        expires_on TEXT, verified INTEGER DEFAULT 0, created_at TEXT);
        CREATE TABLE IF NOT EXISTS clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, deal_id INTEGER, clicked_at TEXT);
        CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, store TEXT, title TEXT,
        description TEXT, city TEXT, category TEXT, link TEXT, submitted_at TEXT);
        CREATE TABLE IF NOT EXISTS game_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT NOT NULL,
        month TEXT NOT NULL, player_name TEXT NOT NULL, score INTEGER NOT NULL,
        wave INTEGER NOT NULL, duration_seconds INTEGER NOT NULL,
        submitted_at TEXT NOT NULL, review_status TEXT DEFAULT 'pending');
        CREATE INDEX IF NOT EXISTS idx_game_scores_month_score
        ON game_scores (game, month, score DESC);""")
    ensure_feed_schema(database)
    ensure_retailer_deal_schema(database)
    # Feed expiry is enforced on every request even if the scheduled importer
    # has not run yet.
    database.execute(
        "UPDATE deals SET verified=0 WHERE verified=1 AND expires_on < ?",
        (date.today().isoformat(),),
    )
    database.commit()
    existing_columns = {row[1] for row in database.execute("PRAGMA table_info(deals)").fetchall()}
    for column, definition in {
        "deal_kind": "TEXT DEFAULT 'deal'", "sale_price": "TEXT", "regular_price": "TEXT",
        "coupon_code": "TEXT", "offer_terms": "TEXT", "checked_on": "TEXT", "affiliate_url": "TEXT",
        "product_key": "TEXT", "image_url": "TEXT", "image_source": "TEXT",
        "merchant_product_id": "TEXT", "currency": "TEXT DEFAULT 'USD'",
        "discount_percent": "REAL", "availability_status": "TEXT", "last_checked_at": "TEXT",
        "source_key": "TEXT", "source_provider": "TEXT", "feed_updated_at": "TEXT",
        "status": "TEXT DEFAULT 'active'", "raw_payload_hash": "TEXT"
    }.items():
        if column not in existing_columns:
            database.execute(f"ALTER TABLE deals ADD COLUMN {column} {definition}")
    submission_columns = {row[1] for row in database.execute("PRAGMA table_info(submissions)").fetchall()}
    for column, definition in {
        "coupon_code": "TEXT", "offer_terms": "TEXT", "expires_on": "TEXT",
        "source_type": "TEXT DEFAULT 'user-submitted'"
    }.items():
        if column not in submission_columns:
            database.execute(f"ALTER TABLE submissions ADD COLUMN {column} {definition}")
    # Product cards are populated only by the authorized feed importer. Remove
    # legacy source-hub and hand-seeded rows so a retailer landing page cannot
    # masquerade as an individual deal.
    database.execute("DELETE FROM deals WHERE COALESCE(deal_kind, 'deal') IN ('deal', 'source-hub', 'price-check', 'submission')")
    database.commit()

SORT_OPTIONS = [("featured", "Featured"), ("price_asc", "Cheapest first"), ("price_desc", "Most expensive first"), ("name_asc", "A–Z"), ("name_desc", "Z–A"), ("newest", "Newest first"), ("oldest", "Oldest first")]
SORT_ORDER = {
    "featured": "verified DESC, expires_on ASC, id DESC",
    "price_asc": "CASE WHEN sale_price IS NULL OR sale_price = '' THEN 1 ELSE 0 END, CAST(REPLACE(REPLACE(sale_price, '$', ''), ',', '') AS REAL) ASC, verified DESC",
    "price_desc": "CASE WHEN sale_price IS NULL OR sale_price = '' THEN 1 ELSE 0 END, CAST(REPLACE(REPLACE(sale_price, '$', ''), ',', '') AS REAL) DESC, verified DESC",
    "name_asc": "LOWER(title) ASC, verified DESC",
    "name_desc": "LOWER(title) DESC, verified DESC",
    "newest": "created_at DESC, verified DESC",
    "oldest": "created_at ASC, verified DESC",
}

def _product_listing_filters():
    city = request.args.get("city", "All")
    category = request.args.get("category", "All")
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "featured")
    if sort not in SORT_ORDER:
        sort = "featured"
    query, values = "SELECT * FROM deals WHERE verified=1 AND deal_kind='product' AND status='active' AND (expires_on IS NULL OR expires_on >= ?)", [date.today().isoformat()]
    if city != "All": query += " AND city = ?"; values.append(city)
    if category != "All": query += " AND category = ?"; values.append(category)
    if search:
        query += " AND (store LIKE ? OR title LIKE ? OR description LIKE ? OR city LIKE ?)"
        values.extend([f"%{search}%"] * 4)
    raw_products = db().execute(query + " ORDER BY " + SORT_ORDER[sort], values).fetchall()
    cities = [r[0] for r in db().execute("SELECT DISTINCT city FROM deals WHERE deal_kind='product' ORDER BY city") if r[0] not in {"All", "Online"}]
    categories = [r[0] for r in db().execute("SELECT DISTINCT category FROM deals WHERE deal_kind='product' ORDER BY category")]
    return raw_products, cities, categories, city, category, search, sort

@app.route("/")
def home():
    raw_products, cities, categories, city, category, search, sort = _product_listing_filters()
    discounted_products = [row for row in raw_products if (row["discount_percent"] or 0) > 0]
    regular_products = [row for row in raw_products if (row["discount_percent"] or 0) <= 0][:8]
    comparison_counts = {}
    for deal in raw_products:
        if deal["product_key"]:
            comparison_counts[deal["product_key"]] = comparison_counts.get(deal["product_key"], 0) + 1
    # Matched retailer listings are one shopping opportunity, not duplicate cards.
    deals, shown_product_keys = [], set()
    for deal in discounted_products:
        product_key = deal["product_key"]
        if product_key and comparison_counts.get(product_key, 0) > 1:
            if product_key in shown_product_keys:
                continue
            shown_product_keys.add(product_key)
        deals.append(deal)
    homepage_coupons = db().execute(
        "SELECT * FROM deals WHERE verified=1 AND deal_kind='coupon' AND status='active' "
        "AND (expires_on IS NULL OR expires_on >= ?) ORDER BY expires_on ASC LIMIT 4",
        (date.today().isoformat(),),
    ).fetchall()
    return render_template("index.html", deals=deals, regular_products=regular_products, homepage_coupons=homepage_coupons, retailer_picks=published_picks(db(), limit=4), cities=cities, categories=categories, selected_city=city, selected_category=category, selected_sort=sort, sort_options=SORT_OPTIONS, search=search, comparison_counts=comparison_counts)

@app.route("/products")
def products():
    raw_products, cities, categories, city, category, search, sort = _product_listing_filters()
    per_page = 24
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    total_count = len(raw_products)
    page_count = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, page_count)
    start = (page - 1) * per_page
    return render_template(
        "products.html", products=raw_products[start:start + per_page], total_count=total_count,
        page=page, page_count=page_count, cities=cities, categories=categories,
        selected_city=city, selected_category=category, selected_sort=sort,
        sort_options=SORT_OPTIONS, search=search,
    )

@app.route("/guides")
def guides():
    return render_template("guides.html", guides=GUIDES)

@app.route("/guides/<slug>")
def guide_detail(slug):
    guide = GUIDE_BY_SLUG.get(slug)
    if not guide:
        abort(404)
    return render_template("guide.html", guide=guide)

@app.route("/daily")
def daily_game():
    return render_template("daily.html", puzzle_date=puzzle_date(), daily_session=daily_session(), practice=request.args.get("practice") == "1")

@app.route("/api/daily/guess", methods=["POST"])
def daily_guess():
    payload = request.get_json(silent=True) or {}
    return jsonify(evaluate_guess(
        payload.get("guess", ""),
        payload.get("attempts", 0),
        payload.get("puzzle_index", 0),
        payload.get("hints_used", 0),
    ))


@app.route("/api/daily/hint", methods=["POST"])
def daily_hint_api():
    payload = request.get_json(silent=True) or {}
    try:
        hint_index = int(payload.get("hint_index", 0))
    except (TypeError, ValueError):
        hint_index = 0
    return jsonify(daily_hint(hint_index, payload.get("puzzle_index", 0)))

@app.route("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\nSitemap: https://mak3deals.com/sitemap.xml\n", 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/sitemap.xml")
def sitemap():
    urls = ["https://mak3deals.com/", "https://mak3deals.com/coupons", "https://mak3deals.com/retailer-picks"]
    urls.extend(f"https://mak3deals.com/guides/{guide['slug']}" for guide in GUIDES)
    body = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>', 200, {"Content-Type": "application/xml; charset=utf-8"}

@app.route("/compare/<product_key>")
def compare_product(product_key):
    offers = db().execute(
        "SELECT * FROM deals WHERE product_key=? AND deal_kind='product' AND verified=1 AND status='active' AND (expires_on IS NULL OR expires_on >= ?) ORDER BY sale_price ASC, checked_on DESC",
        (product_key, date.today().isoformat()),
    ).fetchall()
    if not offers:
        abort(404)
    priced = [(price_number(offer["sale_price"]), offer) for offer in offers]
    known_prices = [item for item in priced if item[0] is not None]
    lowest_price = min((item[0] for item in known_prices), default=None)
    best_ids = {offer["id"] for price, offer in known_prices if price == lowest_price}
    return render_template("compare.html", product=offers[0], offers=offers, best_ids=best_ids)

@app.route("/coupons")
def coupons():
    deals = db().execute("SELECT * FROM deals WHERE verified=1 AND deal_kind='coupon' AND status='active' AND (expires_on IS NULL OR expires_on >= ?) ORDER BY expires_on ASC", (date.today().isoformat(),)).fetchall()
    return render_template("coupons.html", deals=deals)

@app.route("/retailer-picks")
def retailer_picks_page():
    return render_template("retailer-picks.html", picks=published_picks(db()))

@app.route("/api/coupons")
def coupon_api():
    """Return only current, verified coupon codes for the browser extension."""
    store = request.args.get("store", "").strip()
    query = ("SELECT id, store, title, coupon_code, offer_terms, expires_on, checked_on, "
             "last_checked_at, link, affiliate_url FROM deals WHERE verified=1 "
             "AND deal_kind='coupon' AND status='active' AND coupon_code IS NOT NULL "
             "AND TRIM(coupon_code) <> '' AND (expires_on IS NULL OR expires_on >= ?)")
    values = [date.today().isoformat()]
    if store:
        query += " AND lower(store)=lower(?)"
        values.append(store[:80])
    rows = db().execute(query + " ORDER BY checked_on DESC, expires_on ASC LIMIT 50", values).fetchall()
    return jsonify({"coupons": [dict(row) for row in rows]})

@app.route("/api/offers")
def offer_api():
    """Return current verified offers that match a product title or store."""
    store = request.args.get("store", "").strip()
    search = " ".join(request.args.get("q", "").lower().split())
    query = ("SELECT id, store, title, description, sale_price, regular_price, discount_percent, "
             "offer_terms, expires_on, checked_on, last_checked_at, availability_status, source_provider, "
             "link, affiliate_url, product_key, image_url, deal_kind FROM deals "
             "WHERE verified=1 AND deal_kind='product' AND status='active' AND (expires_on IS NULL OR expires_on >= ?)")
    values = [date.today().isoformat()]
    if store:
        query += " AND lower(store)=lower(?)"
        values.append(store[:80])
    if not search:
        rows = db().execute(query + " ORDER BY checked_on DESC, expires_on ASC LIMIT 10", values).fetchall()
        return jsonify({"offers": [dict(row) for row in rows]})
    rows = db().execute(query + " ORDER BY checked_on DESC, expires_on ASC LIMIT 100", values).fetchall()
    tokens = [token for token in search.split() if len(token) > 2]
    matches = []
    for row in rows:
        haystack = f"{row['title']} {row['description']}".lower()
        score = sum(token in haystack for token in tokens)
        if score and score >= max(1, len(tokens) // 2):
            item = dict(row)
            item["match_score"] = score
            matches.append(item)
    matches.sort(key=lambda item: (-item["match_score"], item["expires_on"] is None, item["expires_on"] or ""))
    return jsonify({"offers": matches[:10]})

@app.route("/api/feed-status")
def feed_status_api():
    """Public health summary; it never exposes credentials or unpublished data."""
    ensure_feed_schema(db())
    latest = db().execute(
        "SELECT started_at, completed_at, published_count, retired_count, error_count, mode, message "
        "FROM feed_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    sources = db().execute(
        "SELECT source_key, store, url, mode, enabled, http_status, status, checked_at, offer_count, "
        "imported_count, retired_count, last_imported_at, last_error, message "
        "FROM feed_sources ORDER BY store"
    ).fetchall()
    return jsonify({
        "generator": "Mak3Deals verified offer health",
        "latest_run": dict(latest) if latest else None,
        "sources": [dict(source) for source in sources],
    })

@app.route("/internal/refresh-offers", methods=["POST"])
def internal_refresh_offers():
    """Protected hook for a future Render cron job or another trusted scheduler."""
    expected = os.environ.get("MAK3DEALS_REFRESH_TOKEN", "").strip()
    provided = request.headers.get("X-Mak3Deals-Refresh-Token", "").strip()
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        return jsonify({"error": "Not authorized."}), 403
    return jsonify(refresh_sources(db()))

@app.route("/internal/discover-retailer-deals", methods=["POST"])
def internal_discover_retailer_deals():
    """Protected daily pass for official source checks and permitted feeds."""
    expected = os.environ.get("MAK3DEALS_REFRESH_TOKEN", "").strip()
    provided = request.headers.get("X-Mak3Deals-Refresh-Token", "").strip()
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        return jsonify({"error": "Not authorized."}), 403
    return jsonify(discover_retailer_deals(db(), check_urls=True))

@app.route("/api/retailer-deal-status")
def retailer_deal_status_api():
    return jsonify(status_snapshot(db()))

@app.route("/api/retailer-deals/candidates", methods=["POST"])
def retailer_deal_candidate_api():
    payload = request.get_json(silent=True) or {}
    try:
        candidate_id, created = upsert_candidate(db(), payload)
        db().commit()
    except SourceHoldError as exc:
        return jsonify({"error": str(exc)}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": candidate_id, "created": created, "status": "candidate", "affiliate_claimed": False}), 201 if created else 200

@app.route("/api/retailer-deals/<int:candidate_id>/review", methods=["POST"])
def retailer_deal_review_api(candidate_id):
    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"approve", "reject", "publish"}:
        return jsonify({"error": "action must be approve, reject, or publish"}), 400
    candidate = db().execute("SELECT * FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    source_row = db().execute("SELECT enabled FROM retailer_sources WHERE source_key=?", (candidate["source_key"],)).fetchone()
    if action in {"approve", "publish"} and (not source_row or not source_row["enabled"]):
        return jsonify({"error": "This merchant source is currently on hold."}), 409
    if action == "approve":
        issues = publication_issues(candidate)
        if issues:
            return jsonify({"error": "Candidate is not ready for approval.", "issues": issues}), 409
        status = "approved"
    elif action == "publish":
        if candidate["status"] != "approved":
            return jsonify({"error": "Only an approved candidate can be explicitly published."}), 409
        issues = publication_issues(candidate)
        if issues:
            return jsonify({"error": "Candidate is not ready for publication.", "issues": issues}), 409
        status = "published"
    else:
        status = "rejected"
    reviewed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    db().execute(
        "UPDATE retailer_deal_candidates SET status=?, reviewed_at=?, review_note=?, published_at=?, affiliate_claimed=0 WHERE id=?",
        (status, reviewed_at, str(payload.get("note") or "").strip()[:500] or None, reviewed_at if status == "published" else None, candidate_id),
    )
    db().commit()
    return jsonify({"id": candidate_id, "status": status, "affiliate_claimed": False})


@app.route("/api/retailer-deals/export")
def retailer_deal_export_api():
    """Read-only sanitized operator export; never includes credentials or feed URLs."""
    rows = db().execute(
        """SELECT c.id, c.merchant, c.title, c.summary, c.source_url, c.retailer_url,
                  c.checked_on, c.expires_on, c.recheck_on, c.evidence_reference,
                  c.evidence_scope, c.promotion_type,
                  c.promotion_terms, c.location_restrictions, c.membership_restrictions,
                  c.link_scope, c.status, c.affiliate_claimed,
                  s.status AS source_status, s.http_status AS source_http_status,
                  s.source_check_state, s.feed_state, s.last_error AS source_error,
                  s.feed_last_error, s.last_checked_at AS source_checked_at
           FROM retailer_deal_candidates c
           LEFT JOIN retailer_sources s ON s.source_key=c.source_key
           ORDER BY c.id"""
    ).fetchall()
    def safe_error_category(value):
        if not value:
            return None
        text = str(value).lower()
        if "hold" in text:
            return "source_held"
        if "http error" in text or "status" in text:
            return "http_error"
        if "timeout" in text or "urlopen" in text or "network" in text:
            return "network_error"
        if "json" in text or "payload" in text:
            return "feed_payload_error"
        return "source_or_feed_error"

    candidates = []
    for row in rows:
        item = dict(row)
        item["source_error"] = safe_error_category(item["source_error"])
        item["feed_last_error"] = safe_error_category(item["feed_last_error"])
        candidates.append(item)
    return jsonify({"candidates": candidates})

@app.route("/feed-status")
@app.route("/sources")
def feed_status_page():
    ensure_feed_schema(db())
    latest = db().execute(
        "SELECT started_at, completed_at, published_count, retired_count, error_count, mode, message "
        "FROM feed_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    sources = db().execute("SELECT * FROM feed_sources ORDER BY store").fetchall()
    return render_template("feed-status.html", latest=latest, sources=sources)

@app.route("/retailer-deal-admin")
def retailer_deal_admin_page():
    snapshot = status_snapshot(db())
    candidates = db().execute(
        "SELECT * FROM retailer_deal_candidates ORDER BY CASE status WHEN 'candidate' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END, expires_on IS NULL, expires_on ASC, id DESC"
    ).fetchall()
    return render_template("retailer-deal-admin.html", snapshot=snapshot, candidates=candidates)

@app.route("/watchlist")
def watchlist():
    return render_template("watchlist.html")

@app.route("/game")
def game():
    return render_template("game.html")

@app.route("/games")
def games():
    return render_template("games.html")

@app.route("/game/deal-dash")
@app.route("/game/tile-shift")
@app.route("/game/bubble-crush")
def deal_dash():
    return render_template("tile-shift.html")

@app.route("/game/cart-quest")
def cart_quest():
    return render_template("cart-quest.html")

@app.route("/game/vault-runner")
def vault_runner():
    return render_template("vault-runner.html")

@app.route("/game/dealway-drift")
def dealway_drift():
    return render_template("dealway-drift.html")

@app.route("/game/deal-dash-royale")
def deal_dash_royale():
    return render_template("deal-dash-royale.html")

@app.route("/game/deal-siege")
def deal_siege():
    return render_template("deal-siege.html")

@app.route("/api/leaderboard")
def leaderboard():
    month = date.today().strftime("%Y-%m")
    game_name = request.args.get("game", "void-strike").strip().lower()
    if game_name not in {"void-strike", "deal-dash", "bubble-crush", "cart-quest", "vault-runner", "dealway-drift", "deal-dash-royale", "deal-siege"}:
        game_name = "void-strike"
    rows = db().execute(
        "SELECT player_name, score, wave, submitted_at FROM game_scores "
        "WHERE game=? AND month=? ORDER BY score DESC, wave DESC, id ASC LIMIT 25",
        (game_name, month),
    ).fetchall()
    return jsonify({"game": game_name, "month": month, "scores": [dict(row) for row in rows]})

@app.route("/api/score", methods=["POST"])
def submit_score():
    payload = request.get_json(silent=True) or {}
    game_name = str(payload.get("game", "void-strike")).strip().lower()
    if game_name not in {"void-strike", "deal-dash", "bubble-crush", "cart-quest", "vault-runner", "dealway-drift", "deal-dash-royale", "deal-siege"}:
        return jsonify({"error": "That game is not available."}), 400
    name = " ".join(str(payload.get("name", "")).split())[:20]
    try:
        score = int(payload.get("score", 0))
        wave = int(payload.get("wave", 1))
        duration = int(payload.get("duration", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Score data is invalid."}), 400
    if not 2 <= len(name) <= 20 or not 0 < score <= 10_000_000:
        return jsonify({"error": "Enter a name and a valid score."}), 400
    if not 1 <= wave <= 100 or not 10 <= duration <= 7200:
        return jsonify({"error": "That run could not be verified."}), 400
    month = date.today().strftime("%Y-%m")
    db().execute(
        "INSERT INTO game_scores "
        "(game, month, player_name, score, wave, duration_seconds, submitted_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (game_name, month, name, score, wave, duration, datetime.now().isoformat()),
    )
    db().commit()
    return jsonify({"ok": True, "message": "Score submitted for review."})

@app.route("/ads.txt")
def ads_txt():
    return "google.com, pub-3943554631291586, DIRECT, f08c47fec0942fa0\n", 200, {"Content-Type": "text/plain"}

@app.route("/about")
def about():
    return render_template("legal.html", title="About Mak3Deals", heading="Save more with Mak3Deals", body=["Mak3Deals is a nationwide savings guide for online retailers and local businesses. We organize useful offers in one place so shoppers can compare opportunities and keep more money in their pockets.", "We publish curated deal links and clearly identify sponsored or affiliate relationships. Offers, prices, availability, and expiration dates can change, so confirm details with the retailer before buying."])

@app.route("/privacy")
def privacy():
    return render_template("legal.html", title="Privacy Policy", heading="Privacy Policy", body=["Mak3Deals collects only information needed to operate this site, respond to deal submissions, and understand general site usage. We do not sell personal information.", "Our advertising and analytics partners, including Google AdSense, may use cookies or similar technologies to serve and measure ads. You can manage cookie and personalized-ad settings through your browser and Google account settings.", "If you submit a deal, we receive the information you choose to send. Contact us if you want a submission removed or have a privacy question."])

@app.route("/terms")
def terms():
    return render_template("legal.html", title="Terms of Use", heading="Terms of Use", body=["Mak3Deals is provided for general informational purposes. We do not guarantee that a deal, price, product, service, or retailer offer will remain available or accurate.", "Review the retailer's terms, shipping information, return policy, and final price before buying. Mak3Deals is not a party to transactions with retailers.", "By using the site, you agree not to misuse the site, submit unlawful content, or interfere with its operation."])

@app.route("/affiliate-disclosure")
def affiliate_disclosure():
    return render_template("legal.html", title="Affiliate Disclosure", heading="Affiliate Disclosure", body=["Some links on Mak3Deals may be affiliate links. If you click a link and make a qualifying purchase, we may receive a commission at no additional cost to you.", "Our goal is to highlight useful savings, not change the price you pay. Retailers control their own prices, inventory, shipping, and policies."])

@app.route("/contact")
def contact():
    return render_template("legal.html", title="Contact Mak3Deals", heading="Contact Mak3Deals", body=["For corrections, deal updates, privacy questions, or partnership inquiries, please use the Submit a Deal page and include enough detail for us to identify the listing.", "We review submissions before publishing them, but cannot guarantee publication or a specific response time."])

@app.route("/click/<int:deal_id>")
def click(deal_id):
    deal = db().execute("SELECT link, affiliate_url FROM deals WHERE id=?", (deal_id,)).fetchone()
    if not deal: abort(404)
    db().execute("INSERT INTO clicks (deal_id,clicked_at) VALUES (?,?)", (deal_id, datetime.now().isoformat()))
    db().commit()
    return redirect(deal["affiliate_url"] or deal["link"])

@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        fields = ["store", "title", "description", "city", "category"]
        values = [request.form.get(field, "").strip() for field in fields]
        if not all(values): return render_template("submit.html", error="Please complete all required fields."), 400
        link = request.form.get("link", "").strip()
        coupon_code = request.form.get("coupon_code", "").strip().upper()[:80]
        offer_terms = request.form.get("offer_terms", "").strip()[:500]
        expires_on = request.form.get("expires_on", "").strip()
        source_type = request.form.get("source_type", "user-submitted").strip()[:40]
        if coupon_code and not link:
            return render_template("submit.html", error="A coupon code must include the official source link where it can be confirmed."), 400
        db().execute("INSERT INTO submissions (store,title,description,city,category,link,submitted_at,coupon_code,offer_terms,expires_on,source_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (*values, link, datetime.now().isoformat(), coupon_code, offer_terms, expires_on, source_type))
        db().commit()
        return render_template("submit.html", success="Thanks! We will review your deal before publishing it.")
    return render_template("submit.html")

if __name__ == "__main__":
    app.run(debug=True)
