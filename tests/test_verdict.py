"""P6a step 2 — the verdict engine's scoring contract (PLATFORM_PLAN §1/§9).

Properties pinned: monotone in every component; profile-sensitive (same
evidence, different profile -> different read); confidence-gated (INSUFFICIENT
EVIDENCE is first-class and names what's missing); the preserve profile raises
the cash bar so HYSA beats a negative-lean equity; missing components are
excluded + named, never imputed; splits don't read as crashes; delisted means
no verdict; the exported contract matches the engine's own tables exactly.
"""

from __future__ import annotations

import numpy as np
import pytest

from forecasting_lab.signals.verdict import (
    BASE_WEIGHTS,
    INSUFFICIENT,
    Component,
    Profile,
    adjusted_returns,
    compute_verdict,
    profile_weights,
    scoring_contract,
)


def _full(score: float = 0.3, conf: float = 0.9) -> dict:
    return {name: Component(name, score, conf) for name in BASE_WEIGHTS}


def test_monotone_in_every_component():
    for name in BASE_WEIGHTS:
        lo = _full(0.2)
        hi = dict(lo)
        hi[name] = Component(name, 0.9, 0.9)
        v_lo = compute_verdict(lo)
        v_hi = compute_verdict(hi)
        assert v_hi.score >= v_lo.score, f"raising {name} lowered the score"


def test_labels_are_monotone_in_score():
    labels = [compute_verdict(_full(s)).label for s in (-0.9, -0.4, 0.0, 0.3, 0.8)]
    assert labels == ["AVOID", "TRIM", "HOLD", "BUY", "STRONG BUY"]


def test_profile_changes_the_read_of_the_same_evidence():
    components = _full(0.0, 0.9)
    components["trend"] = Component("trend", 0.9, 0.9)       # strong momentum
    components["backtest"] = Component("backtest", -0.2, 0.9)  # weak long-run
    short = compute_verdict(components, Profile(horizon="0-1y"))
    long = compute_verdict(components, Profile(horizon="5y+"))
    assert short.score > long.score  # momentum matters more on a short horizon
    w_short = profile_weights(Profile(horizon="0-1y"))
    w_long = profile_weights(Profile(horizon="5y+"))
    assert w_short["trend"] > w_long["trend"]
    assert w_long["backtest"] > w_short["backtest"]
    # goal shifts too: income overweights yield
    assert profile_weights(Profile(goal="income"))["yield"] > profile_weights(Profile())["yield"]


def test_confidence_gate_is_first_class_and_names_the_problem():
    v = compute_verdict(_full(0.8, conf=0.2))  # great lean, terrible data
    assert v.label == INSUFFICIENT and v.insufficient
    assert any("floor" in r for r in v.reasons)
    assert any(m.startswith("low-confidence:") for m in v.missing)
    # a strong lean must never leak through weak data as a BUY
    assert v.dials["data_confidence"] < 0.4


def test_missing_components_are_excluded_named_never_imputed():
    components = {"trend": Component("trend", 0.5, 0.9),
                  "backtest": Component("backtest", 0.5, 0.9),
                  "macro": Component("macro", 0.5, 0.9),
                  "yield": Component("yield", 0.5, 0.9)}
    v = compute_verdict(components)
    assert set(v.missing) == set(BASE_WEIGHTS) - set(components)
    assert any("excluded (no data)" in r for r in v.reasons)
    assert v.label != INSUFFICIENT  # enough coverage to speak
    assert pytest.approx(sum(v.weights_used.values()), abs=1e-9) == 1.0
    # too little coverage -> INSUFFICIENT, stated in %
    v2 = compute_verdict({"news": Component("news", 0.9, 0.9)})
    assert v2.label == INSUFFICIENT and any("evidence weight" in r for r in v2.reasons)


def test_preserve_profile_raises_the_cash_bar():
    weak = _full(0.05, 0.9)  # barely-positive equity lean
    grow = compute_verdict(weak, Profile(goal="grow"), hysa_yield_pct=5.0)
    preserve = compute_verdict(weak, Profile(goal="preserve"), hysa_yield_pct=5.0)
    assert preserve.score < grow.score  # cash bar subtracted
    assert any("cash bar" in r for r in preserve.reasons)
    # a negative-lean equity under preserve lands at/below TRIM — HYSA wins
    bad = compute_verdict(_full(-0.2, 0.9), Profile(goal="preserve"), hysa_yield_pct=5.0)
    assert bad.label in ("TRIM", "AVOID")


