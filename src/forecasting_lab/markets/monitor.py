"""The market monitor: the concrete cross-venue divergence pipeline.

This is the ``master-index.md`` "market monitor" made real — a
:class:`~forecasting_lab.pipeline.Pipeline` that fetches open markets from both
venues, matches them by title, scores after-fee divergence, and files a dated
digest into ``inputs/``:

    from forecasting_lab.markets.monitor import DivergencePipeline
    DivergencePipeline().run()          # -> inputs/YYYY-MM-DD-market-divergence.md

The payload extractors handle each venue's real quirks: Kalshi quotes prices as
integer *cents* (``yes_bid=42`` means $0.42), and Polymarket's Gamma API returns
``outcomePrices`` as a JSON *string* (``'["0.45", "0.55"]'``) — both silently
corrupt naive parsing.
"""

from __future__ import annotations

import json

import pandas as pd

from ..pipeline.base import Pipeline
from ..pipeline.digest import render_digest
from .divergence import find_divergences
from .kalshi import KalshiClient
from .matching import match_markets
from .polymarket import PolymarketClient, to_float


def _dollars(value) -> float | None:
    """Parse a Kalshi ``*_dollars`` string field; 0 means an empty side, not $0."""
    f = to_float(value)
    return f if f else None


def kalshi_yes_price(market: dict) -> float | None:
    """YES mid from a Kalshi market payload.

    The current API returns string-dollar fields (``yes_bid_dollars='0.4200'``);
    older payloads used integer cents (``yes_bid=42``). Handle both, preferring
    dollars. Zero/None quotes mean an empty book side and yield no price.
    """
    bid, ask = _dollars(market.get("yes_bid_dollars")), _dollars(market.get("yes_ask_dollars"))
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0
    last = _dollars(market.get("last_price_dollars"))
    if last is not None:
        return last
    bid, ask = market.get("yes_bid"), market.get("yes_ask")
    if bid and ask:
        return (float(bid) + float(ask)) / 2.0 / 100.0
    if market.get("last_price"):
        return float(market["last_price"]) / 100.0
    return None


def poly_yes_price(market: dict) -> float | None:
    """YES price from a Gamma market payload.

    ``outcomePrices`` arrives as a JSON string of stringified floats, ordered to
    match ``outcomes`` (YES first on binary markets). Falls back to
    ``lastTradePrice`` / bestBid-bestAsk mid.
    """
    raw = market.get("outcomePrices")
    if raw:
        try:
            prices = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(prices, list) and prices:
                return to_float(prices[0])
        except (json.JSONDecodeError, TypeError):
            pass
    last = to_float(market.get("lastTradePrice"))
    if last is not None:
        return last
    bid, ask = to_float(market.get("bestBid")), to_float(market.get("bestAsk"))
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0
    return None


