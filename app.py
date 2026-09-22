from datetime import date, datetime, timedelta
import sqlite3
from flask import Flask, abort, g, redirect, render_template, request

app = Flask(__name__)
DATABASE = "deals.db"

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    connection = g.pop("db", None)
    if connection: connection.close()

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
        description TEXT, city TEXT, category TEXT, link TEXT, submitted_at TEXT);""")
    if database.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 0:
        today = date.today()
        rows = [
            ("Costco", "Western Washington member savings", "Check this week's rotating warehouse offers and instant savings.", "Tacoma", "Groceries", "https://www.costco.com", 7, 1),
            ("Target", "Weekly household essentials deals", "Browse current household, kitchen, and personal-care offers.", "Seattle", "Household", "https://www.target.com/c/weekly-ad/-/N-4xw74", 6, 1),
            ("Best Buy", "Local electronics deals", "See current offers with pickup options at nearby stores.", "Bellevue", "Electronics", "https://www.bestbuy.com/site/top-deals", 5, 1),
            ("Walmart", "Current Rollbacks and online savings", "Find current Walmart Rollbacks across groceries, household, electronics, and more.", "Online", "Household", "https://www.walmart.com/shop/deals", 30, 1),
            ("Home Depot", "Special Buy savings", "See current savings on tools, appliances, outdoor, and home-improvement supplies.", "Online", "Home", "https://www.homedepot.com/SpecialBuy", 30, 1),
            ("Amazon", "Today's Deals", "Browse limited-time offers across everyday essentials, electronics, and more.", "Online", "All", "https://www.amazon.com/gp/goldbox", 30, 1),
            ("Costco", "Member warehouse savings", "Explore current Costco warehouse savings and seasonal member offers.", "Online", "Groceries", "https://www.costco.com/warehouse-savings.html", 30, 1),
            ("Local businesses", "Get your deal in front of shoppers", "Submit an offer from your business and reach shoppers looking for savings.", "All", "Local", "/submit", 45, 0)]
        database.executemany("INSERT INTO deals (store,title,description,city,category,link,expires_on,verified,created_at) VALUES (?,?,?,?,?,?,?,?,?)", [(a,b,c,d,e,f,(today+timedelta(days=g)).isoformat(),h,datetime.now().isoformat()) for a,b,c,d,e,f,g,h in rows])
        database.commit()

@app.route("/")
def home():
    city = request.args.get("city", "All")
    category = request.args.get("category", "All")
    search = request.args.get("q", "").strip()
    query, values = "SELECT * FROM deals WHERE expires_on >= ?", [date.today().isoformat()]
    if city != "All": query += " AND city = ?"; values.append(city)
    if category != "All": query += " AND category = ?"; values.append(category)
    if search:
        query += " AND (store LIKE ? OR title LIKE ? OR description LIKE ? OR city LIKE ?)"
        values.extend([f"%{search}%"] * 4)
    deals = db().execute(query + " ORDER BY verified DESC, expires_on ASC", values).fetchall()
    cities = [r[0] for r in db().execute("SELECT DISTINCT city FROM deals ORDER BY city")]
    categories = [r[0] for r in db().execute("SELECT DISTINCT category FROM deals ORDER BY category")]
    return render_template("index.html", deals=deals, cities=cities, categories=categories, selected_city=city, selected_category=category, search=search)

@app.route("/ads.txt")
def ads_txt():
    return "google.com, pub-3943554631291586, DIRECT, f08c47fec0942fa0\\n", 200, {"Content-Type": "text/plain"}

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
    deal = db().execute("SELECT link FROM deals WHERE id=?", (deal_id,)).fetchone()
    if not deal: abort(404)
    db().execute("INSERT INTO clicks (deal_id,clicked_at) VALUES (?,?)", (deal_id, datetime.now().isoformat()))
    db().commit()
    return redirect(deal["link"])

@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        fields = ["store", "title", "description", "city", "category"]
        values = [request.form.get(field, "").strip() for field in fields]
        if not all(values): return render_template("submit.html", error="Please complete all required fields."), 400
        db().execute("INSERT INTO submissions (store,title,description,city,category,link,submitted_at) VALUES (?,?,?,?,?,?,?)", (*values, request.form.get("link", "").strip(), datetime.now().isoformat()))
        db().commit()
        return render_template("submit.html", success="Thanks! We will review your deal before publishing it.")
    return render_template("submit.html")

if __name__ == "__main__":
    app.run(debug=True)
