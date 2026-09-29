# Daily retailer deal discovery

This branch adds a separate editorial workflow for Walmart, Target, and Fred
Meyer. It is intentionally conservative: a retailer deals landing page is a
source to review, not proof that an individual product is discounted. The
workflow does not scrape retailer pages, bypass controls, copy retailer
catalogs, or claim affiliate attribution.

## Source registry

The registered official starting points are:

| Merchant | Official starting point | What it is used for |
| --- | --- | --- |
| Walmart | `https://www.walmart.com/shop/deals/shop-advertised-deals` | advertised-deal review |
| Target | `https://www.target.com/c/top-deals/-/N-4xw74` | top-deal and digital-promotion review |
| Fred Meyer | `https://www.fredmeyer.com/savingsoverview/weekly-ad-info` | weekly-ad and digital-promotion review |

The daily pass checks those URLs for reachability and records the result. It
creates a candidate only from one of these two controlled inputs:

1. An editor submits a candidate through the protected review API after
   checking the official source; or
2. The operator configures a permitted JSON feed URL server-side in
   `MAK3DEALS_RETAILER_FEED_WALMART`, `MAK3DEALS_RETAILER_FEED_TARGET`, or
   `MAK3DEALS_RETAILER_FEED_FRED_MEYER`.

Feed URLs are environment secrets. They are never written to the database or
shown in the customer-facing pages. A permitted feed must return an array (or
`{"candidates": [...]}` / `{"items": [...]}`) of objects containing a title,
original summary, HTTPS source URL, HTTPS retailer destination, and checked
date. The normalized record always has `affiliate_claimed = 0`.

## Review queue and publication

SQLite staging creates the schema automatically. PostgreSQL preparation is in
`migrations/002_retailer_editorial_deals.sql`. Candidates hold the merchant,
source URL, retailer destination, checked date, promotion type, known terms,
expiration, location restrictions, membership restrictions, dedupe key, and
review history.

The protected operator page is `/retailer-deal-admin`. It exposes the counts
and source health to an authenticated local operator or a request carrying the
configured `MAK3DEALS_ADMIN_TOKEN`. The API routes are:

- `POST /api/retailer-deals/candidates` — create or refresh a candidate.
- `POST /api/retailer-deals/<id>/review` with `{"action":"approve"}` or
  `{"action":"reject"}` — manual editorial decision.
- `GET /api/retailer-deal-status` — protected counts and source health.
- `POST /internal/discover-retailer-deals` — protected daily pass, using
  `X-Mak3Deals-Refresh-Token`.

Only approved, unexpired rows appear at `/retailer-picks` or in the homepage
Retailer Deal Picks section. Customer cards link to the retailer and carry a
clear statement that no affiliate commission is claimed for these editorial
picks. This does not make a numerical discount claim unless separate reliable
product evidence supports it.

Fred Meyer candidates must include the applicable store or region, whether a
membership or digital account is required, coupon-clipping requirements, and a
valid-through date when those restrictions apply. Missing restrictions remain
visible in the queue for the editor to resolve rather than being guessed.

## Daily execution

`.github/workflows/discover-retailer-deals.yml` runs the protected endpoint once
per day and can also be started manually. Configure the GitHub secret
`MAK3DEALS_REFRESH_TOKEN` to the same server-side `MAK3DEALS_REFRESH_TOKEN`
before enabling it. The local/staging equivalent is:

```powershell
$env:MAK3DEALS_DATABASE = "staging-deals.db"
python scripts/discover_retailer_deals.py
```

Use `--no-url-check` only for an offline staging smoke test. A failed feed
refresh records the error and leaves existing approved candidates intact.
Expired candidates are retired automatically before each status read and daily
run. Dedupe uses merchant/source, normalized title, retailer destination, and
expiration, so a repeated discovery refreshes the existing row instead of
creating another listing.
