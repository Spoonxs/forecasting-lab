"""P6c section A — the portfolio evaluation engine.

Pinned: holdings normalize from weights OR dollars (bad rows dropped, never
guessed); ETF overlap flags shared megacap exposure; over-cap concentration is a
mandate block; the decision-friction detector fires only on the data present
(over-cap, earnings proximity, wide spread, wash-sale) and stays silent
otherwise; vs-SPY/vs-HYSA computed; empty book handled; the contract round-trips
the thresholds the client mirror needs.
"""

from __future__ import annotations

from forecasting_lab.signals.portfolio import (
    CORE_ETF_HOLDINGS,
    decision_friction,
    etf_overlap,
    evaluate_portfolio,
    normalize_holdings,
    portfolio_contract,
)

VERDICTS = {"NVDA": {"label": "STRONG BUY", "score": 0.62},
            "VOO": {"label": "BUY", "score": 0.30},
            "QQQ": {"label": "BUY", "score": 0.28},
            "SPY": {"label": "HOLD", "score": 0.10}}


def test_normalize_from_weights_or_dollars_drops_bad_rows():
    by_dollars = normalize_holdings([{"symbol": "NVDA", "dollars": 6000},
                                     {"symbol": "VOO", "dollars": 4000}])
    assert {h.symbol: round(h.weight, 2) for h in by_dollars} == {"NVDA": 0.6, "VOO": 0.4}
    by_weight = normalize_holdings([{"symbol": "nvda", "weight": 0.5}, {"symbol": "voo", "weight": 0.3}])
    assert {h.symbol for h in by_weight} == {"NVDA", "VOO"}  # uppercased, cash remainder kept
    assert normalize_holdings([{"weight": 0.5}, {"symbol": "", "dollars": 1}]) == []  # no symbol -> dropped
    assert normalize_holdings([]) == []


def test_etf_overlap_flags_shared_megacaps():
    holds = normalize_holdings([{"symbol": "VOO", "weight": 0.5}, {"symbol": "QQQ", "weight": 0.5}])
    ov = etf_overlap(holds)
    assert ov and ov[0]["a"] in ("VOO", "QQQ") and ov[0]["book_overlap"] > 0.02
    assert "NVDA" in ov[0]["names"] or "AAPL" in ov[0]["names"]  # the doubled megacaps
    # ETF holding a stock the user also owns
    mix = normalize_holdings([{"symbol": "QQQ", "weight": 0.5}, {"symbol": "NVDA", "weight": 0.5}])
    assert any(o["names"] == ["NVDA"] for o in etf_overlap(mix))


def test_over_cap_concentration_is_a_mandate_block():
    ev = evaluate_portfolio([{"symbol": "NVDA", "dollars": 5000}, {"symbol": "VOO", "dollars": 5000}],
                            VERDICTS)
    assert ev["mandate_status"] == "block"  # 50% NVDA exceeds the 25% cap
    assert any(a["kind"] == "block" for a in ev["advice"])
    nvda = next(r for r in ev["holdings"] if r["symbol"] == "NVDA")
    assert nvda["label"] == "STRONG BUY" and nvda["weight"] == 0.5


def test_decision_friction_fires_only_on_present_data():
    # a positive verdict already over the cap -> "don't add" friction
    over = decision_friction("NVDA", 0.4, "STRONG BUY", 0.25)
    assert any("cap" in f for f in over)
    # earnings / spread / wash-sale fire only when that datum is present
    assert any("earnings" in f for f in decision_friction("NVDA", 0.1, "BUY", 0.25, earnings_days=2))
    assert any("spread" in f for f in decision_friction("NVDA", 0.1, "BUY", 0.25, spread_pct=0.2))
    # wash-sale requires the prior sale to have been AT A LOSS (Codex fix)
    assert any("wash-sale" in f for f in
               decision_friction("NVDA", 0.1, "BUY", 0.25, recent_sale_days=5, recent_sale_loss=True))
    assert decision_friction("NVDA", 0.1, "BUY", 0.25, recent_sale_days=5, recent_sale_loss=False) == []
    # a HOLD/AVOID verdict has no "don't buy now" friction, and absent data stays silent
    assert decision_friction("NVDA", 0.1, "HOLD", 0.25, earnings_days=2) == []
    assert decision_friction("NVDA", 0.1, "BUY", 0.25) == []


