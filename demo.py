"""Demo provider: fake but plausible items so the site can be previewed before API keys exist.

Every item it produces is marked demo=True and the site shows a "示例数据" banner.
Links go to the store's search page for the product name, never to a made-up product page.
"""
import hashlib
import random
import urllib.parse

TEMPLATES = {
    "food": [
        ("{b} Adult Dry Cat Food, Chicken Recipe, {n} lb Bag", [3.5, 7, 16], 2.1),
        ("{b} Wet Cat Food Variety Pack, 3 oz Cans (Pack of {n})", [12, 24, 30], 0.55),
        ("{b} Kitten Formula Dry Cat Food, {n} lb", [3, 6], 2.6),
        ("{b} Grain Free Pate Wet Cat Food, Salmon, {n} Count", [12, 24], 0.9),
    ],
    "treat": [
        ("{b} Lickable Cat Treats Variety Pack, {n} Tubes", [20, 50, 100], 0.32),
    ],
    "litter": [
        ("{b} Clumping Cat Litter, Unscented, {n} lb", [14, 25, 40], 0.75),
        ("{b} Multi-Cat Clumping Clay Cat Litter, {n} lb", [20, 35], 0.7),
    ],
    "meds": [
        ("{b} Flea Treatment for Large Cats over 9 lbs, {n} Doses", [2, 4, 6], 13.5),
        ("{b} Flea Treatment for Small Cats 5-9 lbs, {n} Doses", [2, 4, 6], 12.5),
    ],
}
COLLAR = ("{b} Flea & Tick Collar for Cats, 8-Month Protection", [1], 62.0)


def _rng(*parts):
    seed = int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)
    return random.Random(seed)


class Demo:
    def __init__(self, store, day):
        self.store = store
        self.day = day

    def configured(self):
        return True

    def search_entry(self, entry):
        """Demo works per brand entry instead of per keyword."""
        cat = entry["category"]
        b = entry["brand"].replace(" (VE)", "")
        if b.startswith("Purina ") or entry.get("group") != "Purina":
            name = b
        else:
            name = f"Purina {b}"
        if "Churu" in b or "Delectables" in b:
            pool = TEMPLATES["treat"]
        elif "Seresto" in b:
            pool = [COLLAR]
        else:
            pool = TEMPLATES[cat]
        rng = _rng(self.store, entry["brand"])
        out = []
        for i, (tpl, sizes, per) in enumerate(pool):
            if rng.random() < 0.35:
                continue
            n = rng.choice(sizes)
            title = tpl.format(b=name, n=n)
            base = round(max(4.99, per * n * rng.uniform(0.85, 1.25)), 2)
            day_rng = _rng(self.store, entry["brand"], i, self.day)
            ratio = day_rng.choice([1, 1, 0.97, 0.92, 0.85, 0.8, 0.75, 0.66, 0.58, 0.45])
            price = round(base * ratio, 2)
            # Demo titles are invented, so link to a real search for the brand instead.
            q = urllib.parse.quote_plus(entry["queries"][0])
            url = (f"https://www.amazon.com/s?k={q}" if self.store == "amazon"
                   else f"https://www.walmart.com/search?q={q}")
            unit = None
            if self.store == "amazon" and " lb" in title:
                unit = f"${price / n / 16:.2f} / Ounce"
            sns_price = None
            if self.store == "amazon" and day_rng.random() < 0.6:
                sns_price = round(price * (1 - day_rng.choice([0.05, 0.1, 0.15])), 2)
            out.append({
                "sns_price": sns_price,
                "id": "demo-" + hashlib.md5(f"{self.store}|{entry['brand']}|{i}".encode()).hexdigest()[:10],
                "title": title,
                "brand_raw": name,
                "price": price,
                "orig_price": base if ratio < 1 else None,
                "orig_label": "List Price" if self.store == "amazon" else "Was",
                "unit_price": unit,
                "url": url,
                "image": None,
                "in_stock": True,
                "deal": "Lightning Deal" if ratio <= 0.6 and self.store == "amazon" else (
                    "Rollback" if ratio <= 0.8 and self.store == "walmart" else None),
                "seller": "Amazon.com" if self.store == "amazon" else "Walmart.com",
            })
        return out
