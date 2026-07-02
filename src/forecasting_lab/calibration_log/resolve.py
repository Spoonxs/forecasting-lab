"""Venue settlement lookups — the source of truth for auto-resolution.

``venue_resolver(venue, market_id) -> 0 | 1 | None`` returns the realized YES
outcome once a market has settled (None while still open). Kalshi exposes a
``result`` field ("yes"/"no"); Polymarket's Gamma marks a market ``closed`` with
its ``outcomePrices`` collapsing to 1/0. Any lookup error yields None so a flaky
venue never crashes the daily run — it just tries again next time.
"""

from __future__ import annotations


def kalshi_outcome(ticker: str) -> int | None:
    """Realized YES outcome for a settled Kalshi market, else None."""
    try:
        from ..markets.kalshi import KalshiClient

        market = KalshiClient().market(ticker)
    except Exception:  # noqa: BLE001
        return None
    if (market.get("status") or "").lower() not in ("settled", "finalized", "closed"):
        return None
    result = (market.get("result") or "").lower()
    if result == "yes":
        return 1
    if result == "no":
        return 0
    return None


def poly_outcome(market_id: str) -> int | None:
    """Realized YES outcome for a resolved Polymarket market, else None."""
    try:
        from ..markets.polymarket import PolymarketClient, to_float

        markets = PolymarketClient(use_cache=False).markets(id=market_id)
    except Exception:  # noqa: BLE001
        return None
    market = markets[0] if markets else {}
    if not market.get("closed"):
        return None
    raw = market.get("outcomePrices")
    if raw:
        import json

        try:
            prices = json.loads(raw) if isinstance(raw, str) else raw
            yes = to_float(prices[0]) if prices else None
            if yes is not None:
                return 1 if yes >= 0.5 else 0
        except (json.JSONDecodeError, TypeError, IndexError):
            pass
    return None


def venue_resolver(venue: str, market_id: str) -> int | None:
    """Dispatch to the right venue by ``venue`` string (case-insensitive)."""
    v = (venue or "").lower()
    if "kalshi" in v:
        return kalshi_outcome(market_id)
    if "poly" in v:
        return poly_outcome(market_id)
    return None
