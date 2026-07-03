"""Phase 4 — the paper->live promotion gate. It PROMOTES a genuinely-skilled
strategy, REJECTS an overfit/lucky one, writes a signed dated record, and contains
no order-execution code (a decision, never a trade)."""

from __future__ import annotations

import json
from pathlib import Path

import forecasting_lab.promotion as promo
from forecasting_lab.promotion import (
    GateThresholds,
    evaluate_promotion,
    write_promotion_record,
)

# a strategy that has genuinely earned consideration — clears all six gates
SKILLED = {
    "deflated_sharpe": 1.5, "pbo": 0.10, "live_marks": 30, "brier_skill_vs_market": 0.05,
    "net_return": 0.18, "turnover": 0.6, "kelly_fraction": 0.20, "max_name_weight": 0.20,
    "max_drawdown": 0.12, "gross_exposure": 1.0,
}
# an overfit / lucky strategy — fails the important gates
OVERFIT = {
    "deflated_sharpe": 0.30, "pbo": 0.55, "live_marks": 4, "brier_skill_vs_market": -0.02,
    "net_return": -0.05, "turnover": 3.0, "kelly_fraction": 0.80, "max_name_weight": 0.60,
    "max_drawdown": 0.40, "gross_exposure": 1.5,
}


def test_skilled_strategy_is_promoted_across_all_six_gates():
    rec = evaluate_promotion("momentum_60d", SKILLED, as_of="2026-07-03")
    assert rec.passed is True
    assert len(rec.checks) == 6 and all(c.passed for c in rec.checks)
    assert "PROMOTE" in rec.rationale
    assert rec.signature  # signed
    assert rec.as_of == "2026-07-03"  # dated


def test_overfit_strategy_is_rejected():
    rec = evaluate_promotion("lucky_curvefit", OVERFIT, as_of="2026-07-03")
    assert rec.passed is False
    assert "HOLD" in rec.rationale and "Stays on paper" in rec.rationale
    # the tell-tale gates fail
    by = {c.name: c.passed for c in rec.checks}
    assert by["Deflated Sharpe"] is False
    assert by["Overfitting (PBO)"] is False
    assert by["Risk gate"] is False


def test_a_single_failing_gate_blocks_promotion():
    almost = dict(SKILLED, pbo=0.5)  # everything good except overfitting
    rec = evaluate_promotion("almost", almost, as_of="2026-07-03")
    assert rec.passed is False
    by = {c.name: c.passed for c in rec.checks}
    assert by["Overfitting (PBO)"] is False
    assert sum(by.values()) == 5  # only the PBO gate blocks it


def test_missing_metrics_fail_conservatively():
    rec = evaluate_promotion("empty", {}, as_of="2026-07-03")
    assert rec.passed is False and not any(c.passed for c in rec.checks)


def test_thresholds_are_the_documented_risk_limits():
    t = GateThresholds()
    assert t.min_deflated_sharpe == 1.0 and t.max_pbo == 0.2
    assert t.kelly_cap == 0.25 and t.max_gross_exposure == 1.0  # <=1/4 Kelly, no leverage


def test_signature_is_deterministic_and_content_sensitive():
    a = evaluate_promotion("s", SKILLED, as_of="2026-07-03")
    b = evaluate_promotion("s", SKILLED, as_of="2026-07-03")
    c = evaluate_promotion("s", OVERFIT, as_of="2026-07-03")
    assert a.signature == b.signature  # deterministic
    assert a.signature != c.signature  # different decision -> different signature


def test_promotion_record_writes_and_round_trips(tmp_path):
    rec = evaluate_promotion("momentum_60d", SKILLED, as_of="2026-07-03")
    path = write_promotion_record(rec, tmp_path / "promotions.jsonl")
    lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["strategy"] == "momentum_60d" and row["passed"] is True
    assert row["signature"] == rec.signature and len(row["checks"]) == 6


def test_gate_contains_no_order_execution_code():
    # target execution CODE (order verbs + broker SDKs + network), not the English
    # word "broker" — the docstring legitimately says the gate uses no broker.
    src = Path(promo.__file__).read_text(encoding="utf-8").lower()
    forbidden = ["place_order", "submit_order", "create_order", "execute_order",
                 "alpaca", "ib_insync", "ccxt", "orderclient", "import requests"]
    hits = [term for term in forbidden if term in src]
    assert hits == [], f"promotion gate must not contain execution code, found: {hits}"
