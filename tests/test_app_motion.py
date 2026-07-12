"""P9-3 — the restrained app-page motion layer.

Pinned: motion.js is the ONLY script loaded by src on app pages; the verdict
dials carry data-sweep (they animate to the server-rendered truth), the home
sources counter carries data-count (it eases to the printed number), the
research tabs get a pure-UI active state, and the html.motion-off class kills
every transition/animation on both pages — no data the page doesn't already
have is ever animated.
"""

from __future__ import annotations

import re

from forecasting_lab.dashboard.collect import collect_lab_state
from forecasting_lab.dashboard.render import render_dashboard
from forecasting_lab.dashboard.verdict_page import render_verdict_page
from forecasting_lab.signals.verdict import scoring_contract

ROW = {"label": "BUY", "score": 0.31,
       "dials": {"expected_return": 0.42, "drawdown_risk": 0.2,
                 "data_confidence": 0.8, "model_confidence": 0.7},
       "components": {}, "missing": [], "labels_by_profile": {}, "reasons": []}
# Codex review: the src extractor must catch single quotes and spacing too
SRC_RE = re.compile(r"<script[^>]*src\s*=\s*[\"']?([^\"'\s>]+)", re.I)


def script_srcs(html: str) -> list[str]:
    srcs = SRC_RE.findall(html)
    assert all(not s.lower().startswith(("http:", "https:", "//")) for s in srcs), srcs
    return srcs


def test_verdict_page_motion_is_restrained_and_killable():
    html = render_verdict_page("NVDA", ROW, scoring_contract())
    assert html.count("data-sweep") == 4                 # the four dials sweep
    assert script_srcs(html) == ["../motion.js"]
    assert ".rtabs a.on{" in html                        # tab active state
    assert "b.classList.toggle('on',b===a)" in html      # pure UI, no data
    assert "html.motion-off *{transition:none!important" in html


def test_home_counter_and_kill_css():
    html = render_dashboard(collect_lab_state(seed=0))
    assert "data-count" in html and "sources tracked" in html
    assert script_srcs(html) == ["motion.js"]
    assert "html.motion-off .reveal" in html
    # Codex review: the kill covers ANIMATIONS too (the home .draw keyframes)
    assert "animation:none !important" in html.split("html.motion-off *")[1][:80]
