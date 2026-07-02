from datetime import date

import numpy as np
import pandas as pd

from forecasting_lab.signals.trending import (
    TrendingStocksPipeline,
    compute_features,
)


def _history(days=130, drift=0.0, spike_last_volume=False, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + drift + rng.normal(0, 0.01, days))
    volume = rng.integers(1_000_000, 1_500_000, days).astype(float)
    if spike_last_volume:
        volume[-1] *= 8
    return pd.DataFrame(
        {"date": pd.date_range("2026-01-01", periods=days), "close": close, "volume": volume}
    )


def test_compute_features_shapes_and_signs():
    f = compute_features(_history(drift=0.004), n_headlines=7)
    assert f is not None
    assert f["ret_60d"] > 0  # uptrend drift shows up
    assert f["pct_from_high"] <= 0  # never above the period high
    assert f["news_intensity"] == 7.0
    # too-short history refuses to score rather than fabricate
    assert compute_features(_history(days=20), 0) is None


def test_volume_spike_feature_detects_spike():
    quiet = compute_features(_history(seed=1), 0)
    spiked = compute_features(_history(spike_last_volume=True, seed=1), 0)
    assert spiked["volume_spike"] > 4 * quiet["volume_spike"]


class _StubFetcher:
    """One squeeze-shaped name, one momentum-shaped name, one unscoreable."""

    def trending_tickers(self, count=15):
        return ["SQUEEZY", "STEADY", "NODATA"]

    def daily_history(self, symbol, range_="6mo"):
        if symbol == "SQUEEZY":  # flat then a violent last week + volume spike
            h = _history(drift=0.0, spike_last_volume=True, seed=2)
            h.loc[h.index[-5:], "close"] = h["close"].iloc[-6] * np.array([1.1, 1.25, 1.4, 1.6, 1.9])
            return h
        if symbol == "STEADY":  # persistent grind higher
            return _history(drift=0.005, seed=3)
        return pd.DataFrame(columns=["date", "close", "volume"])

    def news_headlines(self, query, hours=48):
        if query.startswith("SQUEEZY"):
            return [f"SQUEEZY headline {i}" for i in range(12)]
        return ["STEADY quarterly note"] if query.startswith("STEADY") else []


def test_pipeline_ranks_shapes_correctly_and_writes_digest(tmp_path):
    pipe = TrendingStocksPipeline(fetcher=_StubFetcher(), top=2, use_social=False)
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name == "2026-07-01-trending-stocks.md"
    # the violent mover tops fast-money; the grinder tops secular momentum
    fast_section = text.split("Fast-money")[1].split("Secular-momentum")[0]
    momentum_section = text.split("Secular-momentum")[1].split("Recent headlines")[0]
    assert fast_section.find("SQUEEZY") < fast_section.find("STEADY")
    assert "STEADY" in momentum_section
    # headlines and honesty
    assert "SQUEEZY headline 0" in text
    assert "Not financial advice" in text
    assert "2 of 3 trending tickers" in text


def test_pipeline_survives_all_unscoreable(tmp_path):
    class _Empty:
        def trending_tickers(self, count=15):
            return ["X"]

        def daily_history(self, symbol, range_="6mo"):
            return pd.DataFrame(columns=["date", "close", "volume"])

        def news_headlines(self, query, hours=48):
            return []

    path = TrendingStocksPipeline(fetcher=_Empty(), use_social=False).run(on=date(2026, 7, 1), out_dir=tmp_path)
    assert "no trending tickers" in path.read_text(encoding="utf-8")


def test_social_mentions_feed_the_fast_money_composite(tmp_path, monkeypatch):
    # inject reddit mentions so SQUEEZY also leads on social, not just volume
    import forecasting_lab.signals.trending as trending

    def fake_mentions(tickers, *a, **k):
        return {"SQUEEZY": 40, "STEADY": 1, "_reddit_reachable": 1}

    monkeypatch.setattr(trending, "mention_counts", fake_mentions, raising=False)
    monkeypatch.setattr(
        "forecasting_lab.sources.social.mention_counts", fake_mentions, raising=False
    )
    pipe = TrendingStocksPipeline(fetcher=_StubFetcher(), top=2, use_social=True)
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "Reddit social velocity: live" in text
    assert "SQUEEZY" in text
