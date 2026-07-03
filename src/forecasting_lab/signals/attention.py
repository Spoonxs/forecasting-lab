"""Attention acceleration — the leading edge of a trend.

The research is consistent: it's the **acceleration** of attention (news / social
mentions rising *faster* than a name's own baseline), not the level, that leads
short-horizon moves. Levels are already priced in. This computes a per-entity
z-score of the day-over-day change in mentions against its trailing baseline, and
persists dated counts so the velocity has history to stand on (it strengthens as
the store fills, like the forward study).

Leak-free: the signal is lagged one day before it's allowed to predict a move, so
today's mention spike can only inform *tomorrow's* decision.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..config import PATHS


def attention_acceleration(counts: pd.Series, window: int = 20, min_periods: int = 5) -> pd.Series:
    """Rolling z-score of the day-over-day change in mention counts.

    Zero-mean on a stationary series; a genuine spike scores high. Returns 0 where
    there isn't enough history yet (honest degradation)."""
    counts = pd.Series(counts, dtype=float).reset_index(drop=True)
    delta = counts.diff()
    roll = delta.rolling(window=window, min_periods=min_periods)
    std = roll.std(ddof=0).replace(0.0, np.nan)
    z = (delta - roll.mean()) / std
    return z.fillna(0.0)


class AttentionStore:
    """Dated per-ticker mention counts, persisted so velocity has a history."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else PATHS.data / "attention.csv"

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=["date", "ticker", "count"])
        return pd.read_csv(self.path)

    def record(self, on: str, counts: dict[str, float]) -> None:
        """Append (or replace) one day's counts for a set of tickers."""
        df = self.load()
        df = df[df["date"] != on]  # idempotent: a re-run for the same day overwrites
        rows = pd.DataFrame([{"date": on, "ticker": t, "count": float(c)} for t, c in counts.items()])
        out = pd.concat([df, rows], ignore_index=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(self.path, index=False)

    def series(self, ticker: str) -> pd.Series:
        """Mention counts for one ticker, chronological (empty if unseen)."""
        df = self.load()
        s = df[df["ticker"] == ticker].sort_values("date")["count"]
        return pd.Series(s.to_numpy(dtype=float))

    def latest_acceleration(self, ticker: str, window: int = 20) -> float:
        """The most recent, already-realized acceleration z (0 without history)."""
        s = self.series(ticker)
        if len(s) < 3:
            return 0.0
        return float(attention_acceleration(s, window=window).iloc[-1])


def attention_skill_report(seed: int = 0, n_tickers: int = 50, n_days: int = 160,
                           strength: float = 1.1, k_model: float = 0.9) -> dict:
    """OOS Brier-skill of the lagged acceleration signal vs. the 0.5 base rate."""
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for t in range(n_tickers):
        base = rng.uniform(6, 22)
        counts = rng.poisson(base, n_days).astype(float)
        spikes = rng.uniform(size=n_days) < 0.08
        counts[spikes] += rng.uniform(25, 70, int(spikes.sum()))
        accel = attention_acceleration(pd.Series(counts)).to_numpy()
        accel_lag = np.roll(accel, 1)
        accel_lag[0] = 0.0  # yesterday's acceleration decides today — no look-ahead
        p_up = 1.0 / (1.0 + np.exp(-strength * accel_lag))
        y = (rng.uniform(size=n_days) < p_up).astype(float)
        for d in range(n_days):
            rows.append({"period": d, "ticker": t, "accel": accel_lag[d], "y": y[d]})
    df = pd.DataFrame(rows)
    df["prob"] = 1.0 / (1.0 + np.exp(-k_model * df["accel"]))  # a fixed model map, not the oracle
    df["ref"] = 0.5
    from ..eval.skill import walk_forward_skill
    skill = walk_forward_skill(df, prob_col="prob", label_col="y", ref_col="ref", time_col="period")
    return {"feature": "attention acceleration", "n": len(df),
            "brier_skill_vs_baseline": round(skill, 4), "baseline": "0.5 base rate"}
