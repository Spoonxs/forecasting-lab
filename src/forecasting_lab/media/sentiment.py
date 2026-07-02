"""Lightweight finance sentiment — tone, not just mention count.

A small, transparent lexicon (Loughran-McDonald flavour: finance-specific, not
generic) scores headline/title tone in [-1, 1]. It's deliberately simple and
deterministic so it's testable and needs no API. For a stronger signal, swap in
an LLM judge with a *frozen* prompt — but validate any sentiment feature against
forward returns with the purged CV in ``ml/`` before trusting it. Tone is a weak
proxy; the number only matters if it predicts.
"""

from __future__ import annotations

import re

POSITIVE = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies", "jump",
    "jumps", "gain", "gains", "upgrade", "upgraded", "record", "growth", "bullish",
    "breakout", "outperform", "tops", "strong", "rebound", "boom", "profit", "wins",
    "approval", "approved", "raises", "raised", "beat estimates", "all-time high",
    "soaring", "rockets", "rocket", "moon", "squeeze", "pops", "spikes",
}
NEGATIVE = {
    "miss", "misses", "plunge", "plunges", "crash", "crashes", "drop", "drops",
    "downgrade", "downgraded", "cut", "cuts", "fall", "falls", "bearish", "slump",
    "lawsuit", "probe", "warning", "warns", "weak", "layoffs", "halt", "halted",
    "fraud", "bankruptcy", "tumble", "tumbles", "sink", "sinks", "plummet",
    "plummets", "selloff", "sell-off", "loss", "losses", "recall", "delay", "sinking",
}

_WORD = re.compile(r"[a-z][a-z'\-]+")


def score_text(text: str) -> float:
    """Sentiment of one string in [-1, 1]. 0 when no lexicon words appear."""
    low = text.lower()
    pos = sum(1 for w in POSITIVE if re.search(rf"\b{re.escape(w)}\b", low))
    neg = sum(1 for w in NEGATIVE if re.search(rf"\b{re.escape(w)}\b", low))
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def score_texts(texts: list[str]) -> float:
    """Mean sentiment over texts that carry any tone (0 if none do)."""
    scores = [s for s in (score_text(t) for t in texts) if s != 0.0]
    return sum(scores) / len(scores) if scores else 0.0
