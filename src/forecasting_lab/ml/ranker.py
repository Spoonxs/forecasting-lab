"""Cross-sectional ranker.

On tabular market data, gradient-boosted trees beat deep nets in practice — this
is the real state of the art for alpha, not a compromise. We regress the forward
(relative) return and rank by the prediction. Backend preference: LightGBM ->
scikit-learn HistGradientBoosting -> Ridge, so the code runs even in a minimal
environment (and degrades loudly via the ``backend`` attribute).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .cv import PurgedWalkForwardCV


def _build_model(params: dict):
    """Return ``(estimator, backend_name)`` using the best available library."""
    try:
        import lightgbm as lgb

        defaults = dict(n_estimators=300, learning_rate=0.03, num_leaves=31, subsample=0.8,
                        subsample_freq=1, colsample_bytree=0.8, min_child_samples=50, verbose=-1)
        defaults.update(params)
        return lgb.LGBMRegressor(**defaults), "lightgbm"
    except ImportError:
        pass
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor

        defaults = dict(max_iter=300, learning_rate=0.03, max_leaf_nodes=31)
        defaults.update({k: v for k, v in params.items() if k in HistGradientBoostingRegressor().get_params()})
        return HistGradientBoostingRegressor(**defaults), "sklearn-hgb"
    except ImportError:
        pass
    from sklearn.linear_model import Ridge

    return Ridge(alpha=params.get("alpha", 1.0)), "ridge"


class CrossSectionalRanker:
    """Regress a forward-return target with a GBM and rank by the prediction."""

    def __init__(self, **params):
        self.params = params
        self.model, self.backend = _build_model(params)

    def fit(self, X, y) -> CrossSectionalRanker:
        self.model.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=float))
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(np.asarray(X, dtype=float))

    def oos_predict(
        self,
        panel: pd.DataFrame,
        feature_cols,
        label_col: str,
        time_col: str = "period",
        cv: PurgedWalkForwardCV | None = None,
        score_col: str = "score",
    ) -> pd.DataFrame:
        """Out-of-sample walk-forward predictions.

        Trains a fresh model on each purged training fold and predicts its test
        block. Returns only the rows that were ever in a test fold, with the
        model's ``score_col`` attached — these are the honest, leak-free
        predictions to feed into :mod:`forecasting_lab.backtest` and
        :mod:`forecasting_lab.eval`.
        """
        cv = cv or PurgedWalkForwardCV()
        feature_cols = [feature_cols] if isinstance(feature_cols, str) else list(feature_cols)
        data = panel.reset_index(drop=True)
        usable = data.dropna(subset=feature_cols + [label_col, time_col])
        times = usable[time_col].to_numpy()
        # Keep a DataFrame for X so the model sees consistent feature names at fit
        # and predict time (avoids LightGBM's feature-name mismatch warning).
        X = usable[feature_cols].astype(float).reset_index(drop=True)
        y = usable[label_col].to_numpy(dtype=float)

        scores = np.full(len(usable), np.nan)
        for train_idx, test_idx in cv.split(times):
            model, _ = _build_model(self.params)
            model.fit(X.iloc[train_idx], y[train_idx])
            scores[test_idx] = model.predict(X.iloc[test_idx])

        out = usable.copy()
        out[score_col] = scores
        return out.dropna(subset=[score_col]).reset_index(drop=True)
