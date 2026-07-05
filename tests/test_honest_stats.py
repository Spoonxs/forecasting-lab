"""V2 — small-sample and correlation-honest stats (MASTER_PLAN §3).

The two injections these pin down:
- a 3-0 record must never read as a 100% win rate (tiny-sample bravado);
- N fills of the same bet must never count as N independent bets (the publicly
  retracted 20.87-z bug class: significance computed on fills, not clusters).
"""

from __future__ import annotations

import math

import pytest

from forecasting_lab.eval import (
    cluster_outcomes,
    independent_bets,
    shrunk_win_rate,
    win_rate_zscore,
)


def test_tiny_sample_cannot_read_as_certainty():
    # raw 3/3 is "100%"; the shrunk rate stays honestly close to the prior
    assert shrunk_win_rate(3, 3) == pytest.approx((3 + 0.5 * 10) / (3 + 10))
    assert shrunk_win_rate(3, 3) < 0.65
    # no data -> the prior, exactly
    assert shrunk_win_rate(0, 0) == pytest.approx(0.5)


def test_shrinkage_fades_as_evidence_accrues():
    small = shrunk_win_rate(6, 10)          # 60% on 10 trials
    large = shrunk_win_rate(600, 1000)      # 60% on 1000 trials
    assert abs(large - 0.6) < abs(small - 0.6)
    assert large == pytest.approx(0.6, abs=0.01)
    # monotone in wins at fixed n
    assert shrunk_win_rate(8, 10) > shrunk_win_rate(5, 10)


def test_duplicated_fills_do_not_inflate_significance():
    """The crowdintel injection: score one bet's fills as independent bets."""
    outcomes = [1, 0, 1, 1, 0, 1, 1, 0, 1, 1]  # 7/10 wins, 10 real bets
    honest = win_rate_zscore(outcomes, clusters=list(range(10)))

    dup_outcomes = [o for o in outcomes for _ in range(25)]  # 25 fills per bet
    dup_clusters = [c for c in range(10) for _ in range(25)]
    naive = win_rate_zscore(dup_outcomes)                     # fills as bets
    clustered = win_rate_zscore(dup_outcomes, clusters=dup_clusters)

    assert naive == pytest.approx(honest * math.sqrt(25))  # the inflation, exactly
    assert clustered == pytest.approx(honest)              # the guard removes it
    assert independent_bets(dup_clusters) == 10


def test_cluster_means_are_the_units():
    # 3 fills of one winning bet + 1 losing bet = two units, mean 0.5 each way
    units = cluster_outcomes([1, 1, 1, 0], ["mktA", "mktA", "mktA", "mktB"])
    assert sorted(units) == [0.0, 1.0]
    with pytest.raises(ValueError):
        cluster_outcomes([1, 0], ["a"])  # misaligned inputs are an error, not a guess


def test_input_validation_is_loud():
    with pytest.raises(ValueError):
        shrunk_win_rate(5, 3)  # wins > n
    with pytest.raises(ValueError):
        shrunk_win_rate(1, 2, prior_p=1.5)
    with pytest.raises(ValueError):
        win_rate_zscore([1, 0], p0=1.0)
    assert win_rate_zscore([]) == 0.0  # empty log has no significance to claim
