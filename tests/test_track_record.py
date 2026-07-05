"""V8 — track-record hardening (MASTER_PLAN §3).

Properties pinned: a pick's audit record replays byte-for-byte (and a tampered
record fails LOUDLY); loop picks flow into the public Brier-scored forecast log
and resolve/score through the existing path; the risk-awareness hypothesis test
recovers a planted "legible risks are priced in" effect OOS and pins ~0 on noise.
"""

from __future__ import annotations

import json

import pytest

from forecasting_lab.agent_trader.execution import PaperBroker, RiskLimits
from forecasting_lab.agent_trader.loop import run_once
from forecasting_lab.calibration_log import AuditTrail, ForecastLog, canonical_json, content_hash
from forecasting_lab.eval.recalibration import risk_awareness_report
from forecasting_lab.predictions import Driver, Prediction


def _judge(role, ctx):
    return {
        "scout": {"catalysts": []},
        "analyst": {"prob": 0.6, "thesis": "t"},
        "risk": {"veto": False, "reason": "ok"},
        "red_team": {"counter": "c"},
        "portfolio_manager": {"changes": {}, "rationale": "hold"},
    }[role]


def test_audit_replay_is_byte_for_byte(tmp_path):
    trail = AuditTrail(tmp_path / "audit.jsonl")
    inputs = {"prices": {"AAA": 10.0, "BBB": 3.5}, "targets": {"AAA": 0.2}, "run_id": "r1"}
    sha = trail.record("r1", inputs, on="2026-07-04")
    replayed, sha2 = trail.replay("r1")
    assert canonical_json(replayed) == canonical_json(inputs)  # the bytes, not "roughly"
    assert sha == sha2 == content_hash(inputs)
    with pytest.raises(KeyError):
        trail.replay("nope")


def test_tampered_audit_record_fails_loudly(tmp_path):
    trail = AuditTrail(tmp_path / "audit.jsonl")
    trail.record("r1", {"a": 1}, on="2026-07-04")
    row = json.loads(trail.path.read_text(encoding="utf-8").splitlines()[0])
    row["inputs"]["a"] = 2  # the quiet edit
    trail.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        trail.replay("r1")


def test_loop_picks_land_in_the_forecast_log_with_audit(tmp_path):
    log = ForecastLog(tmp_path / "cal.csv")
    trail = AuditTrail(tmp_path / "audit.jsonl")
    prices = {"AAA": 10.0}

    def picks(brief):
        return [Prediction(
            probability=0.62,
            drivers=(Driver("trend composite (z)", 0.5, 0.5),),
            caveat="heuristic lean, not calibrated",
            label="AAA marks up next cycle",
        )]

    snapshot = run_once(
        ticker="AAA", judge=_judge, strategy=lambda b: {"AAA": 0.2},
        broker=PaperBroker(cash=10_000.0), limits=RiskLimits(), prices=prices,
        run_id="r9", audit=trail, forecast_log=log, pick_builder=picks,
    )
    # the audit hash is in the snapshot and replays to this cycle's exact inputs
    replayed, _ = trail.replay("r9")
    assert replayed["prices"] == {"AAA": 10.0} and replayed["targets"] == {"AAA": 0.2}
    assert snapshot["inputs_sha256"] == content_hash(replayed)
    # the pick is in the public log, linked to the audit record
    [fid] = snapshot["forecast_ids"]
    row = log.to_frame().set_index("id").loc[fid]
    assert row["question"] == "AAA marks up next cycle" and row["prob"] == 0.62
    assert snapshot["inputs_sha256"][:12] in row["notes"]
    # and it scores through the existing resolve path
    log.resolve(fid, 1)
    assert log.score()["n"] == 1


def test_risk_awareness_hypothesis_separates_effect_from_noise():
    planted = risk_awareness_report(seed=0, effect=1.0)
    assert planted["brier_skill_vs_base_prob"] > 0.015
    assert planted["fitted_shift"] < -0.05  # the fitted direction IS negative
    null = risk_awareness_report(seed=0, effect=0.0)
    assert abs(null["brier_skill_vs_base_prob"]) < 0.005
