"""P6d section A — the decision journal.

Pinned: the journal surface renders server-side with an honest empty state and
the embedded PUBLIC regret rows (reduced: no basket internals, resolved rows
carry the edges, open rows don't); the page has NO fetch/upload path — journal
entries live in localStorage only; the client join is keyed symbol+as_of with
honest "not tracked" / "not yet resolved" branches; hostile text can't break
out of the embedded JSON; the ticker and portfolio pages both write the SAME
flab_journal store and link the journal; the encrypted export covers the
journal (legacy holdings-only imports still work); build writes the page with
and without a regret ledger.
"""

from __future__ import annotations

import json

from forecasting_lab.calibration_log.regret import RegretLedger
from forecasting_lab.dashboard.journal_page import (
    build_journal_page,
    regret_join_rows,
    render_journal_page,
)

RECS = [{"symbol": "NVDA", "label": "STRONG BUY", "score": 0.62},
        {"symbol": "VOO", "label": "BUY", "score": 0.30}]


def _ledger(tmp_path) -> RegretLedger:
    led = RegretLedger(path=tmp_path / "regret.json")
    led.record("2026-01-01", RECS, {"NVDA": 100.0, "VOO": 400.0},
               spy_price=500.0, hysa_yield_pct=5.0)
    led.resolve("2026-02-06", {"NVDA": 110.0}, spy_price=520.0)  # VOO stays open
    return led


def test_regret_reduction_is_public_and_minimal(tmp_path):
    rows = regret_join_rows(_ledger(tmp_path))
    nvda = next(r for r in rows if r["symbol"] == "NVDA")
    voo = next(r for r in rows if r["symbol"] == "VOO")
    assert nvda["resolved"] is True and nvda["edge_spy"] is not None
    assert nvda["as_of"] == "2026-01-01" and nvda["horizon_days"] == 30
    assert voo["resolved"] is False and "edge_spy" not in voo  # open: no numbers
    allowed = {"symbol", "as_of", "horizon_days", "resolved",
               "return", "edge_spy", "edge_hysa"}
    assert all(set(r) <= allowed for r in rows)  # no basket prices, nothing extra


def test_page_renders_empty_state_and_join_branches(tmp_path):
    html = render_journal_page(regret_join_rows(_ledger(tmp_path)))
    assert html.startswith("<!DOCTYPE html>")
    assert "No decisions logged yet" in html                 # server-rendered empty state
    blob = html.split('id="regret" type="application/json">')[1].split("</script>")[0]
    parsed = json.loads(blob.replace("\\u003c", "<").replace("\\u003e", ">"))
    assert any(r["symbol"] == "NVDA" and r["resolved"] for r in parsed)
    # the honest client branches exist verbatim
    assert "not tracked" in html and "not yet resolved" in html
    assert "beat" in html and "lagged" in html
    assert "not financial advice" in html.lower()


def test_journal_never_leaves_the_browser(tmp_path):
    html = render_journal_page(regret_join_rows(_ledger(tmp_path)))
    assert "flab_journal" in html and "localStorage" in html
    for banned in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "WebSocket",
                   "<script src=", "fonts.googleapis", "http://", "https://"):
        assert banned not in html


def test_hostile_regret_text_cannot_escape_the_json(tmp_path):
    rows = [{"symbol": "</script><img src=x onerror=alert(1)>", "as_of": "d",
             "horizon_days": 30, "resolved": False}]
    html = render_journal_page(rows)
    blob = html.split('id="regret" type="application/json">')[1].split("</script>")[0]
    assert "</script" not in blob and "onerror=alert(1)>" not in blob


def test_build_with_and_without_a_ledger(tmp_path):
    led = _ledger(tmp_path)
    led.save()
    page = build_journal_page(tmp_path / "site", regret_path=led.path)
    assert page.name == "journal.html" and "NVDA" in page.read_text(encoding="utf-8")
    bare = build_journal_page(tmp_path / "site2", regret_path=tmp_path / "none.json")
    text = bare.read_text(encoding="utf-8")
    assert "No decisions logged yet" in text                 # honest, never blank
    assert json.loads(text.split('id="regret" type="application/json">')[1]
                      .split("</script>")[0]) == []


def test_ticker_and_portfolio_pages_write_the_same_journal_store():
    from forecasting_lab.dashboard.portfolio_page import render_portfolio_page
    from forecasting_lab.dashboard.verdict_page import render_verdict_page
    from forecasting_lab.signals.verdict import scoring_contract

    row = {"label": "BUY", "score": 0.31,
           "dials": {"expected_return": 0.4, "drawdown_risk": 0.2,
                     "data_confidence": 0.8, "model_confidence": 0.7},
           "components": {}, "missing": [], "labels_by_profile": {}, "reasons": []}
    tick = render_verdict_page("NVDA", row, scoring_contract(), as_of="2026-07-05")
    port = render_portfolio_page({"as_of": "2026-07-05", "verdicts": {
        "VOO": {"label": "BUY", "score": 0.3}}})
    for html in (tick, port):
        assert "flab_journal" in html and "journal.html" in html
    assert "I followed this" in tick and "I ignored this" in tick
    assert 'data-a="followed"' in port and 'data-a="ignored"' in port
    # the portfolio export now covers the journal; legacy imports still work
    assert "journal:jn" in port and "Array.isArray(data)" in port
