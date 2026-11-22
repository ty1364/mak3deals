from pathlib import Path
import unittest


class PositiveSavingsFixtureTests(unittest.TestCase):
    def test_fixture_is_explicitly_synthetic_and_cannot_start_a_purchase(self):
        fixture = Path(__file__).parents[1] / "extension" / "fixtures" / "positive-savings.html"
        page = fixture.read_text(encoding="utf-8")

        self.assertIn("STAGING FIXTURE · SAMPLE DATA ONLY", page)
        self.assertIn("SIMULATED WALMART PAGE · TEST STATE", page)
        self.assertIn("Synthetic item and prices", page)
        self.assertIn("Not a live Walmart offer", page)
        self.assertIn("disabled>Example deal action", page)
        self.assertNotIn("awin", page.lower())


if __name__ == "__main__":
    unittest.main()
