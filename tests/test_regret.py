"""P6c section C — the regret ledger (the credibility engine, before the arena).

Pinned: the four baselines (SPY / HYSA / equal-weight / do-nothing) are computed
correctly at resolution; a rec that beat or lagged each baseline is scored
right; nothing resolves before the horizon; missing exit data leaves an entry
open (n/a, never fabricated); the empty ledger says "no resolved horizons yet";
entries are content-hashed at record time and a tampered ledger fails loudly;
save/load round-trips; only attractive labels are tracked, one open horizon per
name.
"""

from __future__ import annotations

import json

import pytest

from forecasting_lab.calibration_log.regret import BASELINES, RegretLedger

RECS = [{"symbol": "NVDA", "label": "STRONG BUY", "score": 0.62},
        {"symbol": "VOO", "label": "BUY", "score": 0.30},
        {"symbol": "XYZ", "label": "HOLD", "score": 0.05}]          # not attractive
ENTRY_PX = {"NVDA": 100.0, "VOO": 400.0, "AAPL": 200.0}


def _ledger(tmp_path) -> RegretLedger:
    return RegretLedger(path=tmp_path / "ledger.json")


def test_four_baselines_computed_correctly(tmp_path):
    led = _ledger(tmp_path)
    ids = led.record("2026-01-01", RECS, ENTRY_PX, spy_price=500.0,
                     hysa_yield_pct=5.0, horizon_days=30)
    assert len(ids) == 2                                # HOLD not tracked
    # +10% NVDA vs SPY +4%, HYSA 5%*(36/365)~0.49%, EW mean(+10,+5,-10)/3~+1.67%
    out = led.resolve("2026-02-06", {"NVDA": 110.0, "VOO": 420.0, "AAPL": 180.0},
                      spy_price=520.0)
    nvda = next(r for r in out if r["entry"]["symbol"] == "NVDA")["resolution"]
    assert nvda["days"] == 36 and nvda["return"] == pytest.approx(0.10)
    assert nvda["baselines"]["spy"] == pytest.approx(0.04)
    assert nvda["baselines"]["hysa"] == pytest.approx(0.05 * 36 / 365, abs=1e-6)
    assert nvda["baselines"]["equal_weight"] == pytest.approx((0.10 + 0.05 - 0.10) / 3, abs=1e-4)
    assert nvda["baselines"]["do_nothing"] == 0.0
    assert set(nvda["baselines"]) == set(BASELINES)


def test_beat_and_lag_are_scored_right(tmp_path):
    led = _ledger(tmp_path)
    led.record("2026-01-01", RECS, ENTRY_PX, spy_price=500.0, hysa_yield_pct=5.0)
    led.resolve("2026-02-06", {"NVDA": 110.0, "VOO": 402.0, "AAPL": 180.0}, spy_price=520.0)
    nvda = next(r for r in led.entries if r["entry"]["symbol"] == "NVDA")["resolution"]
    voo = next(r for r in led.entries if r["entry"]["symbol"] == "VOO")["resolution"]
    assert all(nvda["beat"][b] for b in BASELINES)      # +10% beat everything
    assert voo["beat"]["spy"] is False                  # +0.5% lagged SPY's +4%
    assert voo["beat"]["do_nothing"] is True            # ...but beat doing nothing
    assert voo["edge_vs"]["spy"] == pytest.approx(0.005 - 0.04, abs=1e-6)
    s = led.summary()
    assert s["resolved"] == 2
    assert s["baselines"]["spy"]["beat_rate"] == 0.5    # honest: 1 of 2
    assert s["baselines"]["do_nothing"]["beat_rate"] == 1.0


def test_nothing_resolves_before_the_horizon(tmp_path):
    led = _ledger(tmp_path)
    led.record("2026-01-01", RECS, ENTRY_PX, horizon_days=30)
    assert led.resolve("2026-01-15", {"NVDA": 200.0, "VOO": 500.0}) == []
    assert led.summary()["resolved"] == 0


def test_missing_exit_or_baseline_is_na_never_fabricated(tmp_path):
    led = _ledger(tmp_path)
    led.record("2026-01-01", RECS, ENTRY_PX)            # no spy, no hysa recorded
    out = led.resolve("2026-02-06", {"NVDA": 110.0})    # VOO exit unknown
    assert [r["entry"]["symbol"] for r in out] == ["NVDA"]
    voo = next(r for r in led.entries if r["entry"]["symbol"] == "VOO")
    assert "resolution" not in voo                      # stays open, no guess
    nvda = next(r for r in out)["resolution"]
    assert nvda["baselines"]["spy"] is None and nvda["beat"]["spy"] is None
    assert nvda["baselines"]["hysa"] is None
    assert nvda["baselines"]["equal_weight"] is None    # basket incomplete -> n/a
    s = led.summary()
    assert s["baselines"]["spy"]["n"] == 0 and s["baselines"]["spy"]["beat_rate"] is None
    assert s["baselines"]["do_nothing"]["n"] == 1       # denominator per baseline


def test_empty_ledger_states_it_honestly(tmp_path):
    s = _ledger(tmp_path).summary()
    assert s["recorded"] == 0 and s["resolved"] == 0
    assert s["note"] == "no resolved horizons yet" and s["baselines"] == {}


