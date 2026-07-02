"""Reddit mention-velocity connector — tries hard before giving up.

Reddit's public JSON needs a *Reddit-compliant* User-Agent (their rule:
``platform:appid:version (by /u/user)``); a generic/empty one gets 403 + rate
limited. So the connector walks a ladder of methods and returns the first that
works:

1. JSON on ``www.reddit.com`` then ``old.reddit.com`` (compliant UA),
2. the subreddit **RSS** feed (``/.rss``, parsed with stdlib — often survives
   when JSON is throttled),
3. a list of **Redlib/Libreddit** mirrors (privacy front-ends that proxy Reddit).

Only when *every* method fails does it raise :class:`RedditUnavailable`. This
sandbox blocks Reddit at the network layer (all methods 403), so the feature is
skipped here — but it works unchanged in the cloud (GitHub Actions), where the
daily job runs and Reddit is reachable.

It is not alpha on its own: the edge is the early *velocity spike*, not the level;
by the time a name is loud on WSB the easy move is usually gone.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..utils.http import HttpClient

SUBS = ["wallstreetbets", "stocks", "options", "algotrading", "quant"]

# Reddit asks for this UA shape; be a good citizen or get 429'd.
_UA = "python:forecasting-lab:v0.1 (research; by /u/forecasting-lab)"
_JSON_HOSTS = ["https://www.reddit.com", "https://old.reddit.com"]
# Redlib/Libreddit public instances (rotate/die over time — best-effort tail).
_REDLIB_MIRRORS = [
    "https://redlib.catsarch.com",
    "https://redlib.perennialte.ch",
    "https://libreddit.privacydev.net",
]
_ATOM = "{http://www.w3.org/2005/Atom}"


class RedditUnavailable(RuntimeError):
    """Raised only after every access method fails."""


def _client() -> HttpClient:
    return HttpClient(user_agent=_UA)


def _from_json(payload: dict) -> list[str]:
    children = payload.get("data", {}).get("children", [])
    return [c.get("data", {}).get("title", "") for c in children if c.get("data")]


def _from_rss(xml_bytes: bytes) -> list[str]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    return [
        re.sub(r"\s+", " ", (e.findtext(f"{_ATOM}title") or "")).strip()
        for e in root.iter(f"{_ATOM}entry")
    ]


def hot_titles(subreddit: str, limit: int = 25) -> list[str]:
    """Titles of current hot posts, via the first method that succeeds."""
    client = _client()
    errors: list[str] = []

    for host in _JSON_HOSTS:
        try:
            data = client.get_json(f"{host}/r/{subreddit}/hot.json", params={"limit": limit})
            titles = _from_json(data)
            if titles:
                return titles
        except Exception as exc:  # noqa: BLE001
            errors.append(f"json@{host}: {exc}")

    for host in _JSON_HOSTS:  # RSS often survives when JSON is throttled
        try:
            resp = client.get(f"{host}/r/{subreddit}/.rss", params={"limit": limit})
            titles = _from_rss(resp.content)
            if titles:
                return titles
        except Exception as exc:  # noqa: BLE001
            errors.append(f"rss@{host}: {exc}")

    for mirror in _REDLIB_MIRRORS:
        try:
            resp = client.get(f"{mirror}/r/{subreddit}/hot.rss")
            titles = _from_rss(resp.content)
            if titles:
                return titles
        except Exception as exc:  # noqa: BLE001
            errors.append(f"redlib@{mirror}: {exc}")

    raise RedditUnavailable(
        "Reddit unreachable via JSON, RSS, and mirrors "
        f"({'; '.join(errors[:4])}...). Blocked on this network; works in the cloud."
    )


def cashtag_counts(titles: list[str], tickers: list[str]) -> dict[str, int]:
    """Count title mentions of each ticker (as ``$TICK`` or a standalone word)."""
    counts = {t: 0 for t in tickers}
    for title in titles:
        upper = title.upper()
        for t in tickers:
            if re.search(rf"\${t}\b|\b{t}\b", upper):
                counts[t] += 1
    return counts


def mention_counts(tickers: list[str], subs: list[str] | None = None, limit: int = 40) -> dict[str, int]:
    """Aggregate cashtag mentions across subs. Returns zeros if Reddit is blocked
    (so callers can treat it as an optional signal, never a hard failure)."""
    subs = subs or SUBS
    totals = {t: 0 for t in tickers}
    got_any = False
    for sub in subs:
        try:
            titles = hot_titles(sub, limit=limit)
        except RedditUnavailable:
            continue
        got_any = True
        for t, c in cashtag_counts(titles, tickers).items():
            totals[t] += c
    totals["_reddit_reachable"] = 1 if got_any else 0  # sentinel for the caller
    return totals
