# Mak3Deals product-feed pipeline

Mak3Deals now publishes only individual `product` records from an authorized
merchant or affiliate-network feed. Retailer homepages, sale-page links,
hand-entered prices, and guessed coupon codes are not product records.

The importer accepts CSV, JSON, JSONL, and gzip-compressed feeds. Every
published row requires a title, image URL, direct product URL, current price,
availability, merchant product ID, and a last-checked timestamp. A row with a
verifiable reference price greater than its current price is classified as a
`Verified Deal`; a normal catalog row without a discount is classified as a
`Shop Product`. The normalizer never fabricates a reference price, crossed-out
price, sale badge, or discount percentage. It stores the source provider,
affiliate URL when supplied, feed expiry, and a payload hash. Re-imports update
by `source_key + merchant_product_id`; records missing from a successful
complete feed are retired. A failed feed never retires existing products.

## Feed configuration

Feed URLs are secrets when they contain a network download key, so configure
them only in Render environment variables. The preferred setting is one JSON
object in `MAK3DEALS_FEED_CONFIG`:

```json
{
  "upper": {"store": "UPPER Brand", "provider": "awin", "format": "csv", "compression": "gzip", "url": "https://authorized-feed.example/upper.csv.gz"},
  "walmart": {"store": "Walmart", "provider": "awin", "format": "csv", "url": "https://authorized-feed.example/walmart.csv.gz"},
  "best-buy": {"store": "Best Buy", "provider": "awin", "format": "csv", "url": "https://authorized-feed.example/best-buy.csv.gz"},
  "amazon": {"store": "Amazon", "provider": "cj", "format": "json", "url": "https://authorized-feed.example/amazon.json"},
  "target": {"store": "Target", "provider": "impact", "format": "csv", "url": "https://authorized-feed.example/target.csv"},
  "home-depot": {"store": "Home Depot", "provider": "awin", "format": "csv", "url": "https://authorized-feed.example/home-depot.csv"}
}
```

The example URLs are placeholders and must not be used as data. A merchant
counts as connected only after its real feed URL is supplied and an ingestion
run reports imported product records.

The per-source fallback names include `MAK3DEALS_FEED_URL_UPPER`,
`MAK3DEALS_FEED_URL_WALMART`,
`MAK3DEALS_FEED_URL_BEST_BUY`, `MAK3DEALS_FEED_URL_AMAZON`,
`MAK3DEALS_FEED_URL_TARGET`, and `MAK3DEALS_FEED_URL_HOME_DEPOT`.

## Scheduler and storage

## Isolated staging fixtures

The review branch includes four clearly labeled fixture products so the page
can be tested before an advertiser feed is approved. They use `example.invalid`
product links and are never real offers. Load them into a separate database:

```powershell
$env:MAK3DEALS_DATABASE = "staging-deals.db"
$env:MAK3DEALS_STAGING_ORIGIN = "http://127.0.0.1:5001"
python scripts/load_staging_fixture.py
flask --app app:app run --port 5001
```

Every fixture card is labeled `TEST FIXTURE · NOT A REAL DEAL`. Do not point
`MAK3DEALS_DATABASE` at the production file when running this loader.

`POST /internal/refresh-offers` runs the importer and requires
`MAK3DEALS_REFRESH_TOKEN`. GitHub Actions calls it every 30 minutes from
`.github/workflows/refresh-offers.yml` after that secret is configured.

The current service still uses SQLite. That is suitable for local fixture
tests, but a production milestone with automatic updates needs a shared
persistent database such as Render Postgres before the feed job is enabled in
production. Compute-plan upgrades do not make a SQLite file durable.

`migrations/001_product_pipeline.sql` is additive-only preparation for that
move. `render-postgres.example.yaml` is intentionally not referenced by the
live Render blueprint; creating the database and switching `DATABASE_URL`
requires owner approval and a backup plan first.

## Status and acceptance checks

- `/api/feed-status` exposes source status, imported/retired counts, timestamps,
  and errors without exposing feed URLs that contain credentials.
- `/feed-status` is the human-readable operations page.
- `/api/offers` and the homepage return only active individual product cards;
  the homepage keeps discounted rows in Verified Deals and non-discounted rows
  in Shop Products.
- `python scripts/refresh_offers.py --dry-run` validates configured feeds
  without writing records.
- `python scripts/check_phase1.py` exits non-zero until the live milestone is
  genuinely met; it is currently expected to fail because no feeds are
  connected.
- The first merchant acceptance test is a configured authorized feed with real
  catalog rows. The UPPER staging feed currently contains 135 rows, 107
  reported in stock, and imports 107 active Shop Products. A second run must
  update existing rows and retire a removed or unavailable row without
  fabricating discount fields.
