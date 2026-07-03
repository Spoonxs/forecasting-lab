"""Out-of-sample Brier skill against a reference (usually the market price).

Being calibrated is not an edge; beating the *market's own price* is. These
helpers score a model's probabilities against a reference probability series and
do it out-of-sample under the purged walk-forward split, so a fitted transform
can never peek at its own test fold. Every Phase-1 edge feature is scored through
here, so "does it actually help?" always means the same, honest thing.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from ..ml.cv import PurgedWalkForwardCV
from .metrics import brier_score


def brier_skill_vs(y_true, y_prob, y_ref) -> float:
    """1 − Brier(model)/Brier(reference). >0 means the model beats the reference."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    y_ref = np.asarray(y_ref, dtype=float)
    ref = brier_score(y_true, y_ref)
    if ref <= 0:
        return 0.0
    return float(1.0 - brier_score(y_true, y_prob) / ref)


def walk_forward_skill(
    df: pd.DataFrame,
    *,
    prob_col: str,
    label_col: str,
    ref_col: str,
    time_col: str,
    cv: PurgedWalkForwardCV | None = None,
    fit_transform: Callable[[pd.DataFrame], Callable[[np.ndarray], np.ndarray]] | None = None,
) -> float:
    """OOS Brier-skill-vs-reference under ``PurgedWalkForwardCV``.

    ``fit_transform(train_df) -> f(test_prob_array) -> model_prob_array`` lets a
    feature fit on the training fold and apply to the test fold — leak-free. With
    ``fit_transform=None`` the model probability *is* ``prob_col`` (no fitting),
    which still scores an already-computed signal honestly out-of-sample.
    """
    cv = cv or PurgedWalkForwardCV(n_splits=4, horizon=1)
    data = df.reset_index(drop=True)
    times = data[time_col].to_numpy()
    ys: list[np.ndarray] = []
    models: list[np.ndarray] = []
    refs: list[np.ndarray] = []
    for train_idx, test_idx in cv.split(times):
        train, test = data.iloc[train_idx], data.iloc[test_idx]
        if fit_transform is None:
            model_p = test[prob_col].to_numpy(dtype=float)
        else:
            fn = fit_transform(train)
            model_p = np.asarray(fn(test[prob_col].to_numpy(dtype=float)), dtype=float)
        ys.append(test[label_col].to_numpy(dtype=float))
        models.append(model_p)
        refs.append(test[ref_col].to_numpy(dtype=float))
    if not ys:
        return 0.0
    return brier_skill_vs(np.concatenate(ys), np.concatenate(models), np.concatenate(refs))
