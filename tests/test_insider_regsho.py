"""V10 — insider cluster-buys + Reg-SHO short volume (MASTER_PLAN §3).

Properties pinned: parsers work offline on fixtures and degrade to None/[] on
junk; clusters require DISTINCT insiders inside the window and never count
sells; facts land dated in the TidyStore with freshness stamps; the enriched
squeeze score helps only when the extra feed is informative and changes
nothing when the feed is absent.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from forecasting_lab.signals.squeeze import (
    enriched_squeeze_skill_report,
    squeeze_setup,
    squeeze_setup_enriched,
)
from forecasting_lab.sources.insider import (
    ClusterBuy,
    InsiderTrade,
    cluster_buys,
    parse_openinsider,
    parse_regsho,
    record_cluster_buys,
    record_short_volume,
    short_volume_ratios,
)
from forecasting_lab.sources.store import TidyStore

REGSHO_FIXTURE = """Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
20260702|AAA|600|0|1000|B,Q,N
20260702|BBB|250|0|1000|B,Q,N
20260702|BAD|9|0|0|B,Q,N
20260702|CCC|junk|0|1000|B,Q,N
"""


def test_regsho_parser_ratios_and_degradation():
    ratios = parse_regsho(REGSHO_FIXTURE)
    assert ratios == {"AAA": 0.6, "BBB": 0.25}  # zero-volume + junk rows skipped
    assert parse_regsho("") is None
    assert parse_regsho("<html>blocked</html>") is None


def test_short_volume_fetch_stamps_freshness_and_files_dated_facts(tmp_path):
    class FakeHttp:
        def get_text(self, url, **kw):
            assert "20260702" in url
            return REGSHO_FIXTURE

    t0 = datetime(2026, 7, 2, 22, 0, tzinfo=timezone.utc)
    payload = short_volume_ratios(date(2026, 7, 2), http=FakeHttp(), now=t0)
    assert payload["fetched_at"] == t0.isoformat()  # the V3 stamp travels with the data
    assert payload["as_of"] == "2026-07-02"

    store = TidyStore("test_facts", root=tmp_path)
    assert record_short_volume(payload, store=store) == 2
    assert list(store.series("AAA", "short_volume_ratio")) == [0.6]

    class DownHttp:
        def get_text(self, url, **kw):
            raise OSError("blocked")

    assert short_volume_ratios(date(2026, 7, 2), http=DownHttp()) is None  # honest


def test_cluster_requires_distinct_insiders_within_window():
    one_person = [
        InsiderTrade("AAA", "smith", f"2026-06-{d:02d}", "buy", 10_000.0) for d in (1, 3, 5)
    ]
    assert cluster_buys(one_person) == []  # conviction from ONE person is not a cluster

    three_people = [
        InsiderTrade("AAA", who, f"2026-06-{d:02d}", "buy", 10_000.0)
        for who, d in (("smith", 1), ("jones", 4), ("lee", 9))
    ]
    [c] = cluster_buys(three_people)
    assert c.n_insiders == 3 and c.first_date == "2026-06-01" and c.total_value_usd == 30_000.0

    # outside the window -> no cluster; sells never count
    spread = [
        InsiderTrade("AAA", who, day, "buy")
        for who, day in (("smith", "2026-01-01"), ("jones", "2026-03-01"), ("lee", "2026-06-01"))
    ]
    assert cluster_buys(spread) == []
    sells = [InsiderTrade("AAA", w, "2026-06-01", "sell") for w in ("a", "b", "c")]
    assert cluster_buys(sells) == []


def test_openinsider_parser_degrades_and_cluster_facts_file_dated(tmp_path):
    assert parse_openinsider("<html><body>captcha</body></html>") == []
    store = TidyStore("test_facts2", root=tmp_path)
    clusters = [ClusterBuy("AAA", 4, "2026-06-01", "2026-06-10", 90_000.0)]
    assert record_cluster_buys(clusters, on="2026-06-10", store=store) == 1
    assert store.latest("insider_cluster_buys") == {"AAA": 4.0}
    assert record_cluster_buys([], on="2026-06-10", store=store) == 0


def test_enriched_squeeze_degrades_to_base_and_needs_both_legs():
    # None inputs -> EXACTLY the base score
    assert squeeze_setup_enriched(0.3, 6, 4.0, 0.02) == squeeze_setup(0.3, 6, 4.0, 0.02)
    # enrichment never invents a setup: no fuel or no ignition stays zero
    assert squeeze_setup_enriched(0.0, 6, 4.0, 0.08, short_vol_ratio=0.8) == 0.0
    assert squeeze_setup_enriched(0.3, 6, 1.0, 0.0, cluster_buy_insiders=5) == 0.0
    # heavy daily shorting raises, unusually light lowers
    mid = squeeze_setup_enriched(0.2, 4, 3.0, 0.02, short_vol_ratio=0.45)
    hot = squeeze_setup_enriched(0.2, 4, 3.0, 0.02, short_vol_ratio=0.75)
    cold = squeeze_setup_enriched(0.2, 4, 3.0, 0.02, short_vol_ratio=0.15)
    assert hot > mid > cold
    # a cluster buy only ever adds
    assert squeeze_setup_enriched(0.2, 4, 3.0, 0.02, cluster_buy_insiders=5) >= mid


def test_enriched_skill_helps_only_when_the_feed_is_informative():
    informative = enriched_squeeze_skill_report(seed=0, k_svr=0.6)
    assert informative["brier_skill_enriched"] > informative["brier_skill_base"] + 0.01
    null = enriched_squeeze_skill_report(seed=0, k_svr=0.0)
    assert null["brier_skill_enriched"] <= null["brier_skill_base"] + 0.01  # noise must not help
