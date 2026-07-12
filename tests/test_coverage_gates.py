"""P8-4 — the acceptance gates + the coverage panel.

Pinned: coverage_stats computes % rated / median components / panel failures
and passes the gate only at or above the stated bar; the manifest carries a
schema version; the home coverage panel renders the gate verdict (GATE OK /
GATE MISSED), the availability table and the missingness reasons, with an
honest empty state before the first manifested run; a missed gate is loud,
never silently shipped.
"""

from __future__ import annotations

from forecasting_lab.pipeline.providers import RATED_GATE, coverage_stats


def _payload(rated: int, unrated: int) -> dict:
    v = {}
    for i in range(rated):
        v[f"R{i}"] = {"label": "BUY", "score": 0.3,
                      "components": {"trend": {}, "macro": {}, "backtest": {}}}
    for i in range(unrated):
        v[f"U{i}"] = {"label": "INSUFFICIENT EVIDENCE", "score": 0.0, "components": {}}
    return {"verdicts": v}


def test_gate_passes_only_at_or_above_the_bar():
    ok = coverage_stats(_payload(7, 3), {})              # 70% >= 60%
    assert ok["gate_passed"] is True and ok["pct_rated"] == 0.7
    assert ok["gate_pct_rated"] == RATED_GATE
    miss = coverage_stats(_payload(5, 5), {})            # 50% < 60%
    assert miss["gate_passed"] is False
    edge = coverage_stats(_payload(6, 4), {})            # exactly 60% passes
    assert edge["gate_passed"] is True
    empty = coverage_stats({"verdicts": {}}, {})
    assert empty["rated"] == 0 and empty["gate_passed"] is False


def test_stats_carry_median_components_and_failures():
    s = coverage_stats(_payload(3, 2),
                       {"panel_run": {"failed": [{"symbol": "X"}, {"symbol": "Y"}]}})
    assert s["median_components"] == 3.0                 # odd count: the true middle
    assert s["panel_failures"] == 2
    assert s["n_symbols"] == 5
    # Codex review: the upper-middle shortcut overstated even counts —
    # [0, 0, 3, 3] is 1.5, never 3
    even = coverage_stats(_payload(2, 2), {})
    assert even["median_components"] == 1.5


def test_manifest_schema_version_ships():
    from datetime import date

    from forecasting_lab.pipeline.providers import build_real_provider

    _, manifest = build_real_provider([], as_of=date(2026, 7, 12))
    assert manifest["schema_version"] == 1


def test_coverage_panel_renders_gate_and_reasons(tmp_path):
    import json

    from forecasting_lab.dashboard import render as render_mod

    # honest empty state first
    empty = render_mod._coverage_panel_html(tmp_path / "none.json")
    assert "No run manifest yet" in empty
    vdir = tmp_path / "data" / "verdicts"
    vdir.mkdir(parents=True)
    (vdir / "manifest.json").write_text(json.dumps({
        "as_of": "2026-07-12",
        "components_available": {"trend": 60, "yield": 0},
        "missing_reasons": {"yield": "no per-instrument dividend-yield source yet"},
        "coverage": {"n_symbols": 60, "rated": 60, "pct_rated": 1.0,
                     "median_components": 4, "panel_failures": 0,
                     "gate_pct_rated": 0.6, "gate_passed": True},
    }), encoding="utf-8")
    html = render_mod._coverage_panel_html(vdir / "manifest.json")
    assert "GATE OK" in html and "60/60 rated" in html
    assert "dividend-yield source" in html and ">trend<" in html
    # a missed gate is loud on screen
    m = json.loads((vdir / "manifest.json").read_text(encoding="utf-8"))
    m["coverage"]["gate_passed"] = False
    m["coverage"]["rated"] = 10
    (vdir / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    assert "GATE MISSED" in render_mod._coverage_panel_html(vdir / "manifest.json")
