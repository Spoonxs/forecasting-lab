"""P4 of the agent trader: the fleet's winner must clear the six-gate promotion check on
real marks to become live-eligible; the under-proven winner of a random fleet is rejected."""

from __future__ import annotations

from pathlib import Path

from forecasting_lab.agent_trader import fleet as fleet_mod
from forecasting_lab.agent_trader.fleet import fleet_report
from forecasting_lab.agent_trader.gate import gate_fleet_top

# generous forward/risk inputs so ONLY the fleet stats decide the outcome
GOOD_FORWARD = {"live_marks": 30, "brier_skill_vs_market": 0.05, "turnover": 0.5, "max_drawdown": 0.10}
GOOD_RISK = {"kelly_fraction": 0.2, "max_name_weight": 0.2, "gross_exposure": 1.0}


def test_random_fleet_winner_is_rejected():
    fleet = fleet_report(seed=0, k=20, skilled=False)  # nobody has real edge
    rec = gate_fleet_top(fleet, GOOD_FORWARD, GOOD_RISK, as_of="2026-07-03")
    assert rec.passed is False  # under-proven: low deflated Sharpe + high PBO
    by = {c.name: c.passed for c in rec.checks}
    assert by["Deflated Sharpe"] is False or by["Overfitting (PBO)"] is False
    assert "HOLD" in rec.rationale


def test_a_fully_proven_variant_passes_and_is_signed():
    fleet = {"pbo": 0.10, "n_variants": 5,
             "rows": [{"variant": "v_star", "deflated_sharpe": 1.6, "total_return": 0.2}]}
    rec = gate_fleet_top(fleet, GOOD_FORWARD, GOOD_RISK, as_of="2026-07-03")
    assert rec.passed is True and rec.signature and rec.as_of == "2026-07-03"


def test_thin_forward_marks_block_promotion():
    fleet = {"pbo": 0.10, "n_variants": 5,
             "rows": [{"variant": "v_star", "deflated_sharpe": 1.6, "total_return": 0.2}]}
    thin = dict(GOOD_FORWARD, live_marks=3)  # not enough real out-of-sample evidence
    rec = gate_fleet_top(fleet, thin, GOOD_RISK, as_of="2026-07-03")
    assert rec.passed is False


def test_gate_and_fleet_modules_have_no_order_execution_code():
    from forecasting_lab.agent_trader import gate as gate_mod
    from forecasting_lab.agent_trader import team as team_mod
    for mod in (gate_mod, team_mod, fleet_mod):
        src = Path(mod.__file__).read_text(encoding="utf-8").lower()
        for term in ["place_order", "submit_order", "alpaca", "tradingclient", "import requests"]:
            assert term not in src
