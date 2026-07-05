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

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..eval.deflated import (
    deflated_sharpe_across,
    pbo_cscv,
    probabilistic_sharpe_ratio,
    sharpe_ratio,
)


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


def promotable_variants(fleet: dict, min_deflated: float = 0.95, max_pbo: float = 0.2) -> list[str]:
    """Which variants survive the multiple-testing penalty (empty is the common, honest answer).

    ``deflated_sharpe`` here is the DSR *probability* (P[true Sharpe beats the
    expected max of K trials], in [0, 1]) — so the bar is a confidence level.
    (The original default of 1.0 was unreachable on a probability: the promote
    branch could never open. Found by the V5 tests, fixed to 0.95.)
    """
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
    return score_fleet(synthetic_fleet_returns(seed=seed, k=k, n_bars=n_bars, skilled=skilled),
                       as_of=as_of)


def synthetic_fleet_returns(seed: int = 0, k: int = 20, n_bars: int = 252,
                            skilled: bool = False, common_noise: float = 0.0) -> dict[str, list[float]]:
    """The fleet generator, exposed: K noise variants, optional real edge, optional
    shared factor (``common_noise`` > 0 makes the variants correlated — a crowd)."""
    rng = np.random.default_rng(seed)
    shared = rng.normal(0.0, 0.01, n_bars)
    returns: dict[str, list[float]] = {}
    for i in range(k):
        own = rng.normal(0.0, 0.01, n_bars)
        mix = common_noise * shared + np.sqrt(max(0.0, 1.0 - common_noise**2)) * own
        returns[f"v{i:02d}"] = [round(float(x), 5) for x in mix]
    if skilled:
        returns["v_skilled"] = [round(float(x), 5) for x in rng.normal(0.0016, 0.008, n_bars)]
    return returns


# ------------------------------------------------- V5: fleet-level FDR + default


@dataclass(frozen=True)
class HoldBenchmark:
    """The arena's explicit default: nothing survived, so the stated allocation is
    100% benchmark — a decision object, never an empty dict."""

    benchmark: str = "SPY"
    weight: float = 1.0
    reason: str = ""


@dataclass(frozen=True)
class PromoteSurvivors:
    """The rare branch: these variants survived deflated-Sharpe, PBO AND fleet FDR."""

    survivors: tuple[str, ...]
    fdr: float


def fleet_pvalues(returns_by_variant: dict[str, list[float]]) -> dict[str, float]:
    """Per-variant p-value for H0 "true Sharpe <= 0": p = 1 - PSR.

    The PSR already accounts for sample length, skew, and kurtosis; the FDR step
    below handles the *fleet-level* multiplicity on top.
    """
    return {
        name: 1.0 - probabilistic_sharpe_ratio(np.asarray(r, dtype=float))
        for name, r in returns_by_variant.items()
        if len(r) >= 3
    }


def benjamini_hochberg(pvalues: dict[str, float], fdr: float = 0.05) -> list[str]:
    """Names whose p-values pass the Benjamini-Hochberg step-up at rate ``fdr``.

    Testing 20 strategies at p<0.05 each promotes one by luck; BH controls the
    expected fraction of false promotions across the whole fleet instead.
    """
    if not pvalues:
        return []
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    cutoff = -1
    for rank, (_name, p) in enumerate(items, start=1):
        if p <= fdr * rank / m:
            cutoff = rank
    return [name for name, _p in items[:cutoff]] if cutoff > 0 else []


def fleet_correlation(returns_by_variant: dict[str, list[float]],
                      crowded_above: float = 0.5) -> dict:
    """Mean pairwise return correlation — the systemic-risk gauge. A fleet of
    "different" strategies that all share one bet is one strategy with extra steps."""
    frame = pd.DataFrame({k: v for k, v in returns_by_variant.items() if len(v) >= 3})
    if frame.shape[1] < 2:
        return {"mean_pairwise_corr": 0.0, "crowded": False, "n_variants": int(frame.shape[1])}
    corr = frame.corr().to_numpy()
    upper = corr[np.triu_indices_from(corr, k=1)]
    mean_corr = float(np.nanmean(upper)) if upper.size else 0.0
    return {
        "mean_pairwise_corr": round(mean_corr, 4),
        "crowded": bool(mean_corr > crowded_above),
        "n_variants": int(frame.shape[1]),
    }


def fleet_decision(
    returns_by_variant: dict[str, list[float]],
    as_of: str,
    *,
    fdr: float = 0.05,
    min_deflated: float = 0.95,
    max_pbo: float = 0.2,
    benchmark: str = "SPY",
) -> HoldBenchmark | PromoteSurvivors:
    """The whole gate in one call: deflated Sharpe + PBO + fleet-level FDR.

    A variant must survive ALL THREE to be promoted; when none do, the answer is
    an explicit :class:`HoldBenchmark` — the honest default allocation.
    """
    fleet = score_fleet(returns_by_variant, as_of=as_of)
    per_strategy = set(promotable_variants(fleet, min_deflated=min_deflated, max_pbo=max_pbo))
    fdr_pass = set(benjamini_hochberg(fleet_pvalues(returns_by_variant), fdr=fdr))
    survivors = tuple(sorted(per_strategy & fdr_pass))
    if survivors:
        return PromoteSurvivors(survivors=survivors, fdr=fdr)
    return HoldBenchmark(
        benchmark=benchmark,
        weight=1.0,
        reason=(
            f"0 of {fleet['n_variants']} variants survive deflated-Sharpe>{min_deflated}, "
            f"PBO<{max_pbo:.0%} and fleet FDR<={fdr:.0%} — allocation is 100% {benchmark}."
        ),
    )
