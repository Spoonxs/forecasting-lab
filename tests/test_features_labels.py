import numpy as np
import pandas as pd

from forecasting_lab.ml.features import (
    cross_sectional_rank,
    cross_sectional_zscore,
    lag_features,
)
from forecasting_lab.ml.labels import forward_return, triple_barrier


def _panel():
    return pd.DataFrame(
        {
            "date": [1, 1, 1, 2, 2, 2],
            "ticker": ["A", "B", "C", "A", "B", "C"],
            "x": [10.0, 20.0, 30.0, 5.0, 15.0, 25.0],
        }
    )


def test_cross_sectional_zscore_zero_mean_per_date():
    out = cross_sectional_zscore(_panel(), "x", date_col="date")
    means = out.groupby("date")["x_z"].mean()
    assert np.allclose(means.to_numpy(), 0.0, atol=1e-9)


def test_cross_sectional_rank_centered():
    out = cross_sectional_rank(_panel(), "x", date_col="date", center=True)
    # within each date the max gets +0.5-ish, min gets the lowest
    d1 = out[out["date"] == 1].sort_values("x")
    assert d1["x_rank"].iloc[0] < 0 < d1["x_rank"].iloc[-1]


def test_lag_features_no_cross_entity_bleed():
    out = lag_features(_panel(), "x", entity_col="ticker", date_col="date", periods=1)
    # first observation per ticker has no prior -> NaN
    a = out[out["ticker"] == "A"].sort_values("date")
    assert np.isnan(a["x"].iloc[0])
    assert a["x"].iloc[1] == 10.0  # A's date-2 lag is A's date-1 value, not B/C's


def test_forward_return_and_relative():
    panel = pd.DataFrame(
        {
            "date": [1, 2, 3, 1, 2, 3],
            "ticker": ["A", "A", "A", "B", "B", "B"],
            "close": [100.0, 110.0, 121.0, 100.0, 90.0, 81.0],
        }
    )
    out = forward_return(panel, price_col="close", horizon=1, relative=False)
    a = out[out["ticker"] == "A"].sort_values("date")
    assert abs(a["fwd_return"].iloc[0] - 0.10) < 1e-9  # 100 -> 110
    rel = forward_return(panel, price_col="close", horizon=1, relative=True)
    # cross-sectional mean removed per date
    assert abs(rel.groupby("date")["fwd_return"].mean().dropna().abs().max()) < 1e-9


def test_triple_barrier_hits_barriers():
    # rises 6% by step 2 -> profit-take (+1)
    up = pd.Series([100, 103, 106, 104])
    tb = triple_barrier(up, pt=0.05, sl=0.05, max_holding=3)
    assert tb["label"].iloc[0] == 1
    # falls 6% -> stop (-1)
    down = pd.Series([100, 97, 94, 96])
    tb2 = triple_barrier(down, pt=0.05, sl=0.05, max_holding=3)
    assert tb2["label"].iloc[0] == -1
    # last rows lack a full window -> NaN
    assert np.isnan(tb["label"].iloc[-1])
