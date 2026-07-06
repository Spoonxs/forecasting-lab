"""The lab dashboard: a static, single-file HTML terminal view of the lab.

``flab-dashboard`` collects the lab's real artifacts (model calibration, Elo
leaderboards, the strategy arena's saved state, the latest signal digests) and
renders one self-contained HTML file — no server, no JS frameworks, hand-rolled
SVG. Open it in a browser; regenerate it whenever the lab moves.
"""

from .collect import collect_lab_state
from .compare import build_compare_page, render_compare_page
from .render import render_dashboard
from .scorecard import render_scorecard
from .verdict_page import build_verdict_pages, render_verdict_page

__all__ = ["collect_lab_state", "render_dashboard", "render_scorecard",
           "render_verdict_page", "build_verdict_pages",
           "render_compare_page", "build_compare_page"]
