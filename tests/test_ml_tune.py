"""The ML tuner must find real signal and refuse to invent it from noise."""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecasting_lab.ml.tune import rank_ic, tune_ranker
from forecasting_lab.sim.engine import Arena
from forecasting_lab.sim.strategies import MLRanker, default_strategies


def _panel(n_periods=40, n_tickers=12, signal=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for period in range(n_periods):
        f1 = rng.normal(size=n_tickers)
        f2 = rng.normal(size=n_tickers)
        noise = rng.normal(size=n_tickers)
        label = signal * f1 + (1 - signal) * noise
        for i in range(n_tickers):
            rows.append({"period": period, "ticker": f"T{i}", "f1": f1[i], "f2": f2[i], "label": label[i]})
    return pd.DataFrame(rows)


def test_tuner_finds_signal_when_present():
    best, results = tune_ranker(_panel(signal=0.9, seed=1), ["f1", "f2"], "label")
    assert isinstance(best, dict) and best  # a real param dict
    top_ic = max(r["ic"] for r in results)
    assert top_ic > 0.15  # the ranking genuinely lines up with the label


def test_tuner_does_not_manufacture_skill_from_noise():
    # pure-noise labels: no params should score a meaningful out-of-sample IC
    _, results = tune_ranker(_panel(signal=0.0, seed=2), ["f1", "f2"], "label")
    best_ic = max(abs(r["ic"]) for r in results)
    assert best_ic < 0.15  # ~zero; the leakage/overfitting guard holds


def test_rank_ic_perfect_ranking_is_one():
    frame = pd.DataFrame({
        "period": [0, 0, 0, 1, 1, 1],
        "score": [1, 2, 3, 3, 2, 1],
        "label": [1, 2, 3, 3, 2, 1],
    })
    assert rank_ic(frame, "score", "label") == 1.0


def test_ml_ranker_weights_are_valid_long_only():
    prices = Arena(n_bars=300, seed=3).prices
    ml = MLRanker(k=3, warmup=200)
    w = ml.target_weights(prices.iloc[:260], 259)
    assert all(v >= 0 for v in w.values())
    assert abs(sum(w.values()) - 1.0) < 1e-9 or w == {}
    assert len(w) <= 3


def test_ml_ranker_is_in_the_default_arena():
    names = [s.name for s in default_strategies()]
    assert "ml_ranker" in names
