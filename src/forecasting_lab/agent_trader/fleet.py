"""P3 — the parallel paper fleet, scored for multiple testing.

Running K strategy variants in parallel paper accounts is the right instinct and the
hidden trap: crown the best of K and you've promoted the *luckiest*, not the best. So
the fleet is scored with the lab's honesty core — **deflated Sharpe** (discounts a
variant's Sharpe for having tried K) and **PBO/CSCV** (probability the in-sample winner
is overfit). A variant is "promotable" only if its edge survives that penalty; with K
random variants, none do (pinned in tests). This is the single thing separating an
honest tournament from a lucky-winner generator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..eval.deflated import deflated_sharpe_across, pbo_cscv, sharpe_ratio


def score_fleet(returns_by_variant: dict[str, list[float]], as_of: str) -> dict:
    """Rank K variants by deflated Sharpe + report the fleet PBO. Deterministic, dated."""
    nonempty = {k: v for k, v in returns_by_variant.items() if v}
    deflated = deflated_sharpe_across(nonempty)
    rows = []
    for name, r in nonempty.items():
        arr = np.asarray(r, dtype=float)
        eq = float(np.prod(1.0 + arr))
        rows.append({
            "variant": name,
            "total_return": round(eq - 1.0, 4),
            "sharpe": round(float(sharpe_ratio(arr)), 3),
            "deflated_sharpe": round(float(deflated.get(name, 0.0)), 3),
        })
    frame = pd.DataFrame(nonempty)
    pbo = pbo_cscv(frame.to_numpy(), n_splits=10) if frame.shape[0] >= 20 and frame.shape[1] >= 2 else 0.0
    rows.sort(key=lambda x: x["deflated_sharpe"], reverse=True)
    return {"as_of": as_of, "rows": rows, "pbo": round(float(pbo), 3), "n_variants": len(nonempty)}


def promotable_variants(fleet: dict, min_deflated: float = 1.0, max_pbo: float = 0.2) -> list[str]:
    """Which variants survive the multiple-testing penalty (empty is the common, honest answer)."""
    if fleet.get("pbo", 1.0) >= max_pbo:
        return []  # the winner is likely overfit -> promote nothing
    return [r["variant"] for r in fleet.get("rows", []) if r["deflated_sharpe"] > min_deflated]


def fleet_verdict(fleet: dict) -> str:
    survivors = promotable_variants(fleet)
    if survivors:
        return f"{len(survivors)} variant(s) survive the K={fleet['n_variants']} penalty: {', '.join(survivors)}."
    return (f"No variant survives the multiple-testing penalty across K={fleet.get('n_variants', 0)} "
            f"(PBO {fleet.get('pbo', 0):.0%}). Stay on paper — this is the correct, honest answer.")


def fleet_report(seed: int = 0, k: int = 20, n_bars: int = 252, skilled: bool = False,
                 as_of: str = "synthetic") -> dict:
    """A deterministic synthetic fleet: K noise variants (+ optionally one real edge)."""
    rng = np.random.default_rng(seed)
    returns: dict[str, list[float]] = {}
    for i in range(k):
        returns[f"v{i:02d}"] = [round(float(x), 5) for x in rng.normal(0.0, 0.01, n_bars)]
    if skilled:
        returns["v_skilled"] = [round(float(x), 5) for x in rng.normal(0.0016, 0.008, n_bars)]
    return score_fleet(returns, as_of=as_of)
