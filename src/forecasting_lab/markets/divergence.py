"""Cross-venue divergence screener.

If the same event trades at YES=0.40 on Kalshi and YES=0.45 on Polymarket, buying
YES on the cheaper venue and the complementary NO on the other locks a payoff of
$1 per contract pair for a cost below $1 — the gap, minus fees, is the edge:

    net_edge = |poly_yes - kalshi_yes|
               - kalshi_taker_fee(kalshi_yes)      # the Kalshi leg (fee is
               - polymarket_fee                     #   symmetric around 0.5)

Matching markets to the same real-world event is the hard part (fuzzy titles,
different resolution criteria) and is left to the caller; this module scores an
already-matched table. Always sanity-check that the two contracts truly resolve
on identical criteria before believing an "arb".
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..backtest.costs import kalshi_taker_fee, polymarket_fee


@dataclass(frozen=True)
class Divergence:
    event: str
    kalshi_yes: float
    poly_yes: float
    gross_edge: float  # |poly_yes - kalshi_yes|
    fee: float
    net_edge: float  # gross_edge - fees; positive means a real after-cost gap
    direction: str  # "buy_kalshi" (Kalshi underprices YES) or "buy_poly"

    @property
    def flagged(self) -> bool:
        return self.net_edge > 0


def score_divergence(
    event: str,
    kalshi_yes: float,
    poly_yes: float,
    contracts: float = 1.0,
    poly_fee_bps: float = 0.0,
) -> Divergence:
    """Score a single matched market pair."""
    gross = poly_yes - kalshi_yes
    fee = kalshi_taker_fee(kalshi_yes, contracts) + polymarket_fee(contracts, poly_fee_bps)
    net = abs(gross) * contracts - fee
    direction = "buy_kalshi" if gross > 0 else "buy_poly"
    return Divergence(
        event=event,
        kalshi_yes=kalshi_yes,
        poly_yes=poly_yes,
        gross_edge=abs(gross),
        fee=fee,
        net_edge=net,
        direction=direction,
    )


def find_divergences(
    matched: pd.DataFrame,
    *,
    event_col: str = "event",
    kalshi_col: str = "kalshi_yes",
    poly_col: str = "poly_yes",
    contracts: float = 1.0,
    threshold: float = 0.0,
    poly_fee_bps: float = 0.0,
) -> pd.DataFrame:
    """Score every matched row and return those whose net edge clears ``threshold``.

    Sorted by ``net_edge`` descending. Columns: event, kalshi_yes, poly_yes,
    gross_edge, fee, net_edge, direction.
    """
    rows = []
    for r in matched.itertuples(index=False):
        d = score_divergence(
            event=getattr(r, event_col),
            kalshi_yes=float(getattr(r, kalshi_col)),
            poly_yes=float(getattr(r, poly_col)),
            contracts=contracts,
            poly_fee_bps=poly_fee_bps,
        )
        rows.append(
            {
                "event": d.event,
                "kalshi_yes": d.kalshi_yes,
                "poly_yes": d.poly_yes,
                "gross_edge": d.gross_edge,
                "fee": d.fee,
                "net_edge": d.net_edge,
                "direction": d.direction,
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out[out["net_edge"] > threshold]
    return out.sort_values("net_edge", ascending=False).reset_index(drop=True)
