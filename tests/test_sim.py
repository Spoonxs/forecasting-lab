import numpy as np

from forecasting_lab.sim.data import synthetic_market
from forecasting_lab.sim.engine import Arena
from forecasting_lab.sim.strategies import (
    BuyHold,
    MeanReversion,
    Momentum,
    RandomPicks,
    default_strategies,
)


def _arena(tmp_path, **kw):
    kw.setdefault("state_path", tmp_path / "state.json")
    kw.setdefault("seed", 7)
    return Arena(**kw)


def test_weights_are_long_only_and_bounded(tmp_path):
    arena = _arena(tmp_path)
    arena.run(30)
    for name, weights in arena.weights.items():
        assert all(w >= 0 for w in weights.values()), name
        assert sum(weights.values()) <= 1.0 + 1e-9, name


def test_resume_equals_single_session(tmp_path):
    # 60 bars in one go...
    one = _arena(tmp_path / "a", state_path=tmp_path / "a.json")
    one.run(60)

    # ...must equal 30 bars, save, load, 30 more
    first = _arena(tmp_path / "b", state_path=tmp_path / "b.json")
    first.run(30)
    first.save()
    second = _arena(tmp_path / "b", state_path=tmp_path / "b.json")
    assert second.load() is True
    second.run(30)

    for name in one.returns:
        assert np.allclose(one.returns[name], second.returns[name]), name


def test_incompatible_state_is_ignored(tmp_path):
    a = _arena(tmp_path, seed=1, state_path=tmp_path / "s.json")
    a.run(10)
    a.save()
    b = Arena(seed=2, state_path=tmp_path / "s.json")  # different market
    assert b.load() is False


def test_momentum_beats_random_on_trending_market(tmp_path):
    # strong, persistent drifts -> momentum should find them; random can't
    prices = synthetic_market(n_assets=10, n_bars=1200, seed=3,
                              drift_persistence=0.999, drift_vol=0.0008, noise_vol=0.01)
    arena = Arena(
        strategies=[Momentum(60, 3), RandomPicks(3), BuyHold()],
        prices=prices, state_path=tmp_path / "s.json", warmup=130,
    )
    arena.run(1000)
    board = arena.leaderboard()
    assert board.loc["momentum_60d", "sharpe"] > board.loc["random", "sharpe"]


def test_costs_reduce_high_turnover_strategy(tmp_path):
    prices = synthetic_market(n_assets=8, n_bars=600, seed=5)
    free = Arena(strategies=[MeanReversion(5, 3)], prices=prices,
                 cost_bps=0.0, state_path=tmp_path / "f.json")
    costly = Arena(strategies=[MeanReversion(5, 3)], prices=prices,
                   cost_bps=50.0, state_path=tmp_path / "c.json")
    free.run(400)
    costly.run(400)
    # mean-reversion churns every bar; 50bps must hurt
    assert sum(costly.returns["meanrev_5d"]) < sum(free.returns["meanrev_5d"])


def test_leaderboard_has_all_strategies(tmp_path):
    arena = _arena(tmp_path)
    arena.run(200)
    board = arena.leaderboard()
    assert set(board.index) == {s.name for s in default_strategies()}
    assert {"sharpe", "total_return", "max_drawdown", "bars"} <= set(board.columns)
