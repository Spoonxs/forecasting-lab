"""P9-2 — the Sakura-bar landing, with enforced budgets and honesty.

Pinned: the storyboard sections S1–S5 are ALL server-rendered and readable
with no JavaScript (the WebGL canvas is only created by JS; a CSS/SVG poster
backs the hero); every number comes from the committed artifacts (real card
rows, real arena curve, real regret counts) with honest fallbacks when an
artifact is missing — never a demo number; scripts load ONLY from local
./vendor/ + ./motion.js (http(s) srcs stay forbidden); reduced motion and the
kill-switch leave the static page; budgets hold (HTML < 60KB; the vendored JS
bundle budget is pinned in test_motion_assets).
"""

from __future__ import annotations

import re

from forecasting_lab.dashboard.landing import build_landing, collect_story, render_landing

STORY = {
    "as_of": "2026-07-12", "audit": "ead0e7fcb175",
    "card": {"symbol": "AAPL", "label": "STRONG BUY", "score": 0.517,
             "dials": {"expected_return": 0.42, "drawdown_risk": 0.2,
                       "data_confidence": 0.8, "model_confidence": 0.55},
             "components": [
                 {"name": "trend", "score": 0.61, "detail": "secular-momentum z +1.8"},
                 {"name": "backtest", "score": 0.38, "detail": "walk-forward 62% of 46"},
                 {"name": "residual_momentum", "score": 0.22, "detail": "z +0.7"},
                 {"name": "macro", "score": 0.30, "detail": "recession odds 20%"}]},
    "arena": {"claude": [1.0, 1.01, 1.03, 1.02, 1.05], "SPY": [1.0, 1.0, 1.01, 1.01, 1.02]},
    "regret": {"recorded": 27, "resolved": 0, "open": 27},
}


def test_storyboard_is_server_rendered_and_readable_without_js():
    h = render_landing(STORY)
    assert h.startswith("<!DOCTYPE html>")
    for sid in ("s1", "s2", "s3", "s4", "s5"):
        assert f'id="{sid}"' in h                          # every scene in the DOM
    # the REAL numbers, present without any JS
    assert "AAPL" in h and "STRONG BUY +0.517" in h
    assert "walk-forward 62% of 46" in h                   # a real component row
    assert "27 recommendations tracked" in h
    assert 'id="poster"' in h                              # the no-JS hero poster
    assert "polyline" in h                                 # the arena SVG is static markup
    assert "not financial advice" in h.lower()
    assert "<img" not in h                                 # zero layout shift, no images


def test_honest_fallbacks_when_artifacts_are_missing():
    h = render_landing()                                   # no story at all
    assert "INSUFFICIENT EVIDENCE" in h                    # the card says so
    assert "Honest empty, never a demo number" in h
    assert "The arena opens with the first" in h
    assert "The regret ledger opens with" in h
    assert "0.517" not in h                                # nothing invented


def test_sakura_treatment_present():
    h = render_landing(STORY)
    assert 'id="grain"' in h and "@keyframes grain" in h   # film grain
    assert "--serif:" in h and "clamp(40px" in h           # display-serif hero
    assert "letter-spacing:.5em" in h                      # tracked eyebrow + rail
    assert "writing-mode:vertical-rl" in h                 # the vertical rail
    assert "cubic-bezier(.7,0,.2,1)" in h                  # decisive easing
    assert "scrollcue" in h
    assert 'href="index.html"' in h and 'href="scorecard.html"' in h


def test_motion_is_gated_and_reduced_motion_is_static():
    h = render_landing(STORY)
    assert "prefers-reduced-motion" in h
    assert "flabMotion" in h and "flabMotion.off()" in h   # the ONE kill-switch
    # both script blocks bail to the static page when motion is off
    assert h.count("static page stands") >= 1
    assert "html.motion-off #grain" in h                   # live toggle kills grain too
    # the WebGL loop self-gates every frame and pauses when the tab hides
    assert "visibilitychange" in h and "if (hidden) return" in h


def test_scripts_are_local_only():
    h = render_landing(STORY)
    srcs = re.findall(r'<script[^>]*src="([^"]+)"', h)
    assert srcs == ["vendor/gsap.min.js", "vendor/ScrollTrigger.min.js", "motion.js"]
    assert re.findall(r'(?:src|href)\s*=\s*["\']https?://', h) == []
    imports = re.findall(r"import\(['\"]([^'\"]+)", h)
    assert imports == ["./vendor/three.module.min.js"]     # three via local module import
    assert "fonts.googleapis" not in h and '<link rel="stylesheet"' not in h
    for m in re.findall(r'https?://[^\s"\'()]+', h):
        assert m.startswith("http://www.w3.org/2000/svg"), m


def test_html_budget_holds():
    h = render_landing(STORY)
    assert len(h.encode("utf-8")) < 60_000                 # HTML < 60KB


def test_gsap_choreography_targets_only_server_rendered_content():
    h = render_landing(STORY)
    # every scroll scene manipulates elements that already exist in the DOM
    for target in ("#s1 .vcard", "#s2 [data-sweep]", "#s3 [data-draw]",
                   "#s4 [data-stamp]", "#s5 h2"):
        assert target in h
    # the dials sweep TO the server-rendered truth, never to a JS value
    assert "getAttribute('stroke-dasharray')" in h


# ------------------------------------------------ Codex code-review fixes pinned
def test_both_ai_books_render_when_they_exist():
    """Codex finding 1: 'two AIs race' must not silently drop Codex's line."""
    story = dict(STORY, arena={"claude": [1.0, 1.05], "codex": [1.0, 1.02],
                               "SPY": [1.0, 1.01]})
    h = render_landing(story)
    assert "claude&#8217;s book" in h and "codex&#8217;s book" in h
    assert h.count("<polyline") == 3
    # claude-only is honest too (codex absent, not faked)
    solo = render_landing(STORY)                          # STORY has no codex curve
    assert "codex&#8217;s book" not in solo and solo.count("<polyline") == 2


def test_live_kill_disposes_webgl_and_ends_gsap():
    """Codex findings 2+3: flipping the switch after load frees the GPU and
    jumps every trigger to its END state (content fully visible)."""
    h = render_landing(STORY)
    assert "function dispose()" in h and "renderer.dispose()" in h
    assert "geometry.dispose()" in h and "m.dispose()" in h
    assert "removeEventListener('resize'" in h
    assert "st.progress(1); st.kill();" in h              # end state, then dead
    assert "gsap.ticker.remove(killWatch)" in h


def test_build_collects_the_real_story(tmp_path):
    from datetime import date

    from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts
    from forecasting_lab.signals.verdict import Component

    payload = build_verdicts(
        ["NVDA"], lambda s: {n: Component(n, 0.5, 0.9, f"{n} detail") for n in
                             ("backtest", "trend", "residual_momentum", "macro", "yield")},
        on=date(2026, 7, 12))
    vdir = tmp_path / "verdicts"
    write_verdicts(payload, out_dir=vdir)
    story = collect_story(verdicts_dir=vdir, arena_path=tmp_path / "a.json",
                          regret_path=tmp_path / "r.json")
    assert story["card"]["symbol"] == "NVDA" and story["card"]["label"]
    assert story["regret"] == {"recorded": 0, "resolved": 0, "open": 0}
    path = build_landing(tmp_path / "site", verdicts_dir=vdir,
                         arena_path=tmp_path / "a.json", regret_path=tmp_path / "r.json")
    assert "NVDA" in path.read_text(encoding="utf-8")
