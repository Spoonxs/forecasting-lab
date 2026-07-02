from datetime import date

from forecasting_lab.media.entities import extract_themes, extract_tickers
from forecasting_lab.media.watch import MediaWatchPipeline
from forecasting_lab.media.youtube import parse_feed

_FEED = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
  <entry>
    <yt:videoId>abc123</yt:videoId>
    <title>Why NVIDIA and the AI trade keep ripping</title>
    <published>2026-07-01T12:00:00Z</published>
    <media:group><media:description>Nvidia, OpenAI, and $AMD in focus.</media:description></media:group>
  </entry>
</feed>"""


def test_parse_feed_pulls_title_desc_date():
    vids = parse_feed(_FEED)
    assert len(vids) == 1
    assert vids[0]["title"].startswith("Why NVIDIA")
    assert vids[0]["published"] == "2026-07-01"
    assert "OpenAI" in vids[0]["description"]
    assert parse_feed(b"garbage") == []


def test_extract_tickers_names_and_cashtags():
    text = "NVIDIA earnings crushed it, $AMD too, and GameStop squeezed again"
    found = extract_tickers(text)
    assert {"NVDA", "AMD", "GME"} <= found
    # a curated name not present shouldn't appear
    assert "AAPL" not in found


def test_extract_tickers_avoids_false_positive():
    # 'apple pie' should not surface AAPL (alias is 'apple inc' / 'iphone')
    assert "AAPL" not in extract_tickers("I ate apple pie today")


def test_extract_themes():
    assert "AI" in extract_themes("OpenAI and ChatGPT dominate the AI chips race")
    assert "crypto" in extract_themes("Bitcoin is exploding again")
    assert extract_themes("nothing relevant here") == set()


class _StubYouTube:
    """Patch target for recent_videos + news."""


def test_pipeline_builds_buzz_and_digest(tmp_path, monkeypatch):

    def fake_recent(channel_id, http=None):
        if channel_id:
            return [{"title": "NVIDIA and OpenAI news", "description": "$AMD and Bitcoin", "published": "2026-07-01", "video_id": "x"}]
        return []

    class _Fetcher:
        def news_headlines(self, q, hours=48):
            return ["GameStop short squeeze returns", "Tesla delivery beat"]

    monkeypatch.setattr("forecasting_lab.media.youtube.recent_videos", fake_recent)
    monkeypatch.setattr("forecasting_lab.signals.trending.TrendingFetcher", lambda *a, **k: _Fetcher())

    from forecasting_lab.media.watchlist import Channel

    pipe = MediaWatchPipeline(channels=[Channel("Test", "tech", channel_id="UC123", news_query="AI stocks")])
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "Media Watch Digest" in text
    assert "NVDA" in text and "AMD" in text and "GME" in text
    assert pipe.buzz.get("NVDA", 0) >= 1
    assert "Not financial advice" in text


def test_resolve_channel_id_extracts_uc(monkeypatch):
    import forecasting_lab.media.youtube as yt

    class _Resp:
        text = 'stuff "UCdK2BueKxC9VxXh7e1Ne4oQ" more stuff'

    class _C:
        def get(self, url):
            return _Resp()

    monkeypatch.setattr(yt, "HttpClient", lambda *a, **k: _C())
    assert yt.resolve_channel_id("SomeTestHandle_xyz", refresh=True) == "UCdK2BueKxC9VxXh7e1Ne4oQ"


def test_watchlist_is_large_with_fallback_queries():
    from forecasting_lab.media.watchlist import WATCHLIST, channel_count

    assert channel_count() >= 90  # "like 100 channels"
    # every voice has a news_query fallback so a wrong handle is never fatal
    assert all(ch.news_query for ch in WATCHLIST)
    lenses = {ch.lens for ch in WATCHLIST}
    assert {"markets", "macro", "tech", "ai", "crypto", "politics", "geo", "news"} <= lenses


def test_pipeline_degrades_when_nothing_reachable(tmp_path, monkeypatch):
    monkeypatch.setattr("forecasting_lab.media.youtube.recent_videos", lambda cid, http=None: [])

    class _Dead:
        def news_headlines(self, q, hours=48):
            raise ConnectionError("blocked")

    monkeypatch.setattr("forecasting_lab.signals.trending.TrendingFetcher", lambda *a, **k: _Dead())
    from forecasting_lab.media.watchlist import Channel

    pipe = MediaWatchPipeline(channels=[Channel("Test", "tech", news_query="x")])
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    assert "no media reachable" in path.read_text(encoding="utf-8")
