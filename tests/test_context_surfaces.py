"""P7 section D — the external-positioning context surfaces.

Pinned: the ticker-page context module renders 13F holders and congressional
trades with a staleness statement on EVERY row and the standing "context, not
signal" banner; the empty state is honest and points at the health panel;
hostile names are escaped; the Context tab anchors a real section; both
connectors appear in the sources registry and the health panel (with "never
fetched" as their honest first state); and the module never touches the
verdict engine.
"""

from __future__ import annotations

from forecasting_lab.dashboard.verdict_page import _context_module, render_verdict_page
from forecasting_lab.signals.verdict import scoring_contract

ROW = {"label": "BUY", "score": 0.31,
       "dials": {"expected_return": 0.4, "drawdown_risk": 0.2,
                 "data_confidence": 0.8, "model_confidence": 0.7},
       "components": {}, "missing": [], "labels_by_profile": {}, "reasons": []}
HOLDERS = [{"manager": "Berkshire Hathaway", "issuer": "APPLE INC",
            "value_kusd": 1234567.0,
            "staleness": "positions as of 2026-03-31, filed 45d later — 102d old today; context, not signal"}]
TRADES = [{"member": "Hon. A Member", "chamber": "house", "ticker": "AAPL",
           "type": "purchase", "amount_range": "$1,001 - $15,000",
           "transaction_date": "2026-06-01", "disclosed_date": "2026-07-01",
           "lag_days": 30}]


def test_module_states_staleness_on_every_row():
    html = _context_module("AAPL", HOLDERS, TRADES)
    assert "Context — external positioning" in html
    assert "old by design" in html and "never enters a verdict" in html
    assert "Berkshire Hathaway" in html and "102d old today" in html
    assert "Hon. A Member" in html and "30d lag" in html
    assert "disclosed 2026-07-01" in html
    # a lagless row says n/a, never a fabricated number
    nolag = _context_module("AAPL", [], [dict(TRADES[0], lag_days=None,
                                              transaction_date=None)])
    assert "lag n/a" in nolag and "traded n/a" in nolag


def test_empty_state_is_honest_and_points_at_health():
    html = _context_module("AAPL", [], [])
    assert "None on record" in html and "health panel" in html
    assert "never guessed" in html.lower() or "Honest empty" in html
    # Codex review: the standing banner is on the EMPTY state too
    assert "old by design" in html and "never enters a verdict" in html


def test_hostile_lag_value_is_escaped():
    """Codex review: a corrupted digest can't inject through lag_days."""
    evil = [dict(TRADES[0], lag_days='<img src=x onerror=alert(1)>')]
    html = _context_module("AAPL", [], evil)
    assert "<img src=x onerror" not in html and "&lt;img" in html


def test_hostile_names_are_escaped():
    evil = [{"manager": "<img src=x onerror=alert(1)>", "issuer": "<script>x</script>",
             "value_kusd": 1.0, "staleness": "<b>old</b>"}]
    html = _context_module("AAPL", evil, [])
    assert "<img src=x onerror" not in html and "<script>x</script>" not in html
    assert "&lt;img" in html


def test_page_carries_the_context_tab_and_section():
    html = render_verdict_page("AAPL", ROW, scoring_contract(),
                               holders=HOLDERS, trades=TRADES)
    assert 'href="#context"' in html and 'id="context"' in html
    assert "Berkshire Hathaway" in html
    bare = render_verdict_page("AAPL", ROW, scoring_contract())
    assert "None on record" in bare                      # no digests -> honest empty


def test_connectors_registered_and_in_the_health_panel(tmp_path):
    from forecasting_lab.pipeline.health import connector_health
    from forecasting_lab.sources.registry import source_groups

    names = {g.name for g in source_groups()}
    assert "13F holders" in names and "Congress trades" in names

    class _EmptyStore:
        def load(self):
            import pandas as pd

            return pd.DataFrame(columns=["date", "entity", "metric", "value"])

    (tmp_path / "inputs").mkdir()
    rows = {r["name"]: r for r in connector_health(
        "2026-07-11", inputs_dir=tmp_path / "inputs",
        verdicts_dir=tmp_path / "v", store=_EmptyStore())}
    assert rows["13F holders"]["status"] == "never"      # honest first state
    assert rows["Congress trades"]["status"] == "never"


def test_context_never_touches_the_verdict_engine():
    before = scoring_contract()["base_weights"]
    _context_module("AAPL", HOLDERS, TRADES)
    assert scoring_contract()["base_weights"] == before
