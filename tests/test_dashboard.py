from forecasting_lab.dashboard.collect import LabState
from forecasting_lab.dashboard.render import (
    equity_svg,
    reliability_svg,
    render_dashboard,
    sparkline_svg,
)
from forecasting_lab.dashboard.scorecard import render_scorecard


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
    assert "#2F7D31" in up  # green line when it rose (Stock Taper palette)
    assert "#C6392C" in down  # brick line when it fell
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
    state.edge_features = {"empty": False, "rows": [
        {"name": "Cross-venue lead-lag", "skill": 0.05, "what": "who moves first", "status": "live"},
        {"name": "Attention acceleration", "skill": 0.12, "what": "mentions accelerating", "status": "accruing"},
        {"name": "Squeeze setup", "skill": 0.18, "what": "short + ignition", "status": "dormant"},
        {"name": "Favorite-longshot recalibration", "skill": 0.03, "what": "price bias", "status": "live"},
    ]}
    state.voices = {"as_of": "2026-07-03", "rows": [
        {"voice": "@early_sharp", "n_calls": 100, "brier_skill": 0.30, "lead": 3, "corr": 0.3, "weight": 0.20},
        {"voice": "@noise", "n_calls": 100, "brier_skill": -0.50, "lead": 0, "corr": 0.0, "weight": 0.0},
    ]}
    return state


def _verdicts_state():
    state = _minimal_state()
    state.verdicts = {
        "empty": False, "as_of": "2026-07-05",
        "rows": [
            {"symbol": "NVDA", "label": "STRONG BUY", "score": 0.62,
             "matrix": {"1-5y|grow|med": "STRONG BUY", "5y+|preserve|med": "HOLD"}, "is_etf": False},
            {"symbol": "VOO", "label": "BUY", "score": 0.3,
             "matrix": {"1-5y|grow|med": "BUY", "5y+|preserve|med": "BUY"}, "is_etf": True},
            {"symbol": "XYZ", "label": "INSUFFICIENT EVIDENCE", "score": 0.0,
             "matrix": {}, "is_etf": False},
        ],
        "symbols": ["NVDA", "VOO", "XYZ"],
    }
    return state


def test_home_is_the_platform_search_verdicts_profile():
    """P6b-2: the home leads with the platform hero, search, today's verdicts
    grid, the profile control, and the ETF row; the old briefing sits below."""
    html = render_dashboard(_verdicts_state())
    assert "THE" in html and "VERDICT" in html and "DESK" in html   # platform hero
    assert 'id="q"' in html and 'placeholder="Search any stock' in html  # universe search
    assert 'class="vgrid"' in html and 'href="t/NVDA.html"' in html  # today's verdicts grid
    assert ">STRONG BUY<" in html or "STRONG BUY" in html
    assert 'class="vchip insuf"' in html                            # INSUFFICIENT dimmed
    assert 'id="pcH"' in html and 'id="pcG"' in html and 'id="pcR"' in html  # profile control
    assert 'data-m=' in html                                        # matrices embedded for client swap
    assert "Core ETFs" in html and 'id="built"' in html             # ETF row + built-symbol index
    assert "esc(" in html and "fetch('universe.json')" in html      # XSS-safe search + lazy full-universe
    assert "The engine room" in html                                # old sections demoted below
    # no external fetches anywhere on the platform home
    assert "fonts.googleapis" not in html and "<script src=" not in html
    assert '<link rel="stylesheet"' not in html


def test_profile_control_keys_include_risk_and_universe_writes(tmp_path):
    """Codex P6b-2 fixes: the profile swap keys by horizon|goal|risk (risk is
    real, not ignored), and the full-universe index is written for search."""
    html = render_dashboard(_verdicts_state())
    assert "pH.value+'|'+pG.value+'|'+pR.value" in html  # risk in the lookup key
    from forecasting_lab.dashboard.tier_live import write_universe_json
    p = write_universe_json(tmp_path)
    import json
    uni = json.loads(p.read_text(encoding="utf-8"))
    assert len(uni) > 8000 and "NVDA" in uni and "TSLA" in uni  # full listed universe


def test_home_degrades_without_a_verdict_artifact():
    html = render_dashboard(_minimal_state())  # no state.verdicts set
    assert "No recommendation verdicts built yet" in html and "flab-verdicts" in html
    assert html.startswith("<!DOCTYPE html>")  # the rest of the page still renders


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
    # Phase 0 evidence contract: every pick shows odds + an expandable "why"
    assert 'class="why"' in html  # the evidence expander
    assert "· why" in html  # summary carries the odds + a "why" toggle
    assert "trend composite" in html  # a named driver on the mover pick
    # Phase 1: edge-research panel + recalibration edge surfaced on market picks
    assert "Edge research" in html
    assert "Cross-venue lead-lag" in html and "OOS skill" in html
    assert "edge vs market" in html  # favorite-longshot recalibration shows a fair-value edge
    # Phase 3: the "ahead of the curve" voice leaderboard renders with record + lead
    assert "Ahead of the curve" in html
    assert "@early_sharp" in html and "3d early" in html
    # plain-English section titles (apostrophes are HTML-escaped in titles)
    assert "moving now" in html
    assert "Strategy leaderboard" in html
    assert "Economy check" in html
    # verdicts + quality floor
    assert "Well-calibrated" in html
    assert "558 sources tracked" in html
    assert "prefers-reduced-motion" in html and 'role="img"' in html


