"""P4 — the promotion gate for a fleet variant (paper → live-eligible).

Thin adapter over the lab's `promotion.evaluate_promotion`: it assembles a variant's
out-of-sample metrics (deflated Sharpe + fleet PBO from `fleet`, real forward marks from
the paper study, risk numbers from the execution limits) and runs the six-gate check. A
variant becomes eligible for real capital only if ALL gates clear on real marks — and even
then a human signs the version. The under-proven winner of a random fleet is rejected
(pinned). Autonomy note: the deterministic strategy engine executes; nothing in the agent/
decision layer places an order.
"""

from __future__ import annotations

from ..promotion import PromotionRecord, evaluate_promotion


def gate_fleet_top(fleet: dict, forward: dict, risk: dict, as_of: str) -> PromotionRecord | None:
    """Run the fleet's top-ranked variant through the promotion gate."""
    rows = fleet.get("rows") or []
    if not rows:
        return None
    top = rows[0]
    metrics = {
        "deflated_sharpe": top.get("deflated_sharpe", 0.0),
        "pbo": fleet.get("pbo", 1.0),
        "live_marks": forward.get("live_marks", 0),
        "brier_skill_vs_market": forward.get("brier_skill_vs_market", -1.0),
        "net_return": top.get("total_return", -1.0),
        "turnover": forward.get("turnover", 1e9),
        "kelly_fraction": risk.get("kelly_fraction", 1.0),
        "max_name_weight": risk.get("max_name_weight", 1.0),
        "max_drawdown": forward.get("max_drawdown", 1.0),
        "gross_exposure": risk.get("gross_exposure", 1e9),
    }
    return evaluate_promotion(top["variant"], metrics, as_of)
