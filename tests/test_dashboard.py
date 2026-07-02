from forecasting_lab.dashboard.collect import LabState
from forecasting_lab.dashboard.render import (
    equity_svg,
    reliability_svg,
    render_dashboard,
)


def _reliability_records():
    return [
        {"bin": b, "bin_low": b / 10, "bin_high": (b + 1) / 10,
         "count": 10 * (b + 1), "mean_pred": b / 10 + 0.05, "frac_pos": b / 10 + 0.04}
        for b in range(10)
    ]


def test_reliability_svg_has_line_dots_and_label():
    svg = reliability_svg(_reliability_records())
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "a perfect model sits on this line" in svg  # the diagonal, in plain words
    assert "what actually happened" in svg  # axis title, not jargon
    assert svg.count("<circle") == 10  # one dot per non-empty bin


def test_reliability_svg_empty_bins_dont_crash():
    records = _reliability_records()
    for r in records[3:6]:
        r["count"] = 0
    svg = reliability_svg(records)
    assert svg.count("<circle") == 7


def test_equity_svg_paths_and_baseline_dashes():
    curves = {"momentum_60d": [1.0, 1.1, 1.2], "random": [1.0, 0.99, 1.01]}
    svg = equity_svg(curves)
    assert svg.count("<path") == 2
    assert "stroke-dasharray" in svg  # random is a dashed control line
    assert "Momentum" in svg and "Random (control)" in svg  # plain legend names
    assert "log scale" in svg  # equity compounds; the axis must too


def _minimal_state():
    state = LabState(generated="2026-07-01 12:00")
    state.tennis = {
        "summary": {"n": 100, "base_rate": 0.5, "brier": 0.2, "log_loss": 0.6,
                    "brier_skill_score": 0.2, "ece": 0.02, "mce": 0.05,
                    "accuracy_at_0.5": 0.7, "sharpness": 0.3},
        "reliability": _reliability_records(),
        "leaderboard": [{"player": "P001", "rating": 1710.2}],
        "label": "synthetic demo data",
    }
    state.nba = {
        "summary": {"n": 100, "base_rate": 0.6, "brier": 0.23, "log_loss": 0.65,
                    "brier_skill_score": 0.05, "ece": 0.04, "mce": 0.1,
                    "accuracy_at_0.5": 0.62, "sharpness": 0.2},
        "leaderboard": [{"team": "TEAM07", "rating": 1680.0}],
        "label": "synthetic demo data",
    }
    state.soccer = {
        "eval": {"n": 100, "rps": 0.20, "rps_baseline": 0.23, "rps_skill": 0.13,
                 "base_rates": {"home": 0.44, "draw": 0.22, "away": 0.34}},
        "label": "synthetic league",
    }
    state.arena = {"empty": True, "command": "flab-sim run --bars 250"}
    state.forward = {"empty": True, "command": "flab-forward run --backfill"}
    state.strategies = [
        {"name": "momentum_60d", "kind": "trend", "description": "Buy what's been rising."},
        {"name": "random", "kind": "baseline", "description": "Coin-flip null hypothesis."},
    ]
    state.macro = {"empty": True, "command": "flab-macro"}
    state.sources = {"total": 558, "rows": []}
    state.forecast_log = {"empty": True, "command": "flab-calibration record ..."}
    state.digests = {
        "trending-stocks": {"empty": True},
        "market-divergence": {"empty": True},
        "research-digest": {"empty": True},
    }
    return state


def test_render_dashboard_full_page_with_empty_states():
    html = render_dashboard(_minimal_state())
    assert html.startswith("<!DOCTYPE html>")
    # honest framing is front and centre
    assert "not financial advice" in html
    assert "Is it actually making money?" in html  # the honest FAQ
    # plain-English section titles, not CLI commands
    assert "Are the predictions trustworthy?" in html
    assert "Strategy test (simulated)" in html
    assert "How each strategy works" in html
    assert "Economy check" in html
    assert "The ground rules" in html
    # at-a-glance verdicts translate the jargon
    assert "Well-calibrated" in html
    assert "558 sources tracked" in html
    # quality floor
    assert "prefers-reduced-motion" in html
    assert 'role="img"' in html
    # plain-language strategy copy survives (apostrophe is HTML-escaped)
    assert "been rising" in html


def test_render_dashboard_escapes_html_in_data():
    state = _minimal_state()
    state.generated = "<script>alert(1)</script>"
    html = render_dashboard(state)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
