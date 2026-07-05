"""The Agent Terminal renders a dark, alive desk view from the agent's real book."""

from __future__ import annotations

import json
from types import SimpleNamespace

from forecasting_lab.agent_trader.terminal import load_ledger, render_terminal


def _state(picks, ledger=None):
    return SimpleNamespace(
        generated="2026-07-03 09:00",
        movers={"movers": [{"ticker": "NVDA", "ret_5d": 0.03}, {"ticker": "GME", "ret_5d": -0.05}]},
        agent={"equity": 101_500.0, "return": 0.015, "n_stocks": 2, "n_markets": 1,
               "blotter": ["BUY NVDA @ $100.00 — 60-day trend", "BET NO · 'Will X win?' @ 30%"],
               "picks": picks},
        ledger=ledger or {"empty": True},
    )


def _snap(run_id, equity, fills=0, halted=False, notes=(), **extra):
    return {"run_id": run_id, "equity": equity, "fills": fills,
            "halted": halted, "notes": list(notes), **extra}


def test_terminal_renders_book_desks_heatmap_and_chat():
    picks = [
        {"kind": "stock", "name": "NVDA", "side": "long", "prob": 0.62, "entry": 100.0, "mark": 108.0, "pnl": 0.08, "thesis": "momentum"},
        {"kind": "market", "name": "Will X win?", "side": "NO", "prob": 0.20, "entry": 0.30, "mark": 0.28, "pnl": 0.02, "thesis": "fair 20%"},
    ]
    html = render_terminal(_state(picks))
    assert html.startswith("<!DOCTYPE html>")
    assert "Agent Book" in html and "$101,500" in html          # the book equity
    assert "The desk" in html and "Firm chat" in html            # team + activity feed
    assert 'class="tape"' in html and "NVDA" in html             # ticker tape
    assert 'class="heat"' in html and "+8.0%" in html            # positions heatmap with P&L
    assert "FILL" in html or "BET" in html                       # blotter in the chat
    assert "index.html" in html                                  # link back to the briefing
    assert "not financial advice" in html.lower()


def test_terminal_handles_an_empty_book():
    html = render_terminal(_state([]))
    assert "hasn't opened any paper positions" in html
    assert html.startswith("<!DOCTYPE html>")


# ------------------------------------------------------- P5 commit A: console
def test_pill_states_never_guess():
    # NO DATA when the ledger is absent
    html = render_terminal(_state([]))
    assert "NO DATA" in html and "no runs in the ledger yet" in html
    # OPERATIONAL after a clean run
    ok = {"empty": False, "skipped": 0, "n_total": 1,
          "snapshots": [_snap("r1", 100_500.0, fills=2)]}
    html_ok = render_terminal(_state([], ledger=ok))
    assert "OPERATIONAL" in html_ok and "last run completed" in html_ok
    # HALTED says WHICH guardrail fired, in plain English
    halted = {"empty": False, "skipped": 0, "n_total": 2, "snapshots": [
        _snap("r1", 100_500.0),
        _snap("r2", 100_400.0, halted=True,
              notes=["mandate BLOCK: AAA: 40% of invested capital exceeds the 25% cap"]),
    ]}
    html_halt = render_terminal(_state([], ledger=halted))
    assert "HALTED" in html_halt and "mandate blocked the proposal" in html_halt
    kill = {"empty": False, "skipped": 0, "n_total": 1, "snapshots": [
        _snap("r1", 90_000.0, halted=True,
              notes=["kill switch: daily drawdown limit breached — HALT"])]}
    assert "kill switch halted" in render_terminal(_state([], ledger=kill))


def test_heartbeat_shows_equity_change_and_degrades_honestly():
    ledger = {"empty": False, "skipped": 1, "n_total": 2, "snapshots": [
        _snap("r1", 100_000.0), _snap("r2", 101_000.0, fills=3)]}
    html = render_terminal(_state([], ledger=ledger))
    assert "last run" in html and "r2" in html
    assert "+1.00%" in html  # equity vs the prior snapshot
    assert "fills last run" in html and ">3<" in html
    assert "1 malformed ledger line(s) skipped" in html  # counted, not hidden
    empty = render_terminal(_state([]))
    assert "no runs yet" in empty


def test_mandate_desk_notes_render_violations_and_skips_verbatim():
    ledger = {"empty": False, "skipped": 0, "n_total": 1, "snapshots": [
        _snap("r1", 100_000.0, halted=True,
              notes=["mandate BLOCK: AAA over cap"],
              mandate={"status": "block",
                       "violations": ["AAA: 50% of invested capital exceeds the 25% cap"],
                       "warnings": ["unknown rule type 'max_postion_pct'"],
                       "skipped": ["max_sector_pct(tech): no sector data — skipped, not blocked"]})]}
    html = render_terminal(_state([], ledger=ledger))
    assert "Mandate" in html
    assert "50% of invested capital exceeds the 25% cap" in html
    assert "no sector data — skipped, not blocked" in html  # the honesty line, verbatim
    assert "a decision, not an order" in html


def test_load_ledger_is_defensive(tmp_path):
    path = tmp_path / "ledger.jsonl"
    assert load_ledger(path) == {"empty": True}  # missing file
    rows = [json.dumps(_snap(f"r{i}", 100_000 + i)) for i in range(25)]
    path.write_text("\n".join(rows[:10]) + "\nNOT JSON\n" + "\n".join(rows[10:]) + "\n[1,2]\n",
                    encoding="utf-8")
    out = load_ledger(path, limit=20)
    assert out["empty"] is False
    assert len(out["snapshots"]) == 20  # newest N only
    assert out["snapshots"][-1]["run_id"] == "r24"
    assert out["skipped"] == 2  # the junk lines are counted, never a crash
