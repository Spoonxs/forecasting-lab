"""P8-2 — the price panel (polite, cached, self-healing).

Pinned: first sight of a symbol is a full pull; a fresh cache skips the
network entirely; a stale cache gets an incremental pull merged with fresh
values winning; an overlap disagreement >1% (corporate action) triggers a full
refetch that replaces the cache; failures are isolated per symbol and a run of
consecutive failures opens the circuit breaker (the rest are 'not attempted',
never hammered); the manifest labels every series (last_date / fetched_at /
source / adjusted); panel_frame drops short series (missing evidence, never
zeros); the point-in-time guard drops rows after as_of; nothing reads the
wall clock (now is injected).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from forecasting_lab.pipeline.prices import (
    _future_guard,
    mark_full_refresh,
    panel_frame,
    stale_symbols,
    update_panel,
    weekly_full_refresh_due,
)

NOW = date(2026, 7, 10)


def _chart(closes_by_date: dict, adjusted: bool = True) -> dict:
    import calendar
    from datetime import datetime

    stamps = [int(calendar.timegm(datetime.fromisoformat(d + "T16:00:00").timetuple()))
              for d in closes_by_date]
    closes = list(closes_by_date.values())
    ind = {"adjclose": [{"adjclose": closes}]} if adjusted else {}
    ind["quote"] = [{"close": closes}]
    return {"chart": {"result": [{"timestamp": stamps, "indicators": ind}]}}


class _Http:
    """Scripted fetcher: symbol -> list of responses (dict, or Exception)."""

    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def get_json(self, url, params=None):
        sym = url.rsplit("/", 1)[1]
        self.calls.append((sym, params["range"]))
        nxt = self.script[sym].pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


DAYS = [f"2026-0{m}-1{d}" for m in (1, 2, 3, 4, 5) for d in range(5)]  # 25 days


def test_first_pull_is_full_then_fresh_cache_skips(tmp_path):
    hist = {d: 100.0 + i for i, d in enumerate(DAYS)}
    http = _Http({"NVDA": [_chart(hist)]})
    r1 = update_panel(["NVDA"], now=NOW, http=http, root=tmp_path, pacing=0)
    assert r1["updated"] == 1 and http.calls == [("NVDA", "1y")]  # full range first
    meta = json.loads((tmp_path / "panel_meta.json").read_text(encoding="utf-8"))
    assert meta["NVDA"]["source"] == "yahoo-chart" and meta["NVDA"]["adjusted"] is True
    assert meta["NVDA"]["fetched_at"] == "2026-07-10" and meta["NVDA"]["rows"] == 25
    # cache stamped fresh -> the second run makes NO network calls
    meta["NVDA"]["last_date"] = "2026-07-10"
    (tmp_path / "panel_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    r2 = update_panel(["NVDA"], now=NOW, http=_Http({"NVDA": []}), root=tmp_path, pacing=0)
    assert r2["skipped_fresh"] == 1 and r2["updated"] == 0


def test_incremental_merge_fresh_values_win(tmp_path):
    old = {d: 100.0 for d in DAYS[:20]}
    http = _Http({"NVDA": [_chart(old)]})
    update_panel(["NVDA"], now=date(2026, 6, 1), http=http, root=tmp_path, pacing=0)
    # later: a trailing pull overlapping the tail (same values) + new days
    tail = {DAYS[19]: 100.0, "2026-06-10": 111.0, "2026-06-11": 112.0}
    http2 = _Http({"NVDA": [_chart(tail)]})
    r = update_panel(["NVDA"], now=NOW, http=http2, root=tmp_path, pacing=0)
    assert r["updated"] == 1 and http2.calls == [("NVDA", "1mo")]  # incremental
    frame = panel_frame(["NVDA"], root=tmp_path, min_rows=5)
    assert frame["NVDA"].index[-1] == "2026-06-11" and frame["NVDA"].iloc[-1] == 112.0
    assert len(frame) == 22                              # union, no duplicates


def test_corporate_action_overlap_mismatch_triggers_full_refetch(tmp_path):
    old = {d: 100.0 for d in DAYS[:20]}
    update_panel(["NVDA"], now=date(2026, 6, 1),
                 http=_Http({"NVDA": [_chart(old)]}), root=tmp_path, pacing=0)
    # a 4:1 split re-adjusted history: the overlap now reads 25, not 100
    split_tail = {DAYS[19]: 25.0, "2026-06-10": 26.0}
    split_full = {d: 25.0 for d in DAYS[:20]} | {"2026-06-10": 26.0}
    http = _Http({"NVDA": [_chart(split_tail), _chart(split_full)]})
    r = update_panel(["NVDA"], now=NOW, http=http, root=tmp_path, pacing=0)
    assert r["refetched"] == 1                            # self-healed
    assert http.calls == [("NVDA", "1mo"), ("NVDA", "1y")]
    frame = panel_frame(["NVDA"], root=tmp_path, min_rows=5)
    assert float(frame["NVDA"].iloc[0]) == 25.0           # the past was replaced


def test_failures_are_isolated_and_the_circuit_breaks(tmp_path):
    good = {d: 100.0 + i for i, d in enumerate(DAYS)}
    script = {f"BAD{i}": [ConnectionError("down")] for i in range(9)}
    script["GOOD"] = [_chart(good)]
    order = [f"BAD{i}" for i in range(9)] + ["GOOD"]
    r = update_panel(order, now=NOW, http=_Http(script), root=tmp_path, pacing=0)
    assert len(r["failed"]) == 8                          # breaker after 8 consecutive
    assert r["not_attempted"] == ["BAD8", "GOOD"]         # the rest never hammered
    # a failure between successes never opens the breaker
    script2 = {"A": [_chart(good)], "B": [ConnectionError("x")], "C": [_chart(good)]}
    r2 = update_panel(["A", "B", "C"], now=NOW, http=_Http(script2),
                      root=tmp_path / "2", pacing=0)
    assert r2["updated"] == 2 and len(r2["failed"]) == 1 and not r2["not_attempted"]


def test_panel_frame_drops_short_series_and_guard_is_point_in_time(tmp_path):
    long = {d: 100.0 + i for i, d in enumerate(DAYS)}
    short = {"2026-05-01": 10.0}
    http = _Http({"LONG": [_chart(long)], "TINY": [_chart(short)]})
    update_panel(["LONG", "TINY"], now=NOW, http=http, root=tmp_path, pacing=0)
    frame = panel_frame(["LONG", "TINY", "GHOST"], root=tmp_path, min_rows=10)
    assert list(frame.columns) == ["LONG"]                # short + absent are MISSING
    guarded = _future_guard(frame, date(2026, 3, 1))
    assert all(d <= "2026-03-01" for d in guarded.index)  # nothing from the future


def test_staleness_and_weekly_refresh_bookkeeping(tmp_path):
    hist = {d: 100.0 for d in DAYS}
    update_panel(["NVDA"], now=date(2026, 5, 15),
                 http=_Http({"NVDA": [_chart(hist)]}), root=tmp_path, pacing=0)
    assert stale_symbols(["NVDA", "GHOST"], now=NOW, root=tmp_path) == ["NVDA", "GHOST"]
    assert weekly_full_refresh_due(now=NOW, root=tmp_path) is True
    mark_full_refresh(now=NOW, root=tmp_path)
    assert weekly_full_refresh_due(now=NOW, root=tmp_path) is False
    assert weekly_full_refresh_due(now=date(2026, 7, 20), root=tmp_path) is True
    # receipts are JSON-serializable (they ship in the run manifest)
    json.dumps(update_panel([], now=NOW, http=None if False else _Http({}),
                            root=tmp_path, pacing=0))


# ------------------------------------------------ Codex code-review fixes pinned
def test_yesterdays_cache_still_pulls(tmp_path):
    """Codex finding 1: only a cache carrying TODAY's close may skip."""
    hist = {d: 100.0 for d in DAYS}
    update_panel(["NVDA"], now=date(2026, 7, 9),
                 http=_Http({"NVDA": [_chart(hist)]}), root=tmp_path, pacing=0)
    meta = json.loads((tmp_path / "panel_meta.json").read_text(encoding="utf-8"))
    meta["NVDA"]["last_date"] = "2026-07-09"             # yesterday relative to NOW
    (tmp_path / "panel_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    tail = {"2026-07-09": 100.0, "2026-07-10": 101.0}
    http = _Http({"NVDA": [_chart(tail)]})
    r = update_panel(["NVDA"], now=NOW, http=http, root=tmp_path, pacing=0)
    assert r["updated"] == 1 and http.calls == [("NVDA", "1mo")]  # it pulled


def test_corrupt_cache_is_that_symbols_problem_only(tmp_path):
    """Codex finding 2: a garbage CSV or manifest date refetches, never crashes."""
    (tmp_path / "BAD.csv").write_text("not,a,csv\n%%%", encoding="utf-8")
    (tmp_path / "panel_meta.json").write_text(
        json.dumps({"BAD": {"last_date": "not-a-date"}}), encoding="utf-8")
    hist = {d: 100.0 for d in DAYS}
    r = update_panel(["BAD", "GOOD"], now=NOW,
                     http=_Http({"BAD": [_chart(hist)], "GOOD": [_chart(hist)]}),
                     root=tmp_path, pacing=0)
    assert r["updated"] == 2 and not r["failed"]          # both healed


def test_failed_corporate_action_refetch_trips_the_breaker(tmp_path):
    """Codex finding 3: a hammering refetch loop counts toward the breaker."""
    old = {d: 100.0 for d in DAYS[:20]}
    script = {}
    for i in range(9):
        sym = f"S{i}"
        update_panel([sym], now=date(2026, 6, 1),
                     http=_Http({sym: [_chart(old)]}), root=tmp_path, pacing=0)
        # mismatched overlap, then the full refetch fails too
        script[sym] = [_chart({DAYS[19]: 25.0}), ConnectionError("down")]
    script["LAST"] = [_chart(old)]
    r = update_panel([f"S{i}" for i in range(9)] + ["LAST"], now=NOW,
                     http=_Http(script), root=tmp_path, pacing=0)
    assert len(r["failed"]) == 8                          # breaker tripped by refetch fails
    assert "LAST" in r["not_attempted"]


def test_future_dated_rows_never_enter_the_cache(tmp_path):
    """Codex finding 4: point-in-time by construction — the cache can't leak
    rows dated after `now`, so panel_frame can't either."""
    hist = {d: 100.0 for d in DAYS} | {"2026-12-25": 999.0}   # a future row
    update_panel(["NVDA"], now=NOW, http=_Http({"NVDA": [_chart(hist)]}),
                 root=tmp_path, pacing=0)
    frame = panel_frame(["NVDA"], root=tmp_path, min_rows=5)
    assert frame.index.max() <= NOW.isoformat() and 999.0 not in frame["NVDA"].values


def test_prices_cache_stays_out_of_git():
    gi = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "!/data/prices" not in gi                      # no carve-out: ignored
