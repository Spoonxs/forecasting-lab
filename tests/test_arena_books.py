"""P6c section D — the AI arena books.

Pinned: Claude's book is deterministic (same artifact -> same content hash),
mandate-legal by construction, attractive-names-only, with a stated thesis;
Codex's book is validated against the mandate (an illegal book is rejected and
the committed artifact renders WITH its date; the persisted file never carries
a staleness flag); the ledger fills entries only AFTER the book date (no
lookahead), compounds through rebalances (dated events with hash receipts +
turnover costs), accrues HYSA yield on cash, keeps SPY + HYSA benchmarks always
on the board with the open BYOM slots, labels a young book "incubating" for 7
days, and renders unpriced positions as honest n/a. No brokerage code exists in
the module.
"""

from __future__ import annotations

import json

import pytest

from forecasting_lab.agent_trader.arena_books import (
    BOOK_MANDATE,
    INCUBATION_DAYS,
    NOTIONAL,
    OPEN_SLOTS,
    ArenaLedger,
    claude_book,
    codex_book,
)
from forecasting_lab.calibration_log.audit import content_hash

PAYLOAD = {"as_of": "2026-01-01", "verdicts": {
    "NVDA": {"label": "STRONG BUY", "score": 0.62},
    "VOO": {"label": "BUY", "score": 0.30},
    "QQQ": {"label": "BUY", "score": 0.28},
    "SPY": {"label": "HOLD", "score": 0.10},
    "ZZZ": {"label": "INSUFFICIENT EVIDENCE", "score": 0.0}}}


def test_claude_book_is_deterministic_legal_and_hashed():
    a, b = claude_book(PAYLOAD), claude_book(PAYLOAD)
    assert a["sha256"] == b["sha256"]                    # same artifact -> same book
    assert a["sha256"] == content_hash({k: v for k, v in a.items() if k != "sha256"})
    syms = [p["symbol"] for p in a["picks"]]
    assert "NVDA" in syms and "SPY" not in syms and "ZZZ" not in syms  # attractive only
    assert all(p["weight"] <= BOOK_MANDATE["max_position_pct"] + 1e-9 for p in a["picks"])
    assert a["cash"] >= BOOK_MANDATE["min_cash_pct"] - 1e-9
    assert all(p["thesis"] for p in a["picks"]) and a["mandate"] == BOOK_MANDATE
    # a different artifact is a different, differently-hashed book
    p2 = {"as_of": "2026-01-02", "verdicts": {"VOO": {"label": "BUY", "score": 0.4}}}
    assert claude_book(p2)["sha256"] != a["sha256"]


def test_codex_book_valid_runner_persists_a_dated_hashed_book(tmp_path):
    def runner(prompt):
        assert "max 25%" in prompt and "NVDA" in prompt
        return ('noise before {"picks": [{"symbol": "NVDA", "weight": 0.2, "thesis": "t"},'
                '{"symbol": "VOO", "weight": 0.2, "thesis": "t"}], "thesis": "book"} after')

    book = codex_book(PAYLOAD, out_dir=tmp_path, runner=runner)
    assert book["owner"] == "codex" and book["as_of"] == "2026-01-01"
    assert book["sha256"] == content_hash({k: v for k, v in book.items() if k != "sha256"})
    persisted = json.loads((tmp_path / "codex-book.json").read_text(encoding="utf-8"))
    assert "stale" not in persisted                      # staleness computed at read
    assert (tmp_path / "codex-book-2026-01-01.json").exists()


def test_codex_book_illegal_output_is_rejected_not_raced(tmp_path):
    def over_cap(prompt):
        return '{"picks": [{"symbol": "NVDA", "weight": 0.9, "thesis": "yolo"}]}'

    assert codex_book(PAYLOAD, out_dir=tmp_path, runner=over_cap) is None  # open slot
    # with a committed artifact, the fallback renders WITH its original date
    good = codex_book(PAYLOAD, out_dir=tmp_path,
                      runner=lambda p: '{"picks": [{"symbol": "VOO", "weight": 0.2, "thesis": "t"}]}')
    assert good is not None
    fallback = codex_book({"as_of": "2026-06-30", "verdicts": PAYLOAD["verdicts"]},
                          out_dir=tmp_path, runner=over_cap)
    assert fallback["as_of"] == "2026-01-01"             # honest: the old date, kept
    # unknown symbols are dropped, which can make the book empty -> also rejected
    ghost = codex_book(PAYLOAD, out_dir=tmp_path,
                       runner=lambda p: '{"picks": [{"symbol": "GHOST", "weight": 0.2}]}')
    assert ghost["as_of"] == "2026-01-01"                # fell back, didn't race GHOST


