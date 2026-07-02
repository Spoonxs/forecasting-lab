"""The intraday refresh runs only the fast jobs and rebuilds the dashboard."""

from __future__ import annotations

from forecasting_lab.cli import intraday
from forecasting_lab.dashboard.render import _odds_board


def test_intraday_runs_only_fast_jobs(monkeypatch):
    captured = {}

    def fake_run_all(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr("forecasting_lab.cli.run_all.main", fake_run_all)
    rc = intraday.main([])
    assert rc == 0
    argv = captured["argv"]
    assert argv[0] == "--only"
    fast = set(intraday.FAST_JOBS)
    # the heavy once-a-day jobs are never in the intraday set
    assert fast.isdisjoint({"research", "media", "sim", "forward"})
    assert "dashboard" in fast and "trending" in fast and "divergence" in fast
    # no alert unless asked
    assert "alert" not in argv


def test_intraday_alert_flag_adds_alert(monkeypatch):
    captured = {}
    monkeypatch.setattr("forecasting_lab.cli.run_all.main", lambda argv: captured.setdefault("argv", argv) or 0)
    intraday.main(["--alert"])
    assert "alert" in captured["argv"]


def test_odds_board_shows_live_odds_when_no_arb():
    edges = {
        "edges": [], "matched": [],
        "live": {
            "poly": [{"event": "Will USA win the World Cup?", "yes": 0.03}],
            "kalshi": [{"event": "Will humans land on Mars before 2050?", "yes": 0.22}],
        },
    }
    html = _odds_board(edges)
    assert "Will USA win the World Cup?" in html
    assert "Will humans land on Mars before 2050?" in html
    assert "3% yes" in html and "22% yes" in html
    assert "Polymarket" in html and "Kalshi" in html


def test_odds_board_flags_cross_venue_gap():
    edges = {"edges": [{"event": "Fed cut?", "kalshi": 0.4, "poly": 0.55,
                        "net_edge": 0.1, "direction": "buy_kalshi",
                        "poly_event": "Rate cut", "similarity": 0.8}]}
    html = _odds_board(edges)
    assert "Cross-venue gaps" in html and "Fed cut?" in html
    assert "gap after fees" in html
