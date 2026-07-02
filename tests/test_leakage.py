"""The most important test in the repo: a null-signal leakage guard.

If features carry no information about forward returns, an honest, leak-free
pipeline must show ~zero out-of-sample skill. A look-ahead bug (e.g. an
unpurged CV fold, a misaligned label) would manufacture fake skill here — so this
test fails loudly the moment leakage creeps into features/labels/CV/ranker.
"""

import numpy as np
import pandas as pd

from forecasting_lab.backtest import walk_forward_backtest
from forecasting_lab.ml import (
    CrossSectionalRanker,
    PurgedWalkForwardCV,
    cross_sectional_zscore,
    forward_return,
)


def _null_pipeline_sharpe(seed: int) -> float:
    """OOS Sharpe of the full pipeline on features independent of returns."""
    rng = np.random.default_rng(seed)
    T, N = 80, 30
    rows = [{"date": t, "ticker": i, "feat": rng.normal()} for t in range(T) for i in range(N)]
    panel = pd.DataFrame(rows).sort_values(["ticker", "date"])
    # returns are pure noise — no learnable relationship to `feat`
    panel["ret_next"] = rng.normal(0, 0.03, len(panel))
    panel["close"] = panel.groupby("ticker")["ret_next"].transform(
        lambda s: 100 * np.cumprod(1 + s.shift(1).fillna(0))
    )
    panel = cross_sectional_zscore(panel, "feat", date_col="date")
    panel = forward_return(panel, price_col="close", horizon=1, relative=True)
    panel["period"] = panel["date"]
    oos = CrossSectionalRanker().oos_predict(
        panel, ["feat_z"], "fwd_return", time_col="period",
        cv=PurgedWalkForwardCV(n_splits=6, horizon=1),
    )
    bt = walk_forward_backtest(oos, score_col="score", fwd_return_col="fwd_return", top_frac=0.25)
    return bt.stats["sharpe"]


def test_null_signal_has_no_systematic_skill():
    sharpes = np.array([_null_pipeline_sharpe(seed) for seed in range(6)])
    # The mean OOS Sharpe across seeds must hug zero. A leak would push it
    # systematically (and large) positive.
    assert abs(sharpes.mean()) < 1.0, f"null-signal Sharpe biased away from 0: {sharpes}"


def test_ranker_alignment_survives_dropped_rows():
    # Inject NaN features; every returned prediction must correspond to a row that
    # actually had a feature (no positional misalignment after dropna/reset_index).
    T, N = 40, 12
    rows = [{"date": t, "ticker": i, "feat": float(i) + 0.01 * t} for t in range(T) for i in range(N)]
    panel = pd.DataFrame(rows)
    panel["fwd_return"] = panel["feat"] * 0.001
    panel["period"] = panel["date"]
    panel.loc[panel.sample(40, random_state=1).index, "feat"] = np.nan
    oos = CrossSectionalRanker().oos_predict(
        panel, ["feat"], "fwd_return", time_col="period",
        cv=PurgedWalkForwardCV(n_splits=5, horizon=1),
    )
    assert oos["feat"].notna().all()
    assert np.isfinite(oos["score"]).all()
