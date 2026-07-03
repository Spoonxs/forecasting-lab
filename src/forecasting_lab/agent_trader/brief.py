"""P0 — the daily brief: the cached aggregation layer the MCP tool exposes.

Assembles ONE structured, decision-ready brief per ticker from injectable fetchers
(price, news, the lab's own signals, fundamentals). Cheap and cacheable, and — by
design — it holds **no LLM/agent/broker code** (pinned in tests): this is the
"results only" layer that keeps raw data out of the model's context. Each source
degrades honestly: a fetcher that fails marks its section unavailable and the brief
still returns. Deterministic — ``as_of`` and the cache clock are passed in, never
read from the wall.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

from ..utils.cache import DiskCache

# A fetcher maps a ticker to a dict of facts; it may raise (→ section unavailable).
Fetcher = Callable[[str], dict]


@dataclass(frozen=True)
class BriefSection:
    name: str
    ok: bool  # False = the source was unavailable (honest degradation)
    data: dict


@dataclass(frozen=True)
class DailyBrief:
    ticker: str
    as_of: str
    sections: tuple[BriefSection, ...]

    def get(self, name: str) -> BriefSection | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def to_dict(self) -> dict:
        return {"ticker": self.ticker, "as_of": self.as_of,
                "sections": [asdict(s) for s in self.sections]}

    @classmethod
    def from_dict(cls, d: dict) -> DailyBrief:
        secs = tuple(BriefSection(**s) for s in d.get("sections", []))
        return cls(d["ticker"], d["as_of"], secs)


def _safe(name: str, fetch: Fetcher, ticker: str) -> BriefSection:
    try:
        data = fetch(ticker)
        return BriefSection(name, True, dict(data) if data else {})
    except Exception:  # noqa: BLE001 - any source may be blocked; degrade, never crash
        return BriefSection(name, False, {})


def build_brief(ticker: str, as_of: str, fetchers: dict[str, Fetcher]) -> DailyBrief:
    """Assemble a brief from ``fetchers``; each section degrades independently."""
    sections = tuple(_safe(name, fetch, ticker) for name, fetch in fetchers.items())
    return DailyBrief(ticker.upper(), as_of, sections)


# ------------------------------------------------------- default fetchers (reuse the lab)
def _price_fetch(ticker: str) -> dict:
    from ..signals.trending import TrendingFetcher, compute_features

    hist = TrendingFetcher().daily_history(ticker)
    if hist.empty:
        raise RuntimeError("no price history")
    feats = compute_features(hist, 0) or {}
    return {
        "last": round(float(hist["close"].iloc[-1]), 4),
        "ret_5d": feats.get("ret_5d"),
        "ret_20d": feats.get("ret_20d"),
        "ret_60d": feats.get("ret_60d"),
        "pct_from_high": feats.get("pct_from_high"),
    }


def _news_fetch(ticker: str) -> dict:
    from ..signals.trending import TrendingFetcher

    titles = TrendingFetcher().news_headlines(f"{ticker} stock", hours=72)
    return {"count": len(titles), "headlines": titles[:5]}


def _lab_signals_fetch(ticker: str) -> dict:
    """The lab's own read on this name — its mover odds + evidence, if it's in the scan."""
    from ..pipeline.digest import read_latest_data
    from ..predictions import mover_prediction

    data = read_latest_data("trending-stocks") or {}
    for card in (data.get("movers") or []) + (data.get("fast") or []):
        if str(card.get("ticker", "")).upper() == ticker.upper():
            pred = mover_prediction(card)
            return {
                "in_scan": True,
                "odds": pred.pct(),
                "drivers": [d.feature for d in pred.drivers],
                "caveat": pred.caveat,
            }
    return {"in_scan": False}


def _fundamentals_fetch(ticker: str) -> dict:
    # No free fundamentals feed is wired yet (FMP/Yahoo statements are a Phase-2 connector);
    # degrade honestly rather than fabricate.
    raise NotImplementedError("fundamentals connector not wired (Phase 2)")


def default_fetchers() -> dict[str, Fetcher]:
    """Live default sources; each degrades on its own when blocked."""
    return {
        "price": _price_fetch,
        "news": _news_fetch,
        "lab_signals": _lab_signals_fetch,
        "fundamentals": _fundamentals_fetch,
    }


def daily_brief(ticker: str, as_of: str, *, fetchers: dict[str, Fetcher] | None = None,
                cache: DiskCache | None = None, ttl: int = 6 * 3600,
                now: float | None = None) -> DailyBrief:
    """A cached daily brief for one ticker (keyed by ticker + as_of date)."""
    fetchers = fetchers if fetchers is not None else default_fetchers()
    cache = cache if cache is not None else DiskCache("agent_brief", ttl=ttl)
    key = f"{ticker.upper()}:{as_of}"
    hit = cache.get(key, now=now)
    if hit is not None:
        return DailyBrief.from_dict(hit)
    brief = build_brief(ticker, as_of, fetchers)
    cache.set(key, brief.to_dict(), now=now)
    return brief
