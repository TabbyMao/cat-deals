"""Amazon Creators API (successor of PA-API 5).

Needs an Amazon Associates account with Creators API access. Credentials come from
Associates Central -> Tools -> Creators API.

Env vars:
  AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET   Creators API credentials
  AMAZON_PARTNER_TAG                       your Associates tag, e.g. yourname-20
  AMAZON_SEARCH_URL (optional)             override if Amazon changes the path
"""
import os
import time

from .common import http_json, to_float

TOKEN_URL = "https://api.amazon.com/auth/o2/token"
DEFAULT_SEARCH_URL = "https://creatorsapi.amazon/catalog/v1/searchItems"
MARKETPLACE = "www.amazon.com"
RESOURCES = [
    "images.primary.medium",
    "itemInfo.title",
    "itemInfo.byLineInfo",
    "offersV2.listings.price",
    "offersV2.listings.availability",
    "offersV2.listings.type",
    "offersV2.listings.merchantInfo",
    "offersV2.listings.isBuyBoxWinner",
]
PAGES_PER_QUERY = 3       # 10 items per page -> up to 30 results per keyword
SECONDS_BETWEEN_CALLS = 1.1  # stay under the default 1 request/second


class AmazonCreators:
    store = "amazon"

    def __init__(self):
        self.client_id = os.environ.get("AMAZON_CLIENT_ID", "").strip()
        self.client_secret = os.environ.get("AMAZON_CLIENT_SECRET", "").strip()
        self.partner_tag = os.environ.get("AMAZON_PARTNER_TAG", "").strip()
        self.search_url = os.environ.get("AMAZON_SEARCH_URL", "").strip() or DEFAULT_SEARCH_URL
        self._token = None
        self._token_exp = 0

    def configured(self):
        return bool(self.client_id and self.client_secret and self.partner_tag)

    def _get_token(self):
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        resp = http_json(TOKEN_URL, method="POST", body={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "creatorsapi::default",
        })
        self._token = resp["access_token"]
        self._token_exp = time.time() + int(resp.get("expires_in", 3600))
        return self._token

    def search(self, keywords):
        """Yield raw items for a keyword search across a few pages."""
        for page in range(1, PAGES_PER_QUERY + 1):
            body = {
                "partnerTag": self.partner_tag,
                "marketplace": MARKETPLACE,
                "keywords": keywords,
                "searchIndex": "PetSupplies",
                "itemCount": 10,
                "itemPage": page,
                "resources": RESOURCES,
            }
            resp = http_json(self.search_url, method="POST", body=body, headers={
                "Authorization": f"Bearer {self._get_token()}",
                "x-marketplace": MARKETPLACE,
            })
            time.sleep(SECONDS_BETWEEN_CALLS)
            result = resp.get("searchResult") or {}
            items = result.get("items") or []
            yield from items
            total = result.get("totalResultCount") or 0
            if len(items) < 10 or page * 10 >= total:
                break

    @staticmethod
    def normalize(raw):
        """Turn one Creators API item into our common shape (or None if no usable price)."""
        listings = ((raw.get("offersV2") or {}).get("listings")) or []
        if not listings:
            return None
        # A Subscribe & Save offer comes back as its own listing with type SUBSCRIBE_AND_SAVE.
        sns = next((l for l in listings if (l.get("type") or "").upper() == "SUBSCRIBE_AND_SAVE"), None)
        sns_price = to_float((((sns or {}).get("price") or {}).get("money") or {}).get("amount"))
        regular = [l for l in listings if l is not sns] or listings
        listing = next((l for l in regular if l.get("isBuyBoxWinner")), regular[0])
        price_block = listing.get("price") or {}
        price = to_float((price_block.get("money") or {}).get("amount"))
        if price is None:
            return None
        basis = price_block.get("savingBasis") or {}
        orig = to_float((basis.get("money") or {}).get("amount"))
        unit = (price_block.get("pricePerUnit") or {}).get("displayAmount")
        avail = ((listing.get("availability") or {}).get("type") or "").upper()

        info = raw.get("itemInfo") or {}
        title = ((info.get("title") or {}).get("displayValue")) or ""
        brand = ((((info.get("byLineInfo") or {}).get("brand")) or {}).get("displayValue")) or ""
        image = ((((raw.get("images") or {}).get("primary") or {}).get("medium")) or {}).get("url")
        deal_type = listing.get("type") or ""
        return {
            "id": raw.get("asin"),
            "title": title,
            "brand_raw": brand,
            "price": round(price, 2),
            "orig_price": round(orig, 2) if orig else None,
            "orig_label": basis.get("savingBasisTypeLabel") or ("List Price" if orig else None),
            "unit_price": unit,
            "url": raw.get("detailPageURL"),
            "image": image,
            "in_stock": avail not in ("OUT_OF_STOCK", "UNAVAILABLE"),
            "deal": deal_type.replace("_", " ").title() if deal_type and deal_type != "REGULAR" else None,
            "sns_price": round(sns_price, 2) if sns_price and sns_price < price else None,
            "seller": (listing.get("merchantInfo") or {}).get("name"),
        }
