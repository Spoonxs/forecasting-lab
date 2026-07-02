"""FRED (Federal Reserve Economic Data) connector — free, no key for CSV.

The public ``fredgraph.csv`` endpoint serves any series as CSV without an API
key, which is enough for macro nowcasting. The curated ``MACRO_SERIES`` are the
ones the macro model uses; add more freely.
"""

from __future__ import annotations

import io

import pandas as pd

from ..utils.cache import DiskCache
from ..utils.http import HttpClient

FREDGRAPH = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# Series that matter for recession / rate / inflation nowcasting.
MACRO_SERIES = {
    "DGS10": "10-Year Treasury yield",
    "DGS3MO": "3-Month Treasury yield",
    "T10Y3M": "10Y-3M term spread (recession signal)",
    "UNRATE": "Unemployment rate",
    "CPIAUCSL": "CPI (all urban)",
    "FEDFUNDS": "Effective federal funds rate",
    "SP500": "S&P 500 index",
    "VIXCLS": "VIX",
}


def series(series_id: str, refresh: bool = False) -> pd.Series:
    """One FRED series as a date-indexed float Series (missing values dropped)."""
    cache = DiskCache("fred", ttl=12 * 3600)
    key = f"series:{series_id}"
    if not refresh:
        hit = cache.get(key)
        if hit:
            s = pd.Series(hit["values"], index=pd.to_datetime(hit["index"]), name=series_id)
            return s
    text = HttpClient().get(FREDGRAPH, params={"id": series_id}).text
    df = pd.read_csv(io.StringIO(text))
    date_col, val_col = df.columns[0], df.columns[1]
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    df = df.dropna()
    out = pd.Series(df[val_col].to_numpy(), index=pd.to_datetime(df[date_col]), name=series_id)
    cache.set(key, {"index": [d.isoformat() for d in out.index], "values": out.tolist()})
    return out


def latest(series_id: str) -> tuple[str, float] | None:
    """Most recent ``(date, value)`` for a series, or None if empty."""
    s = series(series_id)
    if s.empty:
        return None
    return s.index[-1].date().isoformat(), float(s.iloc[-1])
