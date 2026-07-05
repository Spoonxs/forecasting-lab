"""Small-sample and correlation-honest statistics (MASTER_PLAN V2).

Two bug classes these guard against, both field-verified:

1. **Tiny-sample bravado** — a 3-0 record shown as a "100% win rate". The fix is
   Bayesian shrinkage toward an honest prior: the rate earns its way from the
   prior to the data as evidence accrues.
2. **Fills are not independent bets** — the crowdintel class: hundreds of fills
   in the *same* market on the *same* day scored as independent trials produced
   a z-score of 20.87 (publicly retracted). Significance must be computed on
   independent clusters (market, day, thesis), never raw fills.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Hashable, Sequence


def shrunk_win_rate(
    wins: float,
    n: int,
    prior_p: float = 0.5,
    prior_strength: float = 10.0,
) -> float:
    """Beta-binomial posterior mean of a win rate, shrunk toward ``prior_p``.

    Equivalent to having already observed ``prior_strength`` pseudo-trials at the
    prior rate: 3/3 with the defaults reads ~0.62, not 1.00. Converges to the raw
    rate as ``n`` grows; with no data it *is* the prior.
    """
    if n < 0 or wins < 0 or wins > n:
        raise ValueError(f"need 0 <= wins <= n, got wins={wins}, n={n}")
    if not 0.0 <= prior_p <= 1.0:
        raise ValueError("prior_p must be a probability")
    if prior_strength <= 0:
        raise ValueError("prior_strength must be positive")
    return (wins + prior_p * prior_strength) / (n + prior_strength)


def cluster_outcomes(
    outcomes: Sequence[float],
    clusters: Sequence[Hashable],
) -> list[float]:
    """Collapse raw outcomes to per-cluster means — the independent units.

    Everything sharing a cluster id (same market, same day, same thesis) is one
    bet, however many fills it took.
    """
    if len(outcomes) != len(clusters):
        raise ValueError("outcomes and clusters must align")
    sums: dict[Hashable, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for out, cl in zip(outcomes, clusters, strict=True):
        acc = sums[cl]
        acc[0] += float(out)
        acc[1] += 1.0
    return [s / c for s, c in sums.values()]


def win_rate_zscore(
    outcomes: Sequence[float],
    clusters: Sequence[Hashable] | None = None,
    p0: float = 0.5,
) -> float:
    """Z-score of a win rate against ``p0``, on independent clusters.

    ``outcomes`` are 0/1 (or fractional) results per fill; ``clusters`` groups
    fills that are the same bet. Without clusters every outcome is assumed
    independent — the inflated number the guard exists to prevent, kept only so
    the inflation is demonstrable in tests.
    """
    if not 0.0 < p0 < 1.0:
        raise ValueError("p0 must be strictly inside (0, 1)")
    units = list(map(float, outcomes)) if clusters is None else cluster_outcomes(outcomes, clusters)
    n = len(units)
    if n == 0:
        return 0.0
    mean = sum(units) / n
    se = math.sqrt(p0 * (1.0 - p0) / n)
    return (mean - p0) / se


def independent_bets(clusters: Sequence[Hashable]) -> int:
    """How many independent bets a fill log actually contains."""
    return len(set(clusters))
