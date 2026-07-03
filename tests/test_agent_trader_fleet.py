"""P3 of the agent trader: the parallel fleet is scored for multiple testing, so K
random variants promote nobody (no luckiest-of-K), while a real edge rises to the top."""

from __future__ import annotations

from forecasting_lab.agent_trader.fleet import (
    fleet_report,
    fleet_verdict,
    promotable_variants,
    score_fleet,
)


def test_k_random_variants_promote_nobody():
    fleet = fleet_report(seed=0, k=20, skilled=False)
    assert promotable_variants(fleet) == []  # the luckiest-of-K is not promoted
    assert fleet["pbo"] > 0.2  # high overfitting probability across the fleet
    assert fleet["rows"][0]["deflated_sharpe"] < 1.0  # even the best doesn't clear the bar
    assert "Stay on paper" in fleet_verdict(fleet)


def test_a_real_edge_rises_to_the_top():
    fleet = fleet_report(seed=0, k=20, skilled=True)
    top = fleet["rows"][0]
    assert top["variant"] == "v_skilled"  # the genuinely-skilled variant ranks first
    random_best = max(r["deflated_sharpe"] for r in fleet["rows"] if r["variant"] != "v_skilled")
    assert top["deflated_sharpe"] > random_best  # and beats the best of the noise


def test_fleet_scoring_is_deterministic_and_dated():
    a = fleet_report(seed=1, k=12, as_of="2026-07-03")
    b = fleet_report(seed=1, k=12, as_of="2026-07-03")
    assert a == b
    assert a["as_of"] == "2026-07-03" and a["n_variants"] == 12


def test_score_fleet_ignores_empty_variants():
    fleet = score_fleet({"a": [0.01, -0.01, 0.02] * 10, "b": []}, as_of="x")
    assert fleet["n_variants"] == 1 and fleet["rows"][0]["variant"] == "a"
