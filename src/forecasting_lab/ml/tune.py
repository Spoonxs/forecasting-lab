"""Hyperparameter tuning for the cross-sectional ranker — the honest way.

Tuning a time-series model with random k-fold is how a backtest learns to cheat.
Here every candidate is scored by its **out-of-sample rank IC** under the same
:class:`PurgedWalkForwardCV` (purge + embargo) the model uses live: the mean, over
test folds, of the Spearman correlation between the model's predicted ranking and
the realised forward return. Higher IC = the ranking actually lines up with what
happened next, on data the model never trained on.

A null-feature panel should tune to ~zero IC no matter which params win — if it
didn't, the search would be manufacturing skill from noise (pinned in tests).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .cv import PurgedWalkForwardCV
from .ranker import CrossSectionalRanker

# A small, backend-agnostic grid. Each dict carries keys for every backend; the
# ranker's model builder reads only the ones its library understands (Ridge uses
# ``alpha``; the GBMs use ``learning_rate`` / leaf controls), so one grid tunes
# whichever library is installed.
DEFAULT_GRID = [
    {"alpha": 0.3, "learning_rate": 0.10, "num_leaves": 15, "max_leaf_nodes": 15, "min_child_samples": 20},
    {"alpha": 1.0, "learning_rate": 0.05, "num_leaves": 31, "max_leaf_nodes": 31, "min_child_samples": 40},
    {"alpha": 3.0, "learning_rate": 0.03, "num_leaves": 63, "max_leaf_nodes": 63, "min_child_samples": 60},
    {"alpha": 10.0, "learning_rate": 0.02, "num_leaves": 15, "max_leaf_nodes": 15, "min_child_samples": 80},
]


def rank_ic(frame: pd.DataFrame, score_col: str, label_col: str, time_col: str = "period") -> float:
    """Mean per-period Spearman correlation between score and realised label."""
    ics = []
    for _, grp in frame.groupby(time_col):
        if len(grp) < 3:
            continue
        ic = grp[score_col].corr(grp[label_col], method="spearman")
        if pd.notna(ic):
            ics.append(ic)
    return float(np.mean(ics)) if ics else 0.0


def tune_ranker(
    panel: pd.DataFrame,
    feature_cols,
    label_col: str,
    *,
    time_col: str = "period",
    grid: list[dict] | None = None,
    cv: PurgedWalkForwardCV | None = None,
) -> tuple[dict, list[dict]]:
    """Grid-search ranker params by out-of-sample rank IC (purged walk-forward).

    Returns ``(best_params, results)`` where ``results`` is every candidate with
    its IC, best first. Falls back to the first grid entry if nothing scores.
    """
    grid = grid or DEFAULT_GRID
    cv = cv or PurgedWalkForwardCV(n_splits=4, horizon=1)
    feature_cols = list(feature_cols)
    results: list[dict] = []
    for params in grid:
        try:
            preds = CrossSectionalRanker(**params).oos_predict(
                panel, feature_cols, label_col, time_col=time_col, cv=cv
            )
            ic = rank_ic(preds, "score", label_col, time_col=time_col)
        except (ValueError, ZeroDivisionError):
            ic = float("nan")
        results.append({"params": params, "ic": ic})
    scored = [r for r in results if pd.notna(r["ic"])]
    scored.sort(key=lambda r: r["ic"], reverse=True)
    results.sort(key=lambda r: (pd.notna(r["ic"]), r["ic"] if pd.notna(r["ic"]) else -1e9), reverse=True)
    best = scored[0]["params"] if scored else grid[0]
    return best, results