class DivergencePipeline(Pipeline):
    """fetch (Kalshi binary events + Polymarket by volume) -> match -> score -> digest."""

    slug = "market-divergence"

    def __init__(
        self,
        kalshi: KalshiClient | None = None,
        polymarket: PolymarketClient | None = None,
        *,
        match_threshold: float = 0.5,
        edge_threshold: float = 0.0,
        limit: int = 200,
    ):
        self.kalshi = kalshi or KalshiClient()
        self.polymarket = polymarket or PolymarketClient()
        self.match_threshold = match_threshold
        self.edge_threshold = edge_threshold
        self.limit = limit

    # ---- fetch ----------------------------------------------------------
    def fetch(self) -> dict[str, list[dict]]:
        """Pull the cross-listable universe from each venue.

        Kalshi's raw ``/markets`` book is dominated by multi-leg sports parlays;
        the matchable events (elections, macro, world) live on ``/events`` with
        nested markets. Polymarket is ordered by volume so the liquid,
        prominently listed markets — the ones that get cross-listed — come first.
        """
        return {
            "kalshi": self.kalshi.events(
                status="open", with_nested_markets="true", limit=self.limit
            ),
            "polymarket": self.polymarket.markets(
                active="true",
                closed="false",
                order="volumeNum",
                ascending="false",
                limit=self.limit,
            ),
        }

    # ---- process --------------------------------------------------------
    def _live_odds(self, raw: dict[str, list[dict]]) -> dict:
        """Most-prominent live markets from each venue, with their YES odds — the
        'here are the current high-value predictions' view the dashboard leads with.
        Polymarket arrives ordered by volume; Kalshi binary events by prominence."""
        poly = []
        for m in raw.get("polymarket", []):
            price = poly_yes_price(m)
            q = m.get("question", "")
            if price is None or not q:
                continue
            poly.append({"event": q, "yes": round(float(price), 3),
                         "volume": round(to_float(m.get("volumeNum")) or 0.0, 0)})
            if len(poly) >= 10:
                break
        kalshi = []
        for e in raw.get("kalshi", []):
            markets = e.get("markets") or []
            if len(markets) != 1:
                continue
            price = kalshi_yes_price(markets[0])
            title = e.get("title", "")
            if price is None or not title:
                continue
            kalshi.append({"event": title, "yes": round(float(price), 3)})
            if len(kalshi) >= 10:
                break
        return {"poly": poly, "kalshi": kalshi}

    def process(self, raw: dict[str, list[dict]]) -> str:
        # Binary (single-market) events only: the event title is the question,
        # and its lone market's YES quote is the price.
        k = pd.DataFrame(
            [
                {"title": e.get("title", ""), "kalshi_yes": kalshi_yes_price(e["markets"][0])}
                for e in raw["kalshi"]
                if len(e.get("markets") or []) == 1
            ]
        ).dropna()
        p = pd.DataFrame(
            [
                {"question": m.get("question", ""), "poly_yes": poly_yes_price(m)}
                for m in raw["polymarket"]
            ]
        ).dropna()

        sections: dict[str, str] = {}
        self._data = {"edges": [], "n_kalshi": int(len(k)), "n_poly": int(len(p)),
                      "live": self._live_odds(raw)}
        if k.empty or p.empty:
            sections["Flagged markets (net of fees)"] = "_one or both venues returned no priced markets_"
        else:
            matched = match_markets(k, p, threshold=self.match_threshold)
            # Always surface the closest-matched pairs (with both venues' odds) so
            # the dashboard shows real prices even on days nothing clears the fee hurdle.
            self._data["matched"] = [
                {
                    "event": str(r["event"]),
                    "kalshi": round(float(r["kalshi_yes"]), 3),
                    "poly": round(float(r["poly_yes"]), 3),
                    "gap": round(abs(float(r["kalshi_yes"]) - float(r["poly_yes"])), 3),
                    "poly_event": str(r["poly_event"]),
                    "similarity": round(float(r["similarity"]), 2),
                }
                for _, r in matched.sort_values("similarity", ascending=False).head(10).iterrows()
            ]
            flags = find_divergences(matched, threshold=self.edge_threshold)
            if flags.empty:
                body = "_no after-fee divergences cleared the threshold_"
            else:
                flags = flags.merge(
                    matched[["event", "poly_event", "similarity"]], on="event", how="left"
                )
                lines = [
                    "| event | kalshi_yes | poly_yes | net_edge | direction | matched poly title | sim |",
                    "| --- | --- | --- | --- | --- | --- | --- |",
                ]
                edges = []
                for _, r in flags.iterrows():
                    lines.append(
                        f"| {r['event']} | {r['kalshi_yes']:.3f} | {r['poly_yes']:.3f} "
                        f"| {r['net_edge']:.3f} | {r['direction']} | {r['poly_event']} "
                        f"| {r['similarity']:.2f} |"
                    )
                    edges.append({
                        "event": str(r["event"]),
                        "kalshi": round(float(r["kalshi_yes"]), 3),
                        "poly": round(float(r["poly_yes"]), 3),
                        "net_edge": round(float(r["net_edge"]), 3),
                        "direction": str(r["direction"]),
                        "poly_event": str(r["poly_event"]),
                        "similarity": round(float(r["similarity"]), 2),
                    })
                body = "\n".join(lines)
                self._data["edges"] = edges
            sections["Flagged markets (net of fees)"] = body
            sections["Coverage"] = (
                f"{len(k)} Kalshi binary events and {len(p)} Polymarket priced markets "
                f"scanned; {len(matched)} title-matched at similarity >= {self.match_threshold}."
            )

        return render_digest(
            "Cross-Venue Divergence Digest",
            sections,
            disclaimer=(
                "Title matches are candidates — verify both contracts resolve on identical "
                "criteria before believing any 'arb'. Not financial advice."
            ),
        )
