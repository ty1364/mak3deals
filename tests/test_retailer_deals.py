import os
import sqlite3
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from retailer_deals import (
    discover_retailer_deals,
    ensure_retailer_deal_schema,
    publication_issues,
    published_picks,
    SourceHoldError,
    status_snapshot,
    upsert_candidate,
)


def candidate_payload(**overrides):
    payload = {
        "source_key": "fred-meyer",
        "title": "Fred Meyer weekly savings preview",
        "summary": "A concise editorial preview of current weekly savings and digital promotions.",
        "source_url": "https://www.fredmeyer.com/savingsoverview/weekly-ad-info",
        "retailer_url": "https://www.fredmeyer.com/",
        "checked_on": date.today().isoformat(),
        "promotion_type": "weekly ad",
        "promotion_terms": "Clip digital coupons where required.",
        "expires_on": (date.today() + timedelta(days=7)).isoformat(),
        "location_restrictions": "Select stores; choose a preferred store.",
        "membership_restrictions": "A free Fred Meyer account may be required for digital coupons.",
        "link_scope": "weekly-ad",
    }
    payload.update(overrides)
    payload.setdefault("evidence_reference", payload["source_url"])
    payload.setdefault("evidence_scope", payload["link_scope"] if payload["link_scope"] in {"weekly-ad", "digital-promotion"} else "landing-page")
    return payload


class RetailerDealWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        ensure_retailer_deal_schema(self.connection)
        self.feed_env = "MAK3DEALS_RETAILER_FEED_WALMART"
        self.old_feed = os.environ.pop(self.feed_env, None)

    def tearDown(self):
        if self.old_feed is not None:
            os.environ[self.feed_env] = self.old_feed
        self.connection.close()

    def test_sources_are_registered_and_daily_pass_is_non_destructive(self):
        sources = self.connection.execute("SELECT source_key FROM retailer_sources ORDER BY source_key").fetchall()
        self.assertEqual([row[0] for row in sources], ["fred-meyer", "target", "walmart"])
        target = self.connection.execute("SELECT enabled, status FROM retailer_sources WHERE source_key='target'").fetchone()
        self.assertEqual((target[0], target[1]), (0, "registered"))

        result = discover_retailer_deals(self.connection, check_urls=False)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["held_count"], 1)
        self.assertEqual(published_picks(self.connection), [])
        self.assertEqual(result["approved_count"], 0)

    def test_candidate_dedupes_requires_publication_and_expires(self):
        candidate_id, created = upsert_candidate(self.connection, candidate_payload())
        self.assertTrue(created)
        duplicate_id, duplicate_created = upsert_candidate(
            self.connection, candidate_payload(expires_on=(date.today() + timedelta(days=8)).isoformat())
        )
        self.assertEqual(duplicate_id, candidate_id)
        self.assertFalse(duplicate_created)

        self.connection.execute(
            "UPDATE retailer_deal_candidates SET status='approved', reviewed_at=? WHERE id=?",
            ("2026-09-28T00:00:00Z", candidate_id),
        )
        self.connection.commit()
        self.assertEqual(published_picks(self.connection), [])
        self.connection.execute(
            "UPDATE retailer_deal_candidates SET status='published', published_at=? WHERE id=?",
            ("2026-09-28T00:00:00Z", candidate_id),
        )
        self.connection.commit()
        self.assertEqual(len(published_picks(self.connection)), 1)

        updated_id, updated = upsert_candidate(
            self.connection, candidate_payload(summary="Changed evidence requires another review")
        )
        self.assertEqual(updated_id, candidate_id)
        self.assertFalse(updated)
        changed = self.connection.execute("SELECT status, published_at FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
        self.assertEqual(changed["status"], "candidate")
        self.assertIsNone(changed["published_at"])
        self.assertEqual(published_picks(self.connection), [])

        self.connection.execute(
            "UPDATE retailer_deal_candidates SET expires_on=? WHERE id=?",
            ("2020-01-01", candidate_id),
        )
        self.connection.commit()
        snapshot = status_snapshot(self.connection)
        self.assertEqual(snapshot["counts"].get("expired"), 1)
        self.assertEqual(published_picks(self.connection), [])

    @patch("retailer_deals._fetch_json_candidates")
    def test_feed_refresh_updates_existing_and_failure_preserves_it(self, fetch):
        candidate_id, _ = upsert_candidate(self.connection, candidate_payload(
            source_key="walmart",
            title="Walmart editor-approved item",
            summary="Original Walmart summary before the refresh.",
            source_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
            retailer_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
            link_scope="editorial",
        ))
        self.connection.execute("UPDATE retailer_deal_candidates SET status='approved' WHERE id=?", (candidate_id,))
        self.connection.commit()
        os.environ[self.feed_env] = "https://feeds.example/walmart.json"
        fetch.return_value = [candidate_payload(
            source_key="walmart",
            title="Walmart editor-approved item",
            summary="Updated summary from the permitted feed.",
            source_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
            retailer_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
            link_scope="editorial",
        )]
        result = discover_retailer_deals(self.connection, check_urls=False)
        self.assertEqual(result["error_count"], 0)
        summary = self.connection.execute("SELECT summary, status FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
        self.assertEqual(summary["summary"], "Updated summary from the permitted feed.")
        self.assertEqual(summary["status"], "candidate")

        fetch.side_effect = RuntimeError("temporary permitted-feed outage")
        failed = discover_retailer_deals(self.connection, check_urls=False)
        self.assertEqual(failed["error_count"], 1)
        preserved = self.connection.execute("SELECT summary, status FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
        self.assertEqual(preserved["summary"], "Updated summary from the permitted feed.")
        self.assertEqual(preserved["status"], "candidate")

    def test_domain_validation_and_target_hold(self):
        with self.assertRaises(ValueError):
            upsert_candidate(self.connection, candidate_payload(
                source_key="walmart",
                source_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
                retailer_url="https://not-walmart.example/deal",
            ))
        with self.assertRaises(SourceHoldError):
            upsert_candidate(self.connection, candidate_payload(
                source_key="target",
                source_url="https://www.target.com/c/top-deals/-/N-4xw74",
                retailer_url="https://www.target.com/c/top-deals/-/N-4xw74",
            ))

    def test_landing_page_evidence_cannot_substantiate_item_level_numeric_claim(self):
        candidate = candidate_payload(
            title="Walmart monitor $179, was $249",
            summary="Observed at $179 compared with $249 on the Walmart Rollbacks page.",
            source_key="walmart",
            source_url="https://www.walmart.com/shop/deals/announce",
            retailer_url="https://www.walmart.com/shop/deals/announce",
            evidence_reference="https://www.walmart.com/shop/deals/announce",
            evidence_scope="landing-page",
        )
        candidate_id, _ = upsert_candidate(self.connection, candidate)
        row = self.connection.execute("SELECT * FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
        issues = publication_issues(row)
        self.assertTrue(any("landing-page evidence" in issue for issue in issues))

    def test_recheck_resets_even_when_expiration_is_also_overdue(self):
        candidate_id, _ = upsert_candidate(self.connection, candidate_payload(
            expires_on="2020-01-01",
            recheck_on="2020-01-01",
        ))
        self.connection.execute(
            "UPDATE retailer_deal_candidates SET status='published', published_at=? WHERE id=?",
            ("2026-09-28T00:00:00Z", candidate_id),
        )
        self.connection.commit()
        from retailer_deals import expire_candidates
        expire_candidates(self.connection, today="2026-09-29")
        row = self.connection.execute("SELECT status, review_note FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
        self.assertEqual(row["status"], "candidate")
        self.assertIn("Mandatory recheck", row["review_note"])

    def test_stable_dedupe_migration_is_one_time(self):
        candidate_id, _ = upsert_candidate(self.connection, candidate_payload())
        self.connection.execute("UPDATE retailer_deal_candidates SET dedupe_key='manual-review-key' WHERE id=?", (candidate_id,))
        self.connection.commit()
        ensure_retailer_deal_schema(self.connection)
        row = self.connection.execute("SELECT dedupe_key FROM retailer_deal_candidates WHERE id=?", (candidate_id,)).fetchone()
        marker = self.connection.execute("SELECT value FROM retailer_schema_meta WHERE key='stable_dedupe_v1'").fetchone()
        self.assertEqual(row["dedupe_key"], "manual-review-key")
        self.assertEqual(marker["value"], "complete")

    def test_published_picks_hide_rows_when_source_is_disabled(self):
        candidate_id, _ = upsert_candidate(self.connection, candidate_payload())
        self.connection.execute(
            "UPDATE retailer_deal_candidates SET status='published', published_at=? WHERE id=?",
            ("2026-09-29T00:00:00Z", candidate_id),
        )
        self.connection.commit()
        self.assertEqual(len(published_picks(self.connection)), 1)
        self.connection.execute("UPDATE retailer_sources SET enabled=0 WHERE source_key='fred-meyer'")
        self.connection.commit()
        self.assertEqual(published_picks(self.connection), [])

    @patch("retailer_deals._fetch_json_candidates")
    @patch("retailer_deals._check_official_source", return_value=(405, "method not allowed"))
    def test_source_health_is_distinguished_and_feed_is_atomic(self, check, fetch):
        os.environ[self.feed_env] = "https://feeds.example/walmart.json"
        fetch.side_effect = lambda url: [candidate_payload(
            source_key="walmart",
            title="Atomic feed candidate",
            source_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
            retailer_url="https://www.walmart.com/shop/deals/shop-advertised-deals",
            link_scope="editorial",
        ), {}]
        result = discover_retailer_deals(self.connection, check_urls=True)
        self.assertEqual(result["source_check_failure_count"], 0)
        self.assertEqual(result["feed_error_count"], 1)
        walmart = self.connection.execute("SELECT source_check_state, feed_state FROM retailer_sources WHERE source_key='walmart'").fetchone()
        self.assertEqual((walmart[0], walmart[1]), ("inconclusive", "error"))
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM retailer_deal_candidates WHERE title='Atomic feed candidate'").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
