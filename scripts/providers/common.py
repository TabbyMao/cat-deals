"""Shared helpers for the store providers."""
import json
import time
import urllib.error
import urllib.request

USER_AGENT = "cat-deals-bot/1.0"


def http_json(url, method="GET", headers=None, body=None, timeout=30, retries=2):
    """Small JSON-over-HTTP helper with retry on 429/5xx. Returns parsed JSON."""
    data = None
    hdrs = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last_err = RuntimeError(f"HTTP {e.code} from {url.split('?')[0]}: {detail}")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise last_err
        except urllib.error.URLError as e:
            last_err = RuntimeError(f"Network error for {url.split('?')[0]}: {e.reason}")
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise last_err
    raise last_err


def to_float(v):
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None
