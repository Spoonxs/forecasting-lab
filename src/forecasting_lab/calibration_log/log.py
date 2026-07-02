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

COLUMNS = [
    "id", "date", "venue", "market_id", "question", "prob", "market_prob",
    "outcome", "resolved_date", "notes",
]


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
        for col in ("date", "venue", "market_id", "question", "notes", "resolved_date", "outcome"):
            if col in df.columns:
                df[col] = df[col].astype(object)
        for col in ("prob", "market_prob"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    # ---- mutate --------------------------------------------------------
    def record(
        self,
        question: str,
        prob: float,
        venue: str = "",
        on: _date | None = None,
        notes: str = "",
        market_id: str = "",
        market_prob: float | None = None,
    ) -> int:
        """Log a new forecast. Returns its id.

        ``market_id`` links to a venue market for auto-resolution; ``market_prob``
        records the market's price at decision time so resolution can score you
        *against the market* (the beat-the-closing-line test)."""
        if not 0.0 <= prob <= 1.0:
            raise ValueError("prob must be in [0, 1]")
        if market_prob is not None and not 0.0 <= market_prob <= 1.0:
            raise ValueError("market_prob must be in [0, 1]")
        new_id = (int(self.df["id"].max()) + 1) if len(self.df) else 1
        row = {
            "id": new_id,
            "date": (on or _date.today()).isoformat(),
            "venue": venue,
            "market_id": market_id,
            "question": question,
            "prob": float(prob),
            "market_prob": float(market_prob) if market_prob is not None else pd.NA,
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

    def resolve_open(self, resolver) -> int:
        """Auto-resolve unresolved forecasts that carry a ``market_id``.

        ``resolver(venue, market_id) -> 0 | 1 | None`` looks up the venue's
        settlement (None = not settled yet). Returns how many were resolved.
        This is what turns the daily run into a self-scoring track record."""
        df = self.df
        outcome_num = pd.to_numeric(df["outcome"], errors="coerce")
        open_mask = outcome_num.isna() & df["market_id"].astype("string").fillna("").ne("")
        resolved = 0
        for idx in df.index[open_mask]:
            outcome = resolver(df.at[idx, "venue"], df.at[idx, "market_id"])
            if outcome in (0, 1):
                df.at[idx, "outcome"] = int(outcome)
                df.at[idx, "resolved_date"] = _date.today().isoformat()
                resolved += 1
        if resolved:
            self.save()
        return resolved

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

    def beat_market_score(self) -> dict:
        """Beat-the-closing-line: did your probs beat the market's, after the fact?

        Over resolved forecasts that recorded a ``market_prob``, compares your
        Brier to the market's and the fraction of times you were closer to the
        truth. ``brier_skill_vs_market > 0`` means genuine edge over the price —
        the thing that actually distinguishes skill from mere calibration."""
        res = self.resolved()
        res = res[pd.to_numeric(res["market_prob"], errors="coerce").notna()]
        if res.empty:
            return {"n": 0}
        y = res["outcome"].to_numpy(dtype=float)
        model_p = res["prob"].to_numpy(dtype=float)
        mkt_p = pd.to_numeric(res["market_prob"]).to_numpy(dtype=float)
        model_brier = float(((model_p - y) ** 2).mean())
        market_brier = float(((mkt_p - y) ** 2).mean())
        beat_rate = float((abs(model_p - y) < abs(mkt_p - y)).mean())
        return {
            "n": int(len(res)),
            "model_brier": model_brier,
            "market_brier": market_brier,
            "brier_skill_vs_market": (1.0 - model_brier / market_brier) if market_brier else 0.0,
            "beat_rate": beat_rate,
        }
