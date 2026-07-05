"""V9 — execution realism (MASTER_PLAN §3).

The five properties, each pinned: wide spreads are refused; limit orders fill at
limit or better and never worse; unfilled limits expire loudly after N cycles
(wait-then-cancel); a dead decision service fails CLOSED on every order path
(kill switch independent); a changed payload under a known order id is refused
loudly, never silently deduped or double-filled; bracket exits fire on MARKS.
"""

from __future__ import annotations

import pytest

from forecasting_lab.agent_trader.execution import (
    ExecutionLayer,
    Order,
    PaperBroker,
    RiskLimits,
)


def test_spread_gate_refuses_wide_markets():
    b = PaperBroker(cash=10_000.0)
    wide = Order("AAA", "buy", 100, "o1", bid=9.0, ask=10.5)  # ~15% of mid
    fill = b.submit(wide, price=9.75)
    assert fill.status.startswith("rejected:spread")
    assert b.positions == {} and b.cash == 10_000.0  # nothing moved
    tight = Order("AAA", "buy", 100, "o2", bid=9.95, ask=10.05)
    assert b.submit(tight, price=10.0).status == "filled"


def test_limit_fills_at_limit_or_better_never_worse():
    b = PaperBroker(cash=10_000.0, cost_bps=0.0)
    # market BELOW the buy limit -> fills at the better market price
    f = b.submit(Order("AAA", "buy", 10, "o1", limit=10.0), price=9.5)
    assert f.status == "filled" and f.price == 9.5
    # market ABOVE the buy limit -> waits, no cash moves, never fills worse
    f2 = b.submit(Order("AAA", "buy", 10, "o2", limit=10.0), price=10.5)
    assert f2.status == "pending"
    assert b.cash == 10_000.0 - 95.0  # only the first fill spent cash
    # sell side mirror: market above the sell limit fills; below waits
    assert b.submit(Order("AAA", "sell", 5, "o3", limit=9.0), price=9.4).status == "filled"
    assert b.submit(Order("AAA", "sell", 5, "o4", limit=99.0), price=9.4).status == "pending"


def test_wait_then_cancel_expires_loudly():
    b = PaperBroker(cash=10_000.0)
    b.submit(Order("AAA", "buy", 10, "o1", limit=10.0), price=11.0)  # pending
    notes_seen: list[str] = []
    for _ in range(3):  # never becomes marketable
        _fills, notes = b.sweep_pending({"AAA": 11.0}, max_age=3)
        notes_seen.extend(notes)
    assert b.pending == {}  # gone -
    assert any("expired unfilled" in n and "o1" in n for n in notes_seen), notes_seen
    # and a pending order that BECOMES marketable fills at the (better) new price
    b.submit(Order("BBB", "buy", 10, "o2", limit=10.0), price=11.0)
    fills, _ = b.sweep_pending({"BBB": 9.8}, max_age=3)
    assert fills and fills[0].price == 9.8 and fills[0].status == "filled"


def test_decision_service_fails_closed_kill_switch_independent():
    prices = {"AAA": 10.0}

    def down():
        raise OSError("network")

    ex = ExecutionLayer(PaperBroker(), RiskLimits(), prices, decision_service=down)
    with pytest.raises(RuntimeError, match="failing closed"):
        ex.rebalance({"AAA": 0.2}, "r1")

    ex2 = ExecutionLayer(PaperBroker(), RiskLimits(), prices, decision_service=lambda: False)
    with pytest.raises(RuntimeError, match="unhealthy"):
        ex2.rebalance({"AAA": 0.2}, "r1")

    # the kill switch does NOT depend on the service: drawdown halts BEFORE the check
    b = PaperBroker(cash=100_000.0)
    b.equity_high = 100_000.0
    b.cash = 90_000.0
    ex3 = ExecutionLayer(b, RiskLimits(daily_drawdown_kill=0.08), prices, decision_service=down)
    r = ex3.rebalance({"AAA": 0.5}, "r1")
    assert r.halted is True  # halted, not raised


def test_changed_payload_under_known_id_is_refused_loudly():
    b = PaperBroker(cash=10_000.0)
    b.submit(Order("AAA", "buy", 100, "o1"), price=10.0)
    cash_after = b.cash
    # identical retry -> quiet duplicate, nothing moves
    assert b.submit(Order("AAA", "buy", 100, "o1"), price=10.0).status == "duplicate"
    # changed qty under the same id -> LOUD mismatch, still nothing moves
    mm = b.submit(Order("AAA", "buy", 999, "o1"), price=10.0)
    assert "PAYLOAD-MISMATCH" in mm.status
    assert b.cash == cash_after and b.positions["AAA"].qty == 100
    # pending ids get the same guard
    b.submit(Order("BBB", "buy", 10, "o2", limit=5.0), price=9.0)  # pending
    mm2 = b.submit(Order("BBB", "buy", 20, "o2", limit=5.0), price=9.0)
    assert mm2.status.startswith("rejected:PAYLOAD-MISMATCH")


def test_bracket_exits_fire_on_marks_not_fill_prices():
    prices = {"AAA": 100.0}
    b = PaperBroker(cash=100_000.0, cost_bps=0.0)
    ex = ExecutionLayer(b, RiskLimits(daily_drawdown_kill=0.99), prices)
    b.submit(Order("AAA", "buy", 100, "seed", stop_loss=92.0, take_profit=120.0), 100.0)
    # mark drifts but breaches nothing -> position stays
    ex.prices = {"AAA": 100.0}
    r0 = ex.rebalance({"AAA": 0.1}, "r0")
    assert "AAA" in b.positions and not any("bracket" in n for n in r0.notes)
    # the MARK breaches the stop -> deterministic exit at the mark
    ex.prices = {"AAA": 90.0}
    r = ex.rebalance({}, "r1")
    bracket = [f for f in r.fills if "bracket" in f.client_order_id]
    assert bracket and bracket[0].price == 90.0 and bracket[0].side == "sell"
    assert any("stop-loss" in n for n in r.notes)
    assert "AAA" not in b.positions
    # take-profit mirror
    b2 = PaperBroker(cash=100_000.0, cost_bps=0.0)
    ex2 = ExecutionLayer(b2, RiskLimits(daily_drawdown_kill=0.99), {"AAA": 100.0})
    b2.submit(Order("AAA", "buy", 100, "seed", stop_loss=92.0, take_profit=120.0), 100.0)
    ex2.prices = {"AAA": 125.0}
    r2 = ex2.rebalance({}, "r1")
    assert any("take-profit" in n for n in r2.notes)
    assert "AAA" not in b2.positions
