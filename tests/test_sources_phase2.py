"""Phase 2 data sources: each new connector parses a real-shaped payload AND
degrades honestly (empty/None, never a crash) when the feed is blocked. Plus the
tidy store round-trips, and the catalog count grew materially."""

from __future__ import annotations

from forecasting_lab.sources.finra import ShortInterestClient, short_interest
from forecasting_lab.sources.options import OptionsClient
from forecasting_lab.sources.registry import source_count
from forecasting_lab.sources.store import TidyStore
from forecasting_lab.sources.x_voices import X_VOICES, all_handles, recent_posts, voice_count
from forecasting_lab.sports.soccer import SOCCER_LEAGUES


# ---- stubs -------------------------------------------------------------------
class _JsonStub:
    def __init__(self, payload):
        self.payload = payload

    def get_json(self, url, **kwargs):
        return self.payload


class _Boom:
    def get_json(self, url, **kwargs):
        raise ConnectionError("blocked")

    def get(self, url, **kwargs):
        raise ConnectionError("blocked")


class _RssStub:
    def get(self, url, **kwargs):
        class R:
            content = b"<rss><channel><item><title>Post one</title></item>" \
                      b"<item><title>Post two</title></item></channel></rss>"
        return R()


# ---- FINRA short interest ----------------------------------------------------
def test_short_interest_parses_a_payload():
    stub = _JsonStub([{"shortPercentFloat": 0.28, "daysToCover": 6.4, "settlementDate": "2026-06-15"}])
    si = ShortInterestClient(http=stub).fetch("GME")
    assert si is not None and si.ticker == "GME"
    assert si.short_pct_float == 0.28 and si.days_to_cover == 6.4


def test_short_interest_derives_days_to_cover_from_raw_shares():
    stub = _JsonStub([{"currentShortPositionQuantity": 1_000_000, "averageDailyVolumeQuantity": 250_000}])
    si = ShortInterestClient(http=stub).fetch("AMC")
    assert si is not None and si.days_to_cover == 4.0


def test_short_interest_degrades_to_none_when_blocked():
    assert short_interest("GME", http=_Boom()) is None
    assert ShortInterestClient(http=_JsonStub([])).fetch("GME") is None  # empty payload


# ---- options / gamma ---------------------------------------------------------
def test_gamma_concentration_computes_near_spot_call_share():
    payload = {"optionChain": {"result": [{
        "quote": {"regularMarketPrice": 100.0},
        "options": [{"calls": [
            {"strike": 105.0, "openInterest": 500},   # inside (100, 110]
            {"strike": 108.0, "openInterest": 300},   # inside
            {"strike": 130.0, "openInterest": 200},   # outside
        ]}],
    }]}}
    g = OptionsClient(http=_JsonStub(payload)).gamma_concentration("GME", band=0.10)
    assert g == round(800 / 1000, 4)  # 0.8 of call OI bunched just above spot


def test_gamma_concentration_degrades_and_handles_no_oi():
    assert OptionsClient(http=_Boom()).gamma_concentration("GME") is None
    empty = {"optionChain": {"result": [{"quote": {"regularMarketPrice": 100.0},
                                         "options": [{"calls": []}]}]}}
    assert OptionsClient(http=_JsonStub(empty)).gamma_concentration("GME") == 0.0


# ---- X / Twitter voices ------------------------------------------------------
def test_x_voice_list_is_deduped_and_substantial():
    assert voice_count() >= 40
    assert len(all_handles()) == len(set(all_handles()))  # no dupes across lenses
    assert "unusual_whales" in all_handles() and X_VOICES["macro"]


def test_recent_posts_parses_rss_and_degrades_to_empty():
    posts = recent_posts("unusual_whales", http=_RssStub())
    assert posts == ["Post one", "Post two"]
    assert recent_posts("unusual_whales", http=_Boom()) == []  # all mirrors blocked -> []


# ---- more sports leagues -----------------------------------------------------
def test_soccer_leagues_span_multiple_countries():
    assert len(SOCCER_LEAGUES) >= 8
    assert {"E0", "D1", "SP1", "I1", "F1"}.issubset(SOCCER_LEAGUES)


# ---- persisted tidy store ----------------------------------------------------
def test_tidy_store_round_trips_and_is_idempotent(tmp_path):
    store = TidyStore(name="t", root=tmp_path)
    store.record("2026-07-01", "short_pct", {"GME": 0.25, "AMC": 0.18})
    store.record("2026-07-02", "short_pct", {"GME": 0.30, "AMC": 0.19})
    store.record("2026-07-02", "short_pct", {"GME": 0.31, "AMC": 0.19})  # same day overwrites
    # a fresh instance reads the persisted file
    fresh = TidyStore(name="t", root=tmp_path)
    assert list(fresh.series("GME", "short_pct")) == [0.25, 0.31]
    assert fresh.latest("short_pct") == {"GME": 0.31, "AMC": 0.19}
    assert list(fresh.series("NVDA", "short_pct")) == []  # unseen entity -> empty


# ---- catalog grew ------------------------------------------------------------
def test_source_catalog_grew_materially():
    assert source_count() > 700  # the four new source groups pushed the tally up
