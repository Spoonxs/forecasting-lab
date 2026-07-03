"""Phase 3 — 'ahead of the curve' voice scoring: an early-and-right voice ranks
first, a random-call voice scores ~0 (the leakage guard), the leaderboard is
deterministic and dated, weight decays on regression, and calls persist."""

from __future__ import annotations

import numpy as np

from forecasting_lab.media.voices import (
    VoiceCall,
    VoiceLedger,
    _forward_cumret,
    score_voice,
    voice_leaderboard_report,
)


def _rows(report):
    return {r["voice"]: r for r in report["rows"]}


def test_early_voice_ranks_first_and_noise_scores_zero():
    rep = voice_leaderboard_report(seed=0, as_of="2026-07-03")
    rows = _rows(rep)
    assert rep["rows"][0]["voice"] == "@early_sharp"  # ranked top by record
    assert rows["@early_sharp"]["weight"] > 0.05
    assert rows["@early_sharp"]["brier_skill"] > 0.0
    assert rows["@early_sharp"]["lead"] >= 1  # calls precede the move
    # a random-call voice earns no rank — can't manufacture a track record
    assert rows["@noise"]["weight"] < 0.02
    assert rows["@noise"]["brier_skill"] <= 0.02


def test_leaderboard_is_deterministic_and_dated():
    a = voice_leaderboard_report(seed=1, as_of="2026-07-03")
    b = voice_leaderboard_report(seed=1, as_of="2026-07-03")
    assert a == b  # same seed -> identical
    assert all(r["as_of"] == "2026-07-03" for r in a["rows"])  # every row is dated


def test_weight_decays_when_a_voice_regresses():
    rng = np.random.default_rng(3)
    returns = rng.normal(0.0, 0.02, 140)
    fwd = _forward_cumret(returns, 3)
    right = np.where(np.isnan(fwd), 0.0, np.sign(fwd))  # perfectly right throughout
    regress = right.copy()
    regress[len(regress) // 2:] *= -1.0  # right early, wrong late -> a regressing record
    consistent = score_voice(right, returns)
    regressing = score_voice(regress, returns)
    assert consistent["weight"] > regressing["weight"]  # a stale record fades


def test_voice_ledger_round_trips(tmp_path):
    led = VoiceLedger(tmp_path / "v.csv")
    led.record(VoiceCall("2026-07-01", "@unusual_whales", "NVDA", 1.0))
    led.record(VoiceCall("2026-07-02", "@unusual_whales", "GME", -1.0))
    df = VoiceLedger(tmp_path / "v.csv").to_frame()  # fresh instance reads the file
    assert len(df) == 2
    assert set(df["ticker"]) == {"NVDA", "GME"}
    assert set(df["date"]) == {"2026-07-01", "2026-07-02"}
