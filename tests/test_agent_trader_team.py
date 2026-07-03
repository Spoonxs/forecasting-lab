"""P1 of the agent trader: the team turns a brief into a PROPOSAL (odds + evidence +
risk + red-team), never self-approves, never executes, and runs deterministically."""

from __future__ import annotations

from pathlib import Path

import forecasting_lab.agent_trader.team as team_mod
from forecasting_lab.agent_trader import build_brief, run_cycle


def _fake_judge(role, ctx):
    return {
        "scout": {"catalysts": ["earnings beat", "insider buy"]},
        "analyst": {"prob": 0.62, "thesis": "NVDA continues up", "caveat": "synthetic",
                    "drivers": [["insider buying", 1.0, 0.4], ["news velocity", 2.3, 0.3]]},
        "risk": {"veto": False, "reason": "within caps"},
        "red_team": {"counter": "valuation stretched"},
        "portfolio_manager": {"changes": {"NVDA": 0.10}, "rationale": "add a small starter"},
    }[role]


def _brief():
    return build_brief("NVDA", "2026-07-03", {"price": lambda t: {"last": 100.0}})


def test_cycle_produces_a_proposal_with_odds_and_evidence():
    p = run_cycle(_brief(), _fake_judge)
    assert p.approved is False  # the team never self-approves
    assert 0.0 <= p.prediction.probability <= 1.0 and len(p.prediction.drivers) >= 1
    assert p.risk_veto is False and p.red_team  # risk officer + red team both ran
    assert p.changes == {"NVDA": 0.10}  # a config diff for review, NOT an order
    assert p.from_version == "v0"


def test_cycle_is_deterministic():
    a = run_cycle(_brief(), _fake_judge)
    b = run_cycle(_brief(), _fake_judge)
    assert a.changes == b.changes and a.prediction.probability == b.prediction.probability


def test_risk_officer_can_veto():
    def judge(role, ctx):
        if role == "risk":
            return {"veto": True, "reason": "per-name exposure cap"}
        return _fake_judge(role, ctx)

    p = run_cycle(_brief(), judge)
    assert p.risk_veto is True and "cap" in p.risk_reason


def test_analyst_output_always_yields_a_valid_prediction_even_if_sparse():
    def judge(role, ctx):
        if role == "analyst":
            return {"prob": 0.55}  # no drivers supplied
        return _fake_judge(role, ctx)

    p = run_cycle(_brief(), judge)
    assert len(p.prediction.drivers) >= 1  # a default driver is supplied; contract holds


def test_team_has_no_trade_execution_code():
    src = Path(team_mod.__file__).read_text(encoding="utf-8").lower()
    for term in ["place_order", "submit_order", "create_order", "alpaca",
                 "tradingclient", "import requests"]:
        assert term not in src, f"the team proposes, never executes; found {term!r}"
