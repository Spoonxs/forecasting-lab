from forecasting_lab.dashboard.collect import LabState
from forecasting_lab.dashboard.render import (
    equity_svg,
    reliability_svg,
    render_dashboard,
    sparkline_svg,
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


def test_sparkline_colors_by_net_move():
    up = sparkline_svg([1.0, 1.1, 1.3])
    down = sparkline_svg([1.3, 1.1, 1.0])
    assert up.startswith("<svg") and "role=\"img\"" in up
    assert "#0B6B3A" in up  # green line when it rose
    assert "#B0281A" in down  # red line when it fell
    assert sparkline_svg([1.0]).endswith("</svg>")  # too-short series doesn't crash


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
    state.arena = {
        "empty": False, "bar": 300, "total_bars": 600, "pbo": 0.12,
        "leaderboard": [
            {"strategy": "momentum_60d", "total_return": 0.30, "sharpe": 1.5, "deflated_sharpe": 0.6, "max_drawdown": -0.1},
            {"strategy": "ml_ranker", "total_return": -0.05, "sharpe": -0.2, "deflated_sharpe": 0.02, "max_drawdown": -0.2},
        ],
        "curves": {"momentum_60d": [1.0, 1.1, 1.3], "ml_ranker": [1.0, 0.98, 0.95]},
    }
    state.forward = {"empty": True, "command": "flab-forward run --backfill"}
    state.strategies = [
        {"name": "momentum_60d", "kind": "trend", "description": "Buy what's been rising."},
        {"name": "ml_ranker", "kind": "ml", "description": "A machine-learning model."},
        {"name": "random", "kind": "baseline", "description": "Coin-flip null hypothesis."},
    ]
    state.macro = {"empty": True, "command": "flab-macro"}
    state.sources = {"total": 558, "rows": []}
    state.forecast_log = {"empty": True, "command": "flab-calibration record ..."}
    state.digests = {"media-watch": {"empty": True}}
    state.movers = {
        "reddit_ok": False,
        "movers": [{"ticker": "NVDA", "last": 123.4, "ret_5d": 0.03, "ret_20d": 0.1,
                    "ret_60d": 0.4, "pct_from_high": -0.02, "momentum": 1.2, "fast_money": 0.3,
                    "spark": [100, 105, 110, 123.4], "headline": "NVIDIA hits record"}],
        "fast": [{"ticker": "GME", "last": 25.0, "ret_5d": 0.2, "ret_20d": 0.1,
                  "ret_60d": -0.1, "pct_from_high": -0.3, "momentum": 0.1, "fast_money": 2.0,
                  "spark": [20, 30, 22, 25], "headline": "GME volume spikes"}],
    }
    state.market_edges = {"n_kalshi": 40, "n_poly": 100, "edges": [
        {"event": "Will X happen?", "kalshi": 0.42, "poly": 0.55, "net_edge": 0.1,
         "direction": "buy_kalshi", "poly_event": "X happens", "similarity": 0.9},
    ]}
    return state


def test_render_dashboard_is_an_interactive_visual_tool():
    html = render_dashboard(_minimal_state())
    assert html.startswith("<!DOCTYPE html>")
    # honest framing stays front and centre
    assert "financial advice" in html
    assert "Is it actually making money?" in html
    # editorial masthead: dateline + issue number
    assert "The Forecasting Briefing" in html and "No. " in html
    # it's a tool: nav, tabs, sortable tables, live clock
    assert "<nav>" in html
    assert 'class="sortable"' in html and "th[data-sort]" in html  # click-to-sort wired
    assert 'data-tab-group="movers"' in html  # tabbed movers
    assert 'id="clock"' in html  # "updated N ago" live stamp
    # real data surfaced, not prose: sparkline + odds bars + ticker
    assert "NVDA" in html and "class=\"spark\"" in html  # a price chart is drawn
    assert "Kalshi" in html and "Polymarket" in html  # odds shown side by side
    assert "Will X happen?" in html
    # the ML model is surfaced against the rules
    assert "ML model" in html and "ranks #2" in html
    # plain-English section titles (apostrophes are HTML-escaped in titles)
    assert "moving now" in html
    assert "Strategy leaderboard" in html
    assert "Economy check" in html
    # verdicts + quality floor
    assert "Well-calibrated" in html
    assert "558 sources tracked" in html
    assert "prefers-reduced-motion" in html and 'role="img"' in html


def test_render_dashboard_escapes_html_in_data():
    state = _minimal_state()
    state.generated = "<script>alert(1)</script>"
    html = render_dashboard(state)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_dashboard_degrades_when_scans_are_empty():
    state = _minimal_state()
    state.movers = {"empty": True}
    state.market_edges = {"empty": True}
    html = render_dashboard(state)
    assert "flab-trending" in html  # empty state points to the command that fills it
    assert html.count("<section") >= 6  # the rest of the page still renders
