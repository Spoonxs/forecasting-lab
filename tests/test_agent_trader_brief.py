"""P0 of the agent trader: the daily brief aggregates injectable sources, degrades
honestly when one is blocked, caches, round-trips, and holds no LLM/broker code."""

from __future__ import annotations

from pathlib import Path

import forecasting_lab.agent_trader.brief as brief_mod
from forecasting_lab.agent_trader import DailyBrief, build_brief, daily_brief
from forecasting_lab.utils.cache import DiskCache


def test_build_brief_assembles_injected_sections():
    fetchers = {"price": lambda t: {"last": 100.0}, "news": lambda t: {"count": 3}}
    b = build_brief("nvda", "2026-07-03", fetchers)
    assert b.ticker == "NVDA" and b.as_of == "2026-07-03"
    assert b.get("price").ok and b.get("price").data["last"] == 100.0
    assert b.get("news").ok and b.get("news").data["count"] == 3


def test_a_failing_source_degrades_without_crashing():
    def boom(_t):
        raise ConnectionError("blocked")

    b = build_brief("NVDA", "2026-07-03", {"price": lambda t: {"last": 1.0}, "fund": boom})
    assert b.get("price").ok is True
    assert b.get("fund").ok is False and b.get("fund").data == {}  # honest empty, no crash


def test_daily_brief_caches_and_does_not_refetch(tmp_path):
    calls = {"n": 0}

    def price(_t):
        calls["n"] += 1
        return {"last": 42.0}

    cache = DiskCache("t", ttl=3600, root=tmp_path)
    kw = dict(fetchers={"price": price}, cache=cache, now=1000.0)
    a = daily_brief("NVDA", "2026-07-03", **kw)
    b = daily_brief("NVDA", "2026-07-03", **kw)  # served from cache
    assert calls["n"] == 1  # the second call did not hit the source
    assert a.to_dict() == b.to_dict()


def test_brief_round_trips_through_dict():
    b = build_brief("NVDA", "2026-07-03", {"price": lambda t: {"last": 1.0}})
    assert DailyBrief.from_dict(b.to_dict()).to_dict() == b.to_dict()


def test_brief_layer_holds_no_llm_or_broker_code():
    src = Path(brief_mod.__file__).read_text(encoding="utf-8").lower()
    for term in ["anthropic", "claude_agent", "opus", "place_order", "submit_order",
                 "alpaca", "import requests"]:
        assert term not in src, f"the data layer must stay LLM/broker-free; found {term!r}"
