"""Options-chain connector + a gamma-concentration proxy.

The second half of the GameStop shape is a **gamma squeeze**: heavy call open
interest bunched at strikes just above spot on short-dated options forces dealers
to buy the underlying as it rises. This connector pulls the chain from Yahoo's
options endpoint and reduces it to one honest number — the share of near-term
call open interest sitting in strikes within a band just above spot. Higher =
more dry tinder.

Degrades honestly: any network/parse failure returns ``None`` (no chain, no
number), so the squeeze feature simply doesn't get a gamma leg rather than
inventing one.
"""

from __future__ import annotations

from ..utils.http import HttpClient

OPTIONS_URL = "https://query1.finance.yahoo.com/v7/finance/options/{symbol}"


class OptionsClient:
    """Fetch an options chain and summarise its near-spot call gamma concentration."""

    def __init__(self, http: HttpClient | None = None):
        self.http = http or HttpClient(user_agent="Mozilla/5.0 (research; forecasting-lab)")

    def chain(self, symbol: str) -> dict | None:
        try:
            data = self.http.get_json(OPTIONS_URL.format(symbol=symbol.upper()))
        except Exception:  # noqa: BLE001 - optional signal
            return None
        result = (data.get("optionChain", {}).get("result") or [None])[0]
        return result

    def gamma_concentration(self, symbol: str, band: float = 0.10) -> float | None:
        """Share of nearest-expiry call open interest at strikes in (spot, spot·(1+band)]."""
        result = self.chain(symbol)
        if not result:
            return None
        spot = (result.get("quote") or {}).get("regularMarketPrice")
        options = result.get("options") or []
        if not spot or not options:
            return None
        calls = options[0].get("calls") or []
        total_oi = 0.0
        near_oi = 0.0
        for c in calls:
            oi = c.get("openInterest") or 0
            strike = c.get("strike")
            if not strike:
                continue
            total_oi += oi
            if spot < strike <= spot * (1.0 + band):
                near_oi += oi
        if total_oi <= 0:
            return 0.0
        return round(near_oi / total_oi, 4)


def gamma_concentration(symbol: str, http: HttpClient | None = None) -> float | None:
    """One-shot: near-spot call-gamma concentration for a symbol, or None."""
    return OptionsClient(http=http).gamma_concentration(symbol)
