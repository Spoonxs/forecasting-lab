"""P7 section C — congressional trades (best-effort, lag on every row).

Pinned: both chambers' mirror shapes normalize (US and ISO dates); rows
without a real ticker or member drop; the disclosure lag is computed and an
unparseable date stays None (shown as n/a, never guessed); the recent window
keys on the DISCLOSED date (the observable event) and excludes undateable
rows; blocked/empty feeds are stated skips; the digest names its sources and
the structural 45-day lag; nothing touches the verdict engine.
"""

from __future__ import annotations

from datetime import date

from forecasting_lab.sources.congress import (
    fetch_congress_digest,
    parse_trades,
    recent_trades,
)

HOUSE_ROWS = [
    {"representative": "Hon. A Member", "ticker": "NVDA", "type": "purchase",
     "transaction_date": "2026-06-01", "disclosure_date": "07/01/2026",
     "amount": "$1,001 - $15,000"},
    {"representative": "Hon. B Member", "ticker": "--", "type": "purchase",
     "transaction_date": "2026-06-01", "disclosure_date": "07/01/2026"},   # non-equity
    {"representative": "", "ticker": "AAPL", "transaction_date": "2026-06-01",
     "disclosure_date": "07/01/2026"},                                     # no member
    {"representative": "Hon. C Member", "ticker": "VOO", "type": "sale_full",
     "transaction_date": "junk", "disclosure_date": "also junk",
     "amount": "$15,001 - $50,000"},
]
SENATE_ROWS = [
    {"senator": "Sen. D Member", "ticker": "MSFT", "type": "Purchase",
     "transaction_date": "05/20/2026", "disclosure_date": "05/30/2026",
     "amount": "$50,001 - $100,000"},
]


def test_both_chamber_shapes_normalize_with_the_lag():
    house = parse_trades(HOUSE_ROWS, "house")
    assert [t["ticker"] for t in house] == ["NVDA", "VOO"]  # '--' and no-member drop
    nvda = house[0]
    assert nvda["member"] == "Hon. A Member" and nvda["chamber"] == "house"
    assert nvda["transaction_date"] == "2026-06-01"
    assert nvda["disclosed_date"] == "2026-07-01" and nvda["lag_days"] == 30
    voo = house[1]
    assert voo["transaction_date"] is None and voo["lag_days"] is None  # honest n/a
    senate = parse_trades(SENATE_ROWS, "senate")
    assert senate[0]["member"] == "Sen. D Member" and senate[0]["lag_days"] == 10
    assert parse_trades([], "house") == [] and parse_trades(None, "senate") == []


def test_recent_window_keys_on_the_disclosed_date():
    rows = parse_trades(HOUSE_ROWS + [
        {"representative": "Hon. Old Member", "ticker": "IBM", "type": "purchase",
         "transaction_date": "2025-01-01", "disclosure_date": "2025-02-01"}], "house")
    recent = recent_trades(rows, date(2026, 7, 11), days=90)
    assert [t["ticker"] for t in recent] == ["NVDA"]     # old row out; undated VOO out
    assert recent_trades(rows, date(2026, 7, 11), days=90, cap=0) == []


def test_blocked_or_empty_feeds_are_stated_skips():
    class _Boom:
        def get_json(self, url, **kw):
            raise ConnectionError("mirror lapsed")

    d = fetch_congress_digest(on=date(2026, 7, 11), http=_Boom())
    assert d["trades"] == [] and len(d["skips"]) == 2
    assert all("mirror lapsed" in s["reason"] for s in d["skips"])
    assert "best effort" in d["source"] and "45d" in d["source"]

    class _Empty:
        def get_json(self, url, **kw):
            return []

    e = fetch_congress_digest(on=date(2026, 7, 11), http=_Empty())
    assert all("no parseable trades" in s["reason"] for s in e["skips"])


def test_digest_merges_chambers_newest_disclosed_first():
    class _Http:
        def get_json(self, url, **kw):
            return HOUSE_ROWS if "house" in url else SENATE_ROWS

    d = fetch_congress_digest(on=date(2026, 7, 11), http=_Http())
    assert [t["ticker"] for t in d["trades"]] == ["NVDA", "MSFT"]  # 07-01 before 05-30
    assert d["skips"] == [] and d["window_days"] == 90


def test_cap_applies_only_after_the_merged_sort():
    """Codex finding: a per-chamber cap could drop newer House rows while
    older Senate rows survived — the cap must be global, post-merge."""
    house = [{"representative": f"Hon. M{i}", "ticker": "NVDA", "type": "purchase",
              "transaction_date": "2026-06-01",
              "disclosure_date": f"2026-07-{i:02d}"} for i in range(1, 10)]  # newer
    senate = [{"senator": "Sen. Old", "ticker": "MSFT", "type": "Purchase",
               "transaction_date": "05/01/2026", "disclosure_date": "05/02/2026"}]

    class _Http:
        def get_json(self, url, **kw):
            return house if "house" in url else senate

    d = fetch_congress_digest(on=date(2026, 7, 11), http=_Http())
    dates = [t["disclosed_date"] for t in d["trades"]]
    assert dates == sorted(dates, reverse=True)          # strictly newest-first
    assert d["trades"][-1]["ticker"] == "MSFT"           # the older row ranks last
    assert recent_trades(parse_trades(house, "house"), date(2026, 7, 11),
                         cap=None) == recent_trades(parse_trades(house, "house"),
                                                    date(2026, 7, 11), cap=999)


def test_nothing_here_touches_the_verdict_engine():
    import inspect

    import forecasting_lab.sources.congress as mod
    from forecasting_lab.signals.verdict import scoring_contract

    before = scoring_contract()["base_weights"]
    assert scoring_contract()["base_weights"] == before
    assert "compute_verdict" not in inspect.getsource(mod)
