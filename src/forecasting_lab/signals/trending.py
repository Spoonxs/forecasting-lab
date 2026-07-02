"""Trending-stocks automation: catch the NVIDIA and GME shapes early.

A concrete :class:`~forecasting_lab.pipeline.Pipeline` that, on each run:

1. pulls the day's **trending tickers** (Yahoo trending API),
2. fetches six months of **daily price/volume** per ticker (Yahoo chart API),
3. sweeps **news headlines** per ticker (Google News RSS, no key needed),
4. computes the two composites — **fast-money** (GME shape: volume spike, short-burst
   return, news intensity) and **secular momentum** (NVIDIA shape: 60-day trend,
   proximity to highs, volume uptrend) — ranked *separately*, and
5. files a dated digest with the top candidates and their headlines into ``inputs/``.

Honest limits, by design: free short-interest is weeks stale so it is *not*
in the fast-money composite (see ``signal-monitoring.md``); news intensity is
headline count, not sentiment; and every flag means "look closer", never "enter".
Not financial advice.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd

from ..pipeline.base import Pipeline
from ..pipeline.digest import render_digest
from ..utils.http import HttpClient
from .composites import composite_score

TRENDING_URL = "https://query1.finance.yahoo.com/v1/finance/trending/US"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
NEWS_RSS = "https://news.google.com/rss/search"

# Fast money (GME shape): positioning and crowd velocity, days-to-weeks horizon.
FAST_MONEY_WEIGHTS = {
    "volume_spike": 1.0,  # today vs 20d average volume
    "ret_5d": 1.0,  # short burst
    "social_mentions": 1.0,  # Reddit cashtag velocity (0 when Reddit blocked)
    "news_intensity": 0.75,  # headlines in the last 48h
    "vol_expansion": 0.5,  # recent vs trailing volatility
}

# Secular momentum (NVIDIA shape): trend and persistence, months horizon.
MOMENTUM_TREND_WEIGHTS = {
    "ret_60d": 1.0,
    "pct_from_high": 0.75,  # closeness to the period high (0 = at high)
    "ret_20d": 0.75,
    "volume_trend": 0.5,  # 20d vs 60d average volume
}


class TrendingFetcher:
    """Thin, swappable data access — tests inject a stub with the same surface."""

    def __init__(self, http: HttpClient | None = None):
        self.http = http or HttpClient(
            user_agent="Mozilla/5.0 (research; forecasting-lab)"
        )

    def trending_tickers(self, count: int = 15) -> list[str]:
        data = self.http.get_json(TRENDING_URL, params={"count": count})
        quotes = (data.get("finance", {}).get("result") or [{}])[0].get("quotes", [])
        return [q["symbol"] for q in quotes if q.get("symbol")]

    def daily_history(self, symbol: str, range_: str = "6mo") -> pd.DataFrame:
        """Daily close/volume for one symbol. Empty frame on missing data."""
        data = self.http.get_json(
            CHART_URL.format(symbol=symbol),
            params={"range": range_, "interval": "1d"},
        )
        result = (data.get("chart", {}).get("result") or [None])[0]
        if not result:
            return pd.DataFrame(columns=["date", "close", "volume"])
        stamps = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(stamps, unit="s"),
                "close": quote.get("close") or [],
                "volume": quote.get("volume") or [],
            }
        )
        return frame.dropna().reset_index(drop=True)

    def news_headlines(self, query: str, hours: int = 48) -> list[str]:
        """Headlines from the last ``hours`` via Google News RSS (stdlib parse)."""
        resp = self.http.get(
            NEWS_RSS, params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
        )
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        titles: list[str] = []
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            return titles
        for item in root.iter("item"):
            title = item.findtext("title") or ""
            pub = item.findtext("pubDate")
            if pub:
                try:
                    if parsedate_to_datetime(pub) < cutoff:
                        continue
                except (TypeError, ValueError):
                    pass
            if title:
                titles.append(title)
        return titles


def compute_features(history: pd.DataFrame, n_headlines: int) -> dict[str, float] | None:
    """Per-ticker features from daily history + news count. None if too short."""
    if len(history) < 40:
        return None
    close = history["close"].to_numpy(dtype=float)
    volume = history["volume"].to_numpy(dtype=float)

    def ret(days: int) -> float:
        return close[-1] / close[-min(days + 1, len(close))] - 1.0

    avg20 = float(np.mean(volume[-21:-1])) if np.mean(volume[-21:-1]) else np.nan
    avg60 = float(np.mean(volume[-61:-1])) if len(volume) > 60 else avg20
    recent_vol = float(np.std(np.diff(np.log(close[-11:]))))
    trailing_vol = float(np.std(np.diff(np.log(close[-61:-10]))))

    return {
        "ret_5d": ret(5),
        "ret_20d": ret(20),
        "ret_60d": ret(60),
        "pct_from_high": close[-1] / float(np.max(close)) - 1.0,  # <= 0, 0 = at high
        "volume_spike": float(volume[-1]) / avg20 if avg20 else np.nan,
        "volume_trend": (avg20 / avg60) if avg60 else np.nan,
        "vol_expansion": (recent_vol / trailing_vol) if trailing_vol else np.nan,
        "news_intensity": float(n_headlines),
    }


class TrendingStocksPipeline(Pipeline):
    """trending tickers -> history + news -> two composites -> dated digest."""

    slug = "trending-stocks"

    def __init__(
        self,
        fetcher: TrendingFetcher | None = None,
        *,
        count: int = 15,
        top: int = 5,
        news_hours: int = 48,
        use_social: bool = True,
    ):
        self.fetcher = fetcher or TrendingFetcher()
        self.count = count
        self.top = top
        self.news_hours = news_hours
        self.use_social = use_social
        self._social: dict[str, int] = {}

    def fetch(self) -> dict:
        tickers = self.fetcher.trending_tickers(self.count)
        out: dict[str, dict] = {}
        for symbol in tickers:
            history = self.fetcher.daily_history(symbol)
            headlines = self.fetcher.news_headlines(
                f"{symbol} stock", hours=self.news_hours
            )
            out[symbol] = {"history": history, "headlines": headlines}
        # Optional Reddit social velocity — best-effort, never fatal.
        self._social = {}
        if self.use_social and tickers:
            try:
                from ..sources.social import mention_counts

                self._social = mention_counts(list(tickers))
            except Exception:  # noqa: BLE001 - social is a bonus signal, not required
                self._social = {}
        return out

    def process(self, raw: dict) -> str:
        rows, headlines_by_ticker = [], {}
        reddit_ok = bool(self._social.get("_reddit_reachable"))
        for symbol, blob in raw.items():
            feats = compute_features(blob["history"], len(blob["headlines"]))
            if feats is None:
                continue
            feats["social_mentions"] = float(self._social.get(symbol, 0))
            headlines_by_ticker[symbol] = blob["headlines"][:3]
            rows.append({"ticker": symbol, **feats})

        if not rows:
            return render_digest(
                "Trending Stocks Digest",
                {"Status": "_no trending tickers had enough history to score_"},
                disclaimer=_DISCLAIMER,
            )

        frame = pd.DataFrame(rows)
        fast = composite_score(frame, FAST_MONEY_WEIGHTS, out_col="fast_money")
        trend = composite_score(frame, MOMENTUM_TREND_WEIGHTS, out_col="momentum")

        sections = {
            "Fast-money candidates (GME shape)": _rank_table(
                fast, "fast_money", ["volume_spike", "ret_5d", "news_intensity"], self.top
            ),
            "Secular-momentum candidates (NVIDIA shape)": _rank_table(
                trend, "momentum", ["ret_60d", "pct_from_high", "ret_20d"], self.top
            ),
            "Recent headlines (top fast-money names)": _headline_block(
                fast.head(self.top)["ticker"], headlines_by_ticker
            ),
            "Coverage": (
                f"{len(frame)} of {len(raw)} trending tickers had scoreable history. "
                + ("Reddit social velocity: live." if reddit_ok else "Reddit social velocity: unavailable (blocked here, active in the cloud).")
            ),
        }
        return render_digest("Trending Stocks Digest", sections, disclaimer=_DISCLAIMER)


_DISCLAIMER = (
    "Surfaces candidates from public trending/news data, ranked by composite z-scores. "
    "Most flags do nothing; free data is delayed; this is 'look closer', never 'enter'. "
    "Not financial advice."
)


def _rank_table(scored: pd.DataFrame, score_col: str, detail_cols: list[str], top: int) -> str:
    cols = ["ticker", score_col, *detail_cols]
    head = scored.head(top)[cols]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in head.iterrows():
        cells = [f"{v:.3f}" if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _headline_block(tickers, headlines_by_ticker: dict) -> str:
    parts = []
    for symbol in tickers:
        for title in headlines_by_ticker.get(symbol, []):
            parts.append(f"- **{symbol}**: {title}")
    return "\n".join(parts) if parts else "_no recent headlines_"
