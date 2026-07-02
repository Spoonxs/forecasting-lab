"""A CSV-backed public forecasting log, scored with Brier and calibration.

Record every prediction with your probability estimate; resolve it when the
outcome is known; let the score tell you whether your judgment is calibrated.
The CSV lives at the repo root by default so it can be committed — it *is* the
portfolio piece.
"""

from __future__ import annotations

from datetime import date as _date
from pathlib import Path

import pandas as pd

from ..config import PATHS
from ..eval.metrics import reliability_table, summary

COLUMNS = ["id", "date", "venue", "question", "prob", "outcome", "resolved_date", "notes"]


class ForecastLog:
    """Append-only log of probabilistic forecasts with scoring helpers."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else (PATHS.root / "calibration_log.csv")
        if self.path.exists():
            self.df = pd.read_csv(self.path)
            for col in COLUMNS:
                if col not in self.df.columns:
                    self.df[col] = pd.NA
        else:
            self.df = pd.DataFrame(columns=COLUMNS)
        self.df = self._coerce_schema(self.df)

    @staticmethod
    def _coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
        """Force text/date columns to object so string assignment never trips the
        float64 dtype an all-empty column gets after ``read_csv``."""
        df = df.copy()
        for col in ("date", "venue", "question", "notes", "resolved_date", "outcome"):
            if col in df.columns:
                df[col] = df[col].astype(object)
        if "prob" in df.columns:
            df["prob"] = pd.to_numeric(df["prob"], errors="coerce")
        return df

    # ---- mutate --------------------------------------------------------
    def record(
        self,
        question: str,
        prob: float,
        venue: str = "",
        on: _date | None = None,
        notes: str = "",
    ) -> int:
        """Log a new forecast. Returns its id."""
        if not 0.0 <= prob <= 1.0:
            raise ValueError("prob must be in [0, 1]")
        new_id = (int(self.df["id"].max()) + 1) if len(self.df) else 1
        row = {
            "id": new_id,
            "date": (on or _date.today()).isoformat(),
            "venue": venue,
            "question": question,
            "prob": float(prob),
            "outcome": pd.NA,
            "resolved_date": pd.NA,
            "notes": notes,
        }
        self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
        self.save()
        return new_id

    def resolve(self, forecast_id: int, outcome: int, on: _date | None = None) -> None:
        """Set the realized outcome (0/1) for a forecast."""
        if outcome not in (0, 1):
            raise ValueError("outcome must be 0 or 1")
        mask = self.df["id"] == forecast_id
        if not mask.any():
            raise KeyError(f"no forecast with id {forecast_id}")
        self.df.loc[mask, "outcome"] = int(outcome)
        self.df.loc[mask, "resolved_date"] = (on or _date.today()).isoformat()
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.df.to_csv(self.path, index=False)

    # ---- read / score --------------------------------------------------
    def to_frame(self) -> pd.DataFrame:
        return self.df.copy()

    def resolved(self) -> pd.DataFrame:
        df = self.df.copy()
        df["outcome"] = pd.to_numeric(df["outcome"], errors="coerce")
        return df.dropna(subset=["outcome"])

    def score(self, n_bins: int = 10) -> dict:
        """Brier / log loss / calibration over all resolved forecasts."""
        res = self.resolved()
        if res.empty:
            raise ValueError("no resolved forecasts to score yet")
        return summary(res["outcome"].to_numpy(), res["prob"].to_numpy(), n_bins=n_bins)

    def calibration_table(self, n_bins: int = 10) -> pd.DataFrame:
        res = self.resolved()
        if res.empty:
            raise ValueError("no resolved forecasts to score yet")
        return reliability_table(res["outcome"].to_numpy(), res["prob"].to_numpy(), n_bins=n_bins)
