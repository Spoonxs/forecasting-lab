"""V4 — the mandate validator + refuse-uncomputable-metrics (MASTER_PLAN §3).

Semantics pinned (each is a field-verified honesty trap):
- concentration on INVESTED capital, not total equity;
- sells always pass — a mandate must never trap you in a position;
- missing data skips the rule loudly, never false-blocks;
- a BLOCK stops the rebalance BEFORE the execution layer (wired in the loop);
- alpha without a stored entry-date benchmark renders "n/a", never a number.
"""

from __future__ import annotations

from forecasting_lab.agent_trader.execution import Order, PaperBroker, RiskLimits
from forecasting_lab.agent_trader.loop import run_once
from forecasting_lab.agent_trader.mandate import Rule, check_mandate
from forecasting_lab.eval import alpha_vs_benchmark, format_metric


def _judge(role, ctx):
    return {
        "scout": {"catalysts": []},
        "analyst": {"prob": 0.6, "thesis": "t"},
        "risk": {"veto": False, "reason": "ok"},
        "red_team": {"counter": "c"},
        "portfolio_manager": {"changes": {}, "rationale": "hold"},
    }[role]


def test_concentration_is_measured_on_invested_capital():
    # 20% of equity but HALF of what's actually invested — the honest number blocks
    rules = [Rule("max_position_pct", value=0.25)]
    report = check_mandate({"AAA": 0.2, "BBB": 0.2}, rules)
    assert report.blocked and "AAA" in report.violations[0] + report.violations[-1]
    # same weights inside a fully-invested book pass comfortably
    ok = check_mandate({s: 0.2 for s in ("A", "B", "C", "D", "E")}, rules)
    assert not ok.blocked


def test_sells_always_pass():
    rules = [Rule("max_position_pct", value=0.25), Rule("forbidden_ticker", tickers=("BAD",))]
    # already over-cap and even forbidden — but the proposal REDUCES both: allowed
    report = check_mandate(
        {"BAD": 0.3, "AAA": 0.7},
        rules,
        current_weights={"BAD": 0.5, "AAA": 0.9},
    )
    assert not report.blocked, report.violations
    # buying the forbidden name blocks
    assert check_mandate({"BAD": 0.1}, rules).blocked


def test_missing_sector_data_skips_loudly_never_false_blocks():
    rules = [Rule("max_sector_pct", value=0.4, sector="tech")]
    # no sector map at all -> skipped with a note, no block
    r1 = check_mandate({"AAA": 0.9}, rules)
    assert not r1.blocked and any("no sector data" in s for s in r1.skipped)
    # partial map: unknown symbols noted, known ones still enforced
    r2 = check_mandate(
        {"AAA": 0.5, "MYST": 0.2}, rules, sectors={"AAA": "tech"}
    )
    assert r2.blocked and any("MYST" in s for s in r2.skipped)


def test_unknown_rule_type_warns_never_silently_noops():
    report = check_mandate({"AAA": 0.1}, [Rule("max_postion_pct", value=0.1)])  # typo
    assert report.status == "warn" and "max_postion_pct" in report.warnings[0]
    assert not report.blocked


def test_min_cash_floor():
    rules = [Rule("min_cash_pct", value=0.2)]
    assert check_mandate({"AAA": 0.9}, rules).blocked
    assert not check_mandate({"AAA": 0.7}, rules).blocked


def test_blocked_proposal_never_reaches_the_execution_layer():
    """Wired end-to-end: a violating proposal halts the cycle with zero fills."""
    broker = PaperBroker(cash=10_000.0)
    prices = {"AAA": 10.0, "BBB": 10.0}
    snapshot = run_once(
        ticker="AAA", judge=_judge, strategy=lambda brief: {"AAA": 0.2, "BBB": 0.2},
        broker=broker, limits=RiskLimits(), prices=prices, run_id="m1",
        mandate_rules=[Rule("max_position_pct", value=0.25)],
    )
    assert snapshot["halted"] is True and snapshot["fills"] == 0
    assert broker.positions == {}
    assert snapshot["mandate"]["status"] == "block"
    assert any("mandate BLOCK" in n for n in snapshot["notes"])
    # the same cycle with a compliant book proceeds
    ok = run_once(
        ticker="AAA", judge=_judge, strategy=lambda brief: {s: 0.2 for s in ("AAA", "BBB")},
        broker=PaperBroker(cash=10_000.0), limits=RiskLimits(),
        prices=prices, run_id="m2",
        mandate_rules=[Rule("max_position_pct", value=0.6)],
    )
    assert ok["halted"] is False and ok["fills"] == 2


def test_sell_only_cycle_passes_mandate_even_over_cap():
    broker = PaperBroker(cash=10_000.0)
    broker.submit(Order("AAA", "buy", 500, "seed"), 10.0)  # ~half the book in one name
    prices = {"AAA": 10.0}
    snapshot = run_once(
        ticker="AAA", judge=_judge, strategy=lambda brief: {"AAA": 0.1},  # reduce
        broker=broker, limits=RiskLimits(), prices=prices, run_id="m3",
        mandate_rules=[Rule("max_position_pct", value=0.25)],
    )
    assert snapshot["halted"] is False, snapshot["notes"]


def test_alpha_without_entry_anchor_is_na_never_a_number():
    # all four anchors present -> a real excess return
    a = alpha_vs_benchmark(110.0, 100.0, 103.0, 100.0)
    assert a is not None and abs(a - 0.07) < 1e-12
    # missing entry-date benchmark -> None -> "n/a" (never reconstructed)
    assert alpha_vs_benchmark(110.0, 100.0, 103.0, None) is None
    assert alpha_vs_benchmark(110.0, None, 103.0, 100.0) is None
    assert format_metric(None) == "n/a"
    assert format_metric(0.07) == "+7.00%"
