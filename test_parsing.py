"""Run: python -m unittest discover tests"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_deals import matches, pick_tier, price_deal  # noqa: E402
from providers import AmazonCreators, WalmartAffiliate  # noqa: E402

CFG = json.loads((ROOT / "config" / "brands.json").read_text("utf-8"))
TIERS = CFG["tiers"]


def entry(brand):
    return next(b for b in CFG["brands"] if b["brand"] == brand)


class TestAmazon(unittest.TestCase):
    RAW = {
        "asin": "B000TEST01",
        "detailPageURL": "https://www.amazon.com/dp/B000TEST01?tag=x-20",
        "images": {"primary": {"medium": {"url": "https://m.media-amazon.com/x.jpg"}}},
        "itemInfo": {"title": {"displayValue": "Purina Fancy Feast Gravy Lovers Wet Cat Food, 24 Cans"},
                     "byLineInfo": {"brand": {"displayValue": "Purina Fancy Feast"}}},
        "offersV2": {"listings": [{
            "isBuyBoxWinner": True, "type": "LIGHTNING_DEAL",
            "availability": {"type": "IN_STOCK"},
            "price": {"money": {"amount": 15.99}, "pricePerUnit": {"displayAmount": "$0.22 / Ounce"},
                      "savingBasis": {"money": {"amount": 23.99}, "savingBasisTypeLabel": "List Price"},
                      "savings": {"percentage": 33}}}]},
    }

    def test_normalize(self):
        n = AmazonCreators.normalize(self.RAW)
        self.assertEqual(n["price"], 15.99)
        self.assertEqual(n["orig_price"], 23.99)
        self.assertEqual(n["deal"], "Lightning Deal")
        self.assertEqual(n["unit_price"], "$0.22 / Ounce")
        self.assertTrue(matches(n, entry("Fancy Feast"), CFG["categories"]["food"]))

    def test_subscribe_and_save(self):
        raw = json.loads(json.dumps(self.RAW))
        raw["offersV2"]["listings"][0]["type"] = None
        raw["offersV2"]["listings"][0]["price"].pop("savingBasis")
        raw["offersV2"]["listings"].append({"type": "SUBSCRIBE_AND_SAVE", "price": {"money": {"amount": 14.39}}})
        n = AmazonCreators.normalize(raw)
        self.assertEqual((n["price"], n["sns_price"], n["orig_price"]), (15.99, 14.39, None))
        d = price_deal(n, [], TIERS)
        self.assertNotIn("tier", d)            # no one-time discount
        self.assertEqual((d["sns_tier"], d["sns_pct_off"], d["sns_ref_type"]), ("80-90", 10, "onetime"))  # 14.39/15.99 = 0.8999

    def test_no_offer(self):
        self.assertIsNone(AmazonCreators.normalize({"asin": "X"}))


class TestWalmart(unittest.TestCase):
    def test_normalize(self):
        raw = {"itemId": 123, "name": "Fresh Step Clumping Cat Litter, Unscented, 25 lb", "brandName": "Fresh Step",
               "salePrice": 12.48, "msrp": 18.99, "productTrackingUrl": "https://goto.walmart.com/x", "stock": "Available"}
        n = WalmartAffiliate.normalize(raw)
        self.assertEqual((n["id"], n["price"], n["orig_price"]), ("123", 12.48, 18.99))
        self.assertTrue(matches(n, entry("Fresh Step"), CFG["categories"]["litter"]))


class TestFilters(unittest.TestCase):
    def item(self, title, brand=""):
        return {"title": title, "brand_raw": brand}

    def test_rejects_dog(self):
        self.assertFalse(matches(self.item("Instinct Raw Boost Dog Food"), entry("Instinct"), CFG["categories"]["food"]))

    def test_rejects_non_litter_arm_hammer(self):
        self.assertFalse(matches(self.item("Arm & Hammer Baking Soda 4 lb"), entry("Arm & Hammer"), CFG["categories"]["litter"]))

    def test_curly_apostrophe(self):
        self.assertTrue(matches(self.item("Cat’s Pride Max Power Clumping Litter 15 lb"), entry("Cat's Pride"), CFG["categories"]["litter"]))

    def test_advantage_ii_vs_xd(self):
        t = self.item("Advantage XD Flea Prevention for Large Cats, 2 doses")
        self.assertTrue(matches(t, entry("Advantage XD"), CFG["categories"]["meds"]))
        self.assertFalse(matches(t, entry("Advantage II"), CFG["categories"]["meds"]))


class TestTiers(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(pick_tier(0.50, TIERS), "le50")
        self.assertEqual(pick_tier(0.55, TIERS), "50-60")
        self.assertEqual(pick_tier(0.60, TIERS), "50-60")
        self.assertEqual(pick_tier(0.95, TIERS), "90+")
        self.assertIsNone(pick_tier(0.995, TIERS))

    def test_history_reference(self):
        d = price_deal({"price": 10.0, "orig_price": None}, [14.0, 14.0, 13.0], TIERS)
        self.assertEqual((d["ref_type"], d["tier"], d["pct_off"]), ("high30", "70-80", 29))
        self.assertIsNone(price_deal({"price": 10.0, "orig_price": None}, [10.0, 10.0, 10.0], TIERS))


if __name__ == "__main__":
    unittest.main()
