"""Phase 1 edge features: each extracts real signal when it's there, and CANNOT
manufacture positive skill from noise (the leakage guard), scored out-of-sample
under the purged walk-forward split. Plus each feature's shape property."""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecasting_lab.eval.recalibration import (
    FavoriteLongshotRecalibrator,
    recalibration_skill_report,
)
from forecasting_lab.eval.skill import brier_skill_vs
from forecasting_lab.markets.leadlag import (
    convergence_prob,
    lead_lag,
    leadlag_skill_report,
)
from forecasting_lab.signals.attention import (
    AttentionStore,
    attention_acceleration,
    attention_skill_report,
)
from forecasting_lab.signals.squeeze import squeeze_setup, squeeze_skill_report

SIGNAL = 0.02   # a real feature must clear this out-of-sample
NULL = 0.02     # noise must not exceed this (it may go negative — confidently wrong)


# ---- shared scorer -----------------------------------------------------------
def test_brier_skill_vs_is_zero_when_model_equals_reference():
    y = np.array([0, 1, 0, 1, 1.0])
    p = np.array([0.4, 0.6, 0.3, 0.7, 0.8])
    assert brier_skill_vs(y, p, p) == 0.0
    assert brier_skill_vs(y, y, p) > 0.0  # a perfect model beats any imperfect reference


# ---- feature 1: cross-venue lead-lag ----------------------------------------
def test_leadlag_detects_the_leader_and_convergence_direction():
    a = np.cumsum(np.random.default_rng(0).normal(size=200))
    b = np.empty(200)
    b[:3] = a[0]
    b[3:] = a[:-3]  # b follows a by 3
    r = lead_lag(a, b)
    assert r["leader"] == "a" and r["lead_lag"] == 3
    assert convergence_prob(0.7, 0.4) > 0.5  # laggard below leader -> expected to rise
    assert convergence_prob(0.4, 0.7) < 0.5


def test_leadlag_signal_beats_baseline_but_noise_does_not():
    assert leadlag_skill_report(seed=0, follow=True)["brier_skill_vs_baseline"] > SIGNAL
    assert leadlag_skill_report(seed=0, follow=False)["brier_skill_vs_baseline"] < NULL


# ---- feature 2: attention acceleration --------------------------------------
def test_attention_acceleration_is_zero_mean_on_stationary_noise():
    counts = pd.Series(np.random.default_rng(1).poisson(12, 300).astype(float))
    z = attention_acceleration(counts)
    assert abs(float(z.mean())) < 0.15  # a spike scores high, steady noise nets to ~0
    assert np.isfinite(z.to_numpy()).all()


def test_attention_store_round_trips(tmp_path):
    store = AttentionStore(tmp_path / "attn.csv")
    store.record("2026-07-01", {"NVDA": 12, "GME": 40})
    store.record("2026-07-02", {"NVDA": 30, "GME": 22})
    store.record("2026-07-02", {"NVDA": 31, "GME": 22})  # same-day re-run overwrites
    s = store.series("NVDA")
    assert list(s) == [12.0, 31.0]
    assert store.latest_acceleration("NVDA") == 0.0  # too little history yet -> honest zero


def test_attention_signal_beats_baseline_but_noise_does_not():
    assert attention_skill_report(seed=0, strength=1.1)["brier_skill_vs_baseline"] > SIGNAL
    assert attention_skill_report(seed=0, strength=0.0)["brier_skill_vs_baseline"] < NULL


# ---- feature 3: squeeze setup ------------------------------------------------
def test_squeeze_is_monotone_in_short_interest_and_needs_both_legs():
    # monotone in short interest, holding the rest fixed
    lo = squeeze_setup(0.10, 6, 4.0, 0.0)
    hi = squeeze_setup(0.30, 6, 4.0, 0.0)
    assert hi >= lo > 0
    # both legs required: no fuel -> 0; no ignition -> 0
    assert squeeze_setup(0.0, 6, 4.0, 0.08) == 0.0
    assert squeeze_setup(0.30, 6, 1.0, 0.0) == 0.0


def test_squeeze_signal_beats_baseline_but_noise_does_not():
    assert squeeze_skill_report(seed=0, k_true=0.6)["brier_skill_vs_baseline"] > SIGNAL
    assert squeeze_skill_report(seed=0, k_true=0.0)["brier_skill_vs_baseline"] < NULL


# ---- feature 4: favorite-longshot recalibration -----------------------------
def test_recalibration_is_monotone():
    rng = np.random.default_rng(0)
    r = FavoriteLongshotRecalibrator().fit(rng.uniform(size=3000), (rng.uniform(size=3000) < 0.5).astype(float))
    t = r.transform(np.linspace(0, 1, 21))
    assert np.all(np.diff(t) >= -1e-9)  # non-decreasing


def test_recalibration_helps_biased_prices_and_not_calibrated_ones():
    assert recalibration_skill_report(seed=0, bias=1.3)["brier_skill_vs_market"] > SIGNAL
    assert abs(recalibration_skill_report(seed=0, bias=1.0)["brier_skill_vs_market"]) < NULL
