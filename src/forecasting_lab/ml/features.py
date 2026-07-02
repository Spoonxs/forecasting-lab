"""Feature engineering for cross-sectional models.

Two rules that prevent the most common silent bugs:
1. Normalise *within each date* (rank or z-score), so the model learns relative
   position, not absolute levels that drift with the market.
2. Lag everything. A feature computed from end-of-day data cannot be used to
   trade that same day's close — shift it forward first.
"""

from __future__ import annotations

import pandas as pd


def cross_sectional_rank(
    panel: pd.DataFrame,
    cols,
    date_col: str = "date",
    center: bool = True,
    suffix: str = "_rank",
) -> pd.DataFrame:
    """Percentile-rank ``cols`` within each date. ``center`` shifts to [-0.5, 0.5]."""
    cols = [cols] if isinstance(cols, str) else list(cols)
    out = panel.copy()
    for col in cols:
        ranked = out.groupby(date_col)[col].rank(pct=True)
        out[col + suffix] = ranked - 0.5 if center else ranked
    return out


def cross_sectional_zscore(
    panel: pd.DataFrame,
    cols,
    date_col: str = "date",
    suffix: str = "_z",
) -> pd.DataFrame:
    """Z-score ``cols`` within each date (mean 0, std 1 cross-sectionally)."""
    cols = [cols] if isinstance(cols, str) else list(cols)
    out = panel.copy()
    grp = out.groupby(date_col)
    for col in cols:
        mean = grp[col].transform("mean")
        std = grp[col].transform("std").replace(0, pd.NA)
        out[col + suffix] = ((out[col] - mean) / std).astype(float)
    return out


def lag_features(
    panel: pd.DataFrame,
    cols,
    entity_col: str = "ticker",
    date_col: str = "date",
    periods: int = 1,
    suffix: str | None = None,
) -> pd.DataFrame:
    """Shift ``cols`` forward by ``periods`` within each entity to kill look-ahead.

    With ``suffix=None`` the columns are replaced in place; otherwise lagged copies
    are added. Always sorts by (entity, date) first.
    """
    cols = [cols] if isinstance(cols, str) else list(cols)
    out = panel.sort_values([entity_col, date_col], kind="stable").copy()
    grouped = out.groupby(entity_col)[cols].shift(periods)
    for col in cols:
        target = col if suffix is None else col + suffix
        out[target] = grouped[col]
    return out


def zscore_velocity(
    series: pd.Series,
    window: int = 60,
    min_periods: int = 20,
) -> pd.Series:
    """Rolling z-score of a series against its own trailing baseline.

    This is the "spike, not the level" transform used for social-velocity signals:
    a 5x jump in mentions scores high; a high steady level does not. Uses only
    past data (the current point is included; shift if you need strict causality).
    """
    roll = series.rolling(window=window, min_periods=min_periods)
    mean = roll.mean()
    std = roll.std()
    return ((series - mean) / std.replace(0, pd.NA)).astype(float)
