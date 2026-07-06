"""P6b section C — compare page + materiality change feed.

Pinned: compare renders two tickers side-by-side with a per-component data map
embedded (self-contained, no fetch, XSS-safe); the change feed attributes each
label change to the component that drove it and is honest with one artifact;
build_compare_page writes from a fixture and degrades to no page without one.
"""

from __future__ import annotations

from datetime import date

from forecasting_lab.dashboard.compare import (
    build_compare_page,
    materiality_changes,
    materiality_feed_html,
    render_compare_page,
)
from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts
from forecasting_lab.signals.verdict import Component


def _payload(trend_score: float):
    def provider(sym):
        return {"trend": Component("trend", trend_score, 0.9, f"trend {trend_score:+.2f}"),
                "macro": Component("macro", -0.1, 0.7, "recession odds 30%"),
                "backtest": Component("backtest", 0.3, 0.85, "OOS Sharpe 0.7")}
    return build_verdicts(["NVDA", "VOO"], provider, on=date(2026, 7, 5))


def test_compare_page_is_self_contained_and_side_by_side():
    html = render_compare_page(_payload(0.5), "NVDA", "VOO")
    assert html.startswith("<!DOCTYPE html>")
    assert html.count("<select") == 2                       # two ticker pickers
    assert 'id="cmap"' in html and '"NVDA"' in html         # the per-symbol map is embedded
    assert "win" in html                                    # per-row winner styling exists
    assert "esc(" in html                                   # XSS-safe client rendering
    assert "fonts.googleapis" not in html and "<script src=" not in html


def test_materiality_attributes_the_driving_component():
    """The spec example: a label change is explained by the component that moved."""
    latest = _payload(-0.3)    # trend turned negative -> lower verdict
    prior = _payload(0.8)      # trend was strongly positive
    changes = materiality_changes(latest, prior)
    nvda = next((c for c in changes if c["symbol"] == "NVDA"), None)
    assert nvda is not None
    assert nvda["was"] != nvda["now"]                       # the label actually changed
    assert "Trend" in nvda["why"] and "-1.1" in nvda["why"]  # attributed + signed delta
    assert nvda["dir"] == "down"                            # a downgrade (driver moved DOWN with it)


def test_insufficient_transition_is_neutral_not_an_upgrade():
    """Codex fix: INSUFFICIENT EVIDENCE -> AVOID must not render as a green upgrade."""
    from forecasting_lab.dashboard.compare import materiality_changes as mc
    latest = {"verdicts": {"X": {"label": "AVOID", "score": -0.6,
                                 "components": {"trend": {"score": -0.6, "confidence": 0.9}}}}}
    prior = {"verdicts": {"X": {"label": "INSUFFICIENT EVIDENCE", "score": 0.0, "components": {}}}}
    [ch] = mc(latest, prior)
    assert ch["dir"] == "neutral"                           # not up/down
    assert "rate it now" in ch["why"]


def test_change_feed_is_honest_with_one_or_zero_changes():
    assert "first build" in materiality_feed_html([], has_prior=False).lower()
    assert "No verdict changed" in materiality_feed_html([], has_prior=True)
    assert materiality_changes(_payload(0.5), None) == []   # no prior -> nothing claimed


def test_build_compare_writes_or_degrades(tmp_path):
    vdir = tmp_path / "v"
    write_verdicts(_payload(0.5), out_dir=vdir)
    assert build_compare_page(tmp_path / "site", verdicts_dir=vdir) is True
    assert (tmp_path / "site" / "compare.html").read_text(encoding="utf-8").startswith("<!DOCTYPE")
    assert build_compare_page(tmp_path / "site2", verdicts_dir=tmp_path / "none") is False
