import pytest

from forecasting_lab.sources.registry import source_count, source_groups, source_table
from forecasting_lab.sources.social import RedditUnavailable, cashtag_counts, hot_titles
from forecasting_lab.sources.universe import equity_universe


def test_universe_meets_500_floor_offline(monkeypatch):
    # force the bundled fallback (simulate no network) and still clear 500
    import forecasting_lab.sources.universe as uni

    monkeypatch.setattr(uni, "sp500_symbols", lambda refresh=False: [])
    universe = uni.equity_universe()
    assert len(universe) >= 500
    assert len(universe) == len(set(universe))  # deduplicated
    assert "NVDA" in universe and "GME" in universe


def test_registry_counts_at_least_500():
    assert source_count() >= 500
    table = source_table()
    assert {"group", "kind", "reachable", "count", "note"} <= set(table.columns)
    # equities dominate; every group has a positive count
    assert (table["count"] > 0).all()


def test_registry_labels_blocked_sources_honestly():
    groups = {g.name: g for g in source_groups()}
    assert groups["Reddit subs"].reachable == "blocked here"
    assert groups["Equities"].reachable == "live"


def test_cashtag_counts_matches_dollar_and_word():
    titles = ["$GME to the moon", "I love NVDA", "nothing here", "GME again"]
    counts = cashtag_counts(titles, ["GME", "NVDA", "AMC"])
    assert counts["GME"] == 2 and counts["NVDA"] == 1 and counts["AMC"] == 0


def test_reddit_raises_only_after_all_methods_fail(monkeypatch):
    import forecasting_lab.sources.social as social

    class _Boom:
        def get_json(self, *a, **k):
            raise ConnectionError("blocked")

        def get(self, *a, **k):  # RSS + redlib paths also fail
            raise ConnectionError("blocked")

    monkeypatch.setattr(social, "HttpClient", lambda *a, **k: _Boom())
    with pytest.raises(RedditUnavailable):
        hot_titles("wallstreetbets")


def test_reddit_falls_back_to_rss(monkeypatch):
    import forecasting_lab.sources.social as social

    rss = (
        b"<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'>"
        b"<entry><title>GME squeeze incoming</title></entry>"
        b"<entry><title>Thoughts on NVDA</title></entry></feed>"
    )

    class _JsonDeadRssOk:
        def get_json(self, *a, **k):
            raise ConnectionError("json blocked")  # force fallthrough to RSS

        def get(self, url, **k):
            class R:
                content = rss
            return R()

    monkeypatch.setattr(social, "HttpClient", lambda *a, **k: _JsonDeadRssOk())
    titles = hot_titles("wallstreetbets")
    assert "GME squeeze incoming" in titles  # recovered via RSS, did not give up


def test_mention_counts_zero_and_sentinel_when_blocked(monkeypatch):
    import forecasting_lab.sources.social as social

    def _blocked(sub, limit=40):
        raise RedditUnavailable("blocked")

    monkeypatch.setattr(social, "hot_titles", _blocked)
    counts = social.mention_counts(["GME", "NVDA"], subs=["wallstreetbets"])
    assert counts["GME"] == 0 and counts["_reddit_reachable"] == 0  # graceful, not a crash


def test_equity_universe_deterministic_order():
    a, b = equity_universe(), equity_universe()
    assert a == b
