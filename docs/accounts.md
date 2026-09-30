# Mak3Deals accounts

The account flow is implemented in the existing Flask application; React is not required. Shopping, the daily challenge, and the browser watchlist remain available to guests.

## Current behavior

- `/signup` creates an account with a Werkzeug password hash.
- `/login` verifies the password and creates a 30-day server-side session. The browser cookie contains only a random token; the token hash is stored in `auth_sessions`.
- `/logout` is a POST with CSRF protection.
- `/account` is the first authenticated page.
- `/verify-email/<token>` consumes a single-use, 48-hour verification token.
- Account creation is not connected to a mail sender yet. Until a transactional email provider is configured, production signups remain pending verification. No verification links are displayed in the public UI.

## Production configuration

Set these as Render environment variables; do not commit values to GitHub:

```text
MAK3DEALS_DATABASE=<Render Postgres connection string after the database is provisioned>
MAK3DEALS_SECRET_KEY=<long random secret, 32+ bytes>
MAK3DEALS_COOKIE_SECURE=1
MAK3DEALS_AUTH_REQUIRE_EMAIL_VERIFICATION=1
```

`MAK3DEALS_AUTH_AUTOCONFIRM=1` is for isolated local tests only and must not be set in production. A mail provider and server-side delivery adapter are still required before production verification emails can be sent.

The Postgres schema is prepared in `migrations/003_accounts.sql`. The current staging app continues to use the repository's SQLite-compatible path until the database adapter migration is explicitly approved.
