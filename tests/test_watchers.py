"""P6d section B — the watcher templates.

Pinned: each of the five templates fires on injected data and stays silent
otherwise; every event is dated by ITS SOURCE's own date (never the wall
clock) and carries a content hash of the exact inputs behind it; a missing
source is an honest stated skip, never a fabricated trigger; the feed file is
named by the newest event date and is not written at all without dated events;
config merges over stated defaults; the alerts digest and the home feed render
the events (with the audit hash) and degrade silently.
"""

from __future__ import annotations

import json
from datetime import date

from forecasting_lab.calibration_log.audit import content_hash
from forecasting_lab.pipeline.watchers import (
    DEFAULT_CONFIG,
    earnings_proximity_events,
    insider_cluster_events,
    load_config,
    macro_flip_events,
    run_watchers,
    squeeze_trigger_events,
    verdict_change_events,
    write_watchers_feed,
)


def test_earnings_proximity_fires_only_inside_the_window():
    ev = earnings_proximity_events(["NVDA", "VOO", "GHOST"],
                                   {"NVDA": 2, "VOO": 10}, "2026-07-01", days=3)
    assert [e["symbol"] for e in ev] == ["NVDA"]        # VOO outside, GHOST absent
    assert "reports in 2d" in ev[0]["reason"] and ev[0]["date"] == "2026-07-01"
    assert earnings_proximity_events(["NVDA"], {}, "2026-07-01") == []


def test_squeeze_trigger_fires_at_or_over_the_stated_threshold():
    ev = squeeze_trigger_events({"GME": 0.72, "AMC": 0.60, "AAPL": 0.31},
                                "2026-07-01", threshold=0.6)
    assert [e["symbol"] for e in ev] == ["AMC", "GME"]  # at + over; AAPL silent
    assert all("0.60 trigger" in e["reason"] for e in ev)
    assert ev[0]["inputs"]["metric"] == "short_volume_ratio"


def test_insider_cluster_fires_at_the_minimum():
    ev = insider_cluster_events({"XYZ": 4, "ABC": 2}, "2026-07-01", min_insiders=3)
    assert [e["symbol"] for e in ev] == ["XYZ"]
    assert "4 distinct insiders" in ev[0]["reason"]


def test_verdict_change_label_flip_and_score_move():
    prior = {"verdicts": {"NVDA": {"label": "BUY", "score": 0.30},
                          "VOO": {"label": "BUY", "score": 0.30},
                          "QQQ": {"label": "BUY", "score": 0.30}}}
    now = {"as_of": "2026-07-02", "verdicts": {
        "NVDA": {"label": "HOLD", "score": 0.10},       # label flip -> fires
        "VOO": {"label": "BUY", "score": 0.50},          # +0.20 move -> fires
        "QQQ": {"label": "BUY", "score": 0.35},          # +0.05 -> silent
        "NEW": {"label": "BUY", "score": 0.40}}}         # no prior row -> silent
    ev = verdict_change_events(now, prior, score_move=0.15)
    kinds = {e["symbol"]: e["reason"] for e in ev}
    assert set(kinds) == {"NVDA", "VOO"}
    assert "BUY -> HOLD" in kinds["NVDA"] and "label unchanged" in kinds["VOO"]
    assert all(e["date"] == "2026-07-02" for e in ev)   # dated by the artifact
    assert verdict_change_events(now, None) == []       # no prior -> nothing


def test_macro_flip_fires_on_crossings_only():
    up = macro_flip_events(0.55, 0.40, "2026-07-02", line=0.5)
    down = macro_flip_events(0.42, 0.60, "2026-07-02", line=0.5)
    assert "above" in up[0]["reason"] and "back below" in down[0]["reason"]
    assert macro_flip_events(0.65, 0.60, "2026-07-02", line=0.5) == []  # both above
    assert macro_flip_events(0.30, 0.40, "2026-07-02", line=0.5) == []  # both below


def test_events_carry_replayable_hashes():
    ev = squeeze_trigger_events({"GME": 0.9}, "2026-07-01", threshold=0.6)[0]
    assert ev["sha256"] == content_hash(ev["inputs"])   # replayable receipt


def test_missing_sources_are_honest_stated_skips(tmp_path):
    from forecasting_lab.sources.store import TidyStore

    result = run_watchers(config={k: dict(v) for k, v in DEFAULT_CONFIG.items()},
                          verdicts_dir=tmp_path / "none", inputs_dir=tmp_path,
                          store=TidyStore(root=tmp_path))
    assert result["events"] == []                        # nothing fabricated
    skipped = {s["kind"] for s in result["skips"]}
    assert skipped == {"earnings_proximity", "squeeze_trigger", "insider_cluster",
                       "verdict_change", "macro_flip"}
    assert all(s["reason"] for s in result["skips"])     # every skip states why


