"""X / Twitter finance-voice universe.

The people who are *early* — the "Hasan Piker of investing" the brief keeps asking
for — mostly post on X, not YouTube. This is the tracked handle list (macro,
markets, quant, options-flow, crypto, journalists), which feeds the attention
signal and seeds the Phase-3 "who's ahead of the curve" track-record scoring.

Fetching a public timeline without the paid API is the hard part: this tries
Nitter RSS mirrors and returns the first that works, degrading to an **empty
list** when all are blocked (as they are on this network and increasingly in the
cloud). The *list itself* is the durable asset; the live pull is best-effort. A
voice earns weight only by its track record vs. the market, never by follower
count (`PLAN.md` Phase 3).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..utils.http import HttpClient

# Curated finance voices by lens. Handles are public; inclusion is not endorsement.
X_VOICES: dict[str, list[str]] = {
    "macro": ["Nouriel", "LynAldenContact", "biancoresearch", "elerianm", "GregDaco",
              "SoberLook", "M_McDonough", "RobinBrooksIIF", "jsblokland"],
    "markets": ["Mayhem4Markets", "sentimentrader", "hmeisler", "allstarcharts",
                "Callum_Thomas", "MacroCharts", "OphirGottlieb", "verniman"],
    "quant": ["macrocephalopod", "quantian1", "choffstein", "dailydirtnap",
              "therobotjames", "quantivity", "MrOptionsBets"],
    "options_flow": ["unusual_whales", "SpotGamma", "TradeGenius", "Barchart",
                     "cheddarflow", "FlowAlgo"],
    "equities": ["StockMKTNewz", "TrungTPhan", "TESLAcharts", "GerberKawasaki",
                 "modestproposal1", "WallStCynic", "LadyFOHF"],
    "crypto": ["woonomic", "CryptoHayes", "zhusu", "raoulGMI", "APompliano", "DocumentingBTC"],
    "journalists": ["business", "markets", "SquawkCNBC", "TheStalwart",
                    "tracyalloway", "elonmusk", "carlquintanilla"],
}

_NITTER_MIRRORS = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]
_RSS_TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL)


def all_handles() -> list[str]:
    """Every tracked handle, de-duplicated, order-stable."""
    seen: dict[str, None] = {}
    for handles in X_VOICES.values():
        for h in handles:
            seen.setdefault(h.lstrip("@"), None)
    return list(seen)


def voice_count() -> int:
    return len(all_handles())


def _from_rss(xml_bytes: bytes) -> list[str]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    out = []
    for item in root.iter("item"):
        t = item.findtext("title")
        if t:
            out.append(re.sub(r"\s+", " ", t).strip())
    return out


def recent_posts(handle: str, http: HttpClient | None = None, limit: int = 20) -> list[str]:
    """Recent post texts for a handle via the first working Nitter mirror.

    Returns ``[]`` when every mirror is blocked — honest degradation, never raises.
    """
    client = http or HttpClient(user_agent="Mozilla/5.0 (research; forecasting-lab)")
    handle = handle.lstrip("@")
    for mirror in _NITTER_MIRRORS:
        try:
            resp = client.get(f"{mirror}/{handle}/rss")
            posts = _from_rss(resp.content)
            if posts:
                return posts[:limit]
        except Exception:  # noqa: BLE001 - try the next mirror, then give up quietly
            continue
    return []
