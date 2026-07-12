"""P8-1 — the macro JSON sidecar (the audit's root cause #1).

Pinned: `flab-macro --digest` writes BOTH the markdown note and the JSON
sidecar; the sidecar carries recession_prob_12m (what the verdict provider
reads) and is dated by the SPREAD OBSERVATION's own date (what the macro-flip
watcher prefers); read_latest_data round-trips it.
"""

from __future__ import annotations

import json


def test_digest_writes_the_json_sidecar_the_provider_reads(tmp_path, monkeypatch):
    snap = {"term_spread": {"value": 1.2, "date": "2026-07-10"},
            "recession_prob_12m": 0.18,
            "levels": {"CPI": {"value": 3.1, "date": "2026-06-01"}}}
    monkeypatch.setattr("forecasting_lab.macro.macro_snapshot", lambda: snap)
    from forecasting_lab.cli.macro import main

    assert main(["--digest", "--out", str(tmp_path)]) == 0
    sidecars = list(tmp_path.glob("*-macro-nowcast.json"))
    assert len(sidecars) == 1, "the JSON sidecar must exist — without it the macro component never fires"
    data = json.loads(sidecars[0].read_text(encoding="utf-8"))
    assert data["recession_prob_12m"] == 0.18
    assert data["as_of"] == "2026-07-10"                 # the observation's own date
    # the exact read path the verdict provider and the watchers use
    from forecasting_lab.pipeline.digest import read_latest_data

    assert read_latest_data("macro-nowcast", out_dir=tmp_path)["recession_prob_12m"] == 0.18
    # the markdown note still files alongside
    assert list(tmp_path.glob("*-macro-nowcast.md"))
