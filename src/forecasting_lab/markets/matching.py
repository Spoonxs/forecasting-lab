"""Match markets across venues by title similarity.

Matching Kalshi and Polymarket listings of the same real-world event is the hard
part of the divergence screen: titles differ ("Will the Fed cut rates in March?"
vs "Fed rate cut by March 2026"), and a wrong match produces a fake "arb".

Approach: normalise each title to a token set (lowercase, strip punctuation and
filler words, keep numbers and years — they carry the resolution criteria), then
score pairs by Jaccard similarity and match greedily one-to-one, best pair first.

Two matched titles are a *candidate*, never a confirmed pair: always verify the
two contracts resolve on identical criteria (source, deadline, threshold) before
trading the gap. The default threshold is deliberately conservative.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

# Filler that carries no resolution information. Numbers, months, and names stay.
_STOPWORDS = {
    "will", "the", "a", "an", "in", "by", "of", "to", "be", "on", "at", "for",
    "is", "are", "does", "do", "and", "or", "than", "before", "after", "this",
    "there", "it", "as", "any", "how", "many", "what", "who", "which", "yes",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_title(title: str) -> frozenset[str]:
    """Reduce a market title to its informative token set.

    ``"Will the Fed cut rates in March 2026?"`` -> ``{fed, cut, rates, march, 2026}``.
    Percent signs are kept attached to their number ("60%" -> "60pct") so
    threshold markets ("turnout > 60%") keep their defining token.
    """
    text = title.lower().replace("%", "pct ")
    tokens = _WORD_RE.findall(text)
    return frozenset(t for t in tokens if t not in _STOPWORDS)


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity of normalised token sets, in [0, 1]."""
    ta, tb = normalize_title(a), normalize_title(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


@dataclass(frozen=True)
class Match:
    left: str
    right: str
    similarity: float


def match_titles(
    left_titles,
    right_titles,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Greedy one-to-one matching of two title lists, best pairs first.

    Returns a DataFrame ``[left, right, similarity]`` sorted by similarity
    descending, containing only pairs at or above ``threshold``. Each title is
    used at most once, so a single Kalshi market can't "match" three Polymarket
    markets and triple-count a divergence.
    """
    left_titles = list(left_titles)
    right_titles = list(right_titles)
    scored: list[Match] = []
    for lt in left_titles:
        for rt in right_titles:
            sim = title_similarity(lt, rt)
            if sim >= threshold:
                scored.append(Match(lt, rt, sim))
    scored.sort(key=lambda m: m.similarity, reverse=True)

    used_left: set[str] = set()
    used_right: set[str] = set()
    rows = []
    for m in scored:
        if m.left in used_left or m.right in used_right:
            continue
        used_left.add(m.left)
        used_right.add(m.right)
        rows.append({"left": m.left, "right": m.right, "similarity": m.similarity})
    return pd.DataFrame(rows, columns=["left", "right", "similarity"])


def match_markets(
    kalshi_markets: pd.DataFrame,
    poly_markets: pd.DataFrame,
    *,
    kalshi_title_col: str = "title",
    poly_title_col: str = "question",
    kalshi_price_col: str = "kalshi_yes",
    poly_price_col: str = "poly_yes",
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Match two per-venue market frames and return the screener-ready table.

    Input frames need a title column and a YES-probability column each. Output
    columns: ``event`` (the Kalshi title), ``kalshi_yes``, ``poly_yes``,
    ``poly_event``, ``similarity`` — feed straight into
    :func:`forecasting_lab.markets.divergence.find_divergences`.
    """
    # Real feeds contain duplicate titles (re-listed markets, repeated event
    # names); keep the first of each so the title -> price mapping is unique.
    kalshi_markets = kalshi_markets.drop_duplicates(subset=kalshi_title_col, keep="first")
    poly_markets = poly_markets.drop_duplicates(subset=poly_title_col, keep="first")
    pairs = match_titles(
        kalshi_markets[kalshi_title_col], poly_markets[poly_title_col], threshold=threshold
    )
    if pairs.empty:
        return pd.DataFrame(
            columns=["event", "kalshi_yes", "poly_yes", "poly_event", "similarity"]
        )
    k = kalshi_markets.set_index(kalshi_title_col)[kalshi_price_col]
    p = poly_markets.set_index(poly_title_col)[poly_price_col]
    out = pd.DataFrame(
        {
            "event": pairs["left"],
            "kalshi_yes": pairs["left"].map(k).astype(float),
            "poly_yes": pairs["right"].map(p).astype(float),
            "poly_event": pairs["right"],
            "similarity": pairs["similarity"],
        }
    )
    return out.dropna(subset=["kalshi_yes", "poly_yes"]).reset_index(drop=True)
