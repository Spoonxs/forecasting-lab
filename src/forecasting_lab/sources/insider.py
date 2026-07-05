"""Insider cluster-buys + Reg-SHO daily short volume (MASTER_PLAN V10).

Two free positioning feeds, both literature-grounded (the endpoints and the
freshness caveats mirror the OpenInsider-MCP catalog, MIT; code is our own):

- **Form-4 insider cluster buys** — multiple *distinct* insiders buying the same
  name inside a short window is the strongest-evidenced insider signal (single
  buys are noise; clusters have literature behind them). Trades come from the
  openinsider.com screener (free, T+2-ish freshness); the cluster logic is a
  pure function so it tests offline.
- **Reg-SHO daily short-volume ratio** — FINRA's daily short-sale volume files
  (pipe-delimited, one file per trading day). Short volume / total volume is a
  *daily* pressure gauge that complements the bi-monthly short-interest stock.

Both connectors degrade honestly (None on any failure), stamp their payloads
with ``pipeline.freshness`` fetch times, and file dated facts into the shared
``TidyStore`` so velocity features can accrue history. SEC fails-to-deliver
(FTD) zips are deliberately NOT wired yet — free but twice-monthly with a
multi-week publication lag; noted here rather than half-built.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as _date
from datetime import datetime, timezone

from ..pipeline.freshness import stamp
from ..utils.http import HttpClient
from .store import TidyStore

REGSHO_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{yyyymmdd}.txt"
OPENINSIDER_URL = "http://openinsider.com/screener"


# ------------------------------------------------------------------- Reg-SHO


def parse_regsho(text: str) -> dict[str, float] | None:
    """Parse a FINRA daily short-volume file into ``ticker -> short-vol ratio``.

    Format: ``Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market``.
    Ratios are clamped to [0, 1]; rows that don't parse are skipped; an empty
    or headerless payload returns None (degrade, don't guess).
    """
    out: dict[str, float] = {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or "|" not in lines[0]:
        return None
    for line in lines[1:]:  # first line is the header
        parts = line.split("|")
        if len(parts) < 5:
            continue
        try:
            short_vol = float(parts[2])
            total_vol = float(parts[4])
        except ValueError:
            continue
        if total_vol <= 0:
            continue
        out[parts[1].upper()] = max(0.0, min(1.0, short_vol / total_vol))
    return out or None


def short_volume_ratios(
    on: _date,
    http: HttpClient | None = None,
    now: datetime | None = None,
) -> dict | None:
    """One day's short-volume ratios, freshness-stamped — or None if unreachable."""
    url = REGSHO_URL.format(yyyymmdd=on.strftime("%Y%m%d"))
    try:
        text = (http or HttpClient()).get_text(url)
    except Exception:  # noqa: BLE001 - optional signal, never fatal
        return None
    ratios = parse_regsho(text) if text else None
    if ratios is None:
        return None
    fetched = now or datetime.now(timezone.utc)  # I/O boundary: stamping a fetch
    return stamp({"as_of": on.isoformat(), "ratios": ratios}, fetched_at=fetched)


def record_short_volume(payload: dict, store: TidyStore | None = None) -> int:
    """File a fetched day's ratios into the tidy store as dated facts."""
    store = store or TidyStore()
    store.record(payload["as_of"], "short_volume_ratio", payload["ratios"])
    return len(payload["ratios"])


# ------------------------------------------------------------- cluster buys


@dataclass(frozen=True)
class InsiderTrade:
    ticker: str
    insider: str
    trade_date: str  # ISO
    side: str  # "buy" | "sell"
    value_usd: float | None = None


@dataclass(frozen=True)
class ClusterBuy:
    ticker: str
    n_insiders: int
    first_date: str
    last_date: str
    total_value_usd: float


def cluster_buys(
    trades: list[InsiderTrade],
    *,
    window_days: int = 14,
    min_insiders: int = 3,
) -> list[ClusterBuy]:
    """Distinct-insider buy clusters per ticker within a rolling window.

    The distinctness requirement is the point: one insider buying three times is
    conviction from one person; three insiders buying the same fortnight is the
    cluster the literature scores. Sells never count toward a cluster.
    """
    out: list[ClusterBuy] = []
    buys = [t for t in trades if t.side == "buy"]
    by_ticker: dict[str, list[InsiderTrade]] = {}
    for t in buys:
        by_ticker.setdefault(t.ticker.upper(), []).append(t)
    for ticker, rows in sorted(by_ticker.items()):
        rows = sorted(rows, key=lambda t: t.trade_date)
        dates = [_date.fromisoformat(t.trade_date) for t in rows]
        best: ClusterBuy | None = None
        for i in range(len(rows)):
            in_window = [
                rows[j]
                for j in range(i, len(rows))
                if (dates[j] - dates[i]).days <= window_days
            ]
            insiders = {t.insider for t in in_window}
            if len(insiders) >= min_insiders:
                cand = ClusterBuy(
                    ticker=ticker,
                    n_insiders=len(insiders),
                    first_date=in_window[0].trade_date,
                    last_date=in_window[-1].trade_date,
                    total_value_usd=float(sum(t.value_usd or 0.0 for t in in_window)),
                )
                if best is None or cand.n_insiders > best.n_insiders:
                    best = cand
        if best is not None:
            out.append(best)
    return out


_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def parse_openinsider(html: str) -> list[InsiderTrade]:
    """Defensive parse of the openinsider screener table. [] when unrecognisable."""
    trades: list[InsiderTrade] = []
    for row in _ROW.findall(html):
        cells = [_TAG.sub("", c).replace("&nbsp;", " ").strip() for c in _CELL.findall(row)]
        if len(cells) < 9:
            continue
        # layout: X, filing date, trade date, ticker, insider, title, type, price, qty, ...
        trade_date, ticker, insider, ttype = cells[2][:10], cells[3], cells[4], cells[6]
        if not re.match(r"\d{4}-\d{2}-\d{2}", trade_date) or not ticker:
            continue
        side = "buy" if "p - purchase" in ttype.lower() else (
            "sell" if "s - sale" in ttype.lower() else ""
        )
        if not side:
            continue
        value = None
        for cell in cells[7:]:
            m = re.search(r"[-+]?\$([\d,]+)", cell)
            if m and "$" in cell and "," in cell:
                value = float(m.group(1).replace(",", ""))
        trades.append(InsiderTrade(ticker.upper(), insider, trade_date, side, value))
    return trades


def insider_trades(
    ticker: str | None = None,
    http: HttpClient | None = None,
) -> list[InsiderTrade]:
    """Recent insider trades from the openinsider screener; [] when blocked."""
    params = {"s": ticker.upper()} if ticker else {}
    try:
        html = (http or HttpClient()).get_text(OPENINSIDER_URL, params=params)
    except Exception:  # noqa: BLE001 - optional signal, never fatal
        return []
    return parse_openinsider(html or "")


def record_cluster_buys(
    clusters: list[ClusterBuy],
    on: str,
    store: TidyStore | None = None,
) -> int:
    """File today's cluster-buy insider counts as dated facts."""
    if not clusters:
        return 0
    store = store or TidyStore()
    store.record(on, "insider_cluster_buys", {c.ticker: float(c.n_insiders) for c in clusters})
    return len(clusters)
