"""The source catalog: everything the lab tracks, and how many.

``source_count()`` is the honest tally behind "500+ sources tracked
simultaneously": the equity universe dominates, plus market venues, sports
leagues, macro series, and research feeds. ``flab-sources`` prints the table.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fred import MACRO_SERIES
from .universe import equity_universe


@dataclass(frozen=True)
class SourceGroup:
    name: str
    kind: str
    reachable: str  # "live", "blocked here", "manual"
    count: int
    note: str


# arXiv categories swept by flab-research (kept in sync with pipeline.research).
_ARXIV_CATS = ["q-fin.TR", "q-fin.PM", "q-fin.ST", "q-fin.CP", "q-fin.RM", "stat.ML"]
# Reddit subs the squeeze signal would use where reachable.
_REDDIT_SUBS = ["wallstreetbets", "stocks", "options", "algotrading", "quant"]


def source_groups(refresh: bool = False) -> list[SourceGroup]:
    equities = equity_universe(refresh=refresh)
    try:
        from ..media.watchlist import channel_count

        n_voices = channel_count()
    except Exception:  # pragma: no cover
        n_voices = 0
    return [
        SourceGroup("Equities", "prices+news", "live", len(equities),
                    "S&P 500 + growth/meme; Yahoo charts + Google News each"),
        SourceGroup("Prediction markets", "prices", "live", 2, "Kalshi + Polymarket venues"),
        SourceGroup("Macro series (FRED)", "timeseries", "live", len(MACRO_SERIES),
                    "yields, CPI, unemployment, VIX, S&P"),
        SourceGroup("arXiv categories", "research", "live", len(_ARXIV_CATS),
                    "q-fin + stat.ML, relevance-ranked"),
        SourceGroup("SEC EDGAR", "filings", "live", 1, "full-text + ticker map (proper UA)"),
        SourceGroup("Media voices", "video+news", "live", n_voices,
                    "YouTube (RSS/yt-dlp) + Google News; key figures & outlets"),
        SourceGroup("Sports leagues", "results", "manual", 3, "ATP/WTA tennis, NBA (synthetic here)"),
        SourceGroup("Soccer leagues", "results", "live", len(_soccer_leagues()),
                    "football-data.co.uk divisions (EPL, Bundesliga, La Liga, Serie A, ...)"),
        SourceGroup("Options chains (gamma)", "options", "live", 1,
                    "Yahoo options endpoint; near-spot call-gamma concentration"),
        SourceGroup("Short interest (FINRA)", "positioning", "blocked here", 1,
                    "consolidated short interest %float + days-to-cover; needs API access"),
        SourceGroup("X / Twitter voices", "social", "blocked here", _x_voice_count(),
                    "curated finance handles; Nitter pull best-effort, list is the asset"),
        SourceGroup("Reddit subs", "sentiment", "blocked here", len(_REDDIT_SUBS),
                    "supported when reachable; 403 on this network"),
    ]


def _soccer_leagues() -> dict:
    from ..sports.soccer import SOCCER_LEAGUES

    return SOCCER_LEAGUES


def _x_voice_count() -> int:
    try:
        from .x_voices import voice_count

        return voice_count()
    except Exception:  # pragma: no cover
        return 0


# A static view for tests / quick reference (equity count from the bundled list).
SOURCES = source_groups


def source_count(refresh: bool = False) -> int:
    return sum(g.count for g in source_groups(refresh=refresh))


def source_table(refresh: bool = False):
    import pandas as pd

    rows = [
        {"group": g.name, "kind": g.kind, "reachable": g.reachable, "count": g.count, "note": g.note}
        for g in source_groups(refresh=refresh)
    ]
    return pd.DataFrame(rows)
