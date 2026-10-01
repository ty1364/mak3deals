"""Database compatibility for local SQLite and Render Postgres."""

from pathlib import Path
import os
import sqlite3

try:
    import psycopg
except ImportError:  # Local SQLite development does not require psycopg.
    psycopg = None

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if psycopg is not None:
    DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)


class CompatRow(dict):
    """A row that supports both row[0] and row[\"column\"]."""

    def __init__(self, values, columns):
        self._values = tuple(values)
        super().__init__(zip(columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class CompatCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def lastrowid(self):
        return getattr(self._cursor, "lastrowid", None)

    def _row(self, value):
        if value is None:
            return None
        columns = [item.name for item in (self._cursor.description or ())]
        return CompatRow(value, columns)

    def fetchone(self):
        return self._row(self._cursor.fetchone())

    def fetchall(self):
        return [self._row(value) for value in self._cursor.fetchall()]

    def __iter__(self):
        for value in self._cursor:
            yield self._row(value)


class PostgresConnection:
    is_postgres = True

    def __init__(self, url):
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is configured but psycopg is not installed.")
        self._connection = psycopg.connect(url)

    def execute(self, sql, params=()):
        cursor = self._connection.cursor()
        cursor.execute(sql.replace("?", "%s"), tuple(params))
        return CompatCursor(cursor)

    def executemany(self, sql, params):
        cursor = self._connection.cursor()
        cursor.executemany(sql.replace("?", "%s"), params)
        return CompatCursor(cursor)

    def executescript(self, script):
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def connect_database(sqlite_path):
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith(("postgres://", "postgresql://")):
        return PostgresConnection(url)
    if os.environ.get("RENDER") == "true":
        raise RuntimeError("DATABASE_URL must be configured for a Render deployment.")
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_postgres_schema(connection):
    """Apply additive migrations and create the app-owned support tables."""
    root = Path(__file__).resolve().parent
    for migration in sorted((root / "migrations").glob("*.sql")):
        connection.executescript(migration.read_text(encoding="utf-8"))
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS clicks (
            id BIGSERIAL PRIMARY KEY, deal_id BIGINT, clicked_at TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submissions (
            id BIGSERIAL PRIMARY KEY, store TEXT, title TEXT, description TEXT,
            city TEXT, category TEXT, link TEXT, submitted_at TIMESTAMPTZ NOT NULL,
            coupon_code TEXT, offer_terms TEXT, expires_on DATE,
            source_type TEXT DEFAULT 'user-submitted'
        );
        CREATE TABLE IF NOT EXISTS game_scores (
            id BIGSERIAL PRIMARY KEY, game TEXT NOT NULL, month TEXT NOT NULL,
            player_name TEXT NOT NULL, score INTEGER NOT NULL, wave INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL, submitted_at TIMESTAMPTZ NOT NULL,
            review_status TEXT DEFAULT 'pending'
        );
        CREATE INDEX IF NOT EXISTS idx_game_scores_month_score
            ON game_scores (game, month, score DESC);
        """
    )
    connection.commit()
