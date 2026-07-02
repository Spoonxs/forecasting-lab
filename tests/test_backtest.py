import numpy as np
import pandas as pd

from forecasting_lab.backtest import walk_forward_backtest
from forecasting_lab.backtest.engine import max_drawdown


def test_max_drawdown_known_curve():
    equity = pd.Series([1.0, 1.2, 0.9, 1.1])  # peak 1.2 -> trough 0.9 = -25%
    assert abs(max_drawdown(equity) - (-0.25)) < 1e-9


def test_perfect_score_beats_random():
    # score == forward return, so the strategy is perfectly informed
    rng = np.random.default_rng(0)
    rows = []
    for d in range(30):
        for i in range(20):
            r = rng.normal(0, 0.02)
            rows.append({"date": d, "ticker": i, "score": r, "fwd_return": r})
    panel = pd.DataFrame(rows)
    res = walk_forward_backtest(panel, top_frac=0.25, periods_per_year=52)
    assert res.stats["sharpe"] > res.baselines["random"]["sharpe"]
    assert res.stats["mean_period_return"] > 0
    assert set(res.baselines) == {"equal_weight", "random"}


def test_cost_reduces_returns():
    rows = [{"date": d, "ticker": i, "score": i, "fwd_return": 0.01} for d in range(10) for i in range(10)]
    panel = pd.DataFrame(rows)
    free = walk_forward_backtest(panel, cost=0.0, baselines=False)
    costly = walk_forward_backtest(panel, cost=0.005, baselines=False)
    assert costly.stats["mean_period_return"] < free.stats["mean_period_return"]
