"""SEC EDGAR connector — a working "port" once the User-Agent is right.

SEC returns 403 to a default/empty User-Agent; it requires one that identifies
you with a contact (their fair-access policy). Set ``SEC_USER_AGENT`` in ``.env``
(e.g. ``"my-project you@example.com"``). Rate limit: <= 10 req/s.

- ``company_tickers()`` — the full ticker↔CIK map (~10k names), the master list
  behind any fundamental lookup.
- ``full_text_search(query)`` — EDGAR full-text filing search (8-K/10-Q/etc.),
  the best free "what did they just file" signal for the momentum composite.
"""

from __future__ import annotations

import os
from typing import Any

from ..utils.cache import DiskCache
from ..utils.http import HttpClient

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FULLTEXT_URL = "https://efts.sec.gov/LATEST/search-index"


def _user_agent() -> str:
    return os.environ.get("SEC_USER_AGENT", "forecasting-lab research contact@example.com")


def _client() -> HttpClient:
    return HttpClient(user_agent=_user_agent())


def company_tickers(refresh: bool = False) -> dict[str, int]:
    """Map ``TICKER -> CIK`` for every SEC registrant. Cached a day."""
    cache = DiskCache("sec", ttl=24 * 3600)
    if not refresh:
        hit = cache.get("tickers")
        if hit:
            return hit
    data = _client().get_json(TICKERS_URL)
    out = {v["ticker"]: int(v["cik_str"]) for v in data.values()}
    cache.set("tickers", out)
    return out


def full_text_search(query: str, forms: str | None = None) -> list[dict]:
    """EDGAR full-text search. Returns hit metadata (accession, form, date)."""
    params: dict[str, Any] = {"q": query}
    if forms:
        params["forms"] = forms
    data = _client().get_json(FULLTEXT_URL, params=params)
    hits = data.get("hits", {}).get("hits", [])
    return [
        {
            "accession": h.get("_id"),
            "form": h.get("_source", {}).get("file_type"),
            "date": h.get("_source", {}).get("file_date"),
            "display_names": h.get("_source", {}).get("display_names"),
        }
        for h in hits
    ]
