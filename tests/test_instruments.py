"""P6a step 1 — the full-universe instrument registry (PLATFORM_PLAN §2b).

Properties pinned: the bundled snapshot alone yields a brokerage-scale universe
(>8k symbols, offline); ETF flags come from the official directories (VOO/QQQ
are ETFs, NVDA is a stock); unknown tickers are None, never a guess; HYSA is a
first-class cash instrument whose yield is None until a live feed provides it;
live refresh degrades to the bundle on any failure.
"""

from __future__ import annotations

from forecasting_lab.sources.instruments import (
    CORE_ETFS,
    HYSA_SYMBOL,
    InstrumentRegistry,
    hysa_yield_pct,
)


def _registry():
    return InstrumentRegistry()


def test_bundled_universe_is_brokerage_scale_offline():
    reg = _registry()
    assert len(reg) > 8000, f"universe too small: {len(reg)}"
    assert reg.source == "bundled snapshot"
    kinds = {reg.get(s).kind for s in ("VOO", "NVDA", HYSA_SYMBOL)}
    assert kinds == {"etf", "stock", "cash"}


def test_etf_flags_come_from_the_official_directories():
    reg = _registry()
    for etf in ("VOO", "QQQ", "SPY", "VTI", "IWM", "DIA", "SCHD"):
        inst = reg.get(etf)
        assert inst is not None and inst.kind == "etf", etf
    nvda = reg.get("NVDA")
    assert nvda.kind == "stock" and "NVIDIA" in nvda.name.upper()
    # core ETFs carry curated metadata; other ETFs honestly carry None
    assert reg.get("VOO").expense_ratio == CORE_ETFS["VOO"]["expense_ratio"]
    assert reg.get("VOO").benchmark == "S&P 500"


def test_unknown_ticker_is_none_never_a_guess():
    reg = _registry()
    assert reg.get("ZZZZZZZZ") is None
    assert reg.get("") is None
    assert reg.get(None) is None
    assert reg.get(" nvda ") is not None  # normalization, not guessing


def test_hysa_is_first_class_and_never_invents_a_rate():
    reg = _registry()
    cash = reg.get(HYSA_SYMBOL)
    assert cash.kind == "cash" and cash.yield_pct is None  # n/a offline
    live = reg.hysa(tbill_yield_pct=5.2)
    assert live.yield_pct == 5.2 and reg.get(HYSA_SYMBOL).yield_pct is None

    class Down:
        def get_text(self, url, **kw):
            raise OSError("offline")

    assert hysa_yield_pct(http=Down()) is None

    class Fred:
        def get_text(self, url, **kw):
            return "DATE,DTB3\n2026-07-02,5.31\n2026-07-03,.\n"

    assert hysa_yield_pct(http=Fred()) == 5.31  # last PARSEABLE value, dots skipped


def test_refresh_degrades_to_the_bundle_on_failure():
    reg = _registry()
    n_before = len(reg)

    class Down:
        def get_text(self, url, **kw):
            raise OSError("blocked")

    assert reg.refresh(http=Down()) is False
    assert len(reg) == n_before and reg.source == "bundled snapshot"

    class Junk:
        def get_text(self, url, **kw):
            return "<html>captcha</html>"

    assert reg.refresh(http=Junk()) is False  # malformed payload never replaces the bundle


def test_codex_review_fixes_class_shares_noncommon_and_stale_label():
    reg = _registry()
    # Yahoo-style hyphen input resolves to the directory's dot-style listing
    assert reg.get("BRK-B") is not None and reg.get("BRK-B").symbol == "BRK.B"
    assert reg.get("BF-B").kind == "stock"
    # preferreds/warrants/units are "other", never posing as common stock
    sample = [i for i in reg._by_symbol.values() if i.kind == "other"]
    assert len(sample) > 100  # the taxonomy actually fires on the real directory
    assert all(i.kind != "stock" for i in sample)
    # a previously-live registry that fails to re-refresh says STALE, not live
    reg.source = "nasdaqtrader.com (live)"

    class Down:
        def get_text(self, url, **kw):
            raise OSError("blocked")

    reg.refresh(http=Down())
    assert "stale" in reg.source


def test_search_is_brokerage_style():
    reg = _registry()
    exact = reg.search("NVDA")
    assert exact and exact[0].symbol == "NVDA"  # exact symbol always ranks first
    # a shorter real ticker (NVD, a leveraged ETF) legitimately outranks on its
    # own prefix; NVDA must still be in the top results
    assert "NVDA" in {i.symbol for i in reg.search("NVD")[:4]}
    assert any(i.symbol == "VOO" for i in reg.search("VOO"))
    assert reg.search("") == []
    by_name = reg.search("Agilent")
    assert any(i.symbol == "A" for i in by_name)  # name substring works too
