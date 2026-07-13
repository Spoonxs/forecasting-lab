"""Fundamentals — SEC XBRL ``companyfacts``, point-in-time honest (P10-2).

Free and official: one JSON per registrant with every reported us-gaap fact.
The files are BIG (megabytes), so the connector is a ROLLING sweep: each
night it refreshes only the symbols whose reduced cache is stale (quarterly
data doesn't need daily pulls), extracts the few series the Financials tab
shows — revenue, net income, diluted EPS — and discards the raw payload.
EVERY datum carries its fiscal period AND the date it was FILED (the
point-in-time rule: nothing filed after ``as_of`` is kept, and the page
prints the filed date so staleness is on screen). NEVER a verdict input.
Blocked network or an unmapped ticker is a per-symbol stated skip.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..config import PATHS

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:0>10}.json"
#: tag preference per metric (issuers vary in which us-gaap tag they file)
METRIC_TAGS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "SalesRevenueNet"),
    "net_income": ("NetIncomeLoss",),
    "eps": ("EarningsPerShareDiluted", "EarningsPerShareBasic"),
}
ANNUAL_KEEP = 6      # FY periods shown
QUARTER_KEEP = 8     # quarterly periods kept (the tab may show fewer)
REFRESH_DAYS = 30    # a symbol's reduced cache is fresh this long (quarterly data)
MAX_FETCH_PER_RUN = 40   # the rolling window — polite to the fair-access policy
CIRCUIT_BREAK_AFTER = 6


def funda_dir(root: Path | str | None = None) -> Path:
    return Path(root) if root else (PATHS.data / "fundamentals")


# ---------------------------------------------------------------- extract
def _series(facts: dict, tags: tuple[str, ...], unit_keys: tuple[str, ...],
            as_of: date) -> list[dict]:
    """The dated series for one metric: dedup by (fiscal end, period type),
    keeping the LATEST filing at or before ``as_of`` — never anything filed
    after it (point-in-time)."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    rows: dict[tuple, dict] = {}
    for tag in tags:
        units = gaap.get(tag, {}).get("units", {})
        entries = next((units[k] for k in unit_keys if k in units), None)
        if not entries:
            continue
        for e in entries:
            filed, end, fp = e.get("filed"), e.get("end"), e.get("fp")
            form = e.get("form", "")
            if not (filed and end and e.get("val") is not None):
                continue
            if filed > as_of.isoformat():
                continue  # the point-in-time pin: not known yet
            if form not in ("10-K", "10-K/A", "10-Q", "10-Q/A", "20-F"):
                continue
            kind = "FY" if fp == "FY" else str(fp or "")
            start = e.get("start")
            if start:  # duration facts: a YTD span must never pose as a
                # quarter, nor a quarter as a fiscal year (Codex review)
                span = (date.fromisoformat(end) - date.fromisoformat(start)).days
                if kind == "FY" and span < 300:
                    continue
                if kind != "FY" and span > 100:
                    continue
            key = (end, kind)
            if key not in rows or filed > rows[key]["filed"]:
                rows[key] = {"end": end, "fp": kind, "fy": e.get("fy"),
                             "val": float(e["val"]), "filed": filed}
        if rows:
            break  # the first tag that yields data wins (no mixing)
    return sorted(rows.values(), key=lambda r: r["end"])


def extract_metrics(facts: dict, as_of: date) -> dict:
    """The reduced record the tab renders: {metric: {annual: [...], quarterly:
    [...]}} — every row carrying end/fp/val/filed. Empty dict when the filing
    has none of the tags (honest absence)."""
    out = {}
    for metric, tags in METRIC_TAGS.items():
        unit_keys = ("USD/shares",) if metric == "eps" else ("USD",)
        series = _series(facts, tags, unit_keys, as_of)
        annual = [r for r in series if r["fp"] == "FY"][-ANNUAL_KEEP:]
        quarterly = [r for r in series if r["fp"] != "FY"][-QUARTER_KEEP:]
        if annual or quarterly:
            out[metric] = {"annual": annual, "quarterly": quarterly}
    # ALWAYS stamp the record (Codex review): a fetched registrant with no
    # matching tags must render "no us-gaap series", never "not fetched yet"
    out["entity"] = facts.get("entityName", "")
    out["as_of"] = as_of.isoformat()
    return out


# ---------------------------------------------------------------- sweep
def fetch_fundamentals(symbols: list[str], *, as_of: date, http=None,
                       root: Path | str | None = None,
                       max_fetch: int = MAX_FETCH_PER_RUN) -> dict:
    """The rolling nightly sweep: refresh up to ``max_fetch`` stale symbols,
    extract, discard the raw. Returns the receipt {fetched, fresh, skips}."""
    if http is None:
        from .sec import _client

        http = _client()
    root = funda_dir(root)
    root.mkdir(parents=True, exist_ok=True)
    meta_path = root / "funda_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    try:
        from .sec import company_tickers

        ciks = company_tickers()
    except Exception as exc:  # noqa: BLE001 - no ticker map -> everything skips, stated
        return {"as_of": as_of.isoformat(), "fetched": 0, "fresh": 0,
                "skips": [{"symbol": "*", "reason": f"ticker map unavailable: {exc}"[:120]}]}

    receipt = {"as_of": as_of.isoformat(), "fetched": 0, "fresh": 0, "skips": []}
    consecutive = 0
    for sym in symbols:
        if receipt["fetched"] >= max_fetch:
            break  # the rolling window — the rest refresh on later nights
        if consecutive >= CIRCUIT_BREAK_AFTER:
            receipt["skips"].append({"symbol": "*", "reason": "circuit open — SEC unreachable"})
            break
        last = meta.get(sym, {}).get("fetched_at")
        try:
            cache_ok = load_fundamentals(sym, root) is not None  # Codex review:
            # a fresh meta entry over a missing/corrupt cache must refetch
            if (cache_ok and last
                    and (as_of - date.fromisoformat(last)).days < REFRESH_DAYS):
                receipt["fresh"] += 1
                continue
        except ValueError:
            pass
        cik = ciks.get(sym.upper())
        if cik is None:
            receipt["skips"].append({"symbol": sym, "reason": "no CIK mapping (ETF/fund or unlisted)"})
            continue
        try:
            facts = http.get_json(COMPANYFACTS_URL.format(cik=cik))
            reduced = extract_metrics(facts, as_of)
        except Exception as exc:  # noqa: BLE001 - per-symbol skip, never a crash
            receipt["skips"].append({"symbol": sym,
                                     "reason": f"{type(exc).__name__}: {exc}"[:120]})
            consecutive += 1
            continue
        consecutive = 0
        (root / f"{sym.upper()}.json").write_text(
            json.dumps(reduced, separators=(",", ":")), encoding="utf-8")
        meta[sym] = {"fetched_at": as_of.isoformat(), "cik": cik}
        receipt["fetched"] += 1
    meta_path.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")
    return receipt


def load_fundamentals(symbol: str, root: Path | str | None = None) -> dict | None:
    """The reduced record for one symbol; None when never fetched (honest)."""
    path = funda_dir(root) / f"{symbol.upper()}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
