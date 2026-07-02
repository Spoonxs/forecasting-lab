"""Composite signal scoring.

Each composite is a weighted sum of cross-sectionally z-scored features. Missing
features contribute a neutral 0 so a ticker is never penalised for a gap in the
data. Squeeze and momentum are ranked *separately* — never blend them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std()
    if not std or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def composite_score(
    df: pd.DataFrame,
    weights: dict[str, float],
    date_col: str | None = None,
    out_col: str = "composite",
) -> pd.DataFrame:
    """Weighted-z-score composite. Z-scores within ``date_col`` if given, else
    over the whole frame. Adds ``out_col`` and ``out_col + '_rank'`` (pct rank)."""
    out = df.copy()
    contrib = pd.DataFrame(index=out.index)
    used = []
    for feat, w in weights.items():
        if feat not in out.columns:
            continue
        used.append(feat)
        if date_col:
            z = out.groupby(date_col)[feat].transform(_zscore)
        else:
            z = _zscore(out[feat])
        contrib[feat] = z.fillna(0.0) * w
    if not used:
        raise ValueError("none of the weighted features are present in the frame")
    out[out_col] = contrib.sum(axis=1)
    if date_col:
        out[out_col + "_rank"] = out.groupby(date_col)[out_col].rank(pct=True)
    else:
        out[out_col + "_rank"] = out[out_col].rank(pct=True)
    return out.sort_values(out_col, ascending=False)


def squeeze_composite(df: pd.DataFrame, date_col: str | None = None) -> pd.DataFrame:
    from . import SQUEEZE_WEIGHTS

    return composite_score(df, SQUEEZE_WEIGHTS, date_col=date_col, out_col="squeeze")


def momentum_composite(df: pd.DataFrame, date_col: str | None = None) -> pd.DataFrame:
    from . import MOMENTUM_WEIGHTS

    return composite_score(df, MOMENTUM_WEIGHTS, date_col=date_col, out_col="momentum")


def flag_candidates(
    scored: pd.DataFrame, score_col: str, threshold: float = 0.9
) -> pd.DataFrame:
    """Rows in the top ``1 - threshold`` of the composite rank. Candidates to look
    closer at — never an entry signal."""
    rank_col = score_col + "_rank"
    if rank_col not in scored.columns:
        raise KeyError(f"{rank_col} not found; run the composite first")
    return scored[scored[rank_col] >= threshold].sort_values(score_col, ascending=False)
