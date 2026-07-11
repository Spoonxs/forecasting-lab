"""P6d section C — the changed-since-last-visit digest.

Pinned: the banner is a pure client-side FILTER over the server-rendered
change feed (no score is ever recomputed); the first visit only stamps and
stays silent; dismissing stamps the build as seen; the embedded JSON is a
minimal reduction (symbol/was/now/dir, capped) and hostile text can't break
out of it; the home page carries the banner wiring.
"""

from __future__ import annotations

import json

from forecasting_lab.dashboard.render import _since_last_visit_html

CHANGES = [{"symbol": "NVDA", "was": "BUY", "now": "STRONG BUY", "dir": "up",
            "why": "Trend rose +0.2"},
           {"symbol": "VOO", "was": "BUY", "now": "HOLD", "dir": "down",
            "why": "Macro fell -0.3"}]


def test_embedded_json_is_minimal_and_capped():
    html = _since_last_visit_html("2026-07-10", CHANGES * 10)  # 20 changes
    blob = html.split('id="sincelast" type="application/json">')[1].split("</script>")[0]
    data = json.loads(blob.replace("\\u003c", "<").replace("\\u003e", ">"))
    assert data["as_of"] == "2026-07-10" and len(data["changes"]) == 12  # capped
    assert set(data["changes"][0]) == {"symbol", "was", "now", "dir"}   # no extras
    assert "why" not in blob                                            # reduced


def test_first_visit_is_silent_and_dismiss_stamps():
    js = _since_last_visit_html("2026-07-10", CHANGES).split("<script>")[-1]
    assert "if(!seen){localStorage.setItem('flab_seen_asof',d.as_of);return;}" in js
    assert "d.as_of<=seen" in js                        # already-seen builds stay quiet
    assert "visitdismiss" in js and "bar.hidden=true" in js
    # it filters the server feed; it NEVER recomputes a score
    assert "score" not in js and "weight" not in js


def test_hostile_symbol_cannot_escape_the_json():
    evil = [{"symbol": "</script><img src=x onerror=alert(1)>", "was": "BUY",
             "now": "HOLD", "dir": "down"}]
    html = _since_last_visit_html("2026-07-10", evil)
    blob = html.split('id="sincelast" type="application/json">')[1].split("</script>")[0]
    assert "</script" not in blob and "onerror=alert(1)>" not in blob
    # the banner text is built via textContent, never innerHTML
    assert "msg.textContent=" in html and "msg.innerHTML" not in html


def test_home_page_carries_the_banner():
    from forecasting_lab.dashboard.collect import collect_lab_state
    from forecasting_lab.dashboard.render import render_dashboard

    html = render_dashboard(collect_lab_state(seed=0))
    assert 'id="sincelast"' in html and 'id="visitbar"' in html
    assert "flab_seen_asof" in html


def test_no_changes_renders_the_wiring_but_stays_quiet():
    html = _since_last_visit_html("2026-07-10", [])
    data = json.loads(html.split('id="sincelast" type="application/json">')[1]
                      .split("</script>")[0])
    assert data["changes"] == []
    assert "!(d.changes||[]).length)return" in html      # empty feed -> no banner
