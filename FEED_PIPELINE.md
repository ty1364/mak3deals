# Mak3Deals offer pipeline

The generator is intentionally conservative. It checks official retailer pages,
records source health, and retires expired verified listings. It does not scrape
or guess a price, coupon code, image, or commission relationship.

The live app exposes:

- `/api/feed-status` for a safe health summary
- `/feed-status` for the human-readable dashboard
- `POST /internal/refresh-offers` for a trusted scheduler

The internal endpoint requires the `MAK3DEALS_REFRESH_TOKEN` environment
variable and the matching `X-Mak3Deals-Refresh-Token` header. Keep that token
private.

## Why the scheduler is not in the first deploy

Render cron jobs run as a separate service and cannot share this app's SQLite
file. The scheduler must therefore call the protected web hook, or we must
migrate the app to a shared database such as Render Postgres first. Render also
charges a minimum of $1/month per cron job, even though the task may only run
for a few seconds.

The repository includes a GitHub Actions schedule at `.github/workflows/refresh-offers.yml`.
After `MAK3DEALS_REFRESH_TOKEN` is added as a repository Actions secret, it
checks the site every 30 minutes and can also be started manually from the
Actions tab. This avoids paying for a separate Render Cron Job while the
project is small.

If we later choose Render Cron instead, its command can call:

```text
curl -fsS -X POST https://mak3deals.com/internal/refresh-offers -H "X-Mak3Deals-Refresh-Token: $MAK3DEALS_REFRESH_TOKEN"
```

## Real affiliate ingestion

Walmart and Best Buy are currently source-health checked and the page only
publishes the verified rows already in the catalog. Amazon, Target, and Home
Depot are listed as pending until their affiliate approvals or authorized feeds
are connected. A connector may publish a new offer only when it receives an
official/authorized feed row with a source URL, observed price, image source,
terms, and expiry.
