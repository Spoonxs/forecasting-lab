"""Favorite–longshot recalibration.

Prediction-market prices are biased: longshots (near 0) are systematically
overpriced and favorites (near 1) underpriced. Fitting the *realized* outcome
rate by price bucket yields a monotone map that corrects it — a free calibration
edge, provided it is fit only on **past resolved** markets and applied to new
ones (leak-free). On already-calibrated prices it converges to the identity and
manufactures nothing (pinned in tests).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .skill import walk_forward_skill


class FavoriteLongshotRecalibrator:
    """Map raw market probabilities to realized-rate-by-bucket, monotone."""

    def __init__(self, n_bins: int = 12, smoothing: float = 3.0):
        self.n_bins = n_bins
        self.smoothing = smoothing
        self.centers_: np.ndarray | None = None
        self.map_: np.ndarray | None = None

    def fit(self, probs, outcomes) -> FavoriteLongshotRecalibrator:
        p = np.asarray(probs, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        edges = np.linspace(0.0, 1.0, self.n_bins + 1)
        centers = 0.5 * (edges[:-1] + edges[1:])
        rate = centers.copy()
        idx = np.clip(np.digitize(p, edges[1:-1]), 0, self.n_bins - 1)
        for b in range(self.n_bins):
            m = idx == b
            if m.any():
                # realized rate, smoothed toward the bin center so sparse bins don't overfit
                rate[b] = (y[m].sum() + self.smoothing * centers[b]) / (m.sum() + self.smoothing)
        rate = np.maximum.accumulate(rate)  # enforce monotone non-decreasing (isotonic-lite)
        self.centers_ = centers
        self.map_ = rate
        return self

    def transform(self, probs):
        if self.map_ is None:
            raise RuntimeError("fit before transform")
        return np.interp(np.asarray(probs, dtype=float), self.centers_, self.map_)

    def fit_transform(self, probs, outcomes):
        return self.fit(probs, outcomes).transform(probs)


def default_fair_value(market_prob: float, stretch: float = 1.12) -> float:
    """A mild, literature-shaped favorite-longshot correction for use before a fit
    on resolved markets exists: nudge the price a little more extreme (longshots
    down, favorites up). Monotone, identity at 0.5, clamped to [0.01, 0.99]."""
    p = float(market_prob)
    return float(min(0.99, max(0.01, 0.5 + (p - 0.5) * stretch)))


def _synthetic(seed: int, n: int, bias: float):
    """Market prices with (bias>1) or without (bias==1) favorite-longshot bias.

    ``bias>1`` makes the *true* probability more extreme than the price — longshots
    overpriced, favorites underpriced — the documented real-world distortion.
    """
    rng = np.random.default_rng(seed)
    market = rng.uniform(0.03, 0.97, n)
    true_p = np.clip(0.5 + (market - 0.5) * bias, 0.01, 0.99)
    y = (rng.uniform(size=n) < true_p).astype(float)
    period = (np.arange(n) // max(1, n // 20)).astype(int)
    return pd.DataFrame({"period": period, "market": market, "y": y})


def recalibration_skill_report(seed: int = 0, n: int = 6000, bias: float = 1.3, n_bins: int = 12) -> dict:
    """OOS Brier-skill of the recalibrated price vs. the raw market price."""
    df = _synthetic(seed, n, bias)

    def fit_transform(train):
        r = FavoriteLongshotRecalibrator(n_bins=n_bins).fit(train["market"], train["y"])
        return r.transform

    skill = walk_forward_skill(
        df, prob_col="market", label_col="y", ref_col="market", time_col="period",
        fit_transform=fit_transform,
    )
    return {"feature": "favorite-longshot recalibration", "n": n, "bias": bias,
            "brier_skill_vs_market": round(skill, 4), "baseline": "raw market price"}


def risk_awareness_report(seed: int = 0, n: int = 6000, effect: float = 1.0) -> dict:
    """The V8 hypothesis test: does a rec's stated risk-acknowledgement predict
    outcomes NEGATIVELY ("legible risks are priced in" — the 547-recs finding)?

    Synthetic recs: each has a base probability and a risk-acknowledgement flag.
    With ``effect>0`` the world makes risk-aware recs land BELOW their stated
    probability; with ``effect=0`` the flag is pure noise. Per fold, the shift is
    fit on the train block only and applied OOS — the honest answer is skill > 0
    exactly when the effect is planted, ~0 when it isn't (pinned in tests).
    """
    rng = np.random.default_rng(seed)
    base_p = rng.uniform(0.25, 0.75, n)
    risk_ack = (rng.uniform(size=n) < 0.5).astype(float)
    true_p = np.clip(base_p - effect * 0.12 * risk_ack, 0.01, 0.99)
    y = (rng.uniform(size=n) < true_p).astype(float)
    period = (np.arange(n) // max(1, n // 20)).astype(int)
    df = pd.DataFrame({"period": period, "prob": base_p, "risk_ack": risk_ack, "y": y})

    # walk_forward_skill's fit_transform only sees the prob column, so run the
    # purged split by hand — the fitted shift needs the risk_ack column OOS too.
    from ..ml.cv import PurgedWalkForwardCV

    cv = PurgedWalkForwardCV(n_splits=4, horizon=1)
    ys, model, ref = [], [], []
    times = df["period"].to_numpy()
    fitted_shift = 0.0
    for train_idx, test_idx in cv.split(times):
        train, test = df.iloc[train_idx], df.iloc[test_idx]
        ack = train["risk_ack"].to_numpy(dtype=float)
        resid = train["y"].to_numpy(dtype=float) - train["prob"].to_numpy(dtype=float)
        shift = float(resid[ack == 1].mean()) if (ack == 1).any() else 0.0
        fitted_shift = shift
        adjusted = np.clip(
            test["prob"].to_numpy(dtype=float)
            + shift * test["risk_ack"].to_numpy(dtype=float),
            0.01, 0.99,
        )
        ys.append(test["y"].to_numpy(dtype=float))
        model.append(adjusted)
        ref.append(test["prob"].to_numpy(dtype=float))
    from .skill import brier_skill_vs

    skill = brier_skill_vs(np.concatenate(ys), np.concatenate(model), np.concatenate(ref))
    return {
        "hypothesis": "risk-awareness predicts outcomes negatively (legible risks priced in)",
        "n": n,
        "effect": effect,
        "fitted_shift": round(fitted_shift, 4),  # negative when the effect is real
        "brier_skill_vs_base_prob": round(float(skill), 4),
    }