def test_entries_are_hashed_and_tampering_fails_loudly(tmp_path):
    led = _ledger(tmp_path)
    led.record("2026-01-01", RECS, ENTRY_PX, spy_price=500.0)
    led.save()
    # round-trip is clean
    again = RegretLedger(path=led.path)
    assert [r["id"] for r in again.entries] == [r["id"] for r in led.entries]
    # tamper with a recorded entry price on disk -> loading fails loudly
    rows = json.loads(led.path.read_text(encoding="utf-8"))
    rows[0]["entry"]["price"] = 1.0
    led.path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="fails its hash"):
        RegretLedger(path=led.path)


def test_one_open_horizon_per_name_and_no_entry_price_skipped(tmp_path):
    led = _ledger(tmp_path)
    first = led.record("2026-01-01", RECS, ENTRY_PX)
    dup = led.record("2026-01-02", RECS, ENTRY_PX)      # same names still open
    assert first and dup == []
    ghost = led.record("2026-01-03", [{"symbol": "GHOST", "label": "BUY", "score": 0.4}], {})
    assert ghost == []                                  # no entry anchor -> skipped


def test_stale_closes_never_masquerade_as_todays_marks(tmp_path):
    """Codex review (P6c-6) + P8-4: entries anchor to the CLOSES' own date
    within a small stated lag (a weekend build uses Friday's close — the exact
    close its verdicts came from); older closes open nothing; resolutions are
    marked at the closes' own date."""
    led = _ledger(tmp_path)
    payload = {"as_of": "2026-02-10", "verdicts": {"NVDA": {"label": "BUY", "score": 0.4}}}
    stale = led.update_from_build(payload, {"NVDA": 100.0}, "2026-02-06")
    assert stale["opened"] == []                        # 4d old -> stale, no anchor
    fresh = led.update_from_build(payload, {"NVDA": 100.0}, "2026-02-10")
    assert fresh["opened"] == ["2026-02-10:NVDA:30d"]
    # P8-4: a weekend/pre-market build anchors to the recent close, DATED BY IT
    led2 = _ledger(tmp_path / "b")
    saturday = {"as_of": "2026-02-14", "verdicts": {"NVDA": {"label": "BUY", "score": 0.4}}}
    out = led2.update_from_build(saturday, {"NVDA": 100.0}, "2026-02-13")  # Friday close
    assert out["opened"] == ["2026-02-13:NVDA:30d"]     # the close's date, not the build's
    # and a close dated AFTER the artifact never anchors (negative lag)
    weird = led2.update_from_build(saturday, {"NVDA": 100.0}, "2026-02-16")
    assert weird["opened"] == []
    # resolution happens at the CLOSES' date, not the build's
    later = {"as_of": "2026-04-01", "verdicts": {}}
    out = led.update_from_build(later, {"NVDA": 110.0}, "2026-03-15")
    assert out["resolved"] and out["resolved"][0]["resolution"]["date"] == "2026-03-15"
    assert led.update_from_build(payload, {}, None) == {"opened": [], "resolved": []}


def test_record_from_verdicts_takes_the_artifact_shape(tmp_path):
    led = _ledger(tmp_path)
    payload = {"as_of": "2026-01-01", "hysa_yield_pct": 4.0, "verdicts": {
        "NVDA": {"label": "STRONG BUY", "score": 0.6},
        "VOO": {"label": "HOLD", "score": 0.1},
        "ZZZ": {"label": "INSUFFICIENT EVIDENCE", "score": 0.0}}}
    ids = led.record_from_verdicts(payload, {"NVDA": 100.0, "VOO": 400.0}, spy_price=500.0)
    assert ids == ["2026-01-01:NVDA:30d"]
    assert led.entries[0]["entry"]["hysa_yield_pct"] == 4.0


# ------------------------------------------------ Codex code-review fixes pinned
def test_equal_weight_never_averages_a_partial_basket(tmp_path):
    """Codex finding 1: a basket member missing its exit price -> equal_weight
    is n/a, never a silently reweighted average of the survivors."""
    led = _ledger(tmp_path)
    led.record("2026-01-01", RECS, ENTRY_PX)            # basket: NVDA, VOO, AAPL
    led.resolve("2026-02-06", {"NVDA": 110.0, "VOO": 420.0})  # AAPL exit unknown
    nvda = next(r for r in led.entries if r["entry"]["symbol"] == "NVDA")["resolution"]
    assert nvda["baselines"]["equal_weight"] is None
    assert nvda["return"] == pytest.approx(0.10)        # the rec itself still scores


def test_basket_is_the_rated_universe_not_the_price_dict(tmp_path):
    """Codex finding 2: an unrated ticker in the price feed never leaks into
    the frozen equal-weight basket."""
    led = _ledger(tmp_path)
    payload = {"as_of": "2026-01-01", "verdicts": {
        "NVDA": {"label": "BUY", "score": 0.4}, "VOO": {"label": "HOLD", "score": 0.1},
        "ZZZ": {"label": "INSUFFICIENT EVIDENCE", "score": 0.0}}}
    led.record_from_verdicts(payload, {"NVDA": 100.0, "VOO": 400.0,
                                       "RANDOM": 7.0, "ZZZ": 3.0})
    basket = led.entries[0]["entry"]["basket"]
    assert set(basket) == {"NVDA", "VOO"}               # rated only, frozen + hashed
    # explicit basket_symbols is honored on the raw record() path too
    led2 = _ledger(tmp_path / "b")
    led2.record("2026-01-01", RECS, ENTRY_PX, basket_symbols=["NVDA", "VOO"])
    assert set(led2.entries[0]["entry"]["basket"]) == {"NVDA", "VOO"}
