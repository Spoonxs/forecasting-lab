"""The tracked equity universe.

``equity_universe()`` returns 500+ symbols: the live S&P 500 constituents
(scraped from Wikipedia, cached) unioned with a curated set of liquid growth and
meme names the trending scanner cares about. Falls back to the bundled snapshot
(``_bundled.py``, 500+ tickers) when offline — so the count never drops below the
promise even with no network.
"""

from __future__ import annotations

import re

from ..utils.cache import DiskCache
from ..utils.http import HttpClient
from ._bundled import SP500_AND_POPULAR

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_POPULAR = [
    "NVDA", "GME", "AMC", "PLTR", "SOFI", "RIVN", "COIN", "MSTR", "SMCI", "ARM",
    "SNOW", "DDOG", "NET", "CRWD", "RBLX", "HOOD", "SOXL", "TQQQ", "NBIS", "RDDT",
    "MARA", "RIOT", "TSM", "ASML", "MU",
]


def sp500_symbols(refresh: bool = False) -> list[str]:
    """Live S&P 500 tickers from Wikipedia (cached 7 days); bundled on failure."""
    cache = DiskCache("universe", ttl=7 * 24 * 3600)
    if not refresh:
        hit = cache.get("sp500")
        if hit:
            return hit
    try:
        html = HttpClient(user_agent="Mozilla/5.0 (research; forecasting-lab)").get(WIKI_SP500).text
        syms = re.findall(r"<td><a[^>]*>([A-Z][A-Z.\-]{0,6})</a>", html)
        out, seen = [], set()
        for s in syms:
            if re.fullmatch(r"[A-Z][A-Z.\-]{0,5}", s) and s not in seen:
                seen.add(s)
                out.append(s)
        if len(out) >= 400:  # sanity: the table parsed
            cache.set("sp500", out)
            return out
    except Exception:  # pragma: no cover - network dependent
        pass
    return [s for s in SP500_AND_POPULAR if s not in _POPULAR]  # bundled S&P slice


def equity_universe(refresh: bool = False) -> list[str]:
    """The full tracked equity list: S&P 500 ∪ popular names. Always 500+."""
    base = sp500_symbols(refresh=refresh)
    out, seen = [], set()
    for s in [*base, *_POPULAR, *SP500_AND_POPULAR]:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out
