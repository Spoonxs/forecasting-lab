"""The Agent Terminal renders a dark, alive desk view from the agent's real book."""

from __future__ import annotations

from types import SimpleNamespace

from forecasting_lab.agent_trader.terminal import render_terminal


def _state(picks):
    return SimpleNamespace(
        generated="2026-07-03 09:00",
        movers={"movers": [{"ticker": "NVDA", "ret_5d": 0.03}, {"ticker": "GME", "ret_5d": -0.05}]},
        agent={"equity": 101_500.0, "return": 0.015, "n_stocks": 2, "n_markets": 1,
               "blotter": ["BUY NVDA @ $100.00 — 60-day trend", "BET NO · 'Will X win?' @ 30%"],
               "picks": picks},
    )


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
