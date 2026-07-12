"""Congressional trades — best-effort, lag-stated, never a signal (P7 §C).

Members disclose trades up to 45 days after making them (STOCK Act), and the
free community mirrors of the official House/Senate disclosures are flaky by
nature — exactly the "best effort with staleness labels" the operator
approved. Every row carries BOTH dates and the computed disclosure lag; a
blocked or lapsed feed is a stated skip that lands in the health panel; and
nothing here ever enters a verdict. Context, not signal.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from ..utils.http import HttpClient

#: free community mirrors of the official clerk/EFD disclosures (best effort —
#: the sources are stated in the digest so a lapse is visible, never silent)
FEEDS = {
    "house": ("https://house-stock-watcher-data.s3-us-west-2.amazonaws.com"
              "/data/all_transactions.json"),
    "senate": ("https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com"
               "/aggregate/all_transactions.json"),
}
SOURCE_NOTE = ("community mirrors of the official House Clerk / Senate EFD "
               "disclosures — best effort; disclosed up to 45d after the trade")


def _parse_date(raw) -> str | None:
    """ISO or US-style dates -> ISO; anything else -> None (kept honest)."""
    s = str(raw or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_trades(raw_rows: list, chamber: str) -> list[dict]:
    """Normalize one chamber's mirror rows. Rows without a real ticker are
    dropped (the mirrors use '--' for non-equity assets); unparseable dates
    stay None with lag n/a — shown, never guessed."""
    out = []
    for r in raw_rows or []:
        ticker = str(r.get("ticker", "")).strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z.\-]{0,9}", ticker or ""):
            continue
        member = str(r.get("representative") or r.get("senator") or "").strip()
        if not member:
            continue
        tdate = _parse_date(r.get("transaction_date"))
        ddate = _parse_date(r.get("disclosure_date"))
        lag = ((date.fromisoformat(ddate) - date.fromisoformat(tdate)).days
               if tdate and ddate else None)
        out.append({
            "member": member, "chamber": chamber, "ticker": ticker,
            "transaction_date": tdate, "disclosed_date": ddate,
            "lag_days": lag,
            "type": str(r.get("type", "")).strip().lower(),
            "amount_range": str(r.get("amount", "")).strip(),
        })
    return out


def recent_trades(rows: list[dict], on: date, days: int = 90,
                  cap: int | None = 200) -> list[dict]:
    """The window the surfaces show: disclosed within ``days`` of ``on``
    (disclosure is the event the public can actually observe), newest first.
    Rows without a disclosed date can't be windowed — excluded here, honest.
    ``cap=None`` skips truncation (the digest caps AFTER merging chambers)."""
    keep = [r for r in rows if r["disclosed_date"]
            and 0 <= (on - date.fromisoformat(r["disclosed_date"])).days <= days]
    keep.sort(key=lambda r: r["disclosed_date"], reverse=True)
    return keep if cap is None else keep[:cap]


def fetch_congress_digest(on: date | None = None, *, days: int = 90,
                          http: HttpClient | None = None) -> dict:
    """Best-effort sweep of both chambers. Every failure is a stated skip;
    the digest names its sources and the structural lag."""
    today = on or date.today()
    client = http or HttpClient()
    trades, skips = [], []
    for chamber, url in FEEDS.items():
        try:
            rows = parse_trades(client.get_json(url), chamber)
        except Exception as exc:  # noqa: BLE001 - a lapsed mirror is a skip, not a crash
            skips.append({"chamber": chamber,
                          "reason": f"{type(exc).__name__}: {exc}"[:160]})
            continue
        if not rows:
            skips.append({"chamber": chamber, "reason": "feed returned no parseable trades"})
            continue
        # no per-chamber cap (Codex review): truncating before the merged sort
        # could drop newer House rows while older Senate rows survive
        trades += recent_trades(rows, today, days=days, cap=None)
    trades.sort(key=lambda r: r["disclosed_date"], reverse=True)
    return {"as_of": today.isoformat(), "source": SOURCE_NOTE,
            "window_days": days, "trades": trades[:400], "skips": skips}
