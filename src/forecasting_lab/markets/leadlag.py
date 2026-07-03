"""Cross-venue lead–lag — which market discovers the price first.

When the same question trades on two venues, one usually moves first (the leader)
and the other catches up (the laggard). The lead is measurable: cross-correlate
the two venues' *changes* at a range of offsets; the offset with the strongest
correlation says who leads and by how much. The tradeable read is convergence —
the laggard tends to move toward the leader's current price.

Leak-free: everything uses only past changes; the convergence call for the next
step is formed from prices already observed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def lead_lag(a, b, max_lag: int = 5) -> dict:
    """Which of two aligned series leads. ``lead_lag>0`` => ``a`` leads ``b``."""
    da = np.diff(np.asarray(a, dtype=float))
    db = np.diff(np.asarray(b, dtype=float))
    best_lag, best_corr = 0, 0.0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x, z = da[: len(da) - lag], db[lag:]
        else:
            x, z = da[-lag:], db[: len(db) + lag]
        if len(x) > 3 and np.std(x) > 0 and np.std(z) > 0:
            c = float(np.corrcoef(x, z)[0, 1])
            if abs(c) > abs(best_corr):
                best_lag, best_corr = lag, c
    leader = "a" if best_lag > 0 else ("b" if best_lag < 0 else None)
    return {"lead_lag": best_lag, "leader": leader, "corr": round(best_corr, 3)}


def convergence_prob(leader_price: float, laggard_price: float, k: float = 4.0) -> float:
    """P(laggard moves up next) — >0.5 when the laggard sits below the leader."""
    gap = float(leader_price) - float(laggard_price)
    return 1.0 / (1.0 + np.exp(-k * gap))


def leadlag_skill_report(seed: int = 0, n_markets: int = 60, n_steps: int = 140,
                         lag: int = 1, noise: float = 0.03, follow: bool = True) -> dict:
    """OOS Brier-skill of the convergence call (laggard→leader) vs. the 0.5 base rate.

    ``follow=False`` makes the laggard an *independent* walk (the null case): with no
    real lead–lag, the convergence call has nothing to exploit and skill collapses to
    ~0 — the leakage guard."""
    rng = np.random.default_rng(seed)
    lag = max(1, lag)
    rows: list[dict] = []
    for _m in range(n_markets):
        steps = np.clip(np.cumsum(rng.normal(0, 0.04, n_steps)) + rng.uniform(0.2, 0.8), 0.02, 0.98)
        leader = steps
        laggard = np.empty_like(leader)
        if follow:
            laggard[:lag] = leader[0]
            laggard[lag:] = leader[:-lag] + rng.normal(0, noise, n_steps - lag)  # follows the leader, delayed
        else:
            laggard = np.clip(np.cumsum(rng.normal(0, 0.04, n_steps)) + rng.uniform(0.2, 0.8), 0.02, 0.98)
        laggard = np.clip(laggard, 0.02, 0.98)
        for t in range(lag, n_steps - 1):
            prob_up = convergence_prob(leader[t], laggard[t])
            moved_up = 1.0 if laggard[t + 1] > laggard[t] else 0.0
            rows.append({"period": t, "prob": prob_up, "y": moved_up, "ref": 0.5})
    df = pd.DataFrame(rows)
    from ..eval.skill import walk_forward_skill
    skill = walk_forward_skill(df, prob_col="prob", label_col="y", ref_col="ref", time_col="period")
    return {"feature": "cross-venue lead-lag", "n": len(df),
            "brier_skill_vs_baseline": round(skill, 4), "baseline": "0.5 (coin flip)"}
