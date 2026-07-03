"""P6 of the agent trader: the capital ladder can't climb without a passing gate AND
explicit human confirmation, and the live board shows the honest paper/real banner."""

from __future__ import annotations

from forecasting_lab.agent_trader.board import render_account
from forecasting_lab.agent_trader.ladder import LadderState, advance, can_advance


def test_ladder_cannot_advance_without_a_passing_gate():
    s = LadderState()  # paper, $0
    assert advance(s, gate_passed=False, human_confirmed=True) == s  # no gate -> no move
    ok, why = can_advance(s, gate_passed=False, human_confirmed=True)
    assert ok is False and "gate" in why


def test_ladder_cannot_advance_without_human_confirmation():
    s = LadderState()
    assert advance(s, gate_passed=True, human_confirmed=False) == s  # no confirmation -> no move


def test_ladder_advances_one_rung_with_gate_and_confirmation():
    s = LadderState()
    s1 = advance(s, gate_passed=True, human_confirmed=True, live_version="v3")
    assert s1.step == 1 and s1.capital == 100.0 and s1.live_version == "v3"
    assert not s1.is_paper


def test_ladder_cannot_skip_or_pass_the_top():
    s = LadderState(step=len(__import__("forecasting_lab.agent_trader.ladder", fromlist=["STEPS"]).STEPS) - 1)
    assert advance(s, gate_passed=True, human_confirmed=True) == s  # already at the top


def _snapshot(**over):
    base = {"run_id": "r1", "equity": 100_000.0, "halted": False,
            "positions": {"NVDA": 2000}, "version_live": "v0"}
    base.update(over)
    return base


def test_board_shows_paper_banner_and_honest_verdict():
    html = render_account(_snapshot(equity=101_500.0), start_equity=100_000.0,
                          benchmark_return=0.02, ladder=LadderState())
    assert "PAPER" in html and "$0 at risk" in html
    assert "stay on paper" in html.lower()
    assert "Not financial advice" in html
    assert "+1.50%" in html  # real return vs a real benchmark


def test_board_shows_live_banner_and_dollars_at_risk():
    html = render_account(_snapshot(), start_equity=100_000.0, benchmark_return=0.0,
                          ladder=LadderState(step=2, live_version="v3"))
    assert "LIVE" in html and "1,000 at risk" in html
    assert "Live version v3" in html


def test_board_flags_a_halted_account():
    html = render_account(_snapshot(halted=True), start_equity=100_000.0,
                          benchmark_return=0.0, ladder=LadderState())
    assert "HALTED" in html
