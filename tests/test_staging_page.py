import os
import sqlite3
import tempfile
import unittest

import app as app_module
from offer_pipeline import _upsert_product, ensure_feed_schema, normalize_product


class StagingPageTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.tempdir.name, "staging.db")
        self.previous_database = app_module.DATABASE
        app_module.DATABASE = self.database_path
        self.client = app_module.app.test_client()

        # The request initializes the same schema used by the staging service.
        self.client.get("/")
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        products = [
            {
                "id": "fixture-busy-baby",
                "title": "Busy Baby Fixture",
                "description": "Staging-only baby mealtime example.",
                "price": "24.99",
                "rrp_price": "39.99",
                "merchant_deep_link": "https://example.invalid/busy-baby",
                "merchant_image_url": "https://example.invalid/busy-baby.svg",
                "brand": "Busy Baby",
                "gtin": "fixture-1001",
                "in_stock": "1",
                "category": "Baby & Family",
            },
            {
                "id": "upper-regular-1",
                "title": "UPPER Everyday Tote",
                "description": "Authorized UPPER catalog product without a claimed discount.",
                "price": "79.00",
                "merchant_deep_link": "https://example.invalid/upper-everyday-tote",
                "merchant_image_url": "https://example.invalid/upper-everyday-tote.jpg",
                "brand": "UPPER Brand",
                "gtin": "upper-regular-1",
                "in_stock": "1",
                "category": "Luggage & Bags",
            },
            {
                "id": "fixture-bully-beds",
                "title": "Bully Beds Fixture",
                "description": "Staging-only pet-care example.",
                "price": "59.99",
                "rrp_price": "89.99",
                "merchant_deep_link": "https://example.invalid/bully-beds",
                "merchant_image_url": "https://example.invalid/bully-beds.svg",
                "brand": "Bully Beds",
                "gtin": "fixture-1002",
                "in_stock": "1",
                "category": "Pet Care",
            },
        ]
        for row in products:
            product, reason = normalize_product(
                row,
                {"source_key": "staging-fixtures", "store": row["brand"], "provider": "staging-fixture"},
                "2026-09-28T00:00:00Z",
            )
            self.assertIsNone(reason)
            _upsert_product(connection, product)
        ensure_feed_schema(connection)
        connection.commit()
        connection.close()

    def tearDown(self):
        app_module.DATABASE = self.previous_database
        self.tempdir.cleanup()

    def test_search_filter_and_staging_label(self):
        response = self.client.get("/?q=fixture&category=Pet%20Care")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("TEST FIXTURE", body)
        self.assertIn("Bully Beds Fixture", body)
        self.assertNotIn("Busy Baby Fixture", body)
        self.assertIn("Verified Deals", body)
        self.assertIn("Shop Products", body)
        self.assertIn("Daily Word Challenge", body)
        self.assertIn('class="hero-right"', body)
        self.assertLess(body.index('class="hero-right"'), body.index("SHOP BY CATEGORY"))
        self.assertIn('class="site-ad-tv"', body)
        self.assertIn("PLACEMENT", body)
        self.assertNotIn("● LIVE", body)

    def test_offer_api_returns_product_details(self):
        response = self.client.get("/api/offers?store=Bully%20Beds")
        self.assertEqual(response.status_code, 200)
        offers = response.get_json()["offers"]
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["link"], "https://example.invalid/bully-beds")
        self.assertEqual(offers[0]["discount_percent"], 33.3)
        self.assertEqual(offers[0]["source_provider"], "staging-fixture")

    def test_customer_routes_share_shell_and_hide_sources(self):
        routes = ["/", "/coupons", "/guides", "/daily", "/watchlist", "/submit", "/about", "/privacy", "/terms", "/affiliate-disclosure", "/contact"]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                body = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('class="site-header"', body)
                self.assertIn('class="site-footer"', body)
                self.assertNotIn('>Sources<', body)
                self.assertEqual(body.count("<main"), 1)

    def test_feed_diagnostics_are_not_public(self):
        external = {"REMOTE_ADDR": "203.0.113.1", "HTTP_HOST": "mak3deals.com"}
        self.assertEqual(self.client.get("/api/feed-status", environ_overrides=external).status_code, 404)
        self.assertEqual(self.client.get("/feed-status", environ_overrides=external).status_code, 404)
        self.assertEqual(self.client.get("/sources", environ_overrides=external).status_code, 404)

    def test_catalog_cards_show_shopping_essentials_and_tracked_action(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("UPPER Everyday Tote", body)
        self.assertIn('aria-label="Save UPPER Everyday Tote to your watchlist"', body)
        self.assertIn('href="/click/', body)
        self.assertNotIn("No discount is claimed", body)
        self.assertNotIn("Checked 2026", body)
        self.assertNotIn(">awin<", body)
        self.assertEqual(body.count("<main"), 1)

        connection = sqlite3.connect(self.database_path)
        product_id = connection.execute(
            "SELECT id FROM deals WHERE merchant_product_id='upper-regular-1'"
        ).fetchone()[0]
        connection.close()
        tracked = self.client.get(f"/click/{product_id}", follow_redirects=False)
        self.assertEqual(tracked.status_code, 302)
        self.assertEqual(tracked.headers["Location"], "https://example.invalid/upper-everyday-tote")


if __name__ == "__main__":
    unittest.main()
