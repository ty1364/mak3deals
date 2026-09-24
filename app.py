from datetime import date, datetime, timedelta
import re
import sqlite3
from flask import Flask, abort, g, jsonify, redirect, render_template, request

app = Flask(__name__)
DATABASE = "deals.db"

SITE_AD_TV = """
<style>
.hero,.simple-hero{position:relative}
.site-ad-tv{position:absolute;top:24px;right:8%;z-index:4;width:min(42%,500px);min-height:238px;padding:14px;border:2px solid rgba(255,82,211,.75);border-radius:12px;background:#08091a;color:#f7f7ff;box-shadow:0 0 24px rgba(255,55,207,.3),inset 0 0 30px rgba(38,111,190,.16);font:800 10px/1.3 system-ui,sans-serif;letter-spacing:.12em}
.site-ad-tv-top,.site-ad-tv-foot{display:flex;justify-content:space-between;color:#aeb8e4}.site-ad-live{color:#ff5dbe}.site-ad-tv-screen{display:flex;align-items:center;justify-content:space-between;min-height:72px;margin:6px 0;padding:10px;border:1px solid rgba(92,238,255,.55);background:radial-gradient(circle at 50% 40%,#233a86,#0b102c 70%)}.site-ad-tv-screen strong{font-size:16px;line-height:.8;color:#fff;text-shadow:0 0 10px #50eaff}.site-ad-tv-screen em{color:#ff5bd7;font-style:normal}.site-ad-tv-screen small{color:#bdefff;font-size:8px;line-height:1.4;text-align:right;letter-spacing:.06em}@media(max-width:700px){.site-ad-tv{right:8px;bottom:8px;transform:scale(.8);transform-origin:bottom right}}
.site-ad-tv-screen{flex:1;min-height:180px;margin:10px 0;padding:22px;border-color:rgba(92,238,255,.7);background:radial-gradient(circle at 50% 40%,#233a86,#0b102c 70%)}.site-ad-tv-screen strong{font-size:clamp(22px,3vw,38px)}.site-ad-tv-screen small{font-size:11px}
@media(max-width:700px){.site-ad-tv{position:relative;top:auto;right:auto;width:100%;min-height:150px;margin:28px 0 0;transform:none}.site-ad-tv-screen{min-height:100px}.site-ad-tv-screen strong{font-size:24px}}
.ad-player-screen{gap:16px}.ad-player-copy{display:grid;gap:7px;min-width:0;letter-spacing:.02em}.ad-player-copy strong{font-size:clamp(18px,2.4vw,30px);line-height:1.02;letter-spacing:-.04em}.ad-player-copy.pink strong{color:#ff9ee8}.ad-player-copy.blue strong{color:#8cecff}.ad-player-copy.gold strong{color:#ffd36f}.ad-player-copy.cyan strong{color:#a7f7ff}.ad-player-provider,.ad-player-detail{font-size:10px;line-height:1.35;letter-spacing:.04em;color:#bdefff}.ad-player-provider{color:#ff7bdd;text-transform:uppercase}.ad-player-detail{color:#e1e6ff}.ad-player-image{width:88px;height:88px;flex:0 0 88px;object-fit:cover;border-radius:10px;border:1px solid rgba(115,244,255,.5);background:#fff}.ad-player-cta,.ad-player-disclosure{color:#8cecff;text-decoration:none;letter-spacing:.04em}.ad-player-cta{justify-self:start;padding:7px 10px;border:1px solid rgba(115,244,255,.55);border-radius:999px;font-size:10px}.ad-player-cta:hover,.ad-player-disclosure:hover{color:#fff;background:rgba(115,244,255,.12)}.ad-player-disclosure{font-size:9px}
</style>
<aside class="site-ad-tv" data-ad-player aria-label="Mak3Deals advertising channel"><div class="site-ad-tv-top"><span>AD CHANNEL</span><span class="site-ad-live">● LIVE</span></div><div class="site-ad-tv-screen ad-player-screen"><div class="ad-player-copy"><strong>MAK3<br><em>DEALS</em></strong><span class="ad-player-detail">Loading verified placements…</span></div></div><div class="site-ad-tv-foot"><span class="ad-player-provider">Mak3Deals</span><a class="ad-player-disclosure" href="/affiliate-disclosure">Disclosure</a></div></aside>
<script src="/static/ad-player.js?v=4925c9f" defer></script>
"""

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
    # Keep the sponsored panel on every normal HTML page, but avoid duplicating
    # the custom arcade TV already rendered by /game and never touch API data.
    if request.path != "/game" and response.content_type.startswith("text/html"):
        html = response.get_data(as_text=True)
        if "class=\"site-ad-tv\"" not in html:
            if '<section class="hero">' in html:
                html = html.replace('<section class="hero">', '<section class="hero">' + SITE_AD_TV, 1)
            elif '<section class="simple-hero">' in html:
                html = html.replace('<section class="simple-hero">', '<section class="simple-hero">' + SITE_AD_TV, 1)
            else:
                html = html.replace("</body>", SITE_AD_TV + "</body>")
            response.set_data(html)
    return response

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
    existing_columns = {row[1] for row in database.execute("PRAGMA table_info(deals)").fetchall()}
    for column, definition in {
        "deal_kind": "TEXT DEFAULT 'deal'", "sale_price": "TEXT", "regular_price": "TEXT",
        "coupon_code": "TEXT", "offer_terms": "TEXT", "checked_on": "TEXT", "affiliate_url": "TEXT",
        "product_key": "TEXT", "image_url": "TEXT", "image_source": "TEXT"
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
    # Never leave an old verified placeholder visible after the catalog schema upgrade.
    database.execute("DELETE FROM deals WHERE verified=1 AND COALESCE(deal_kind, 'deal')='deal'")
    # Mak3Deals does not promote Target; remove any legacy Target rows from older local catalogs.
    database.execute("DELETE FROM deals WHERE lower(store)=lower('Target')")
    if database.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 0:
        today = date.today()
        rows = [
            ("Costco", "Western Washington member savings", "Check this week's rotating warehouse offers and instant savings.", "Tacoma", "Groceries", "https://www.costco.com", 7, 1),
            ("Best Buy", "Local electronics deals", "See current offers with pickup options at nearby stores.", "Bellevue", "Electronics", "https://www.bestbuy.com/site/top-deals", 5, 1),
            ("Walmart", "Current Rollbacks and online savings", "Find current Walmart Rollbacks across groceries, household, electronics, and more.", "Online", "Household", "https://www.walmart.com/shop/deals", 30, 1),
            ("Home Depot", "Special Buy savings", "See current savings on tools, appliances, outdoor, and home-improvement supplies.", "Online", "Home", "https://www.homedepot.com/SpecialBuy", 30, 1),
            ("Amazon", "Today's Deals", "Browse limited-time offers across everyday essentials, electronics, and more.", "Online", "All", "https://www.amazon.com/gp/goldbox", 30, 1),
            ("Costco", "Member warehouse savings", "Explore current Costco warehouse savings and seasonal member offers.", "Online", "Groceries", "https://www.costco.com/warehouse-savings.html", 30, 1),
            ("Local businesses", "Get your deal in front of shoppers", "Submit an offer from your business and reach shoppers looking for savings.", "All", "Local", "/submit", 45, 0)]
        database.executemany("INSERT INTO deals (store,title,description,city,category,link,expires_on,verified,created_at) VALUES (?,?,?,?,?,?,?,?,?)", [(a,b,c,d,e,f,(today+timedelta(days=g)).isoformat(),h,datetime.now().isoformat()) for a,b,c,d,e,f,g,h in rows])
        database.commit()
    # Remove earlier placeholder claims before adding only sourced offers.
    retired_titles = [
        "Western Washington member savings", "Weekly household essentials deals", "Local electronics deals",
        "Current Rollbacks and online savings", "Special Buy savings", "Today's Deals", "Member warehouse savings",
        "Target Circle member savings", "Weekly savings on home projects", "Pet essentials and autoship savings",
        "Sale shoes and apparel", "Hotel and travel deals", "Seasonal savings and coupons", "Department store sale hub",
        "Get your deal in front of shoppers",
        "Get your offer featured", "Blackstone 28-in griddle rollback — $197", "Starbucks Fall coffee pods — $16",
        "DEWALT drill kit — $199"]
    database.executemany("DELETE FROM deals WHERE title=?", [(title,) for title in retired_titles])

    # These entries come from official retailer pages and include the terms/date shown there.
    curated = [
        ("Walmart", "Lodge Chef Collection 10-in skillet — $29.90", "Live price check for the pre-seasoned Lodge Chef Collection 10-inch cast-iron skillet. This is a retailer price match, not an invented coupon.", "Online", "Kitchen", "https://www.walmart.com/ip/Lodge-Cast-Iron-Inoxidable-10-Inch/204048002?classType=REGULAR", "2026-09-24", "price-check", "$29.90", "", "", "Observed online Sep 23; product price, seller, stock, and shipping can change.", "2026-09-23", "lodge-chef-collection-10-skillet", "https://i5.walmartimages.com/seo/Lodge-Cast-Iron-Inoxidable-10-Inch_50d4e335-fdac-4c9a-82f8-dc5ca0031494.e737235b951799bcbbf771c805e0d677.jpeg?odnBg=FFFFFF&odnHeight=576&odnWidth=576", "Walmart product listing"),
        ("Best Buy", "Lodge Chef Collection 10-in skillet — $29.90", "Live price check for the Lodge Chef Collection 10-inch pre-seasoned cast-iron skillet, model LC10SK. This is a retailer price match, not an invented coupon.", "Online", "Kitchen", "https://www.bestbuy.com/product/lodge-chef-collection-10-pre-seasoned-cast-iron-skillet-kitchen-essential-for-frying-searing-black/J79YYFX38C", "2026-09-24", "price-check", "$29.90", "", "", "Observed online Sep 23; product price, seller, stock, and shipping can change.", "2026-09-23", "lodge-chef-collection-10-skillet", "https://i5.walmartimages.com/seo/Lodge-Cast-Iron-Inoxidable-10-Inch_50d4e335-fdac-4c9a-82f8-dc5ca0031494.e737235b951799bcbbf771c805e0d677.jpeg?odnBg=FFFFFF&odnHeight=576&odnWidth=576", "Walmart product listing"),
        ("Local business", "Submit a verified local offer", "Business owners can submit a real offer for review. We publish it only after checking the details and source link.", "All", "Local", "/submit", "2026-11-01", "submission", "", "", "", "Requires review before publication.", "2026-09-22", "", "", "")]
    for store, title, description, city, category, link, expires_on, deal_kind, sale_price, regular_price, coupon_code, offer_terms, checked_on, product_key, image_url, image_source in curated:
        exists = database.execute("SELECT 1 FROM deals WHERE store=? AND title=?", (store, title)).fetchone()
        if not exists:
            database.execute("INSERT INTO deals (store,title,description,city,category,link,expires_on,verified,created_at,deal_kind,sale_price,regular_price,coupon_code,offer_terms,checked_on,product_key,image_url,image_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (store, title, description, city, category, link, expires_on, 1 if store != "Local business" else 0, datetime.now().isoformat(), deal_kind, sale_price, regular_price, coupon_code, offer_terms, checked_on, product_key, image_url, image_source))
        else:
            database.execute("UPDATE deals SET description=?, link=?, expires_on=?, deal_kind=?, sale_price=?, regular_price=?, coupon_code=?, offer_terms=?, checked_on=?, product_key=?, image_url=?, image_source=? WHERE store=? AND title=?", (description, link, expires_on, deal_kind, sale_price, regular_price, coupon_code, offer_terms, checked_on, product_key, image_url, image_source, store, title))
    database.commit()

@app.route("/")
def home():
    city = request.args.get("city", "All")
    category = request.args.get("category", "All")
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "featured")
    sort_order = {
        "featured": "verified DESC, expires_on ASC, id DESC",
        "price_asc": "CASE WHEN sale_price IS NULL OR sale_price = '' THEN 1 ELSE 0 END, CAST(REPLACE(REPLACE(sale_price, '$', ''), ',', '') AS REAL) ASC, verified DESC",
        "price_desc": "CASE WHEN sale_price IS NULL OR sale_price = '' THEN 1 ELSE 0 END, CAST(REPLACE(REPLACE(sale_price, '$', ''), ',', '') AS REAL) DESC, verified DESC",
        "name_asc": "LOWER(title) ASC, verified DESC",
        "name_desc": "LOWER(title) DESC, verified DESC",
        "newest": "created_at DESC, verified DESC",
        "oldest": "created_at ASC, verified DESC",
    }
    if sort not in sort_order:
        sort = "featured"
    query, values = "SELECT * FROM deals WHERE expires_on >= ?", [date.today().isoformat()]
    if city != "All": query += " AND city = ?"; values.append(city)
    if category != "All": query += " AND category = ?"; values.append(category)
    if search:
        query += " AND (store LIKE ? OR title LIKE ? OR description LIKE ? OR city LIKE ?)"
        values.extend([f"%{search}%"] * 4)
    raw_deals = db().execute(query + " ORDER BY " + sort_order[sort], values).fetchall()
    comparison_counts = {}
    for deal in raw_deals:
        if deal["product_key"]:
            comparison_counts[deal["product_key"]] = comparison_counts.get(deal["product_key"], 0) + 1
    # Matched retailer listings are one shopping opportunity, not duplicate cards.
    deals, shown_product_keys = [], set()
    for deal in raw_deals:
        product_key = deal["product_key"]
        if product_key and comparison_counts.get(product_key, 0) > 1:
            if product_key in shown_product_keys:
                continue
            shown_product_keys.add(product_key)
        deals.append(deal)
    cities = [r[0] for r in db().execute("SELECT DISTINCT city FROM deals ORDER BY city") if r[0] not in {"All", "Online"}]
    categories = [r[0] for r in db().execute("SELECT DISTINCT category FROM deals ORDER BY category")]
    sort_options = [("featured", "Featured"), ("price_asc", "Cheapest first"), ("price_desc", "Most expensive first"), ("name_asc", "A–Z"), ("name_desc", "Z–A"), ("newest", "Newest first"), ("oldest", "Oldest first")]
    return render_template("index.html", deals=deals, cities=cities, categories=categories, selected_city=city, selected_category=category, selected_sort=sort, sort_options=sort_options, search=search, comparison_counts=comparison_counts)

@app.route("/compare/<product_key>")
def compare_product(product_key):
    offers = db().execute(
        "SELECT * FROM deals WHERE product_key=? AND verified=1 AND expires_on >= ? ORDER BY sale_price ASC, checked_on DESC",
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
    deals = db().execute("SELECT * FROM deals WHERE verified=1 AND expires_on >= ? ORDER BY expires_on ASC", (date.today().isoformat(),)).fetchall()
    return render_template("coupons.html", deals=deals)

@app.route("/api/coupons")
def coupon_api():
    """Return only current, verified coupon codes for the browser extension."""
    store = request.args.get("store", "").strip()
    query = ("SELECT id, store, title, coupon_code, offer_terms, expires_on, checked_on, "
             "link, affiliate_url FROM deals WHERE verified=1 AND coupon_code IS NOT NULL "
             "AND TRIM(coupon_code) <> '' AND expires_on >= ?")
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
    query = ("SELECT id, store, title, description, sale_price, regular_price, offer_terms, "
             "expires_on, checked_on, link, affiliate_url, product_key, image_url FROM deals "
             "WHERE verified=1 AND expires_on >= ?")
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
    matches.sort(key=lambda item: (-item["match_score"], item["expires_on"]))
    return jsonify({"offers": matches[:10]})

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
def deal_dash():
    return render_template("deal-dash.html")

@app.route("/api/leaderboard")
def leaderboard():
    month = date.today().strftime("%Y-%m")
    game_name = request.args.get("game", "void-strike").strip().lower()
    if game_name not in {"void-strike", "deal-dash"}:
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
    if game_name not in {"void-strike", "deal-dash"}:
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
