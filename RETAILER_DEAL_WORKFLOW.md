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

Target is intentionally held until its item-level promotion evidence can be
verified cleanly. The daily pass does not check or ingest a held source. For
the other sources, a reachability result is only a source-health signal, never
proof that an individual deal was inspected. The pass creates a candidate only
from one of these two controlled inputs:

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
expiration or mandatory recheck date, location restrictions, membership
restrictions, dedupe key, and review history. Source and retailer URLs must use
the registered merchant's official domain. Broad deals pages remain editorial
link-outs and cannot be labeled individual offers.

The protected operator page is `/retailer-deal-admin`. It exposes the counts
and source health to an authenticated local operator or a request carrying the
configured `MAK3DEALS_ADMIN_TOKEN`. The API routes are:

- `POST /api/retailer-deals/candidates` — create or refresh a candidate.
- `POST /api/retailer-deals/<id>/review` with `{"action":"approve"}` or
  `{"action":"reject"}` — manual editorial decision. Approval does not
  make a candidate public.
- The same route with `{"action":"publish"}` is the separate explicit
  publication step and only accepts an approved candidate whose terms,
  restrictions, evidence, and expiry/recheck date pass validation.
- `GET /api/retailer-deal-status` — protected counts and source health.
- `GET /api/retailer-deals/export` — protected, read-only sanitized review
  export without feed URLs or credentials.
- `POST /internal/discover-retailer-deals` — protected daily pass, using
  `X-Mak3Deals-Refresh-Token`.

Only explicitly published, unexpired rows appear at `/retailer-picks` or in the homepage
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
refresh is atomic: it records the error and leaves existing candidate or
published records intact. Expired candidates are retired automatically before
each status read and daily run; a missed mandatory recheck removes a published
row until it is reviewed again. Dedupe uses merchant/source, normalized title,
and retailer destination, so changing an expiration date refreshes the
existing row instead of creating another listing.
