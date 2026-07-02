"""End-to-end cross-sectional ML demo (the ``ml/`` layer has no CLI of its own).

Plants a *faint* signal in noisy returns, then runs the honest pipeline:
features -> forward-return labels -> purged walk-forward CV ranker ->
walk-forward backtest vs honest baselines. The strategy should beat the random
and equal-weight baselines — but only modestly, because the signal is weak by
design (a realistic information coefficient, not a fantasy 4.0 Sharpe).

Run:  python examples/ml_pipeline_demo.py
(after ``pip install -e ".[all]"`` — needs the optional ML extra).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecasting_lab.backtest import walk_forward_backtest
from forecasting_lab.ml import (
    CrossSectionalRanker,
    PurgedWalkForwardCV,
    cross_sectional_zscore,
    forward_return,
)


def main() -> None:
    rng = np.random.default_rng(7)
    T, N = 150, 50  # 150 dates, 50 names

    rows = [{"date": t, "ticker": i, "feat": rng.normal()} for t in range(T) for i in range(N)]
    panel = pd.DataFrame(rows).sort_values(["ticker", "date"])

    # Faint signal: next-period return loads weakly on `feat` (low info coefficient).
    panel["ret_next"] = 0.004 * panel["feat"] + rng.normal(0, 0.03, len(panel))
    panel["close"] = panel.groupby("ticker")["ret_next"].transform(
        lambda s: 100 * np.cumprod(1 + s.shift(1).fillna(0))
    )

    panel = cross_sectional_zscore(panel, "feat", date_col="date")
    panel = forward_return(panel, price_col="close", horizon=1, relative=True)
    panel["period"] = panel["date"]

    ranker = CrossSectionalRanker()
    print(f"Ranker backend: {ranker.backend}")
    oos = ranker.oos_predict(
        panel, ["feat_z"], "fwd_return", time_col="period",
        cv=PurgedWalkForwardCV(n_splits=8, horizon=1),
    )
    print(f"Out-of-sample predictions: {len(oos):,} rows across {oos['date'].nunique()} dates")

    # A small per-period cost so the backtest isn't a frictionless fantasy.
    bt = walk_forward_backtest(
        oos, score_col="score", fwd_return_col="fwd_return", top_frac=0.2, cost=0.0005
    )
    cols = ["sharpe", "ann_return", "hit_rate", "max_drawdown", "n_periods"]
    print("\nWalk-forward backtest (strategy vs honest baselines, 5bps/period cost):")
    print(bt.summary()[cols].round(3).to_string())
    print(
        "\nThe strategy beats both baselines because the signal is real. The honest "
        "control is tests/test_leakage.py: feed a *null* signal and the same pipeline "
        "yields ~zero Sharpe. That gap is how you know it isn't faking skill — and on "
        "real data, signals are weaker and costs bite harder than this."
    )


if __name__ == "__main__":
    main()
