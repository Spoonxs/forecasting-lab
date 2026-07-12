"""13F holders — quarterly institutional positions, STALE BY DESIGN (P7 §B).

A 13F-HR shows a manager's positions AS OF quarter-end, filed up to 45 days
later — so the freshest possible datum is already weeks old and the oldest is
~135 days. That makes this CONTEXT, never signal: it renders with its
staleness computed and stated, and nothing here ever enters a verdict.

Free path: the SEC submissions API (proper UA, fair-access policy) locates
each curated manager's newest 13F-HR; the information-table XML is parsed
with a dependency-light regex (top holdings by reported value). Issuer names
are best-effort matched to tickers via the instrument registry — an unmatched
issuer stays name-only, honestly. Blocked network → a stated skip.
"""

from __future__ import annotations

import re
from datetime import date

from ..utils.http import HttpClient

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}"

#: the curated manager list (name -> CIK). Small on purpose: famous books whose
#: quarterly moves are widely followed — context, not coverage.
MANAGERS: dict[str, str] = {
    "Berkshire Hathaway": "1067983",
    "Bridgewater Associates": "1350694",
    "Renaissance Technologies": "1037389",
    "Citadel Advisors": "1423053",
    "Pershing Square Capital": "1336528",
}
FILING_WINDOW_DAYS = 45  # 13F-HR is due within 45 days of quarter end


# ------------------------------------------------------------------ parsing
_INFO_RE = re.compile(r"<(?:\w+:)?infoTable>(.*?)</(?:\w+:)?infoTable>", re.S | re.I)


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<(?:\w+:)?{name}>\s*(.*?)\s*</(?:\w+:)?{name}>", block, re.S | re.I)
    return m.group(1).strip() if m else ""


def parse_13f_table(xml_text: str, top: int = 15) -> list[dict]:
    """Top holdings by reported value from an information-table XML. Values
    are as filed (13F reports THOUSANDS of dollars); malformed rows drop."""
    rows = []
    for block in _INFO_RE.findall(xml_text or ""):
        issuer = _tag(block, "nameOfIssuer")
        try:
            value = float(_tag(block, "value").replace(",", ""))
            shares = float(_tag(block, "sshPrnamt").replace(",", ""))
        except ValueError:
            continue
        if issuer:
            rows.append({"issuer": issuer, "cusip": _tag(block, "cusip"),
                         "value_kusd": value, "shares": shares})
    rows.sort(key=lambda r: -r["value_kusd"])
    return rows[:top]


def staleness(period: str, filed: str, today: str | date) -> dict:
    """The honest age statement every 13F datum must carry."""
    t = date.fromisoformat(str(today)[:10])
    p = date.fromisoformat(period[:10])
    f = date.fromisoformat(filed[:10])
    lag, age = (f - p).days, (t - p).days
    return {"period": period[:10], "filed": filed[:10],
            "filing_lag_days": lag, "age_days": age,
            "label": (f"positions as of {period[:10]}, filed {lag}d later — "
                      f"{age}d old today; context, not signal")}


_STOPWORDS = {"the", "of", "and"}
_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company",
             "ltd", "plc", "com", "new", "cl", "class", "a", "b", "c",
             "common", "stock", "capital", "ordinary", "shares", "shs"}


def _name_tokens(s: str) -> list[str]:
    """Corporate-name tokens with stopwords dropped and the legal/share-class
    suffix tail stripped: 'Bank of America Corporation Common Stock' and
    'BANK AMERICA CORP' both become ['bank', 'america']."""
    toks = [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in _STOPWORDS]
    while toks and toks[-1] in _SUFFIXES:
        toks.pop()
    return toks


def match_ticker(issuer: str, registry) -> str | None:
    """Best-effort issuer-name -> ticker: the normalized token lists must be
    EQUAL, and exactly one listed symbol may carry that name — anything
    ambiguous (share classes, similar names) stays None, never guessed."""
    want = _name_tokens(issuer)
    if not want or len("".join(want)) < 3:
        return None
    symbols: set[str] = set()
    for query in (" ".join(want), want[0]):
        for inst in registry.search(query, limit=25):
            if inst.kind in ("stock", "etf") and _name_tokens(inst.name) == want:
                symbols.add(inst.symbol)
        if symbols:
            break
    return symbols.pop() if len(symbols) == 1 else None


# ------------------------------------------------------------------ fetch
def latest_13f(cik: str, http: HttpClient | None = None, top: int = 15) -> dict | None:
    """The newest 13F-HR for one CIK: period, filed date, top holdings.
    None on any failure (the caller states the skip)."""
    if http is None:
        from .sec import _client

        http = _client()  # the proper-UA EDGAR client (fair-access policy)
    client = http
    subs = client.get_json(SUBMISSIONS_URL.format(cik=cik))
    recent = subs.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    idx = next((i for i, f in enumerate(forms) if f == "13F-HR"), None)
    if idx is None:
        return None
    accession = recent["accessionNumber"][idx].replace("-", "")
    filed = recent["filingDate"][idx]
    period = recent["reportDate"][idx]
    index = client.get_json(ARCHIVE_URL.format(cik=int(cik), accession=accession)
                            + "/index.json")
    xml_name = next((it["name"] for it in index.get("directory", {}).get("item", [])
                     if it["name"].lower().endswith(".xml")
                     and "primary_doc" not in it["name"].lower()), None)
    if not xml_name:
        return None
    xml_text = client.get_text(ARCHIVE_URL.format(cik=int(cik), accession=accession)
                               + f"/{xml_name}")
    holdings = parse_13f_table(xml_text, top=top)
    if not holdings:
        return None
    return {"cik": cik, "period": period, "filed": filed, "holdings": holdings}


def fetch_13f_digest(managers: dict[str, str] | None = None, *, top: int = 15,
                     on: date | None = None, http: HttpClient | None = None,
                     registry=None, store=None) -> dict:
    """Best-effort sweep of the curated managers. Every managed block carries
    its staleness; every failure is a stated skip. Matched tickers land in the
    TidyStore dated by the FILING date (never today)."""
    managers = managers or MANAGERS
    today = on or date.today()
    if registry is None:
        from .instruments import InstrumentRegistry

        registry = InstrumentRegistry()
    blocks, skips = [], []
    for name, cik in managers.items():
        try:
            filing = latest_13f(cik, http=http, top=top)
        except Exception as exc:  # noqa: BLE001 - blocked network is a skip, never a crash
            skips.append({"manager": name, "reason": f"{type(exc).__name__}: {exc}"[:160]})
            continue
        if not filing:
            skips.append({"manager": name, "reason": "no parseable 13F-HR found"})
            continue
        for h in filing["holdings"]:
            h["ticker"] = match_ticker(h["issuer"], registry)
        blocks.append({"manager": name,
                       "staleness": staleness(filing["period"], filing["filed"],
                                              today),
                       "holdings": filing["holdings"]})
        if store is not None:
            matched = {h["ticker"]: h["value_kusd"] for h in filing["holdings"]
                       if h.get("ticker")}
            if matched:
                store.record(filing["filed"][:10], f"13f_value_{cik}", matched)
    return {"as_of": today.isoformat(), "managers": blocks, "skips": skips}
