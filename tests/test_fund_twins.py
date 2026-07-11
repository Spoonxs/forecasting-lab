"""P6e section A — mutual-fund twins.

Pinned: the fund->twin mapping resolves both ways with both expense ratios and
an honest fee multiple (None when a ratio is unknown); every mapped twin has
registry metadata (the fee statement is checkable, not vibes); funds register
as kind mutual_fund and are searchable by symbol and name; the worker
allowlist stays ETF/stock-only; the mapping ships in the scoring contract;
fund pages render the TWIN's verdict clearly labeled with the fee delta and
never fabricate a price; an unrated twin means no fund page (honest absence).
"""

from __future__ import annotations

import json
from datetime import date

from forecasting_lab.dashboard.verdict_page import _fund_banner, build_verdict_pages
from forecasting_lab.signals.verdict import Component, scoring_contract
from forecasting_lab.sources.instruments import (
    CORE_ETFS,
    MUTUAL_FUND_TWINS,
    InstrumentRegistry,
    fund_twin,
    funds_for_twin,
)


def test_mapping_resolves_both_ways_with_honest_fee_math():
    card = fund_twin("vtsax")                            # case-insensitive
    assert card["twin"] == "VTI" and card["fund"] == "VTSAX"
    assert card["fund_expense_ratio"] == 0.0004 and card["twin_expense_ratio"] == 0.0003
    assert card["fee_multiple"] == 1.3
    assert "VFIAX" in funds_for_twin("VOO") and "FXAIX" in funds_for_twin("VOO")
    assert fund_twin("NVDA") is None and funds_for_twin("NVDA") == []
    # every mapped twin has published metadata — the fee statement is checkable
    for meta in MUTUAL_FUND_TWINS.values():
        assert CORE_ETFS[meta["twin"]]["expense_ratio"] > 0
    # an unknown twin ratio -> multiple is None, never guessed
    MUTUAL_FUND_TWINS["ZZTEST"] = {"twin": "ZZZZ", "expense_ratio": 0.001, "name": "t"}
    try:
        assert fund_twin("ZZTEST")["fee_multiple"] is None
        assert fund_twin("ZZTEST")["twin_expense_ratio"] is None
    finally:
        del MUTUAL_FUND_TWINS["ZZTEST"]


def test_funds_are_searchable_but_stay_off_the_worker_allowlist():
    reg = InstrumentRegistry()
    vtsax = reg.get("VTSAX")
    assert vtsax and vtsax.kind == "mutual_fund" and "VTI" in (vtsax.benchmark or "")
    assert any(i.symbol == "VTSAX" for i in reg.search("VTSA"))
    assert any(i.symbol == "FXAIX" for i in reg.search("Fidelity 500"))
    assert "VTSAX" not in reg.symbols()                  # default kinds: no NAV proxying
    assert "VTSAX" in reg.symbols(kinds=("stock", "etf", "mutual_fund"))


def test_universe_json_includes_funds(tmp_path):
    from forecasting_lab.dashboard.tier_live import write_universe_json

    syms = json.loads(write_universe_json(tmp_path).read_text(encoding="utf-8"))
    assert "VTSAX" in syms and "VBTLX" in syms


def test_contract_ships_the_twin_mapping():
    twins = scoring_contract()["mutual_fund_twins"]
    assert twins["VTSAX"]["twin"] == "VTI"
    assert twins["VFIAX"]["fund_expense_ratio"] == 0.0004
    assert twins["VFIAX"]["twin_expense_ratio"] == CORE_ETFS["VOO"]["expense_ratio"]
    assert set(twins) == set(MUTUAL_FUND_TWINS)          # complete, not sampled


def test_banner_states_the_fee_delta_honestly():
    pricey = _fund_banner(fund_twin("VTIAX"))            # 0.09% vs 0.05% -> ~1.8x
    assert "scored via its ETF twin" in pricey and "VXUS" in pricey
    assert "1.8x the fee" in pricey
    cheap = _fund_banner(fund_twin("FXAIX"))             # 0.015% vs 0.03% -> cheaper
    assert "cheaper wrapper" in cheap
    mid = _fund_banner(fund_twin("VTSAX"))               # 1.3x: stated fees, no drama
    assert "Fees: 0.04% (fund) vs 0.03% (ETF)" in mid and "x the fee" not in mid
    assert _fund_banner(None) == ""
    assert "Fee comparison: n/a" in _fund_banner(
        {"fund": "X", "twin": "Y", "fund_expense_ratio": 0.001,
         "twin_expense_ratio": None, "fee_multiple": None})


def test_fund_pages_render_via_the_twin_and_unrated_twins_stay_absent(tmp_path):
    from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts

    def provider(sym):
        if sym == "VTI":                                  # rate ONLY VTI
            return {n: Component(n, 0.5, 0.9) for n in
                    ("backtest", "trend", "residual_momentum", "macro", "yield")}
        return {}

    payload = build_verdicts(["VTI", "VOO"], provider, on=date(2026, 7, 10))
    vdir = tmp_path / "verdicts"
    write_verdicts(payload, out_dir=vdir)
    built = build_verdict_pages(tmp_path / "site", verdicts_dir=vdir)
    assert "VTSAX" not in built                           # funds stay off the home grid
    vtsax = (tmp_path / "site" / "t" / "VTSAX.html").read_text(encoding="utf-8")
    assert "Mutual fund" in vtsax and "scored via its ETF twin" in vtsax
    assert 'href="VTI.html"' in vtsax                     # links its twin
    assert 'id="vlabel"' in vtsax                         # the twin's verdict renders
    assert "Fees: 0.04% (fund) vs 0.03% (ETF)" in vtsax
    # no fabricated price: the header is honest n/a on a fund page
    head = vtsax.split('class="pxhead"')[1].split("</div>")[2]
    assert "$" not in head
    # VOO is INSUFFICIENT in this fixture -> its funds render that verdict
    # honestly (the page exists and says so — search lands somewhere true)
    vfiax = (tmp_path / "site" / "t" / "VFIAX.html").read_text(encoding="utf-8")
    assert "INSUFFICIENT EVIDENCE" in vfiax and "scored via its ETF twin" in vfiax
    # a twin absent from the artifact entirely -> no fund page at all
    assert not (tmp_path / "site" / "t" / "VTIAX.html").exists()  # VXUS not built
    assert not (tmp_path / "site" / "t" / "VBTLX.html").exists()  # BND not built


def test_stray_price_fields_in_the_twin_row_never_render_a_fund_price():
    """Codex review (defensive pin): price/spark reach the renderer only as
    explicit kwargs — junk price keys inside an artifact row are ignored, so a
    fund page can never show the ETF's price as its own."""
    from forecasting_lab.dashboard.verdict_page import render_verdict_page

    row = {"label": "BUY", "score": 0.3,
           "dials": {"expected_return": 0.3, "drawdown_risk": 0.2,
                     "data_confidence": 0.8, "model_confidence": 0.7},
           "components": {}, "missing": [], "labels_by_profile": {}, "reasons": [],
           "price": 424.24, "last": 424.24, "spark": [400, 424.24]}  # hostile junk
    html = render_verdict_page("VTSAX", row, scoring_contract(),
                               fund=fund_twin("VTSAX"))
    head = html.split('class="pxhead"')[1].split("</div>")[2]
    assert "$" not in head and "424" not in html
