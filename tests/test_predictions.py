"""The prediction-evidence contract: no pick exists (or renders) without a
probability AND at least one driver. This is the Phase 0 guardrail."""

from __future__ import annotations

import math

import pytest

from forecasting_lab.predictions import (
    Driver,
    Prediction,
    logistic,
    market_prediction,
    mover_prediction,
)


def test_prediction_requires_at_least_one_driver():
    with pytest.raises(ValueError, match="at least one driver"):
        Prediction(probability=0.5, drivers=(), caveat="x")


def test_prediction_requires_a_valid_probability():
    with pytest.raises(ValueError):
        Prediction(probability=None, drivers=(Driver("f", 1.0, 1.0),), caveat="x")
    with pytest.raises(ValueError):
        Prediction(probability=1.4, drivers=(Driver("f", 1.0, 1.0),), caveat="x")
    with pytest.raises(ValueError):
        Prediction(probability=-0.1, drivers=(Driver("f", 1.0, 1.0),), caveat="x")


def test_edge_vs_market_is_none_without_a_market_price():
    p = Prediction(probability=0.6, drivers=(Driver("f", 1.0, 1.0),), caveat="x")
    assert p.edge_vs_market is None


def test_edge_vs_market_is_model_minus_market():
    p = Prediction(probability=0.6, market_implied_prob=0.5,
                   drivers=(Driver("f", 1.0, 1.0),), caveat="x")
    assert p.edge_vs_market == pytest.approx(0.1)


def test_mover_prediction_always_has_probability_and_evidence():
    card = {"ticker": "NVDA", "momentum": 1.2, "ret_5d": 0.03, "ret_60d": 0.4,
            "pct_from_high": -0.02, "volume_spike": 1.8}
    pred = mover_prediction(card)
    assert 0.0 <= pred.probability <= 1.0
    assert len(pred.drivers) >= 1
    assert pred.caveat  # never silent
    assert pred.pct().endswith("%")
    # deterministic: same input -> identical prediction
    assert mover_prediction(card) == pred


def test_mover_prediction_degrades_with_missing_features():
    # even a near-empty card still yields a valid pick (the composite driver is always present)
    pred = mover_prediction({"ticker": "X"})
    assert len(pred.drivers) >= 1
    assert 0.0 <= pred.probability <= 1.0


def test_market_prediction_odds_are_the_market_price():
    pred = market_prediction("Will X happen?", yes=0.42, venue="Kalshi", gap=0.08)
    assert pred.probability == pytest.approx(0.42)
    assert pred.market_implied_prob == pytest.approx(0.42)
    assert pred.edge_vs_market == pytest.approx(0.0)  # no independent model yet
    assert len(pred.drivers) >= 2  # price + liquidity (+ gap)


def test_logistic_is_monotonic_and_bounded():
    assert logistic(-10) < logistic(0) < logistic(10)
    assert 0.0 < logistic(-50) and logistic(50) < 1.0
    assert logistic(0) == pytest.approx(0.5)
    assert not math.isnan(logistic(0.0))


def test_american_odds_sign_matches_favorite():
    fav = Prediction(probability=0.75, drivers=(Driver("f", 1.0, 1.0),), caveat="x")
    dog = Prediction(probability=0.25, drivers=(Driver("f", 1.0, 1.0),), caveat="x")
    assert fav.american_odds().startswith("−")  # favorite -> minus
    assert dog.american_odds().startswith("+")  # underdog -> plus
