"""Overfitting-honest performance stats: PSR, deflated Sharpe, and PBO.

A high backtest Sharpe means little if you tried many strategies — one wins by
luck. These implement López de Prado's antidotes:

- **Probabilistic Sharpe Ratio (PSR)** — confidence that the true Sharpe exceeds
  a benchmark, given sample length, skew, and kurtosis.
- **Deflated Sharpe Ratio (DSR)** — PSR against the *expected maximum* Sharpe from
  ``n_trials`` independent attempts. This is the number that survives the "you
  tried six strategies" objection.
- **Probability of Backtest Overfitting (PBO)** via combinatorially-symmetric
  cross-validation (CSCV): across many in-sample/out-of-sample splits of a
  strategy-by-period return matrix, how often does the in-sample winner land
  below the OOS median? High PBO = the selection is noise.

References: Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*; *The
Probability of Backtest Overfitting* (2015).
"""

from __future__ import annotations

import itertools
import math

import numpy as np
from scipy import stats


def sharpe_ratio(returns, periods_per_year: int = 252) -> float:
    """Annualised Sharpe of a per-period return series (0 if no variance)."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year))


def probabilistic_sharpe_ratio(returns, benchmark_sr: float = 0.0, periods_per_year: int = 252) -> float:
    """P(true Sharpe > benchmark), accounting for sample size, skew, kurtosis.

    ``benchmark_sr`` and the returned SR are in *annualised* units."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = r.size
    if n < 3 or r.std(ddof=1) == 0:
        return 0.0
    sr = sharpe_ratio(r, periods_per_year)
    # work in per-period Sharpe for the standard-error formula
    sr_pp = sr / math.sqrt(periods_per_year)
    bench_pp = benchmark_sr / math.sqrt(periods_per_year)
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))  # non-excess kurtosis
    se = math.sqrt((1 - skew * sr_pp + (kurt - 1) / 4 * sr_pp**2) / (n - 1))
    if se == 0:
        return 1.0 if sr_pp > bench_pp else 0.0
    return float(stats.norm.cdf((sr_pp - bench_pp) / se))


def expected_max_sharpe(n_trials: int, sr_std_pp: float) -> float:
    """Expected maximum per-period Sharpe from ``n_trials`` independent attempts,
    each with Sharpe std ``sr_std_pp`` (the multiple-testing benchmark)."""
    if n_trials < 2:
        return 0.0
    gamma = 0.5772156649015329  # Euler-Mascheroni
    z1 = stats.norm.ppf(1 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
    return sr_std_pp * ((1 - gamma) * z1 + gamma * z2)


def deflated_sharpe_ratio(returns, n_trials: int, periods_per_year: int = 252) -> float:
    """PSR against the expected-max Sharpe from ``n_trials`` — the honest number.

    Uses the observed per-period Sharpe as the trials' dispersion estimate (a
    common practical proxy when the full trial set isn't retained)."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 3:
        return 0.0
    sr_pp = sharpe_ratio(r, periods_per_year) / math.sqrt(periods_per_year)
    sr_std_pp = abs(sr_pp) if sr_pp else 1.0 / math.sqrt(r.size)
    bench_pp = expected_max_sharpe(n_trials, sr_std_pp)
    return probabilistic_sharpe_ratio(r, benchmark_sr=bench_pp * math.sqrt(periods_per_year),
                                      periods_per_year=periods_per_year)


def pbo_cscv(returns_matrix, n_splits: int = 12) -> float:
    """Probability of backtest overfitting via CSCV.

    ``returns_matrix`` is shape (T periods, N strategies). Split the T rows into
    ``n_splits`` contiguous chunks; for every way to choose half as in-sample
    (rest OOS), pick the strategy with the best in-sample Sharpe and record its
    OOS rank. PBO = fraction of splits where that winner is below the OOS median.
    """
    M = np.asarray(returns_matrix, dtype=float)
    if M.ndim != 2 or M.shape[1] < 2:
        return 0.0
    t, n = M.shape
    s = n_splits - (n_splits % 2)  # even number of chunks
    s = max(2, min(s, t))
    chunks = np.array_split(np.arange(t), s)
    logits = []
    for combo in itertools.combinations(range(s), s // 2):
        is_idx = np.concatenate([chunks[c] for c in combo])
        oos_idx = np.concatenate([chunks[c] for c in range(s) if c not in combo])
        is_sr = np.array([sharpe_ratio(M[is_idx, j]) for j in range(n)])
        oos_sr = np.array([sharpe_ratio(M[oos_idx, j]) for j in range(n)])
        best = int(np.argmax(is_sr))
        # OOS relative rank of the in-sample winner, in (0,1)
        rank = (stats.rankdata(oos_sr)[best]) / (n + 1)
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(math.log(rank / (1 - rank)))
    if not logits:
        return 0.0
    # PBO = P(logit <= 0) = fraction of splits where the winner is below OOS median
    return float(np.mean(np.array(logits) <= 0))
