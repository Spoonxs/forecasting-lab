"""P6d section D — the connector health panel.

Pinned: statuses follow the stated budgets (ok / degraded / stale) with
"never fetched" as an honest first-class state; ages come from the artifacts'
OWN dates against a caller-supplied now (nothing in the module reads the wall
clock); a future-dated stamp is flagged, not trusted; the panel renders every
row server-side with the note on screen; and NO infinite retry loop exists
anywhere in the package (rate-limited jobs must skip cleanly).
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from forecasting_lab.dashboard.render import _health_table
from forecasting_lab.pipeline.health import FEEDS, STORE_METRICS, connector_health

NOW = date(2026, 7, 10)


class _EmptyStore:
    def load(self):
        import pandas as pd

        return pd.DataFrame(columns=["date", "entity", "metric", "value"])


def _health(tmp_path, **kw):
    kw.setdefault("inputs_dir", tmp_path / "inputs")
    kw.setdefault("verdicts_dir", tmp_path / "verdicts")
    kw.setdefault("store", _EmptyStore())
    (tmp_path / "inputs").mkdir(exist_ok=True)
    return connector_health(NOW, **kw)


def test_never_fetched_is_a_stated_state(tmp_path):
    rows = _health(tmp_path)
    assert len(rows) == len(FEEDS) + 1 + len(STORE_METRICS)   # feeds + verdicts + store
    assert all(r["status"] == "never" and r["last"] is None for r in rows)
    assert all("never fetched" in r["note"] for r in rows)


def test_budgets_drive_ok_degraded_stale(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    # trending budget: ok<=2d, degraded<=7d, else stale
    (inputs / "2026-07-09-trending-stocks.json").write_text("{}", encoding="utf-8")   # 1d
    (inputs / "2026-07-05-market-divergence.json").write_text("{}", encoding="utf-8")  # 5d
    (inputs / "2026-05-01-macro-nowcast.json").write_text("{}", encoding="utf-8")      # 70d
    rows = {r["name"]: r for r in _health(tmp_path, inputs_dir=inputs)}
    assert rows["Trending scanner"]["status"] == "ok" and rows["Trending scanner"]["age_days"] == 1
    assert rows["Cross-venue divergence"]["status"] == "degraded"
    assert rows["Macro nowcast"]["status"] == "stale"
    assert "history, not signal" in rows["Macro nowcast"]["note"]


def test_newest_artifact_wins_and_verdicts_and_store_rows(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "2026-06-01-trending-stocks.md").write_text("x", encoding="utf-8")
    (inputs / "2026-07-09-trending-stocks.md").write_text("x", encoding="utf-8")
    vdir = tmp_path / "verdicts"
    vdir.mkdir()
    (vdir / "2026-07-08.json").write_text("{}", encoding="utf-8")

    class _Store:
        def load(self):
            import pandas as pd

            return pd.DataFrame([{"date": "2026-07-07", "entity": "GME",
                                  "metric": "short_volume_ratio", "value": 0.5}])

    rows = {r["name"]: r for r in connector_health(NOW, inputs_dir=inputs,
                                                   verdicts_dir=vdir, store=_Store())}
    assert rows["Trending scanner"]["last"] == "2026-07-09"    # newest, not first
    assert rows["Verdict build"]["last"] == "2026-07-08" and rows["Verdict build"]["age_days"] == 2
    assert rows["Reg-SHO short volume"]["last"] == "2026-07-07"
    assert rows["Insider cluster buys"]["status"] == "never"


def test_future_stamp_is_flagged_not_trusted(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "2026-08-01-trending-stocks.json").write_text("{}", encoding="utf-8")
    row = next(r for r in _health(tmp_path, inputs_dir=inputs)
               if r["name"] == "Trending scanner")
    assert row["status"] == "degraded" and "future" in row["note"]


def test_panel_renders_rows_and_the_home_page_carries_it(tmp_path):
    rows = _health(tmp_path)
    html = _health_table(rows)
    assert ">never<" in html and "never fetched" in html
    assert html.count("<tr>") == len(rows) + 1                 # header + every row
    assert _health_table([]).startswith("<p")                  # honest empty fallback
    from forecasting_lab.dashboard.collect import collect_lab_state
    from forecasting_lab.dashboard.render import render_dashboard

    page = render_dashboard(collect_lab_state(seed=0))
    assert "Is the data current?" in page and 'class="htable"' in page


def test_no_infinite_retry_loops_anywhere():
    """P6d §6 pin: rate-limited jobs skip cleanly — no `while True` retry loop
    may exist anywhere in the package."""
    src = Path(__file__).resolve().parents[1] / "src" / "forecasting_lab"
    offenders = []
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"while\s+True", text):
            offenders.append(str(path))
    assert offenders == []


def test_health_rows_are_json_serializable(tmp_path):
    json.dumps(_health(tmp_path))  # the panel data could ship as a sidecar
