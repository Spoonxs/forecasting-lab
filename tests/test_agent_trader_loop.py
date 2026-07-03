"""P5 of the agent trader: the autonomous loop runs a full cycle offline, is idempotent,
halts on the kill switch, and NEVER applies the LLM's proposal to live trades."""

from __future__ import annotations

import json
from pathlib import Path

from forecasting_lab.agent_trader.execution import PaperBroker, RiskLimits
from forecasting_lab.agent_trader.loop import run_once


def _judge(role, ctx):
    # the model proposes a WILD change — the loop must not act on it
    return {
        "scout": {"catalysts": []},
        "analyst": {"prob": 0.6, "thesis": "t"},
        "risk": {"veto": False, "reason": "ok"},
        "red_team": {"counter": "c"},
        "portfolio_manager": {"changes": {"NVDA": 0.90}, "rationale": "all in"},
    }[role]


def _strategy(brief):
    return {brief.ticker: 0.20}  # the APPROVED deterministic strategy: 20% NVDA


def _kw(**over):
    base = dict(ticker="NVDA", judge=_judge, strategy=_strategy,
                limits=RiskLimits(max_name_weight=0.25), prices={"NVDA": 10.0}, run_id="r1")
    base.update(over)
    return base


def test_full_cycle_runs_offline_and_executes_the_deterministic_strategy():
    b = PaperBroker(cash=100_000.0)
    snap = run_once(broker=b, **_kw())
    assert snap["halted"] is False and snap["fills"] == 1
    w = b.positions["NVDA"].qty * 10.0 / b.equity({"NVDA": 10.0})
    assert 0.18 <= w <= 0.22  # executed the 20% strategy weight (not the 90% proposal)


def test_loop_is_idempotent_on_run_id():
    b = PaperBroker(cash=100_000.0)
    run_once(broker=b, **_kw(run_id="r1"))
    qty = b.positions["NVDA"].qty
    run_once(broker=b, **_kw(run_id="r1"))  # same run_id, e.g. a retry after a crash
    assert b.positions["NVDA"].qty == qty  # no double-buy


def test_the_llm_proposal_is_queued_not_applied():
    b = PaperBroker(cash=100_000.0)
    snap = run_once(broker=b, **_kw())
    assert snap["proposal_queued"]["approved"] is False
    assert snap["proposal_queued"]["changes"] == {"NVDA": 0.90}  # proposed...
    w = b.positions["NVDA"].qty * 10.0 / b.equity({"NVDA": 10.0})
    assert w < 0.25  # ...but NOT executed (the 90% never happened)


def test_kill_switch_halts_the_autonomous_cycle():
    b = PaperBroker(cash=100_000.0)
    b.equity_high = 100_000.0
    b.cash = 90_000.0  # down 10% intraday
    snap = run_once(broker=b, **_kw(limits=RiskLimits(daily_drawdown_kill=0.08)))
    assert snap["halted"] is True and snap["fills"] == 0


def test_snapshot_is_appended_to_the_ledger(tmp_path):
    b = PaperBroker(cash=100_000.0)
    path = tmp_path / "ledger.jsonl"
    run_once(broker=b, ledger_path=path, **_kw())
    lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["run_id"] == "r1" and "equity" in row and "positions" in row
