"""FINRA short-interest connector — the fuel gauge for the squeeze feature.

Short interest as a % of float and days-to-cover are the best-evidenced *standing*
conditions for a squeeze (`signals/squeeze`). FINRA publishes consolidated short
interest bi-monthly; the official query API needs OAuth and is typically blocked
on a dev box, so this connector **degrades honestly** — a network/parse failure
returns ``None`` (the squeeze feature then stays dormant rather than fabricating a
number). It works unchanged wherever the feed is reachable.

Field names vary across FINRA's payload shapes, so parsing is defensive: it reads
the first row and tries the common key spellings, and computes days-to-cover from
raw short shares ÷ average daily volume when the field isn't given directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..utils.http import HttpClient

# Consolidated short interest (bi-monthly). Reachable only where FINRA API access
# is configured; degrades to None otherwise.
FINRA_URL = "https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest"


@dataclass(frozen=True)
class ShortInterest:
    ticker: str
    short_pct_float: float | None
    days_to_cover: float | None
    as_of: str | None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class ShortInterestClient:
    """Fetch short interest for a ticker; ``None`` when the feed is unavailable."""

    def __init__(self, http: HttpClient | None = None, url: str = FINRA_URL):
        self.http = http or HttpClient()
        self.url = url

    def fetch(self, ticker: str) -> ShortInterest | None:
        try:
            data = self.http.get_json(self.url, params={"symbol": ticker.upper()})
        except Exception:  # noqa: BLE001 - short interest is an optional signal, never fatal
            return None
        return self.parse(ticker, data)

    @staticmethod
    def parse(ticker: str, data) -> ShortInterest | None:
        rows = data if isinstance(data, list) else (data.get("rows") or data.get("data") or [])
        if not rows:
            return None
        r = rows[0]
        pct = _num(r.get("shortPercentFloat") or r.get("short_pct_float") or r.get("shortInterestPctFloat"))
        dtc = _num(r.get("daysToCover") or r.get("days_to_cover") or r.get("shortInterestRatio"))
        if dtc is None:
            short_shares = _num(r.get("currentShortPositionQuantity") or r.get("shortInterest"))
            adv = _num(r.get("averageDailyVolumeQuantity") or r.get("avgDailyVolume"))
            if short_shares is not None and adv:
                dtc = short_shares / adv
        if pct is None:
            short_shares = _num(r.get("currentShortPositionQuantity") or r.get("shortInterest"))
            float_shares = _num(r.get("floatShares") or r.get("publicFloat"))
            if short_shares is not None and float_shares:
                pct = short_shares / float_shares
        if pct is None and dtc is None:
            return None
        as_of = r.get("settlementDate") or r.get("as_of") or r.get("date")
        return ShortInterest(ticker.upper(), pct, dtc, as_of)


def short_interest(ticker: str, http: HttpClient | None = None) -> ShortInterest | None:
    """One-shot convenience: short interest for a ticker, or None if unavailable."""
    return ShortInterestClient(http=http).fetch(ticker)
