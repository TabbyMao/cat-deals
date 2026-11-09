"""Walmart Affiliate API (walmart.io).

Sign up at https://walmart.io, create an application, upload your RSA public key,
and you get a Consumer ID + key version. Requests are signed with your private key.

Env vars:
  WALMART_CONSUMER_ID     consumer ID from walmart.io
  WALMART_KEY_VERSION     usually "1"
  WALMART_PRIVATE_KEY     the full PEM text of your private key (-----BEGIN PRIVATE KEY----- ...)
  WALMART_PUBLISHER_ID    (optional) your Impact publisher ID, adds affiliate tracking to links
"""
import base64
import os
import time
import urllib.parse

from .common import http_json, to_float

SEARCH_URL = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search"
ITEMS_PER_PAGE = 25
PAGES_PER_QUERY = 2
SECONDS_BETWEEN_CALLS = 0.5


class WalmartAffiliate:
    store = "walmart"

    def __init__(self):
        self.consumer_id = os.environ.get("WALMART_CONSUMER_ID", "").strip()
        self.key_version = os.environ.get("WALMART_KEY_VERSION", "1").strip() or "1"
        self.private_key_pem = os.environ.get("WALMART_PRIVATE_KEY", "").strip()
        self.publisher_id = os.environ.get("WALMART_PUBLISHER_ID", "").strip()
        self._key = None

    def configured(self):
        return bool(self.consumer_id and self.private_key_pem)

    def _signed_headers(self):
        # Imported lazily so the rest of the project runs without the package.
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        if self._key is None:
            pem = self.private_key_pem.replace("\\n", "\n").encode("utf-8")
            self._key = serialization.load_pem_private_key(pem, password=None)
        ts = str(int(time.time() * 1000))
        # Walmart signs: consumerId \n timestamp \n keyVersion \n
        message = f"{self.consumer_id}\n{ts}\n{self.key_version}\n".encode("utf-8")
        sig = self._key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        return {
            "WM_CONSUMER.ID": self.consumer_id,
            "WM_CONSUMER.INTIMESTAMP": ts,
            "WM_SEC.KEY_VERSION": self.key_version,
            "WM_SEC.AUTH_SIGNATURE": base64.b64encode(sig).decode("ascii"),
        }

    def search(self, keywords):
        for page in range(PAGES_PER_QUERY):
            params = {"query": keywords, "numItems": ITEMS_PER_PAGE, "start": page * ITEMS_PER_PAGE + 1}
            if self.publisher_id:
                params["publisherId"] = self.publisher_id
            url = SEARCH_URL + "?" + urllib.parse.urlencode(params)
            resp = http_json(url, headers=self._signed_headers())
            time.sleep(SECONDS_BETWEEN_CALLS)
            items = resp.get("items") or []
            yield from items
            if len(items) < ITEMS_PER_PAGE:
                break

    @staticmethod
    def normalize(raw):
        price = to_float(raw.get("salePrice"))
        if price is None:
            return None
        msrp = to_float(raw.get("msrp"))
        stock = (raw.get("stock") or "").lower()
        return {
            "id": str(raw.get("itemId")),
            "title": raw.get("name") or "",
            "brand_raw": raw.get("brandName") or "",
            "price": round(price, 2),
            "orig_price": round(msrp, 2) if msrp else None,
            "orig_label": "MSRP" if msrp else None,
            "unit_price": None,
            "url": raw.get("productTrackingUrl") or raw.get("productUrl"),
            "image": raw.get("mediumImage") or raw.get("thumbnailImage"),
            "in_stock": stock not in ("not available", "out of stock"),
            "deal": "Rollback" if raw.get("rollback") or raw.get("isRollback") else (
                "Clearance" if raw.get("clearance") else None),
            "seller": raw.get("sellerInfo") or ("Walmart.com" if raw.get("offerType", "").startswith("ONLINE") else None),
        }
