import numpy as np
import pytest

from forecasting_lab.calibration_log import ForecastLog


def test_record_resolve_score_persist(tmp_path):
    path = tmp_path / "cal.csv"
    log = ForecastLog(path)
    rng = np.random.default_rng(0)
    ids = []
    for i in range(50):
        p = float(rng.uniform(0.05, 0.95))
        ids.append((log.record(f"Q{i}?", round(p, 3), venue="Kalshi"), p))
    # ids are unique and increasing
    assert [i for i, _ in ids] == list(range(1, 51))
    for fid, p in ids:
        log.resolve(fid, int(rng.random() < p))
    s = log.score()
    assert s["n"] == 50
    assert 0.0 <= s["brier"] <= 1.0
    # reloading from disk preserves everything
    reloaded = ForecastLog(path)
    assert len(reloaded.to_frame()) == 50
    assert reloaded.score()["n"] == 50


def test_validation(tmp_path):
    log = ForecastLog(tmp_path / "c.csv")
    with pytest.raises(ValueError):
        log.record("bad", 1.5)
    fid = log.record("ok", 0.5)
    with pytest.raises(ValueError):
        log.resolve(fid, 2)
    with pytest.raises(KeyError):
        log.resolve(999, 1)


def test_score_requires_resolved(tmp_path):
    log = ForecastLog(tmp_path / "c.csv")
    log.record("unresolved", 0.5)
    with pytest.raises(ValueError):
        log.score()