def test_runner_dates_events_by_the_sources_own_date(tmp_path):
    from forecasting_lab.sources.store import TidyStore

    store = TidyStore(root=tmp_path)
    store.record("2026-06-30", "short_volume_ratio", {"GME": 0.8})
    store.record("2026-06-30", "insider_cluster_buys", {"XYZ": 5})
    (tmp_path / "2026-06-28-macro-nowcast.json").write_text(
        json.dumps({"recession_prob_12m": 0.4}), encoding="utf-8")
    (tmp_path / "2026-06-29-macro-nowcast.json").write_text(
        json.dumps({"recession_prob_12m": 0.6}), encoding="utf-8")
    result = run_watchers(verdicts_dir=tmp_path / "none", inputs_dir=tmp_path, store=store)
    by_kind = {e["kind"]: e for e in result["events"]}
    assert by_kind["squeeze_trigger"]["date"] == "2026-06-30"   # the store's day
    assert by_kind["insider_cluster"]["date"] == "2026-06-30"
    assert by_kind["macro_flip"]["date"] == "2026-06-29"        # the sidecar's day


def test_feed_is_named_by_the_newest_event_and_never_wall_clock(tmp_path):
    events = (squeeze_trigger_events({"GME": 0.9}, "2026-06-30", 0.6)
              + macro_flip_events(0.6, 0.4, "2026-07-01"))
    path = write_watchers_feed({"events": events, "skips": []}, out_dir=tmp_path)
    assert path.name == "2026-07-01-watchers.json"       # max event date
    assert json.loads(path.read_text(encoding="utf-8"))["events"]
    assert write_watchers_feed({"events": [], "skips": [{"kind": "x", "reason": "y"}]},
                               out_dir=tmp_path) is None  # nothing dated -> no file
    assert str(date.today()) not in "".join(p.name for p in tmp_path.iterdir())


def test_config_merges_over_defaults(tmp_path):
    cfg_path = tmp_path / "watchers.json"
    cfg_path.write_text(json.dumps({"squeeze_trigger": {"threshold": 0.9},
                                    "unknown_kind": {"enabled": True}}), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg["squeeze_trigger"]["threshold"] == 0.9    # override applied
    assert cfg["squeeze_trigger"]["metric"] == "short_volume_ratio"  # default kept
    assert "unknown_kind" not in cfg                     # unknown ignored
    assert load_config(tmp_path / "missing.json") == DEFAULT_CONFIG


# ------------------------------------------------ Codex code-review fixes pinned
def test_alert_text_strips_markup_from_feed_reasons(monkeypatch):
    """Codex finding 1: feed text is file-based — markup never reaches the
    composed alert (Discord embeds render markdown)."""
    import forecasting_lab.pipeline.digest as digest
    from forecasting_lab.alerts.summary import _gather

    feed = {"events": [{"kind": "squeeze_trigger",
                        "reason": "<b>evil</b> [link](x) `code` *bold* GME 0.9",
                        "date": "2026-06-30", "sha256": "x", "inputs": {}}]}
    monkeypatch.setattr(digest, "read_latest_data", lambda slug, out_dir=None: feed)
    sections, _ = _gather(date(2026, 6, 30))
    items = next(items for name, items in sections if name == "Watchers fired")
    assert "<b>" not in items[0] and "[link]" not in items[0] and "`" not in items[0]
    assert "GME 0.9" in items[0]                        # the substance survives


def test_macro_date_comes_from_the_payload_not_the_filename(tmp_path):
    """Codex finding 2: a renamed/regenerated sidecar can't re-date its source."""
    from forecasting_lab.pipeline.watchers import _macro_probs

    (tmp_path / "2026-07-09-macro-nowcast.json").write_text(
        json.dumps({"recession_prob_12m": 0.4, "as_of": "2026-07-01"}), encoding="utf-8")
    (tmp_path / "2026-07-10-macro-nowcast.json").write_text(
        json.dumps({"recession_prob_12m": 0.6,
                    "freshness": {"fetched_at": "2026-07-02T09:00:00Z"}}), encoding="utf-8")
    probs = _macro_probs(tmp_path)
    assert probs == [("2026-07-01", 0.4), ("2026-07-02", 0.6)]  # payload dates win


def test_home_feed_and_alerts_render_events(monkeypatch):
    import forecasting_lab.pipeline.digest as digest
    from forecasting_lab.dashboard.render import _watchers_feed_html

    feed = {"events": squeeze_trigger_events({"GME": 0.9}, "2026-06-30", 0.6),
            "skips": [{"kind": "earnings_proximity", "reason": "no source yet"}]}
    monkeypatch.setattr(digest, "read_latest_data", lambda slug, out_dir=None: feed)
    html = _watchers_feed_html()
    assert "squeeze_trigger" in html and "audit " in html
    assert "no source yet" in html                       # skips shown honestly
    monkeypatch.setattr(digest, "read_latest_data", lambda slug, out_dir=None: None)
    assert _watchers_feed_html() == ""                   # no feed -> silent
    # the alerts composer picks the feed up as a flagged section
    from forecasting_lab.alerts.summary import _gather

    monkeypatch.setattr(digest, "read_latest_data", lambda slug, out_dir=None: feed)
    sections, flagged = _gather(date(2026, 6, 30))
    assert flagged and any(name == "Watchers fired" for name, _ in sections)