def test_reskin_is_stock_taper_x_rallies():
    """P4 commit 1: the skin (cream + Plex Mono + mascots + going-well pairs) and
    the Rallies layout (peer strip, question chips, feed, feature-per-surface nav)."""
    state = _minimal_state()
    state.feed = [{"kind": "pick", "text": "BUY NVDA 20% — trend composite"},
                  {"kind": "resolve", "text": "resolved: said 60%, outcome 1"}]
    html = render_dashboard(state)
    # skin
    assert "#FBF7EB" in html  # cream paper
    assert "IBM Plex Mono" in html and "ui-monospace" in html  # mono with system fallback
    assert 'class="mascot"' in html  # our own tiny SVG doodles
    assert "going well?" in html and "concerning?" in html  # the Stock Taper pair
    # layout
    assert 'class="peers"' in html  # peer strip over the movers
    assert 'class="qchips"' in html and "Is anything squeezing?" in html
    assert 'data-feed-kind="pick"' in html and 'data-feed-kind="resolve"' in html
    assert "scorecard.html" in html  # the Scorecard surface is in the nav
    # self-contained: nothing external is fetched
    assert "fonts.googleapis" not in html and "<script src=" not in html
    assert '<link rel="stylesheet"' not in html


def test_render_dashboard_escapes_html_in_data():
    state = _minimal_state()
    state.generated = "<script>alert(1)</script>"
    html = render_dashboard(state)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_evidence_cards_trust_badges_and_the_arena_gate():
    """P4 commit 3: the evidence-thesis card, trust badges, honest n/a, and the
    Engo-style gate stated in the open on the arena board."""
    state = _minimal_state()
    state.arena["gate"] = {"k": 5, "survivors": [], "hold": True,
                           "benchmark": "buy & hold", "reason": "0 of 5 survive"}
    state.arena["crowding"] = {"mean_pairwise_corr": 0.61, "crowded": True, "n_variants": 5}
    state.agent = {
        "equity": 100_500.0, "return": 0.005, "n_stocks": 1, "n_markets": 0,
        "blotter": ["BUY NVDA"],
        "picks": [{"kind": "stock", "name": "NVDA", "side": "long", "entry": 120.0,
                   "mark": 123.4, "pnl": 0.028, "thesis": "trend"}],  # no alloc stored
    }
    html = render_dashboard(state)
    # the evidence-thesis card (Intel Desk mechanics, restyled)
    assert "Why now" in html and "Evidence" in html
    assert "Watch for" in html and "Red flags" in html
    assert 'class="dots"' in html  # confidence dots, probability bucketed
    assert 'class="trust"' in html and "Yahoo charts + Google News" in html
    assert "freshness unstamped" in html  # silence about freshness is the bug
    # uncomputable metrics render n/a — never reconstructed
    assert ">n/a<" in html
    # the gate stated in the open + the crowding gauge + benchmark on the board
    assert "THE GATE: 5 candidates" in html
    assert "100% buy &amp; hold" in html or "100% buy & hold" in html
    assert "Crowding gauge" in html and "crowded" in html
    assert "Random (control)" in html  # a benchmark row is always on the board


def test_scorecard_empty_state_claims_nothing():
    """P4 commit 2: an empty log states the zero denominator instead of a score."""
    state = _minimal_state()
    state.scorecard = {"empty": True}
    html = render_scorecard(state)
    assert html.startswith("<!DOCTYPE html>")
    assert "denominator is 0" in html and "no score is claimed" in html
    assert "only resolved forecasts are scored" in html
    assert "Not financial advice" in html
    assert "fonts.googleapis" not in html and "<script src=" not in html


def test_scorecard_pins_the_miss_ledger_and_audits_open_forecasts():
    state = _minimal_state()
    state.scorecard = {
        "empty": False, "n_resolved": 3, "n_open": 2,
        "score": {"n": 3, "brier": 0.21, "brier_skill_score": 0.12},
        "beat": {"n": 2, "brier_skill_vs_market": 0.05, "beat_rate": 0.5},
        "reliability": _reliability_records(),
        # collect sorts worst (highest sq_error) first — the render must keep it
        "rows": [
            {"date": "2026-06-01", "question": "Big miss?", "prob": 0.9, "outcome": 0, "sq_error": 0.81},
            {"date": "2026-06-02", "question": "Close call?", "prob": 0.6, "outcome": 1, "sq_error": 0.16},
            {"date": "2026-06-03", "question": "Easy hit?", "prob": 0.9, "outcome": 1, "sq_error": 0.01},
        ],
        "open_rows": [
            {"date": "2026-07-01", "question": "Still open?", "prob": 0.55},
            {"date": "2026-07-02", "question": "Also open?", "prob": 0.4},
        ],
    }
    html = render_scorecard(state)
    assert "<b>3</b> resolved" in html and "<b>2</b> open" in html  # the honest denominator
    assert "miss ledger" in html and "never hidden" in html
    assert html.index("Big miss?") < html.index("Close call?") < html.index("Easy hit?")
    assert 'class="miss"' in html  # the worst call is visually pinned
    assert "Under audit" in html and "Still open?" in html and "not yet counted" in html
    assert "Beats the closing line by" in html
    assert "a perfect model sits on this line" in html  # the reliability SVG renders


def test_render_dashboard_degrades_when_scans_are_empty():
    state = _minimal_state()
    state.movers = {"empty": True}
    state.market_edges = {"empty": True}
    html = render_dashboard(state)
    assert "flab-trending" in html  # empty state points to the command that fills it
    assert html.count("<section") >= 6  # the rest of the page still renders
