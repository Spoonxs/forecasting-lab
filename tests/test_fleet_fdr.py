"""V5 — fleet-level FDR + the hold-benchmark default (MASTER_PLAN §3).

Properties pinned: a pure-noise fleet of 20 promotes NOBODY and the stated
allocation is an explicit 100%-benchmark decision object; a genuinely skilled
seeded strategy survives all three gates (deflated Sharpe, PBO, fleet FDR) and
is promoted ALONE; correlated fleets flag crowding; BH controls the fleet-level
false-promotion rate. Writing these exposed a real bug: the promote branch was
unreachable (a [0,1] DSR probability tested against a >1.0 bar) — fixed.
"""

from __future__ import annotations

import numpy as np

from forecasting_lab.agent_trader.fleet import (
    HoldBenchmark,
    PromoteSurvivors,
    benjamini_hochberg,
    fleet_correlation,
    fleet_decision,
    fleet_pvalues,
    synthetic_fleet_returns,
)
from forecasting_lab.sim.engine import Arena


def _fleet_with_edge(seed: int, mean: float = 0.0025, n_bars: int = 504, k: int = 20):
    returns = synthetic_fleet_returns(seed=seed, k=k, n_bars=n_bars)
    rng = np.random.default_rng(seed + 1000)
    returns["v_skilled"] = [round(float(x), 5) for x in rng.normal(mean, 0.008, n_bars)]
    return returns


def test_pure_noise_fleet_holds_benchmark():
    for seed in (0, 1, 2):
        decision = fleet_decision(synthetic_fleet_returns(seed=seed, k=20, n_bars=504), as_of="t")
        assert isinstance(decision, HoldBenchmark), f"seed {seed} promoted noise"
        assert decision.weight == 1.0 and decision.benchmark == "SPY"
        assert "100% SPY" in decision.reason  # the default is stated, not implied


def test_a_seeded_real_edge_is_promoted_alone():
    for seed in (0, 1, 2):
        decision = fleet_decision(_fleet_with_edge(seed), as_of="t")
        assert isinstance(decision, PromoteSurvivors), f"seed {seed}: real edge not promoted"
        assert decision.survivors == ("v_skilled",), decision.survivors


def test_benjamini_hochberg_step_up():
    # textbook: m=4, q=0.1 -> thresholds 0.025/0.05/0.075/0.1; c passes by step-up
    p = {"a": 0.01, "b": 0.04, "c": 0.07, "d": 0.9}
    assert benjamini_hochberg(p, fdr=0.1) == ["a", "b", "c"]
    # nothing passes when everything is mediocre
    assert benjamini_hochberg({"a": 0.3, "b": 0.6}, fdr=0.05) == []
    assert benjamini_hochberg({}, fdr=0.05) == []


def test_fleet_pvalues_reward_real_skill_only():
    returns = _fleet_with_edge(0)
    p = fleet_pvalues(returns)
    assert p["v_skilled"] < 0.001
    noise_ps = [v for k, v in p.items() if k != "v_skilled"]
    assert min(noise_ps) > 0.001  # no noise variant looks as certain as the edge


def test_correlated_fleet_flags_crowding_independent_does_not():
    independent = fleet_correlation(synthetic_fleet_returns(seed=0, k=10))
    assert independent["crowded"] is False and abs(independent["mean_pairwise_corr"]) < 0.2
    crowd = fleet_correlation(synthetic_fleet_returns(seed=0, k=10, common_noise=0.9))
    assert crowd["crowded"] is True and crowd["mean_pairwise_corr"] > 0.5
    # degenerate: one strategy has no pairs to correlate
    solo = fleet_correlation({"only": [0.01, -0.01, 0.02]})
    assert solo == {"mean_pairwise_corr": 0.0, "crowded": False, "n_variants": 1}


def test_arena_surfaces_the_crowding_gauge():
    arena = Arena(seed=3, n_assets=6, n_bars=300, warmup=140,
                  state_path="data/sim/_test_fdr_arena.json")
    arena.run(60)
    gauge = arena.crowding()
    assert set(gauge) == {"mean_pairwise_corr", "crowded", "n_variants"}
    assert gauge["n_variants"] >= 2
    arena.reset()
