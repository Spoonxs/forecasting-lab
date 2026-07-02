"""Polymarket client (Gamma + CLOB + Data APIs).

Three public surfaces, no auth needed for reads:
- Gamma  (https://gamma-api.polymarket.com): market/event metadata — token IDs,
  end dates, volume, descriptions. You live in ``/markets`` and ``/events``.
- CLOB   (https://clob.polymarket.com): order book and prices.
- Data   (https://data-api.polymarket.com): positions, trades, leaderboard.

Gotchas that silently invert your numbers (all handled here):
- **Prices come back as JSON strings, not floats** — always coerce.
- The order-book arrays have a specific ordering and sizes are strings too.
- Public endpoints are rate-limited and flaky under load — cache aggressively
  (this client uses the retrying session and an optional disk cache).

Order placement (authenticated wallet signing via ``py-clob-client``) is out of
scope for this research client, which is read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from ..config import get_settings
from ..utils.cache import DiskCache
from ..utils.http import HttpClient

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA = "https://data-api.polymarket.com"


def to_float(x: Any, default: float | None = None) -> float | None:
    """Coerce Polymarket's stringified numbers to float. ``None``/``""`` -> default."""
    if x is None or x == "":
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Quote:
    token_id: str
    best_bid: float | None
    best_ask: float | None

    @property
    def mid(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid


def parse_orderbook(payload: dict) -> Quote:
    """Parse a CLOB ``/book`` payload into best bid/ask, coercing string prices.

    The payload looks like ``{"asset_id": "...", "bids": [{"price","size"}...],
    "asks": [...]}``. Best bid is the highest bid price; best ask the lowest ask.
    """
    token_id = str(payload.get("asset_id") or payload.get("market") or "")
    bids = payload.get("bids") or []
    asks = payload.get("asks") or []
    bid_prices = [to_float(b.get("price")) for b in bids if to_float(b.get("price")) is not None]
    ask_prices = [to_float(a.get("price")) for a in asks if to_float(a.get("price")) is not None]
    best_bid = max(bid_prices) if bid_prices else None
    best_ask = min(ask_prices) if ask_prices else None
    return Quote(token_id=token_id, best_bid=best_bid, best_ask=best_ask)


class PolymarketClient:
    """Read-only client across the three Polymarket surfaces."""

    def __init__(
        self,
        http: HttpClient | None = None,
        use_cache: bool = True,
        cache: DiskCache | None = None,
    ):
        self.http = http or HttpClient()
        if cache is not None:
            self.cache = cache
        elif use_cache:
            self.cache = DiskCache("polymarket", ttl=get_settings().cache_ttl_markets)
        else:
            self.cache = None

    def _get(self, url: str, params: dict | None = None, *, cache: bool = False) -> Any:
        """GET JSON, optionally served from the TTL disk cache (keyed by url+params).
        Metadata reads cache; live price reads pass ``cache=False`` for freshness."""
        if cache and self.cache is not None:
            suffix = "?" + urlencode(sorted(params.items())) if params else ""
            return self.cache.get_or_set(
                url + suffix, lambda: self.http.get_json(url, params=params or None)
            )
        return self.http.get_json(url, params=params or None)

    @staticmethod
    def _as_list(data: Any) -> list[dict]:
        return data if isinstance(data, list) else data.get("data", [])

    # ---- Gamma (metadata) ---------------------------------------------
    def markets(self, *, max_pages: int = 10, **params: Any) -> list[dict]:
        """List markets. Common filters: ``active=true``, ``closed=false``, ``limit``.

        Gamma silently caps each response at 100 rows, so requests for more are
        paginated with ``offset`` until ``limit`` is reached or a short page ends
        the listing.
        """
        limit = params.get("limit")
        page_size = min(int(limit), 100) if limit else 100
        out: list[dict] = []
        offset = int(params.get("offset", 0))
        for _ in range(max_pages):
            page_params = {**params, "limit": page_size, "offset": offset}
            page = self._as_list(self._get(f"{GAMMA}/markets", page_params, cache=True))
            out.extend(page)
            if len(page) < page_size or (limit and len(out) >= limit):
                break
            offset += len(page)
        return out[:limit] if limit else out

    def events(self, **params: Any) -> list[dict]:
        return self._as_list(self._get(f"{GAMMA}/events", params or None, cache=True))

    # ---- CLOB (prices — live, never cached) ---------------------------
    def orderbook(self, token_id: str) -> Quote:
        return parse_orderbook(self._get(f"{CLOB}/book", {"token_id": token_id}))

    def midpoint(self, token_id: str) -> float | None:
        return to_float(self._get(f"{CLOB}/midpoint", {"token_id": token_id}).get("mid"))

    def price(self, token_id: str, side: str = "buy") -> float | None:
        """Best price for a side. NOTE: ``side`` semantics are easy to flip —
        ``buy`` is the best ask you'd pay, ``sell`` is the best bid you'd hit."""
        payload = self._get(f"{CLOB}/price", {"token_id": token_id, "side": side})
        return to_float(payload.get("price"))

    # ---- Data (activity) ----------------------------------------------
    def trades(self, **params: Any) -> list[dict]:
        return self._as_list(self._get(f"{DATA}/trades", params or None))
