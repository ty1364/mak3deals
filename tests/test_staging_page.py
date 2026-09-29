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
        routes = ["/", "/coupons", "/guides", "/daily", "/watchlist", "/submit", "/about", "/privacy", "/terms", "/affiliate-disclosure", "/contact", "/retailer-picks"]
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
        self.assertEqual(self.client.get("/retailer-deal-admin", environ_overrides=external).status_code, 404)
        self.assertEqual(self.client.get("/api/retailer-deal-status", environ_overrides=external).status_code, 404)
        self.assertEqual(self.client.post("/api/retailer-deals/candidates", environ_overrides=external).status_code, 404)

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

    def test_products_catalog_has_real_filterable_listing_and_two_channels(self):
        home = self.client.get("/")
        home_body = home.get_data(as_text=True)
        self.assertIn('href="/products"', home_body)
        self.assertIn('data-ad-channel="01"', home_body)
        self.assertIn('data-ad-channel-02', home_body)
        self.assertIn("ad-channel-02.js", home_body)
        self.assertNotIn("● LIVE", home_body)

        catalog = self.client.get("/products?q=UPPER&category=Luggage%20%26%20Bags&sort=name_asc")
        catalog_body = catalog.get_data(as_text=True)
        self.assertEqual(catalog.status_code, 200)
        self.assertIn("UPPER Everyday Tote", catalog_body)
        self.assertIn("Page 1 of 1", catalog_body)
        self.assertIn('id="catalog-search"', catalog_body)
        self.assertEqual(catalog_body.count("<main"), 1)
        self.assertNotIn("No discount is claimed", catalog_body)

        out_of_range = self.client.get("/products?page=99")
        self.assertEqual(out_of_range.status_code, 200)
        self.assertIn("Page 1 of 1", out_of_range.get_data(as_text=True))

    def test_homepage_preserves_filters_and_places_channel_two_after_shop_row(self):
        response = self.client.get("/?q=UPPER&category=Luggage%20%26%20Bags&sort=name_desc")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/products?city=All&amp;category=Luggage+%26+Bags&amp;sort=name_desc&amp;q=UPPER"', body)
        self.assertIn("UPPER Everyday Tote", body)
        self.assertIn('data-ad-channel-02', body)
        self.assertLess(body.index("UPPER Everyday Tote"), body.index('data-ad-channel-02'))
        self.assertNotIn("Authorized affiliate promotion", body)

    def test_retailer_candidate_requires_review_before_customer_publication(self):
        payload = {
            "source_key": "fred-meyer",
            "title": "Fred Meyer weekly savings preview",
            "summary": "A concise original preview of the current weekly ad and digital promotions.",
            "source_url": "https://www.fredmeyer.com/savingsoverview/weekly-ad-info",
            "retailer_url": "https://www.fredmeyer.com/",
            "checked_on": "2026-09-28",
            "promotion_type": "weekly ad",
            "promotion_terms": "Clip digital coupons where required.",
            "expires_on": "2026-10-05",
            "location_restrictions": "Select stores; choose a preferred store.",
            "membership_restrictions": "A free Fred Meyer account may be required for digital coupons.",
            "link_scope": "weekly-ad",
        }
        candidate = self.client.post("/api/retailer-deals/candidates", json=payload)
        self.assertEqual(candidate.status_code, 201)
        candidate_id = candidate.get_json()["id"]
        self.assertNotIn("Fred Meyer weekly savings preview", self.client.get("/retailer-picks").get_data(as_text=True))

        reviewed = self.client.post(
            f"/api/retailer-deals/{candidate_id}/review",
            json={"action": "approve", "note": "Official source checked by editor."},
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertNotIn("Fred Meyer weekly savings preview", self.client.get("/retailer-picks").get_data(as_text=True))
        published = self.client.post(
            f"/api/retailer-deals/{candidate_id}/review",
            json={"action": "publish", "note": "Explicit publication after approval."},
        )
        self.assertEqual(published.status_code, 200)
        picks = self.client.get("/retailer-picks").get_data(as_text=True)
        self.assertIn("Fred Meyer weekly savings preview", picks)
        self.assertIn("Clip digital coupons where required.", picks)
        self.assertIn("No affiliate commission claimed", picks)
        self.assertIn("Fred Meyer weekly savings preview", self.client.get("/").get_data(as_text=True))

    def test_retailer_export_is_sanitized_and_target_is_held(self):
        target_payload = {
            "source_key": "target",
            "title": "Target held candidate",
            "summary": "This should never enter the active review queue while Target is held.",
            "source_url": "https://www.target.com/c/top-deals/-/N-4xw74",
            "retailer_url": "https://www.target.com/c/top-deals/-/N-4xw74",
            "checked_on": "2026-09-29",
            "promotion_terms": "Terms pending verification.",
            "expires_on": "2026-10-05",
            "location_restrictions": "Store-specific.",
            "membership_restrictions": "Target Circle status pending.",
            "link_scope": "editorial",
        }
        held = self.client.post("/api/retailer-deals/candidates", json=target_payload)
        self.assertEqual(held.status_code, 409)

        export = self.client.get("/api/retailer-deals/export")
        self.assertEqual(export.status_code, 200)
        self.assertIn("candidates", export.get_json())
        self.assertNotIn("MAK3DEALS_RETAILER_FEED", export.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