def test_drawdown_penalty_scales_with_risk_appetite():
    comps = _full(0.4, 0.9)
    low = compute_verdict(comps, Profile(risk="low"), drawdown_risk=0.5)
    high = compute_verdict(comps, Profile(risk="high"), drawdown_risk=0.5)
    none = compute_verdict(comps, Profile(risk="low"), drawdown_risk=0.0)
    assert low.score < high.score < none.score


def test_splits_do_not_read_as_crashes_and_delisting_gets_no_verdict():
    closes = [100.0, 101.0, 25.5, 25.8]  # 4:1 split before day 2
    naive = np.asarray(closes[2]) / closes[1] - 1.0
    assert naive < -0.7  # the trap is real
    fixed = adjusted_returns(closes, split_ratios={2: 4.0})
    assert abs(fixed[1]) < 0.02  # the split day reads ~+1%, not -75%
    v = compute_verdict(_full(0.5, 0.9), delisted=True)
    assert v.label == INSUFFICIENT and "delisted" in " ".join(v.missing)


def test_contract_export_matches_the_engine_tables_exactly():
    contract = scoring_contract()
    assert contract["base_weights"] == BASE_WEIGHTS
    assert contract["data_confidence_floor"] == 0.40
    assert [name for _t, name in [tuple(x) for x in contract["thresholds"]]] == [
        "STRONG BUY", "BUY", "HOLD", "TRIM"]
    # every profile the engine accepts is representable from the contract
    for horizon in contract["horizon_multipliers"]:
        for goal in contract["goal_multipliers"]:
            Profile(horizon=horizon, goal=goal)


def test_inputs_are_validated_loudly():
    with pytest.raises(ValueError):
        Component("trend", 1.5, 0.9)
    with pytest.raises(ValueError):
        Component("trend", 0.5, 1.2)
    with pytest.raises(ValueError):
        Profile(horizon="2 weeks")
    with pytest.raises(ValueError):
        compute_verdict(_full(), drawdown_risk=1.5)
    with pytest.raises(ValueError):
        compute_verdict(_full(), model_confidence=2.0)
    with pytest.raises(ValueError):
        compute_verdict(_full(), hysa_yield_pct=-1.0)


# ---------------------------------------------- Codex code-review fixes pinned
def test_zero_confidence_evidence_has_zero_pull():
    """Codex finding 1: a great-looking score with no confidence behind it must
    not move the verdict."""
    honest = _full(0.0, 0.9)
    tempted = dict(honest)
    tempted["backtest"] = Component("backtest", 1.0, 0.0)  # perfect score, zero trust
    v_honest = compute_verdict(honest)
    v_tempted = compute_verdict(tempted)
    assert abs(v_tempted.dials["expected_return"] - v_honest.dials["expected_return"]) < 1e-9
    assert v_tempted.weights_used.get("backtest", 0.0) == 0.0


def test_model_confidence_gates_the_verdict():
    """Codex finding 2: an unproven model gets no verdict, however good the lean."""
    v = compute_verdict(_full(0.8, 0.9), model_confidence=0.1)
    assert v.label == INSUFFICIENT
    assert "model unproven out-of-sample" in v.missing
    assert any("unproven model" in r for r in v.reasons)
    ok = compute_verdict(_full(0.8, 0.9), model_confidence=0.9)
    assert ok.label == "STRONG BUY"


def test_contract_exports_the_algorithm_semantics():
    """Codex finding 4: the JS mirror needs the algorithm, not just the numbers."""
    algo = scoring_contract()["algorithm"]
    assert algo["gate_order"] == ["delisted", "weight_coverage", "data_confidence",
                                  "model_confidence", "label"]
    assert "confidence-weighted" in algo["lean"]
    assert algo["input_ranges"]["drawdown_risk"] == [0, 1]
    assert scoring_contract()["model_confidence_floor"] == 0.20
