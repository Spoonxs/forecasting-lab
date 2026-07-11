"""P6c section B — the portfolio page.

Pinned: the demo book is server-rendered (never blank) with per-holding verdict
chips + mandate tag + vs-SPY/vs-HYSA; holdings live in localStorage only (CSV
parsed in-browser, passphrase-encrypted export, hide-values toggle) with no
upload path in the page; the client mirror reads the SAME embedded contract the
Python engine exports (never re-hardcoded); hostile artifact text cannot break
out of the embedded JSON or the HTML; degraded (no artifact) renders honest
INSUFFICIENT + n/a; build writes the file with and without an artifact; no
external fetches; not-financial-advice present.
"""

from __future__ import annotations

import json
import re
from datetime import date

from forecasting_lab.dashboard.portfolio_page import (
    DEMO_HOLDINGS,
    build_portfolio_page,
    render_portfolio_page,
)
from forecasting_lab.signals.portfolio import portfolio_contract

PAYLOAD = {"as_of": "2026-07-05", "hysa_yield_pct": 5.0, "verdicts": {
    "VOO": {"label": "BUY", "score": 0.30}, "QQQ": {"label": "BUY", "score": 0.28},
    "NVDA": {"label": "STRONG BUY", "score": 0.62}, "SCHD": {"label": "HOLD", "score": 0.05},
    "SPY": {"label": "HOLD", "score": 0.10}}}


def test_demo_book_is_server_rendered_and_never_blank():
    html = render_portfolio_page(PAYLOAD, hysa_yield_pct=5.0)
    assert html.startswith("<!DOCTYPE html>")
    for h in DEMO_HOLDINGS:  # every demo holding is a real row linking its ticker page
        assert f't/{h["symbol"]}.html' in html
    assert 'id="mtag"' in html and 'id="sSpy"' in html and 'id="sHysa"' in html
    assert "STRONG BUY" in html                       # NVDA's verdict chip
    assert "not financial advice" in html.lower()
    # the demo book exercises the friction detector on screen (fidelity pass):
    # NVDA sits at the cap, so "attractive, but..." advice is server-rendered
    assert "at/over the 25% cap" in html


def test_privacy_holdings_stay_in_the_browser():
    html = render_portfolio_page(PAYLOAD)
    assert "flab_holdings" in html and "localStorage" in html
    assert "readAsText" in html                        # CSV parsed client-side
    assert "AES-GCM" in html and "PBKDF2" in html      # encrypted export/import
    assert "hideBtn" in html and "body.hidden .val" in html  # hide-values blur
    # no upload path: nothing in the page can send data anywhere
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert "navigator.sendBeacon" not in html and "WebSocket" not in html


def test_client_mirror_reads_the_embedded_contract_not_hardcoded():
    html = render_portfolio_page(PAYLOAD)
    blob = html.split('id="contract" type="application/json">')[1].split("</script>")[0]
    embedded = json.loads(blob.replace("\\u003c", "<").replace("\\u003e", ">"))
    assert embedded == portfolio_contract()            # byte-identical numbers
    js = html.split('<script>')[-1]
    assert "C.max_position_pct" in js and "C.core_etf_holdings" in js
    assert "C.crowding_overlap_flag" in js and "C.min_cash_pct" in js
    # the JS never re-hardcodes the cap or the flag threshold as literals
    for literal in (str(portfolio_contract()["max_position_pct"]),
                    str(portfolio_contract()["crowding_overlap_flag"])):
        assert not re.search(rf"(?<![\d.]){re.escape(literal)}(?![\d.])", js)


def test_hostile_artifact_text_cannot_escape_json_or_html():
    evil = {"as_of": "d", "verdicts": {
        "VOO": {"label": "</script><img src=x onerror=alert(1)>", "score": 0.1}}}
    html = render_portfolio_page(evil)
    for blob_id in ("contract", "verdicts", "demo"):
        blob = html.split(f'id="{blob_id}" type="application/json">')[1].split("</script>")[0]
        assert "</script" not in blob                  # breakout neutralized
    assert "<img src=x onerror" not in html            # table cell escaped too


def test_degraded_no_artifact_is_honest():
    html = render_portfolio_page({})
    assert html.startswith("<!DOCTYPE html>")
    assert "INSUFFICIENT EVIDENCE" in html             # demo book, honestly unrated
    assert "n/a" in html                               # blended / vs-SPY / vs-HYSA
    assert "0.62" not in html                          # no leftover fabricated score


def test_no_external_fetches():
    html = render_portfolio_page(PAYLOAD)
    assert "fonts.googleapis" not in html and "<script src=" not in html
    assert "http://" not in html and "https://" not in html


def test_build_writes_from_a_fixture_artifact_and_without_one(tmp_path):
    from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts
    from forecasting_lab.signals.verdict import Component

    def provider(sym):
        if sym == "NVDA":
            return {n: Component(n, 0.5, 0.9) for n in
                    ("backtest", "trend", "residual_momentum", "macro", "yield")}
        return {}

    payload = build_verdicts(["NVDA", "VOO", "QQQ", "SPY"], provider,
                             on=date(2026, 7, 5), hysa_yield_pct=4.5)
    vdir = tmp_path / "verdicts"
    write_verdicts(payload, out_dir=vdir)
    page = build_portfolio_page(tmp_path / "site", verdicts_dir=vdir)
    text = page.read_text(encoding="utf-8")
    assert page.name == "portfolio.html" and text.startswith("<!DOCTYPE html>")
    assert "4.5" in text.split('<script>')[-1]         # HYSA yield flows to the mirror
    # no artifact at all -> the page still builds (demo book, honest n/a)
    bare = build_portfolio_page(tmp_path / "site2", verdicts_dir=tmp_path / "none")
    assert bare.exists() and "INSUFFICIENT EVIDENCE" in bare.read_text(encoding="utf-8")


# ------------------------------------------------ Codex code-review fixes pinned
def test_csv_import_handles_quoted_money_and_never_treats_shares_as_dollars():
    """Codex findings 1+2: '"$12,345.67"' fields split correctly; a quantity
    column alone is never imported as dollars (needs a price column too)."""
    js = render_portfolio_page(PAYLOAD).split("<script>")[-1]
    assert "function cells(" in js and "cells(lines[0])" in js and "cells(ln)" in js
    assert "lines[0].split(','" not in js and "ln.split(','" not in js  # naive split gone
    assert "qi>=0&&pi>=0" in js                        # qty counts only with a price


def test_overlap_floor_comes_from_the_contract_not_a_js_literal():
    """Codex finding 3: the pairwise-overlap report floor is a contract number."""
    assert portfolio_contract()["overlap_report_floor"] == 0.005
    js = render_portfolio_page(PAYLOAD).split("<script>")[-1]
    assert "C.overlap_report_floor" in js and "0.005" not in js


def test_home_nav_links_the_portfolio_page():
    from forecasting_lab.dashboard.collect import collect_lab_state
    from forecasting_lab.dashboard.render import render_dashboard

    html = render_dashboard(collect_lab_state(seed=0))
    assert 'href="portfolio.html"' in html