def test_vs_benchmarks_and_empty_book():
    ev = evaluate_portfolio([{"symbol": "NVDA", "weight": 0.2}, {"symbol": "VOO", "weight": 0.2}],
                            VERDICTS, hysa_yield_pct=5.0)
    assert ev["vs_spy"] is not None and ev["vs_hysa"] is not None
    assert ev["blended_score"] > 0  # NVDA + VOO both positive
    # no HYSA yield known -> vs_hysa is None (n/a), never a fabricated compare
    assert evaluate_portfolio([{"symbol": "NVDA", "weight": 0.5}], VERDICTS)["vs_hysa"] is None
    assert evaluate_portfolio([], VERDICTS)["empty"] is True


# ------------------------------------------------ Codex code-review fixes pinned
def test_over_cap_uses_invested_capital_not_total_book():
    """Codex finding 1: 20% NVDA / 20% VOO / 60% cash is 50% NVDA of INVESTED."""
    ev = evaluate_portfolio([{"symbol": "NVDA", "weight": 0.2}, {"symbol": "VOO", "weight": 0.2}],
                            VERDICTS)  # 60% cash implied
    assert ev["cash"] == 0.6
    nvda = next(r for r in ev["holdings"] if r["symbol"] == "NVDA")
    assert any("cap" in f for f in nvda["friction"])  # 50% of invested -> over the 25% cap
    assert ev["mandate_status"] == "block"


def test_crowding_is_deduplicated_lookthrough_not_pairwise_sum():
    """Codex finding 3: NVDA via SPY+VOO+QQQ counted ONCE, not thrice."""
    ev = evaluate_portfolio([{"symbol": "SPY", "weight": 1 / 3}, {"symbol": "VOO", "weight": 1 / 3},
                             {"symbol": "QQQ", "weight": 1 / 3}], VERDICTS)
    lt_top = ev["crowding"]["top_weight"]
    assert 0.0 < lt_top < 0.15  # a single megacap is a modest slice, not an inflated >1 sum
    assert ev["crowding"]["crowded"] is False  # a 3-ETF broad book is not one bet


def test_unrated_holdings_are_named_not_imputed_to_zero():
    """Codex finding 4: an unknown/INSUFFICIENT holding is excluded + named."""
    v = {"NVDA": {"label": "BUY", "score": 0.4},
         "MYSTERY": {"label": "INSUFFICIENT EVIDENCE", "score": 0.0}}
    ev = evaluate_portfolio([{"symbol": "NVDA", "weight": 0.5}, {"symbol": "MYSTERY", "weight": 0.5}], v)
    mystery = next(r for r in ev["holdings"] if r["symbol"] == "MYSTERY")
    assert mystery["score"] is None  # never imputed to 0
    assert ev["blended_score"] == 0.4  # only the rated NVDA, renormalized (not 0.2 averaged w/ a fake 0)
    assert any(a["kind"] == "unrated" and "MYSTERY" in a["text"] for a in ev["advice"])
    # a book with NOTHING rated -> blended is None (n/a), never a fabricated 0
    none_rated = evaluate_portfolio([{"symbol": "ZZZ", "weight": 1.0}], {})
    assert none_rated["blended_score"] is None


def test_duplicate_symbols_consolidate_and_insufficient_variants_excluded():
    """Codex re-review: two lots of one name = one position; INSUFFICIENT* excluded."""
    holds = normalize_holdings([{"symbol": "NVDA", "dollars": 3000},
                                {"symbol": "NVDA", "dollars": 3000},
                                {"symbol": "VOO", "dollars": 4000}])
    nvda = [h for h in holds if h.symbol == "NVDA"]
    assert len(nvda) == 1 and round(nvda[0].weight, 2) == 0.6  # summed, not overwritten
    # an "INSUFFICIENT" (variant) label is treated as unrated, not scored 0
    v = {"NVDA": {"label": "BUY", "score": 0.4}, "ZZ": {"label": "INSUFFICIENT", "score": 0.0}}
    ev = evaluate_portfolio([{"symbol": "NVDA", "weight": 0.5}, {"symbol": "ZZ", "weight": 0.5}], v)
    assert next(r for r in ev["holdings"] if r["symbol"] == "ZZ")["score"] is None
    assert ev["blended_score"] == 0.4


