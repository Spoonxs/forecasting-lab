"""Probabilistic scoring metrics.

Everything here operates on a vector of predicted probabilities ``y_prob`` in
[0, 1] against binary outcomes ``y_true`` in {0, 1}. Lower is better for Brier
and log loss; the skill score is higher-is-better against a base-rate baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

ArrayLike = "np.ndarray | list[float] | pd.Series"


def _validate(y_true, y_prob) -> tuple[np.ndarray, np.ndarray]:
    yt = np.asarray(y_true, dtype=float).ravel()
    yp = np.asarray(y_prob, dtype=float).ravel()
    if yt.shape != yp.shape:
        raise ValueError(f"shape mismatch: y_true {yt.shape} vs y_prob {yp.shape}")
    if yt.size == 0:
        raise ValueError("empty input")
    if not np.all(np.isin(yt, (0.0, 1.0))):
        raise ValueError("y_true must be binary 0/1")
    if np.any(yp < 0) or np.any(yp > 1):
        raise ValueError("y_prob must lie in [0, 1]")
    return yt, yp


def brier_score(y_true, y_prob) -> float:
    """Mean squared error of the probability forecast (0 best, 1 worst)."""
    yt, yp = _validate(y_true, y_prob)
    return float(np.mean((yp - yt) ** 2))


def log_loss(y_true, y_prob, eps: float = 1e-15) -> float:
    """Binary cross-entropy with clipping to avoid infinities at 0/1."""
    yt, yp = _validate(y_true, y_prob)
    yp = np.clip(yp, eps, 1 - eps)
    return float(-np.mean(yt * np.log(yp) + (1 - yt) * np.log(1 - yp)))


def brier_skill_score(y_true, y_prob, base_rate: float | None = None) -> float:
    """Brier skill vs a constant base-rate forecast. >0 beats climatology."""
    yt, yp = _validate(y_true, y_prob)
    base = float(np.mean(yt)) if base_rate is None else float(base_rate)
    bs = float(np.mean((yp - yt) ** 2))
    bs_ref = float(np.mean((base - yt) ** 2))
    if bs_ref == 0:
        return 0.0
    return 1.0 - bs / bs_ref


def reliability_table(y_true, y_prob, n_bins: int = 10) -> pd.DataFrame:
    """Per-bin reliability: count, mean predicted prob, observed frequency.

    Bins are uniform over [0, 1]. Empty bins are kept (NaN means/freqs, count 0)
    so the table shape is stable across calls.
    """
    yt, yp = _validate(y_true, y_prob)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # rightmost edge inclusive so p == 1.0 lands in the last bin
    idx = np.clip(np.digitize(yp, edges[1:-1], right=False), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = idx == b
        count = int(mask.sum())
        rows.append(
            {
                "bin": b,
                "bin_low": edges[b],
                "bin_high": edges[b + 1],
                "count": count,
                "mean_pred": float(np.mean(yp[mask])) if count else np.nan,
                "frac_pos": float(np.mean(yt[mask])) if count else np.nan,
            }
        )
    return pd.DataFrame(rows)


def expected_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    """Count-weighted average gap between confidence and observed frequency."""
    table = reliability_table(y_true, y_prob, n_bins=n_bins)
    table = table[table["count"] > 0]
    if table.empty:
        return 0.0
    weights = table["count"] / table["count"].sum()
    return float(np.sum(weights * np.abs(table["mean_pred"] - table["frac_pos"])))


def maximum_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    """Worst-case bin gap between confidence and observed frequency."""
    table = reliability_table(y_true, y_prob, n_bins=n_bins)
    table = table[table["count"] > 0]
    if table.empty:
        return 0.0
    return float(np.max(np.abs(table["mean_pred"] - table["frac_pos"])))


@dataclass(frozen=True)
class BrierDecomposition:
    """Murphy's three-term decomposition: BS = reliability - resolution + uncertainty."""

    reliability: float  # lower is better (calibration error)
    resolution: float  # higher is better (how much forecasts vary with outcome)
    uncertainty: float  # base-rate variance, irreducible
    brier: float  # reliability - resolution + uncertainty

    def as_dict(self) -> dict[str, float]:
        return {
            "reliability": self.reliability,
            "resolution": self.resolution,
            "uncertainty": self.uncertainty,
            "brier": self.brier,
        }


def brier_decomposition(y_true, y_prob, n_bins: int = 10) -> BrierDecomposition:
    """Murphy (1973) decomposition of the Brier score over uniform bins."""
    yt, _ = _validate(y_true, y_prob)
    table = reliability_table(y_true, y_prob, n_bins=n_bins)
    n = yt.size
    o_bar = float(np.mean(yt))
    used = table[table["count"] > 0]
    reliability = float(np.sum(used["count"] * (used["mean_pred"] - used["frac_pos"]) ** 2) / n)
    resolution = float(np.sum(used["count"] * (used["frac_pos"] - o_bar) ** 2) / n)
    uncertainty = o_bar * (1.0 - o_bar)
    return BrierDecomposition(
        reliability=reliability,
        resolution=resolution,
        uncertainty=uncertainty,
        brier=reliability - resolution + uncertainty,
    )


def summary(y_true, y_prob, n_bins: int = 10) -> dict[str, float]:
    """A one-call scorecard. ``accuracy`` uses a 0.5 threshold and is reported
    only for context — calibration and Brier skill are the metrics that matter."""
    yt, yp = _validate(y_true, y_prob)
    base = float(np.mean(yt))
    return {
        "n": int(yt.size),
        "base_rate": base,
        "brier": brier_score(yt, yp),
        "log_loss": log_loss(yt, yp),
        "brier_skill_score": brier_skill_score(yt, yp),
        "ece": expected_calibration_error(yt, yp, n_bins=n_bins),
        "mce": maximum_calibration_error(yt, yp, n_bins=n_bins),
        "accuracy_at_0.5": float(np.mean((yp >= 0.5) == (yt == 1))),
        "sharpness": float(np.std(yp)),
    }
