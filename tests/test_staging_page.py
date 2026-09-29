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

    def test_offer_api_returns_product_details(self):
        response = self.client.get("/api/offers?store=Bully%20Beds")
        self.assertEqual(response.status_code, 200)
        offers = response.get_json()["offers"]
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["link"], "https://example.invalid/bully-beds")
        self.assertEqual(offers[0]["discount_percent"], 33.3)
        self.assertEqual(offers[0]["source_provider"], "staging-fixture")


if __name__ == "__main__":
    unittest.main()
