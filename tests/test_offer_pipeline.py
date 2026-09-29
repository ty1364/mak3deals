import os
import sqlite3
import unittest
from unittest.mock import patch

import offer_pipeline


SCHEMA = """
CREATE TABLE deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT, store TEXT, title TEXT, description TEXT,
    city TEXT, category TEXT, link TEXT, expires_on TEXT, verified INTEGER DEFAULT 0,
    created_at TEXT, deal_kind TEXT, sale_price TEXT, regular_price TEXT,
    coupon_code TEXT, offer_terms TEXT, checked_on TEXT, affiliate_url TEXT,
    product_key TEXT, image_url TEXT, image_source TEXT
)
"""

FEED = b"""id,title,description,price,rrp_price,merchant_deep_link,merchant_image_url,brand,gtin,in_stock
sku-1,Blue kettle,Steel kettle,19.99,39.99,https://shop.example/kettle,https://img.example/kettle.jpg,Example,0001,1
sku-2,Red toaster,Two slice toaster,24.99,49.99,https://shop.example/toaster,https://img.example/toaster.jpg,Example,0002,1
"""

FEED_WITH_ONE_ROW = b"""id,title,description,price,rrp_price,merchant_deep_link,merchant_image_url,brand,gtin,in_stock
sku-1,Blue kettle,Steel kettle,17.99,39.99,https://shop.example/kettle,https://img.example/kettle.jpg,Example,0001,1
"""


class ProductFeedTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(SCHEMA)
        self.old_config = os.environ.get("MAK3DEALS_FEED_CONFIG")
        os.environ["MAK3DEALS_FEED_CONFIG"] = '{"walmart":{"store":"Walmart","provider":"test","format":"csv","url":"https://feed.example/walmart.csv"}}'

    def tearDown(self):
        if self.old_config is None:
            os.environ.pop("MAK3DEALS_FEED_CONFIG", None)
        else:
            os.environ["MAK3DEALS_FEED_CONFIG"] = self.old_config
        self.connection.close()

    def test_normalize_requires_real_discount_and_direct_assets(self):
        product, reason = offer_pipeline.normalize_product(
            {"id": "1", "title": "Kettle", "price": "20", "rrp_price": "40",
             "merchant_deep_link": "https://shop.example/kettle", "merchant_image_url": "https://img.example/kettle.jpg", "in_stock": "1"},
            {"source_key": "walmart", "store": "Walmart", "provider": "test"},
            "2026-09-29T00:00:00Z",
        )
        self.assertIsNone(reason)
        self.assertEqual(product["discount_percent"], 50.0)
        self.assertEqual(product["link"], "https://shop.example/kettle")

        regular, reason = offer_pipeline.normalize_product(
            {"id": "2", "title": "Not a sale", "price": "20", "rrp_price": "20",
             "merchant_deep_link": "https://shop.example/item", "merchant_image_url": "https://img.example/item.jpg", "in_stock": "1"},
            {"source_key": "walmart", "store": "Walmart"},
        )
        self.assertIsNone(reason)
        self.assertIsNone(regular["regular_price"])
        self.assertIsNone(regular["discount_percent"])

    def test_awin_column_mapping(self):
        product, reason = offer_pipeline.normalize_awin_product(
            {"aw_product_id": "aw-1", "merchant_product_id": "merchant-1", "product_name": "Awin kettle",
             "search_price": "15.00", "rrp_price": "30.00", "merchant_deep_link": "https://shop.example/kettle",
             "merchant_image_url": "https://img.example/kettle.jpg", "aw_deep_link": "https://track.example/kettle",
             "in_stock": "1", "merchant_name": "Walmart"},
            {"source_key": "walmart", "store": "Walmart", "provider": "awin"},
            "2026-09-29T00:00:00Z",
        )
        self.assertIsNone(reason)
        self.assertEqual(product["sale_price"], "$15.00")
        self.assertEqual(product["regular_price"], "$30.00")
        self.assertEqual(product["affiliate_url"], "https://track.example/kettle")

    def test_awin_google_retail_sale_price_mapping(self):
        product, reason = offer_pipeline.normalize_awin_product(
            {"id": "google-1", "title": "UPPER sale bag", "price": "100.00 USD",
             "sale_price": "75.00 USD", "link": "https://shop.example/bag",
             "image_link": "https://img.example/bag.jpg", "availability": "in_stock"},
            {"source_key": "upper", "store": "UPPER Brand"},
            "2026-09-29T00:00:00Z",
        )
        self.assertIsNone(reason)
        self.assertEqual(product["sale_price"], "$75.00")
        self.assertEqual(product["regular_price"], "$100.00")
        self.assertEqual(product["discount_percent"], 25.0)

    def test_awin_catalog_without_sale_price_is_shop_product(self):
        product, reason = offer_pipeline.normalize_awin_product(
            {"id": "catalog-1", "title": "UPPER catalog bag", "price": "100.00 USD",
             "link": "https://shop.example/bag", "image_link": "https://img.example/bag.jpg",
             "availability": "in_stock"},
            {"source_key": "upper", "store": "UPPER Brand"},
            "2026-09-29T00:00:00Z",
        )
        self.assertIsNone(reason)
        self.assertEqual(product["sale_price"], "$100.00")
        self.assertIsNone(product["regular_price"])
        self.assertIsNone(product["discount_percent"])

    def test_awin_catalog_never_fabricates_reference_price(self):
        product, reason = offer_pipeline.normalize_awin_product(
            {"id": "catalog-2", "title": "UPPER regular bag", "price": "100.00 USD",
             "rrp_price": "100.00 USD", "link": "https://shop.example/bag-2",
             "image_link": "https://img.example/bag-2.jpg", "availability": "in_stock"},
            {"source_key": "upper", "store": "UPPER Brand"},
            "2026-09-29T00:00:00Z",
        )
        self.assertIsNone(reason)
        self.assertIsNone(product["regular_price"])
        self.assertIsNone(product["discount_percent"])

    @patch("offer_pipeline._fetch_feed", return_value=(FEED, "text/csv", 200))
    def test_refresh_upserts_and_retires_missing_products(self, _fetch):
        first = offer_pipeline.refresh_sources(self.connection)
        self.assertEqual(first["published_count"], 2)
        active = self.connection.execute("SELECT COUNT(*) FROM deals WHERE verified=1 AND status='active'").fetchone()[0]
        self.assertEqual(active, 2)

        _fetch.return_value = (FEED_WITH_ONE_ROW, "text/csv", 200)
        second = offer_pipeline.refresh_sources(self.connection)
        self.assertEqual(second["published_count"], 1)
        retired = self.connection.execute("SELECT status FROM deals WHERE merchant_product_id='sku-2'").fetchone()[0]
        self.assertEqual(retired, "retired")
        updated_price = self.connection.execute("SELECT sale_price FROM deals WHERE merchant_product_id='sku-1'").fetchone()[0]
        self.assertEqual(updated_price, "$17.99")

    @patch("offer_pipeline._fetch_feed", return_value=(FEED, "text/csv", 200))
    def test_failed_refresh_preserves_existing_products(self, _fetch):
        first = offer_pipeline.refresh_sources(self.connection)
        self.assertEqual(first["published_count"], 2)

        _fetch.side_effect = RuntimeError("temporary upstream outage")
        failed = offer_pipeline.refresh_sources(self.connection)

        self.assertEqual(failed["error_count"], 1)
        active = self.connection.execute(
            "SELECT COUNT(*) FROM deals WHERE verified=1 AND status='active'"
        ).fetchone()[0]
        self.assertEqual(active, 2)
        status = self.connection.execute(
            "SELECT status FROM deals WHERE merchant_product_id='sku-1'"
        ).fetchone()[0]
        self.assertEqual(status, "active")


if __name__ == "__main__":
    unittest.main()