def test_no_lookahead_entries_fill_only_after_the_book_date(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))                # dated 2026-01-01
    led.mark("2026-01-01", {"NVDA": 100.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0})
    nvda = led.state["claude"]["positions"]["NVDA"]
    assert nvda["entry"] is None                         # same-day close: not fillable
    led.mark("2026-01-02", {"NVDA": 100.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0})
    assert nvda["entry"] == 100.0 and nvda["entry_date"] == "2026-01-02"


def test_equity_marks_costs_and_hysa_accrual(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    px0 = {"NVDA": 100.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0}
    led.mark("2026-01-02", px0, hysa_yield_pct=5.0)      # entries fill here
    up = {"NVDA": 110.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0}
    led.mark("2026-02-02", up, hysa_yield_pct=5.0)
    st = led.state["claude"]
    w = st["positions"]["NVDA"]["weight"]
    expected = 1.0 + w * 0.10 + st["cash"] * 0.05 * 31 / 365
    assert st["curve"][-1]["equity"] == pytest.approx(expected, abs=1e-6)
    # the HYSA benchmark accrued its yield; SPY held flat
    assert led.state["HYSA"]["curve"][-1]["equity"] == pytest.approx(1 + 0.05 * 31 / 365, abs=1e-6)
    assert led.state["SPY"]["curve"][-1]["equity"] == pytest.approx(1.0)


def test_rebalance_is_a_dated_receipted_event_and_equity_compounds(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    px = {"NVDA": 100.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0}
    led.mark("2026-01-02", px)
    led.mark("2026-01-20", {**px, "NVDA": 120.0})
    before = led.state["claude"]["curve"][-1]["equity"]
    assert before > 1.0
    v2 = claude_book({"as_of": "2026-01-21", "verdicts": {"VOO": {"label": "BUY", "score": 0.5}}})
    led.upsert_book(v2)
    ev = led.state["claude"]["events"][-1]
    assert ev["kind"] == "rebalance" and ev["date"] == "2026-01-21"
    assert ev["sha256"] == v2["sha256"] and ev["turnover"] > 0  # the receipt
    led.mark("2026-01-22", px)
    after = led.state["claude"]["curve"][-1]["equity"]
    cost = BOOK_MANDATE["cost_bps_per_turnover"] / 1e4 * ev["turnover"] / 2
    assert after == pytest.approx(before * (1.0 - cost), abs=1e-6)  # compounds, pays the toll
    # an identical book is a no-op, not a fake rebalance
    led.upsert_book(v2)
    assert led.state["claude"]["events"][-1] is ev or led.state["claude"]["events"][-1] == ev


def test_benchmarks_and_open_slots_always_on_the_board(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    rows = led.rows("2026-01-01")                        # not a single AI book yet
    owners = [r["owner"] for r in rows]
    assert "SPY" in owners and "HYSA" in owners
    for slot in OPEN_SLOTS:
        assert slot["owner"] in owners and "open slot" in str(
            next(r for r in rows if r["owner"] == slot["owner"])["status"])
    spy = next(r for r in rows if r["owner"] == "SPY")
    assert spy["benchmark"] is True and spy["status"] == "benchmark"


def test_incubation_seven_days_before_any_label(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    led.mark("2026-01-02", {"NVDA": 100.0})
    assert led.status("claude", "2026-01-05") == "incubating"
    assert led.status("claude", f"2026-01-{2 + INCUBATION_DAYS:02d}") == "live"
    assert led.status("nobody", "2026-01-05") == "incubating"    # unknown: no label


def test_rows_are_rallies_shaped_with_honest_na(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    px = {"NVDA": 100.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0}
    led.mark("2026-01-02", px)
    rows = led.rows("2026-01-02", prices={**px, "NVDA": 110.0})
    claude = next(r for r in rows if r["owner"] == "claude")
    nvda = next(p for p in claude["positions"] if p["symbol"] == "NVDA")
    assert nvda["notional"] == pytest.approx(NOTIONAL * nvda["alloc"])
    assert nvda["worth"] == pytest.approx(nvda["notional"] * 1.10)
    assert nvda["pnl"] == pytest.approx(nvda["notional"] * 0.10) and nvda["pnl_pct"] == 0.1
    assert claude["cash"] > 0 and "total_pnl" in claude and claude["book_sha"]
    # a position with no mark yet renders n/a, never a fabricated number
    rows2 = led.rows("2026-01-02", prices={})
    nvda2 = next(p for p in next(r for r in rows2 if r["owner"] == "claude")["positions"]
                 if p["symbol"] == "NVDA")
    assert nvda2["worth"] is None and nvda2["pnl"] is None
    led.save()
    assert ArenaLedger(path=led.path).state["claude"]["book_sha"] == claude["book_sha"]


# ------------------------------------------------ Codex code-review fixes pinned
def test_empty_or_unknown_pick_books_never_persist(tmp_path):
    """Codex finding 1: an all-unknown (or empty) pick list is REJECTED, never
    persisted as a fresh all-cash artifact."""
    good = codex_book(PAYLOAD, out_dir=tmp_path,
                      runner=lambda p: '{"picks": [{"symbol": "VOO", "weight": 0.2, "thesis": "t"}]}')
    assert good["picks"]
    for bad in ('{"picks": []}', '{"picks": [{"symbol": "GHOST", "weight": 0.2}]}'):
        out = codex_book({"as_of": "2026-06-30", "verdicts": PAYLOAD["verdicts"]},
                         out_dir=tmp_path, runner=lambda p, b=bad: b)
        assert out["as_of"] == "2026-01-01"              # fallback, not a fresh empty book
    persisted = json.loads((tmp_path / "codex-book.json").read_text(encoding="utf-8"))
    assert persisted["picks"] and persisted["as_of"] == "2026-01-01"
    assert not (tmp_path / "codex-book-2026-06-30.json").exists()


def test_codex_picks_validated_against_the_attractive_menu_not_all_verdicts(tmp_path):
    """Codex finding 2: SPY is HOLD — legal weights don't make it race-eligible."""
    mixed = ('{"picks": [{"symbol": "NVDA", "weight": 0.2, "thesis": "t"},'
             '{"symbol": "SPY", "weight": 0.2, "thesis": "sneaky hold"}]}')
    book = codex_book(PAYLOAD, out_dir=tmp_path, runner=lambda p: mixed)
    assert [p["symbol"] for p in book["picks"]] == ["NVDA"]  # the HOLD name dropped
    only_hold = '{"picks": [{"symbol": "SPY", "weight": 0.2, "thesis": "t"}]}'
    assert codex_book({"as_of": "2026-07-01", "verdicts": PAYLOAD["verdicts"]},
                      out_dir=tmp_path, runner=lambda p: only_hold)["as_of"] == "2026-01-01"


def test_board_dollars_scale_with_compounded_equity(tmp_path):
    """Codex finding 3: after gains + a rebalance, position notional reflects
    the equity carried in — never a stale NOTIONAL*weight."""
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    px = {"NVDA": 100.0, "VOO": 400.0, "QQQ": 500.0, "SPY": 600.0}
    led.mark("2026-01-02", px)
    led.mark("2026-01-20", {**px, "NVDA": 120.0})
    grown = led.state["claude"]["curve"][-1]["equity"]
    v2 = claude_book({"as_of": "2026-01-21", "verdicts": {"VOO": {"label": "BUY", "score": 0.5}}})
    led.upsert_book(v2)
    led.mark("2026-01-22", px)
    row = next(r for r in led.rows("2026-01-22", prices=px) if r["owner"] == "claude")
    voo = next(p for p in row["positions"] if p["symbol"] == "VOO")
    assert voo["notional"] == pytest.approx(NOTIONAL * grown * voo["alloc"], rel=1e-6)
    # the board's dollars reconcile with the ledger's equity (no fabrication)
    board_total = sum(p["worth"] or p["notional"] for p in row["positions"]) + row["cash"]
    ledger_total = NOTIONAL * led.state["claude"]["curve"][-1]["equity"]
    assert board_total == pytest.approx(ledger_total, rel=1e-4)


def test_no_brokerage_or_order_code_in_the_arena():
    import inspect

    from forecasting_lab.agent_trader import arena_books
    src = inspect.getsource(arena_books).lower()
    for banned in ("submit_order", "place_order", "alpaca", "ibkr", "robin_stocks"):
        assert banned not in src
