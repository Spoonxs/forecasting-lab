"""Logging + scoring analyst JSON blocks: a pasted call becomes a tracked forecast that
resolves against the real stock-vs-S&P outcome — the feedback loop LLM reports lack."""

from __future__ import annotations

import pytest

from forecasting_lab.agent_trader.research_log import ResearchLog, parse_block

BLOCK = {
    "ticker": "nvda", "as_of": "2026-01-01", "prob_beats_SPX_12mo": 0.70,
    "price": 100.0, "call": "buy", "fair_value": {"base": 130}, "one_line_thesis": "AI leader",
}


def test_parse_block_normalizes_and_validates():
    r = parse_block(BLOCK)
    assert r["ticker"] == "NVDA" and r["prob_beats_spx"] == 0.70 and r["horizon_days"] == 365
    assert r["fair_value_base"] == 130.0 and r["resolved"] is False
    with pytest.raises(ValueError):
        parse_block({**BLOCK, "prob_beats_SPX_12mo": 1.5})  # out of range
    with pytest.raises(ValueError):
        parse_block({"as_of": "2026-01-01", "prob_beats_SPX_12mo": 0.5})  # no ticker


def test_record_is_idempotent_on_ticker_and_date(tmp_path):
    log = ResearchLog(tmp_path / "r.csv")
    log.record(BLOCK)
    log.record({**BLOCK, "prob_beats_SPX_12mo": 0.55})  # same ticker+as_of -> replace
    df = log.to_frame()
    assert len(df) == 1 and float(df.iloc[0]["prob_beats_spx"]) == 0.55


def test_resolve_marks_a_matured_call_against_the_benchmark(tmp_path):
    log = ResearchLog(tmp_path / "r.csv")
    log.record(BLOCK)  # as_of 2026-01-01, horizon 365 -> end 2027-01-01
    prices = {("NVDA", "2026-01-01"): 100.0, ("NVDA", "2027-01-01"): 130.0,   # +30%
              ("^GSPC", "2026-01-01"): 100.0, ("^GSPC", "2027-01-01"): 110.0}  # +10%
    n = log.resolve(lambda s, d: prices.get((s, d)), today="2027-02-01")
    assert n == 1
    row = log.to_frame().iloc[0]
    assert bool(row["resolved"]) and int(row["outcome"]) == 1  # NVDA beat the S&P


def test_unmatured_calls_are_not_resolved(tmp_path):
    log = ResearchLog(tmp_path / "r.csv")
    log.record({**BLOCK, "as_of": "2027-01-01"})  # ends 2028 -> still open today
    n = log.resolve(lambda s, d: 100.0, today="2027-02-01")
    assert n == 0 and not bool(log.to_frame().iloc[0]["resolved"])


def test_score_reports_brier_skill_and_hit_rate(tmp_path):
    log = ResearchLog(tmp_path / "r.csv")
    log.record(BLOCK)
    prices = {("NVDA", "2026-01-01"): 100.0, ("NVDA", "2027-01-01"): 130.0,
              ("^GSPC", "2026-01-01"): 100.0, ("^GSPC", "2027-01-01"): 110.0}
    log.resolve(lambda s, d: prices.get((s, d)), today="2027-02-01")
    s = log.score()
    assert s["n"] == 1 and s["hit_rate"] == 1.0
    assert s["brier"] == pytest.approx(0.09)  # (0.70 - 1)^2
    assert s["brier_skill_vs_coinflip"] > 0  # beat a 50/50 guess
