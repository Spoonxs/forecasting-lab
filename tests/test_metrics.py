import numpy as np
import pytest

from forecasting_lab.eval import (
    brier_decomposition,
    brier_score,
    brier_skill_score,
    expected_calibration_error,
    log_loss,
    reliability_table,
    summary,
)


def test_brier_bounds():
    assert brier_score([1, 0, 1], [1.0, 0.0, 1.0]) == 0.0  # perfect
    assert brier_score([1, 0], [0.0, 1.0]) == 1.0  # worst


def test_log_loss_no_infinity_at_extremes():
    # clipping keeps it finite even when a 0/1 prediction is wrong
    assert np.isfinite(log_loss([1], [0.0]))
    assert log_loss([1, 0], [1.0, 0.0]) < 1e-10


def test_brier_skill_score_sign():
    y = [1, 0, 1, 0, 1, 0, 1, 0]
    good = [0.9, 0.1, 0.8, 0.2, 0.7, 0.3, 0.9, 0.1]
    assert brier_skill_score(y, good) > 0
    base = float(np.mean(y))
    # predicting the base rate everywhere has ~zero skill
    assert abs(brier_skill_score(y, [base] * len(y))) < 1e-9


def test_reliability_table_counts_and_freq():
    y = [0, 0, 1, 1]
    p = [0.05, 0.15, 0.85, 0.95]
    tbl = reliability_table(y, p, n_bins=10)
    assert tbl["count"].sum() == 4
    # the two high-prob predictions resolved positive
    high = tbl[tbl["bin"] >= 8]
    assert high["count"].sum() == 2
    assert (high["frac_pos"].dropna() == 1.0).all()


def test_ece_zero_when_calibrated():
    # 100 preds at 0.3 with exactly 30% positive -> perfectly calibrated bin
    y = [1] * 30 + [0] * 70
    p = [0.3] * 100
    assert expected_calibration_error(y, p, n_bins=10) < 1e-9


def test_brier_decomposition_reconstructs_brier():
    rng = np.random.default_rng(0)
    p = rng.uniform(0, 1, 500)
    y = (rng.uniform(0, 1, 500) < p).astype(int)
    d = brier_decomposition(y, p, n_bins=10)
    # BS == reliability - resolution + uncertainty (binned identity)
    assert abs(d.brier - (d.reliability - d.resolution + d.uncertainty)) < 1e-12
    # and it is close to the directly computed Brier (binning approximation)
    assert abs(d.brier - brier_score(y, p)) < 0.02


@pytest.mark.parametrize(
    "y,p",
    [([1, 2], [0.5, 0.5]), ([1, 0], [0.5, 1.5]), ([1], [0.5, 0.5]), ([], [])],
)
def test_validation_errors(y, p):
    with pytest.raises(ValueError):
        brier_score(y, p)


def test_summary_keys():
    s = summary([1, 0, 1, 0], [0.7, 0.3, 0.6, 0.4])
    for key in ("brier", "log_loss", "brier_skill_score", "ece", "base_rate", "n"):
        assert key in s
