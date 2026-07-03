"""A tiny persisted tidy store — dated facts that accrue over time.

Velocity and track-record features are only as good as the history behind them
(you can't measure *acceleration* from a single snapshot). This is the shared,
append-only tidy store: rows of ``(date, entity, metric, value)`` in a CSV, with
same-day idempotency so a re-run overwrites rather than duplicates. Short
interest, gamma, and voice mentions all file into it so that — like the forward
study — the signals strengthen as the days pile up.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import PATHS

COLUMNS = ["date", "entity", "metric", "value"]


class TidyStore:
    """Append-only ``(date, entity, metric, value)`` facts, persisted to CSV."""

    def __init__(self, name: str = "facts", root: Path | str | None = None):
        root = Path(root) if root else PATHS.data
        self.path = root / f"{name}.csv"

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=COLUMNS)
        return pd.read_csv(self.path)

    def record(self, on: str, metric: str, values: dict[str, float]) -> None:
        """Store one day's ``entity -> value`` for ``metric``; a same-day re-run overwrites."""
        df = self.load()
        mask = ~((df["date"] == on) & (df["metric"] == metric)) if not df.empty else slice(None)
        kept = df[mask] if not df.empty else df
        rows = pd.DataFrame(
            [{"date": on, "entity": e, "metric": metric, "value": float(v)} for e, v in values.items()]
        )
        out = pd.concat([kept, rows], ignore_index=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(self.path, index=False)

    def series(self, entity: str, metric: str) -> pd.Series:
        """Chronological values of one metric for one entity (empty if unseen)."""
        df = self.load()
        if df.empty:
            return pd.Series(dtype=float)
        sel = df[(df["entity"] == entity) & (df["metric"] == metric)].sort_values("date")
        return pd.Series(sel["value"].to_numpy(dtype=float))

    def latest(self, metric: str) -> dict[str, float]:
        """The most recent day's ``entity -> value`` for a metric ({} if none)."""
        df = self.load()
        sub = df[df["metric"] == metric] if not df.empty else df
        if sub.empty:
            return {}
        day = sub["date"].max()
        rows = sub[sub["date"] == day]
        return dict(zip(rows["entity"], rows["value"].astype(float), strict=False))
