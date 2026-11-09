#!/usr/bin/env python3
"""Daily job: search Amazon + Walmart for the configured brands, keep only real discounts,
sort them into price tiers, and write public/data/deals.json for the website.

Usage:
  python scripts/fetch_deals.py            # real APIs for whichever store has credentials
  python scripts/fetch_deals.py --demo     # fake sample data (no keys needed)
  python scripts/fetch_deals.py --date 2026-11-09   # pretend it is another day (testing)
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from providers import AmazonCreators, Demo, WalmartAffiliate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "brands.json"
HISTORY = ROOT / "data" / "history.json"
OUTPUT = ROOT / "public" / "data" / "deals.json"
HISTORY_DAYS = 120
STORE_LABELS = {"amazon": "Amazon", "walmart": "Walmart"}


# ---------- filtering ----------

def _norm(s):
    return (s or "").lower().replace("’", "'").replace("‘", "'")


def matches(item, entry, cat_rules):
    title = _norm(item["title"])
    text = title + " " + _norm(item.get("brand_raw"))
    if not any(_norm(m) in text for m in entry["match"]):
        return False
    if not any(w in title for w in cat_rules.get("require_any", [])):
        return False
    if any(w in title for w in cat_rules.get("exclude_any", [])):
        return False
    return True


# ---------- history & pricing ----------

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def update_history(history, key, title, price, today):
    rec = history.setdefault(key, {"t": title, "p": {}})
    rec["t"] = title
    rec["p"][today] = price


def prune_history(history, today):
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    for key in list(history):
        rec = history[key]
        rec["p"] = {d: p for d, p in rec["p"].items() if d >= cutoff}
        if not rec["p"]:
            del history[key]


def past_prices(history, key, today, days=30):
    rec = history.get(key)
    if not rec:
        return []
    start = (dt.date.fromisoformat(today) - dt.timedelta(days=days)).isoformat()
    return [p for d, p in rec["p"].items() if start <= d < today]


def pick_tier(ratio, tiers):
    for t in tiers:
        if ratio <= t["max_ratio"] + 1e-9:
            return t["key"]
    return None


def price_deal(item, prev, tiers):
    """Decide the reference ("original") price and tier. Returns None if not a discount."""
    price = item["price"]
    ref, ref_type = None, None
    if item.get("orig_price") and item["orig_price"] > price * 1.005:
        ref, ref_type = item["orig_price"], "listed"
    elif len(prev) >= 3 and max(prev) > price * 1.005:
        # Store shows no strike-through price (common on Walmart): compare with our own 30-day high.
        ref, ref_type = max(prev), "high30"
    info = {}
    if ref:
        ratio = price / ref
        tier = pick_tier(ratio, tiers)
        if tier:
            info.update({"ref_price": round(ref, 2), "ref_type": ref_type,
                         "pct_off": round((1 - ratio) * 100), "ratio": round(ratio, 4), "tier": tier})

    # Subscribe & Save: compared with the same original price, or with the one-time price if none.
    sns = item.get("sns_price")
    if sns:
        sns_ref = ref or item.get("orig_price") or price
        sns_type = ref_type or ("listed" if item.get("orig_price") else "onetime")
        s_ratio = sns / sns_ref
        s_tier = pick_tier(s_ratio, tiers)
        if s_tier:
            info.update({"sns_ref_price": round(sns_ref, 2), "sns_ref_type": sns_type,
                         "sns_pct_off": round((1 - s_ratio) * 100), "sns_ratio": round(s_ratio, 4),
                         "sns_tier": s_tier})
    return info or None


# ---------- main ----------

def run(demo=False, today=None):
    cfg = load_json(CONFIG, None)
    if cfg is None:
        sys.exit(f"Cannot read {CONFIG}")
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date().isoformat()
    tiers = cfg["tiers"]

    if demo:
        providers = [Demo("amazon", today), Demo("walmart", today)]
    else:
        providers = [p for p in (AmazonCreators(), WalmartAffiliate()) if p.configured()]
        if not providers:
            print("No API credentials found -> falling back to demo data. "
                  "Set AMAZON_* and/or WALMART_* secrets to fetch real prices.")
            providers = [Demo("amazon", today), Demo("walmart", today)]
            demo = True

    history = load_json(HISTORY, {})
    previous = load_json(OUTPUT, {})
    if not demo:
        # Switching to real data: forget sample history and sample deals.
        history = {k: v for k, v in history.items() if ":demo-" not in k}
        if previous.get("demo"):
            previous = {}
    sources = {}
    seen = {}

    for prov in providers:
        store = prov.store
        stat = {"label": STORE_LABELS[store], "status": "ok", "matched": 0, "errors": []}
        for entry in cfg["brands"]:
            cat_rules = cfg["categories"][entry["category"]]
            try:
                if isinstance(prov, Demo):
                    raws = prov.search_entry(entry)
                    normalized = raws
                else:
                    normalized = []
                    for q in entry["queries"]:
                        for raw in prov.search(q):
                            n = prov.normalize(raw)
                            if n:
                                normalized.append(n)
            except Exception as e:  # keep going if one keyword fails
                stat["errors"].append(f"{entry['brand']}: {e}")
                print(f"[{store}] {entry['brand']}: {e}", file=sys.stderr)
                continue
            for it in normalized:
                if not it.get("id") or not matches(it, entry, cat_rules):
                    continue
                key = f"{store}:{it['id']}"
                if key in seen:
                    continue
                it.update({
                    "key": key, "store": store, "category": entry["category"],
                    "brand": entry["brand"], "group": entry.get("group"), "demo": demo,
                })
                seen[key] = it
                stat["matched"] += 1
        if stat["matched"] == 0 and stat["errors"]:
            stat["status"] = "failed"
        elif stat["errors"]:
            stat["status"] = "partial"
        sources[store] = stat

    deals = []
    for key, it in seen.items():
        prev = past_prices(history, key, today)
        info = price_deal(it, prev, tiers)
        update_history(history, key, it["title"], it["price"], today)
        if not info or not it.get("in_stock", True):
            continue
        it.update(info)
        prev60 = past_prices(history, key, today, days=60)
        it["low30"] = min(prev) if prev else None
        it["is_low30"] = len(prev) >= 7 and it["price"] <= min(prev)
        it["low60"] = min(prev60) if prev60 else None
        it.pop("brand_raw", None)
        deals.append(it)

    # If a store failed completely today, keep yesterday's deals for it (marked stale).
    for store, stat in sources.items():
        if stat["status"] == "failed":
            old = [d for d in previous.get("deals", []) if d.get("store") == store]
            for d in old:
                d["stale"] = True
            deals.extend(old)

    deals.sort(key=lambda d: (d.get("ratio", 1), d["price"]))
    prune_history(history, today)

    out = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "date": today,
        "demo": demo,
        # Only counts go public; full error text stays in the Actions log.
        "sources": {s: {"label": v["label"], "status": v["status"], "matched": v["matched"],
                        "error_count": len(v["errors"])} for s, v in sources.items()},
        "tiers": tiers,
        "categories": {k: v["label"] for k, v in cfg["categories"].items()},
        "brands": [{"brand": b["brand"], "category": b["category"], "group": b.get("group")} for b in cfg["brands"]],
        "deals": deals,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), "utf-8")

    print(f"{today}: {len(seen)} matching products, {len(deals)} on sale"
          + (" (DEMO DATA)" if demo else ""))
    for store, s in sources.items():
        print(f"  {s['label']}: {s['status']}, {s['matched']} matched, {len(s['errors'])} errors")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use fake sample data")
    ap.add_argument("--date", help="override today's date (YYYY-MM-DD)")
    args = ap.parse_args()
    run(demo=args.demo, today=args.date)
