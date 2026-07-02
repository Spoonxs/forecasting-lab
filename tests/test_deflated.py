import numpy as np

from forecasting_lab.eval.deflated import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    pbo_cscv,
    probabilistic_sharpe_ratio,
    sharpe_ratio,
)


def test_sharpe_basic():
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, 500)
    assert sharpe_ratio(r) > 0
    assert sharpe_ratio(np.zeros(100)) == 0.0


def test_psr_increases_with_sample_and_sharpe():
    rng = np.random.default_rng(1)
    short = rng.normal(0.001, 0.01, 30)
    long = rng.normal(0.001, 0.01, 2000)
    # more data -> more confident the (same-sign) Sharpe beats zero
    assert probabilistic_sharpe_ratio(long) >= probabilistic_sharpe_ratio(short)
    assert 0.0 <= probabilistic_sharpe_ratio(long) <= 1.0


def test_deflated_below_psr_under_many_trials():
    rng = np.random.default_rng(2)
    r = rng.normal(0.0015, 0.01, 750)
    psr = probabilistic_sharpe_ratio(r)
    dsr_1 = deflated_sharpe_ratio(r, n_trials=1)
    dsr_50 = deflated_sharpe_ratio(r, n_trials=50)
    # deflating for many trials can only lower confidence
    assert dsr_50 <= dsr_1
    assert dsr_50 <= psr + 1e-9


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(100, 0.1) > expected_max_sharpe(5, 0.1) > 0


def test_pbo_high_for_noise_low_for_real_edge():
    rng = np.random.default_rng(3)
    T, N = 240, 8
    # pure noise: the in-sample winner is luck -> PBO should be substantial
    noise = rng.normal(0, 0.01, (T, N))
    pbo_noise = pbo_cscv(noise, n_splits=10)
    # one genuinely dominant strategy -> PBO should be low
    edge = rng.normal(0, 0.01, (T, N))
    edge[:, 0] += 0.01  # column 0 truly outperforms in every period
    pbo_edge = pbo_cscv(edge, n_splits=10)
    assert 0.0 <= pbo_edge <= 1.0 and 0.0 <= pbo_noise <= 1.0
    assert pbo_edge < pbo_noise
    assert pbo_edge < 0.3
