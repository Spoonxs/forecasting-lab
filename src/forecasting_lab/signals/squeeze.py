"""Squeeze-setup composite — the GameStop shape, done honestly.

Two things have to be true at once for a short squeeze: a **standing condition**
(high short interest as a % of float AND a high days-to-cover, so there's fuel)
and an **ignition** (a volume/gap spike, so it's lighting). Either alone is a
perpetually-shorted dud or a normal pop. The score is the *product* — it only
fires when both legs are present — and is monotone in short interest.

Short-interest / days-to-cover come from free bi-monthly FINRA data (a Phase-2
source); until that feed is wired the composite degrades to zero, honestly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def squeeze_setup(si_pct_float: float, days_to_cover: float, rel_volume: float, gap: float,
                  *, si_hi: float = 0.20, dtc_hi: float = 5.0, vol_hi: float = 3.0,
                  gap_hi: float = 0.06) -> float:
    """A [0, 1] squeeze score: standing fuel × ignition. 0 unless *both* are present."""
    standing = _clip01(si_pct_float / si_hi) * _clip01(days_to_cover / dtc_hi)
    ignition = _clip01(max((rel_volume - 1.0) / (vol_hi - 1.0), gap / gap_hi))
    return round(standing * ignition, 4)


def squeeze_setup_enriched(
    si_pct_float: float, days_to_cover: float, rel_volume: float, gap: float,
    *, short_vol_ratio: float | None = None, cluster_buy_insiders: float | None = None,
    svr_hi: float = 0.6, cluster_hi: float = 5.0, **kwargs,
) -> float:
    """The squeeze score with the V10 feeds folded in — honest degradation built in.

    ``short_vol_ratio`` (Reg-SHO daily short volume / total) is read as a
    *deviation from market-normal* (~0.45): unusually heavy daily shorting
    raises the score, unusually light shorting lowers it. An insider cluster
    buy is a confirming ignition (insiders stepping in against a heavy short)
    and only ever adds. Both default to None and change NOTHING when absent —
    the enriched score then equals the base :func:`squeeze_setup` exactly.
    """
    base = squeeze_setup(si_pct_float, days_to_cover, rel_volume, gap, **kwargs)
    if base == 0.0:
        return 0.0  # both original legs still required — enrichment never invents a setup
    boost = 1.0
    if short_vol_ratio is not None:
        svr_mid = 0.45  # market-typical daily short-volume share
        dev = max(-1.0, min(1.0, (float(short_vol_ratio) - svr_mid) / (svr_hi - svr_mid)))
        boost *= 1.0 + 0.4 * dev
    if cluster_buy_insiders is not None:
        boost *= 1.0 + 0.3 * _clip01(cluster_buy_insiders / cluster_hi)
    return round(min(1.0, max(0.0, base * boost)), 4)


def squeeze_skill_report(seed: int = 0, n: int = 5000, k_true: float = 0.6, k_model: float = 0.55) -> dict:
    """OOS Brier-skill of the setup score for predicting a forward squeeze vs. base rate."""
    rng = np.random.default_rng(seed)
    si = rng.uniform(0.0, 0.40, n)
    dtc = rng.uniform(0.0, 10.0, n)
    rel = rng.uniform(0.6, 5.0, n)
    gap = rng.uniform(-0.04, 0.10, n)
    score = np.array([squeeze_setup(si[i], dtc[i], rel[i], max(gap[i], 0.0)) for i in range(n)])
    p_squeeze = np.clip(0.08 + k_true * score, 0.0, 0.95)  # base ~8%, rising with the setup
    y = (rng.uniform(size=n) < p_squeeze).astype(float)
    df = pd.DataFrame({
        "period": (np.arange(n) // max(1, n // 20)).astype(int),
        "prob": np.clip(0.08 + k_model * score, 0.0, 0.95),  # a plausible fixed map, not the oracle
        "y": y,
        "ref": float(y.mean()),
    })
    from ..eval.skill import walk_forward_skill
    skill = walk_forward_skill(df, prob_col="prob", label_col="y", ref_col="ref", time_col="period")
    return {"feature": "squeeze setup", "n": n, "brier_skill_vs_baseline": round(skill, 4),
            "baseline": "base rate (climatology)"}


def enriched_squeeze_skill_report(seed: int = 0, n: int = 5000, k_true: float = 0.6,
                                  k_svr: float = 0.35) -> dict:
    """OOS skill of the enriched score vs the base score on a world where the
    Reg-SHO short-volume ratio genuinely carries extra squeeze information
    (``k_svr>0``). With ``k_svr=0`` the extra feed is noise and the enrichment
    must NOT help (pinned in tests)."""
    rng = np.random.default_rng(seed)
    si = rng.uniform(0.0, 0.40, n)
    dtc = rng.uniform(0.0, 10.0, n)
    rel = rng.uniform(0.6, 5.0, n)
    gap = np.maximum(rng.uniform(-0.04, 0.10, n), 0.0)
    svr = rng.uniform(0.2, 0.8, n)
    base_score = np.array([squeeze_setup(si[i], dtc[i], rel[i], gap[i]) for i in range(n)])
    enr_score = np.array([
        squeeze_setup_enriched(si[i], dtc[i], rel[i], gap[i], short_vol_ratio=svr[i], svr_hi=0.75)
        for i in range(n)
    ])
    p_squeeze = np.clip(0.08 + k_true * base_score * (1.0 + k_svr * (svr - 0.45) / 0.3), 0.0, 0.95)
    y = (rng.uniform(size=n) < p_squeeze).astype(float)
    period = (np.arange(n) // max(1, n // 20)).astype(int)
    from ..eval.skill import walk_forward_skill

    def _skill(score: np.ndarray) -> float:
        df = pd.DataFrame({
            "period": period,
            "prob": np.clip(0.08 + 0.55 * score, 0.0, 0.95),
            "y": y,
            "ref": float(y.mean()),
        })
        return walk_forward_skill(df, prob_col="prob", label_col="y", ref_col="ref", time_col="period")

    return {
        "feature": "squeeze setup (enriched: Reg-SHO short volume)",
        "n": n,
        "brier_skill_base": round(_skill(base_score), 4),
        "brier_skill_enriched": round(_skill(enr_score), 4),
        "baseline": "base rate (climatology)",
    }