def test_contract_carries_the_thresholds_and_overlap_data():
    c = portfolio_contract()
    assert c["max_position_pct"] == 0.25 and c["min_cash_pct"] == 0.0
    assert c["core_etf_holdings"]["QQQ"] == CORE_ETF_HOLDINGS["QQQ"]  # same numbers for the mirror
    assert "crowding_overlap_flag" in c


# ------------------------------------------------ P6e: the tax/account lens
def test_tax_lens_diverges_taxable_vs_ira_on_the_same_book():
    from forecasting_lab.signals.portfolio import ACCOUNT_BEHAVIORS

    fd = {"NVDA": {"recent_sale_days": 5, "recent_sale_loss": True},
          "VOO": {"dividend_yield_pct": 3.4}}
    book = [{"symbol": "NVDA", "weight": 0.2}, {"symbol": "VOO", "weight": 0.2}]
    taxable = evaluate_portfolio(book, VERDICTS, friction_data=fd)  # default: taxable
    ira = evaluate_portfolio(book, VERDICTS, friction_data=fd, account_type="ira")
    assert taxable["account_type"] == "taxable" and ira["account_type"] == "ira"
    # taxable: the wash-sale friction fires and the dividend drag gets a line
    nvda_tx = next(r for r in taxable["holdings"] if r["symbol"] == "NVDA")
    assert any("wash-sale" in f for f in nvda_tx["friction"])
    assert any(a["kind"] == "tax" and "VOO yields 3.4%" in a["text"]
               for a in taxable["advice"])
    # IRA: both suppressed, WITH the reason on screen — never silently dropped
    nvda_ira = next(r for r in ira["holdings"] if r["symbol"] == "NVDA")
    assert not any("wash-sale" in f for f in nvda_ira["friction"])
    assert not any(a["kind"] == "tax" for a in ira["advice"])
    assert any(a["kind"] == "account" and a["text"] == ACCOUNT_BEHAVIORS["ira"]["note"]
               for a in ira["advice"])


def test_tax_lens_stays_silent_without_a_datum():
    import pytest

    book = [{"symbol": "NVDA", "weight": 0.2}, {"symbol": "VOO", "weight": 0.2}]
    # no tax data at all: taxable adds no tax line, IRA states no suppression
    for acct in ("taxable", "ira", "401k"):
        ev = evaluate_portfolio(book, VERDICTS, account_type=acct)
        assert not any(a["kind"] in ("tax", "account") for a in ev["advice"])
    # a below-threshold yield in taxable is not drag-worthy — silent
    low = evaluate_portfolio(book, VERDICTS,
                             friction_data={"VOO": {"dividend_yield_pct": 1.2}})
    assert not any(a["kind"] == "tax" for a in low["advice"])
    with pytest.raises(ValueError, match="account_type"):
        evaluate_portfolio(book, VERDICTS, account_type="offshore")


def test_contract_and_page_carry_the_account_behaviors():
    from forecasting_lab.dashboard.portfolio_page import render_portfolio_page
    from forecasting_lab.signals.portfolio import ACCOUNT_BEHAVIORS

    c = portfolio_contract()
    assert c["account_types"] == ["taxable", "ira", "401k"]
    assert c["account_behaviors"] == ACCOUNT_BEHAVIORS
    assert c["dividend_drag_yield_pct"] == 2.5
    html = render_portfolio_page({"as_of": "2026-07-11", "verdicts": {}})
    assert 'data-acct="ira"' in html and "flab_account" in html
    # the mirror reads the behaviors from the contract, never re-hardcoded:
    # the IRA note appears ONLY inside the embedded contract JSON, not the JS
    js = html.split("<script>")[-1]
    assert "C.account_behaviors" in js and "C.account_types" in js
    assert "wash-sale rules don" not in js
    blob = html.split('id="contract" type="application/json">')[1].split("</script>")[0]
    assert "wash-sale rules don" in blob
    # Codex review pins: the client holds NO tax data, so it never emits the
    # account advice line (the engine gates it on a real datum) — the lens
    # caption on the control carries the description instead; and the only
    # client-computed friction is the cap check (nothing tax-y to suppress)
    assert "kind:'account'" not in js and "kind:'tax'" not in js
    assert "wash-sale" not in js and "dividend" not in js
