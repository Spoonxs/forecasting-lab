"""The media-watch pipeline: what are the key voices talking about, and about whom.

For each channel in the watch list it pulls recent video titles/descriptions
(YouTube RSS) and a Google News sweep for the voice/topic, then extracts the
tickers and themes mentioned. Output: a dated digest ("what HasanAbi / Bloomberg /
the AI theme are on today") plus a per-ticker **buzz** count that other signals
can consume. Blocked on this sandbox; live in the cloud (RSS + News both work there).
"""

from __future__ import annotations

from collections import Counter

from ..pipeline.base import Pipeline
from ..pipeline.digest import render_digest
from .entities import build_name_index, extract_themes, extract_tickers
from .sentiment import score_text
from .watchlist import WATCHLIST


class MediaWatchPipeline(Pipeline):
    """watch list -> recent videos + news -> ticker/theme buzz -> dated digest."""

    slug = "media-watch"

    def __init__(self, channels=None, news_hours: int = 48, top: int = 12, max_channels: int | None = None):
        self.channels = channels if channels is not None else WATCHLIST
        if max_channels:
            self.channels = self.channels[:max_channels]
        self.news_hours = news_hours
        self.top = top

    def fetch(self) -> dict:
        from ..signals.trending import TrendingFetcher
        from .youtube import recent_videos, resolve_channel_id

        fetcher = TrendingFetcher()
        out: dict[str, dict] = {}
        for ch in self.channels:
            # channel id: explicit, else resolve the @handle (cached), else news-only
            cid = ch.channel_id or (resolve_channel_id(ch.handle) if ch.handle else None)
            videos = recent_videos(cid) if cid else []
            headlines = []
            if ch.news_query:
                try:
                    headlines = fetcher.news_headlines(ch.news_query, hours=self.news_hours)
                except Exception:  # noqa: BLE001 - one dead source can't sink the sweep
                    headlines = []
            out[ch.name] = {"lens": ch.lens, "videos": videos, "headlines": headlines}
        return out

    def process(self, raw: dict) -> str:
        index = build_name_index()
        ticker_buzz: Counter = Counter()
        theme_buzz: Counter = Counter()
        ticker_sent: dict[str, list[float]] = {}
        talking: list[str] = []
        reachable = False

        for voice, blob in raw.items():
            texts = [v["title"] + " " + v.get("description", "") for v in blob["videos"]]
            texts += blob["headlines"]
            if texts:
                reachable = True
            for text in texts:
                tone = score_text(text)
                for t in extract_tickers(text, index):
                    ticker_buzz[t] += 1
                    if tone:
                        ticker_sent.setdefault(t, []).append(tone)
                for th in extract_themes(text):
                    theme_buzz[th] += 1
            latest = (blob["videos"][:2] and [v["title"] for v in blob["videos"][:2]]) or blob["headlines"][:2]
            if latest:
                talking.append(f"- **{voice}** ({blob['lens']}): " + " / ".join(latest))

        self.buzz = dict(ticker_buzz)  # exposed for other signals
        self.sentiment = {t: sum(v) / len(v) for t, v in ticker_sent.items()}  # avg tone per ticker

        if not reachable:
            body = "_no media reachable (blocked on this network; live in the cloud)_"
            sections = {"Status": body}
        else:
            ticker_tbl = _counter_table(ticker_buzz, "ticker", self.top) or "_no tickers named_"
            theme_tbl = _counter_table(theme_buzz, "theme", 8) or "_no themes flagged_"
            lenses = sorted({ch.lens for ch in self.channels})
            sent_rows = sorted(self.sentiment.items(), key=lambda kv: kv[1], reverse=True)
            if sent_rows:
                pos = ", ".join(f"{t} (+{s:.2f})" for t, s in sent_rows[:3] if s > 0)
                neg = ", ".join(f"{t} ({s:.2f})" for t, s in reversed(sent_rows[-3:]) if s < 0)
                sentiment_line = f"most positive tone: {pos or 'none'}; most negative: {neg or 'none'}"
            else:
                sentiment_line = "_no toned coverage_"
            sections = {
                "Most-named tickers (attention, not endorsement)": ticker_tbl,
                "Tone (finance lexicon; weak proxy, validate before trusting)": sentiment_line,
                "Hot themes": theme_tbl,
                "What the voices are on today": "\n".join(talking) or "_quiet_",
                "Coverage": f"{len(self.channels)} voices watched across {len(lenses)} lenses "
                f"({', '.join(lenses)}); YouTube auto-updates each run via RSS/yt-dlp.",
            }
        return render_digest(
            "Media Watch Digest",
            sections,
            disclaimer=(
                "Surfaces what key voices are discussing and whom they name. Attention is "
                "not truth or a buy signal, and pundits are often wrong or late. Not financial advice."
            ),
        )


def _counter_table(counter: Counter, label: str, top: int) -> str:
    items = counter.most_common(top)
    if not items:
        return ""
    lines = [f"| {label} | mentions |", "| --- | --- |"]
    for name, count in items:
        lines.append(f"| {name} | {count} |")
    return "\n".join(lines)
