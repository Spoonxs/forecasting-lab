"""Quant-research ingestion: the arXiv sweep ``research-sources.md`` planned.

Fetches recent papers from the q-fin/stat.ML categories via the arXiv API (free,
no key, Atom XML), scores each abstract against the lab's research interests,
and files a ranked digest into ``inputs/``. The point is a filtered feed you
actually read — 3-10 relevant papers a week — not a raw dump.

Scoring is transparent keyword relevance, not an LLM: every match is listed, so
you can see exactly why a paper ranked. Extend ``TOPIC_WEIGHTS`` as interests
shift. Bulk history belongs to the data dumps (see the brief); this pipeline is
the recent tail.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..pipeline.base import Pipeline
from ..pipeline.digest import render_digest
from ..utils.http import HttpClient

ARXIV_API = "https://export.arxiv.org/api/query"

DEFAULT_CATEGORIES = ["q-fin.TR", "q-fin.PM", "q-fin.ST", "q-fin.CP", "q-fin.RM", "stat.ML"]

# What this lab cares about. Weight = how strongly a hit pulls a paper up.
TOPIC_WEIGHTS = {
    "calibration": 3.0,
    "brier": 3.0,
    "prediction market": 3.0,
    "forecast": 2.0,
    "elo": 3.0,
    "backtest": 2.5,
    "overfitting": 2.5,
    "walk-forward": 3.0,
    "cross-validation": 2.0,
    "leakage": 3.0,
    "survivorship": 3.0,
    "momentum": 2.0,
    "short interest": 2.5,
    "squeeze": 2.0,
    "sentiment": 1.5,
    "limit order": 1.5,
    "market making": 1.5,
    "sharpe": 1.5,
    "portfolio": 1.0,
    "gradient boost": 2.0,
    "transformer": 1.0,
    "reinforcement learning": 1.0,
}

_ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivFetcher:
    """Swappable arXiv access — tests inject a stub returning canned Atom XML."""

    def __init__(self, http: HttpClient | None = None):
        self.http = http or HttpClient()

    def recent(self, categories: list[str], max_results: int = 60) -> bytes:
        query = " OR ".join(f"cat:{c}" for c in categories)
        resp = self.http.get(
            ARXIV_API,
            params={
                "search_query": query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": max_results,
            },
        )
        return resp.content


def parse_atom(xml_bytes: bytes) -> list[dict]:
    """Atom feed -> [{title, summary, link, published, categories}]."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    papers = []
    for entry in root.iter(f"{_ATOM}entry"):
        title = re.sub(r"\s+", " ", entry.findtext(f"{_ATOM}title") or "").strip()
        summary = re.sub(r"\s+", " ", entry.findtext(f"{_ATOM}summary") or "").strip()
        link = entry.findtext(f"{_ATOM}id") or ""
        published = (entry.findtext(f"{_ATOM}published") or "")[:10]
        cats = [
            c.get("term", "")
            for c in entry.iter(f"{_ATOM}category")
            if c.get("term")
        ]
        if title:
            papers.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published,
                    "categories": cats,
                }
            )
    return papers


def score_paper(paper: dict, weights: dict[str, float] | None = None) -> tuple[float, list[str]]:
    """Keyword-relevance score + the matched terms (so ranking is explainable).

    Terms match on word boundaries — "elo" must not fire inside "developed".
    """
    weights = weights or TOPIC_WEIGHTS
    text = f"{paper['title']} {paper['summary']}".lower()
    score, hits = 0.0, []
    for term, w in weights.items():
        if re.search(rf"\b{re.escape(term)}\b", text):
            score += w
            hits.append(term)
    return score, hits


class ResearchPipeline(Pipeline):
    """arXiv recent papers -> relevance rank -> dated digest into inputs/."""

    slug = "research-digest"

    def __init__(
        self,
        fetcher: ArxivFetcher | None = None,
        *,
        categories: list[str] | None = None,
        max_results: int = 60,
        top: int = 10,
        min_score: float = 1.0,
    ):
        self.fetcher = fetcher or ArxivFetcher()
        self.categories = categories or DEFAULT_CATEGORIES
        self.max_results = max_results
        self.top = top
        self.min_score = min_score

    def fetch(self) -> list[dict]:
        return parse_atom(self.fetcher.recent(self.categories, self.max_results))

    def process(self, papers: list[dict]) -> str:
        ranked = []
        for p in papers:
            score, hits = score_paper(p)
            if score >= self.min_score:
                ranked.append((score, hits, p))
        ranked.sort(key=lambda t: t[0], reverse=True)

        if not ranked:
            body = "_no relevant papers in this sweep — widen TOPIC_WEIGHTS or categories_"
        else:
            parts = []
            for score, hits, p in ranked[: self.top]:
                cats = ", ".join(p["categories"][:3])
                parts.append(
                    f"- **{p['title']}** ({p['published']}, {cats})\n"
                    f"  relevance {score:.1f} via [{', '.join(hits)}] — {p['link']}\n"
                    f"  {p['summary'][:320]}{'...' if len(p['summary']) > 320 else ''}"
                )
            body = "\n".join(parts)

        return render_digest(
            "Quant Research Digest",
            {
                f"Top papers ({len(ranked)} relevant of {len(papers)} fetched)": body,
                "Categories swept": ", ".join(self.categories),
            },
            disclaimer=(
                "Keyword-ranked recent arXiv tail; read the paper before believing the abstract. "
                "Bulk corpora (Stack Exchange dumps, SSRN) live in research-sources.md."
            ),
        )
