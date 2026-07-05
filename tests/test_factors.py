"""V6 — the factor/residual layer (MASTER_PLAN §3).

Properties pinned: exact zero-sum constraints (KKT), robust winsorize behaviour,
the as-of contract (mutating the FUTURE changes nothing), residual momentum
beating raw momentum OOS on planted alpha, noise pinning ~0, and honest offline
degradation of the R2 metadata reader. No golden numbers, no in-sample gate —
acceptance is purged-CV rank IC only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecasting_lab.ml.factors import (
    constrained_lstsq,
    factor_residuals,
    mad_winsorize,
    mad_winsorize_zscore,
    openfactor_r2_metadata,
    residual_momentum,
    residual_momentum_skill_report,
    weighted_lstsq,
    zero_sum_constraint,
)


def test_constrained_lstsq_satisfies_the_constraint_exactly():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 4))
    y = rng.normal(size=200)
    w = rng.uniform(0.5, 2.0, 200)
    c = np.array([[0.0, 0.0, 1.0, 1.0]])  # last two coefficients sum to zero
    beta = constrained_lstsq(x, y, w, c)
    assert abs(beta[2] + beta[3]) < 1e-9
    # with no constraints it IS the WLS solution
    free = constrained_lstsq(x, y, w, np.empty((0, 0)))
    assert np.allclose(free, weighted_lstsq(x, y, w))


def test_mad_winsorize_caps_outliers_and_keeps_inliers():
    v = np.array([0.1, -0.2, 0.05, 0.0, 100.0])  # one absurd outlier
    out = mad_winsorize(v, k=5.0)
    assert out[-1] < 100.0  # clamped
    assert np.allclose(out[:4], v[:4])  # inliers untouched
    flat = mad_winsorize(np.ones(5))  # zero MAD must not divide by zero
    assert np.allclose(flat, 1.0)

    panel = pd.DataFrame({"date": [0] * 5, "x": v})
    z = mad_winsorize_zscore(panel, "x", date_col="date")["x_rz"]
    assert abs(float(z.mean())) < 1e-9 and abs(float(z.std(ddof=0)) - 1.0) < 0.35


def test_zero_sum_constraint_row_weights_by_cap():
    x_frame = pd.DataFrame({"const": [1.0, 1.0], "sec_a": [1.0, 0.0], "sec_b": [0.0, 1.0]})
    row = zero_sum_constraint(x_frame, ["sec_a", "sec_b"], np.array([3.0, 1.0]))
    assert row[0] == 0.0
    assert row[1] == pytest.approx(0.75) and row[2] == pytest.approx(0.25)


def test_residual_features_are_as_of_future_changes_nothing():
    """The leak test: mutate every row after date T — features at date T are identical."""
    rng = np.random.default_rng(3)
    rows = [
        {"date": t, "ticker": i, "ret": rng.normal(0, 0.01), "beta_exposure": 1.0 + 0.1 * i}
        for t in range(60)
        for i in range(10)
    ]
    panel = pd.DataFrame(rows)

    def features(p: pd.DataFrame) -> pd.Series:
        p = mad_winsorize_zscore(p, "beta_exposure", date_col="date")
        p = factor_residuals(p, ["beta_exposure_rz"], ret_col="ret", date_col="date")
        p = residual_momentum(p, window=10)
        return p.set_index(["date", "ticker"])["resid_mom"]

    base = features(panel)
    tampered = panel.copy()
    tampered.loc[tampered["date"] > 40, "ret"] = 9.9  # rewrite the future
    after = features(tampered)
    t40 = base.xs(40, level="date")
    assert np.allclose(t40.dropna(), after.xs(40, level="date").dropna())


def test_residual_momentum_beats_raw_oos_and_noise_pins_zero():
    seeds = (0, 1, 2)
    sig = [residual_momentum_skill_report(seed=s, alpha_strength=1.0) for s in seeds]
    nul = [residual_momentum_skill_report(seed=s, alpha_strength=0.0) for s in seeds]
    res = float(np.mean([r["oos_rank_ic_residual"] for r in sig]))
    raw = float(np.mean([r["oos_rank_ic_raw"] for r in sig]))
    assert res > 0.10, f"planted alpha not recovered: {res}"
    assert res > raw + 0.01, f"residual ranking no better than raw: {res} vs {raw}"
    null_res = float(np.mean([r["oos_rank_ic_residual"] for r in nul]))
    assert abs(null_res) < 0.05, f"noise manufactured skill: {null_res}"


def test_r2_metadata_degrades_honestly():
    def broken(url):
        raise OSError("offline")

    assert openfactor_r2_metadata(fetcher=broken) is None
    assert openfactor_r2_metadata(fetcher=lambda u: {"nonsense": 1}) is None
    good = {"latest": "2026-06-25", "universe": "openfactor-us1000"}
    assert openfactor_r2_metadata(fetcher=lambda u: good) == good
