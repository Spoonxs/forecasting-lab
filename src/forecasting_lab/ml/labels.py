"""Label construction for forward-return targets.

Fixed-horizon forward returns are the simple default. The triple-barrier method
(profit-take / stop / time limit) gives path-aware labels that better reflect how
a position would actually be exited. See López de Prado, *Advances in Financial
Machine Learning*.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def forward_return(
    panel: pd.DataFrame,
    price_col: str = "close",
    entity_col: str = "ticker",
    date_col: str = "date",
    horizon: int = 5,
    relative: bool = False,
    out_col: str = "fwd_return",
) -> pd.DataFrame:
    """Add forward simple return over ``horizon`` periods per entity.

    With ``relative=True`` the per-date cross-sectional mean is subtracted, giving
    the *forward relative return* — the clean cross-sectional ranking target that
    sidesteps market-wide moves.
    """
    out = panel.sort_values([entity_col, date_col], kind="stable").copy()
    fwd = out.groupby(entity_col)[price_col].shift(-horizon)
    out[out_col] = fwd / out[price_col] - 1.0
    if relative:
        mean = out.groupby(date_col)[out_col].transform("mean")
        out[out_col] = out[out_col] - mean
    return out


@dataclass(frozen=True)
class BarrierLabel:
    entry_index: int
    touch_offset: int  # periods until a barrier was hit
    ret: float
    label: int  # +1 profit-take, -1 stop, 0 time-limit


def triple_barrier(
    prices,
    pt: float = 0.05,
    sl: float = 0.05,
    max_holding: int = 10,
) -> pd.DataFrame:
    """Triple-barrier labels for a single price series.

    For each entry, look forward up to ``max_holding`` periods and record the first
    barrier touched: upper (+``pt``) -> label +1, lower (-``sl``) -> label -1, or
    the vertical (time) barrier -> label 0 with the realized return at expiry.

    Returns a DataFrame aligned to ``prices`` (last ``max_holding`` rows are NaN —
    they have no full forward window, so they must be dropped before training).
    """
    p = np.asarray(prices, dtype=float)
    n = len(p)
    records = []
    for i in range(n):
        if i + max_holding >= n:
            records.append({"touch_offset": np.nan, "ret": np.nan, "label": np.nan})
            continue
        entry = p[i]
        label, ret, touch = 0, np.nan, max_holding
        for h in range(1, max_holding + 1):
            r = p[i + h] / entry - 1.0
            if r >= pt:
                label, ret, touch = 1, r, h
                break
            if r <= -sl:
                label, ret, touch = -1, r, h
                break
        if np.isnan(ret):  # vertical barrier
            ret = p[i + max_holding] / entry - 1.0
        records.append({"touch_offset": touch, "ret": ret, "label": label})

    out = pd.DataFrame.from_records(records)
    if isinstance(prices, pd.Series):
        out.index = prices.index
    return out
