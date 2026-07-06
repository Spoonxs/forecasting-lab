"""P6b section D — the landing page, with enforced perf budgets.

Pinned: the Sakura treatment is present (canvas particles, film grain,
display-serif hero, tracked eyebrows, decisive easing, scroll reveals); reduced
motion kills the animation; the page is self-contained (no external
font/script/stylesheet fetch — the only http is the SVG namespace inside a
data: URI); and the perf budgets hold (inline JS < 50KB, page < 300KB, no
unsized media -> zero layout shift).
"""

from __future__ import annotations

import re

from forecasting_lab.dashboard.landing import build_landing, render_landing


def test_landing_has_the_sakura_treatment():
    h = render_landing()
    assert h.startswith("<!DOCTYPE html>")
    assert 'id="bg"' in h and "getContext('2d')" in h        # canvas particle layer
    assert 'id="grain"' in h and "@keyframes grain" in h      # film grain
    assert "--serif:" in h and "clamp(40px" in h              # display-serif hero
    assert "letter-spacing:.42em" in h                        # tracked eyebrow
    assert "cubic-bezier(.7,0,.2,1)" in h                     # decisive easing
    assert 'class="reveal"' in h                              # scroll reveals
    # real links into the app, never a faked screenshot
    assert 'href="index.html"' in h and 'href="scorecard.html"' in h and "<img" not in h
    assert "financial advice" in h


def test_reduced_motion_kills_all_motion():
    h = render_landing()
    assert "prefers-reduced-motion" in h
    assert "if(reduce) return" in h                            # no particle rAF loop under reduced motion
    # the grain animation and reveal transitions are disabled in the reduced-motion block
    block = h.split("@media (prefers-reduced-motion:reduce)")[1].split("}}")[0] if "@media (prefers-reduced-motion:reduce)" in h else h.split("prefers-reduced-motion:reduce")[1][:200]
    assert "animation:none" in block or "transition:none" in block


def test_perf_budgets_hold():
    h = render_landing()
    assert len(h.encode("utf-8")) < 300_000                   # page < 300KB
    inline_js = h.split("<script>")[-1].split("</script>")[0]
    assert len(inline_js.encode("utf-8")) < 50_000            # inline JS < 50KB
    # zero layout shift: no <img>; the canvas is CSS-sized (100vw/100vh, fixed)
    assert "<img" not in h and "width:100vw" in h and "height:100vh" in h


def test_landing_is_self_contained_no_external_fetch():
    h = render_landing()
    assert "fonts.googleapis" not in h and "fonts.gstatic" not in h
    assert "<script src=" not in h and '<link rel="stylesheet"' not in h
    assert "@import" not in h
    # no resource loaded from an external host; the only http is the SVG xmlns
    # namespace inside a self-contained data: URI (not a network fetch)
    ext = re.findall(r'(?:src|href)\s*=\s*["\']https?://', h)
    assert ext == []
    for m in re.findall(r'https?://[^\s"\'()]+', h):
        assert m.startswith("http://www.w3.org/2000/svg"), m


def test_build_landing_writes_the_file(tmp_path):
    path = build_landing(tmp_path / "site")
    assert path.name == "landing.html"
    assert path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
