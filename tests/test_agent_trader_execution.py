"""P2 of the agent trader: the execution layer enforces limits as refusing tools and
survives the real-money plumbing traps — idempotency, reconciliation, splits, costs."""

from __future__ import annotations

from pathlib import Path

import forecasting_lab.agent_trader.execution as exec_mod
from forecasting_lab.agent_trader.execution import (
    ExecutionLayer,
    Order,
    PaperBroker,
    RiskLimits,
    reconcile_from_broker,
    split_adjusted_day_change,
)


def test_paper_fill_applies_modeled_cost():
    b = PaperBroker(cash=100_000.0, cost_bps=5.0)
    f = b.submit(Order("AAA", "buy", 100, "o1"), price=10.0)
    assert f.status == "filled"
    assert abs(b.cash - (100_000.0 - 1000.0 - 0.5)) < 1e-6  # notional 1000 + cost 0.5
    assert b.positions["AAA"].qty == 100


def test_submit_is_idempotent_no_double_submit():
    b = PaperBroker()
    b.submit(Order("AAA", "buy", 100, "o1"), 10.0)
    cash, qty = b.cash, b.positions["AAA"].qty
    dup = b.submit(Order("AAA", "buy", 100, "o1"), 10.0)  # same client_order_id, retried
    assert dup.status == "duplicate"
    assert b.cash == cash and b.positions["AAA"].qty == qty


def test_kill_switch_halts_the_whole_rebalance():
    b = PaperBroker(cash=100_000.0)
    b.equity_high = 100_000.0
    b.cash = 90_000.0  # down 10% intraday, past the 8% kill line
    ex = ExecutionLayer(b, RiskLimits(daily_drawdown_kill=0.08), prices={"AAA": 10.0})
    r = ex.rebalance({"AAA": 0.5}, "run1")
    assert r.halted is True and r.fills == []


def test_oversized_and_overexposed_orders_are_capped_no_override():
    prices = {s: 10.0 for s in "ABCDE"}
    b = PaperBroker(cash=100_000.0)
    ex = ExecutionLayer(b, RiskLimits(max_name_weight=0.25, max_gross_exposure=1.0), prices=prices)
    ex.rebalance({s: 0.9 for s in "ABCDE"}, "run1")  # asks for 4.5x gross, every name oversized
    eq = b.equity(prices)
    for s in "ABCDE":
        w = (b.positions[s].qty * 10.0) / eq
        assert w <= 0.26  # per-name cap enforced (the layer cannot be overridden)
    gross = sum(b.positions[s].qty * 10.0 for s in b.positions) / eq
    assert gross <= 1.05  # leverage cap enforced (nowhere near the requested 4.5x)


def test_reconcile_uses_the_broker_as_source_of_truth():
    b = PaperBroker()
    b.submit(Order("AAA", "buy", 50, "o1"), 10.0)
    recon = reconcile_from_broker(b)
    assert recon["AAA"].qty == 50  # survives a crash between submit and DB-write


def test_a_split_does_not_read_as_a_crash():
    # 4:1 split: naive day-change reads -75% (would trip a stop); split-adjusted reads ~0
    assert abs(split_adjusted_day_change(100.0, 25.0, split_ratio=4.0)) < 1e-9
    assert split_adjusted_day_change(100.0, 25.0, split_ratio=1.0) < -0.7
    b = PaperBroker()
    b.submit(Order("AAA", "buy", 100, "o1"), 100.0)
    value_before = b.positions["AAA"].qty * 100.0
    b.apply_split("AAA", 4.0)
    value_after = b.positions["AAA"].qty * 25.0  # price is now split-adjusted
    assert abs(value_before - value_after) < 1e-6  # a split changes nothing real


def test_execution_layer_uses_no_real_broker_sdk():
    src = Path(exec_mod.__file__).read_text(encoding="utf-8").lower()
    for term in ["alpaca", "tradingclient", "ib_insync", "import requests"]:
        assert term not in src, f"paper only until gated; found {term!r}"
