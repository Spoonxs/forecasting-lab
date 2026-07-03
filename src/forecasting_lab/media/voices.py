"""Who's actually ahead of the curve — voice track-record scoring.

Following the loudest voice is a losing strategy: loudness and follower count are
*lagging* signals. This scores each tracked voice the only honest way — by whether
their calls were **right vs. the base rate** and **early vs. the move** — and ranks
them by that record, never by audience. A voice's weight *decays* when it starts
regressing, so a stale reputation fades.

Two axes per voice:
- **Brier skill** — implied up-probability of each call vs. the realised outcome,
  skill-scored against the base rate. Being right, measurably.
- **Timing lead** — the horizon at which the voice's signal best predicts returns
  (cross-correlation). A positive lead means the call *precedes* the move; a
  reactor who echoes yesterday scores ~0 here.

A voice making random calls scores ~0 on both (the leakage guard, pinned in
tests). Real rankings need weeks of logged calls marked to real prices — this is
the engine + the guarantees; it fills in live like the forward study.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import PATHS
from ..eval.metrics import brier_skill_score


@dataclass(frozen=True)
class VoiceCall:
    date: str
    voice: str
    ticker: str
    stance: float  # +1 bullish, -1 bearish


class VoiceLedger:
    """Dated log of each voice's ticker calls (persisted; the raw track record)."""

    COLUMNS = ["date", "voice", "ticker", "stance"]

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else PATHS.data / "voice_calls.csv"

    def to_frame(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=self.COLUMNS)
        return pd.read_csv(self.path)

    def record(self, call: VoiceCall) -> None:
        df = self.to_frame()
        row = pd.DataFrame([{**call.__dict__}])
        out = pd.concat([df, row], ignore_index=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(self.path, index=False)


def _forward_cumret(returns: np.ndarray, horizon: int) -> np.ndarray:
    """Cumulative return over the next ``horizon`` steps, aligned to each period."""
    r = np.asarray(returns, dtype=float)
    csum = np.concatenate([[0.0], np.cumsum(r)])
    out = np.full(len(r), np.nan)
    for t in range(len(r) - horizon):
        out[t] = csum[t + horizon] - csum[t]
    return out


def _timing_lead(signal: np.ndarray, returns: np.ndarray, max_lead: int = 6) -> tuple[int, float]:
    """Horizon at which the signal best predicts returns (its lead). >0 = early."""
    s = np.asarray(signal, dtype=float)
    best_lead, best_corr = 0, 0.0
    for lead in range(1, max_lead + 1):
        fwd = _forward_cumret(returns, lead)
        m = ~np.isnan(fwd) & (s != 0)
        if m.sum() < 6:
            continue
        x, z = s[m], fwd[m]
        if np.std(x) > 0 and np.std(z) > 0:
            c = float(np.corrcoef(x, z)[0, 1])
            if c > best_corr:
                best_corr, best_lead = c, lead
    return best_lead, round(best_corr, 3)


def score_voice(signal, returns, horizon: int = 3, max_lead: int = 6) -> dict:
    """Brier skill + timing lead + a record-weighted score for one voice's calls."""
    signal = np.asarray(signal, dtype=float)
    fwd = _forward_cumret(returns, horizon)
    active = (signal != 0) & ~np.isnan(fwd)
    n = int(active.sum())
    if n < 8:
        return {"n_calls": n, "brier_skill": 0.0, "lead": 0, "corr": 0.0, "weight": 0.0}
    prob = 0.5 + 0.4 * np.sign(signal[active])
    y = (fwd[active] > 0).astype(float)
    bs = brier_skill_score(y, prob)
    lead, corr = _timing_lead(signal, returns, max_lead)
    weight = max(0.0, bs)
    # decay a regressing record: recent calls scoring worse than earlier ones
    mid = n // 2
    if mid >= 4:
        early = brier_skill_score(y[:mid], prob[:mid])
        late = brier_skill_score(y[mid:], prob[mid:])
        if late < early - 0.05:
            weight *= 0.6
    return {"n_calls": n, "brier_skill": round(float(bs), 4), "lead": int(lead),
            "corr": corr, "weight": round(float(weight), 4)}


def score_voices(signals: dict[str, np.ndarray], returns, as_of: str,
                 horizon: int = 3, max_lead: int = 6) -> pd.DataFrame:
    """Rank voices by record (weight, then skill) — deterministic, dated."""
    rows = [{"voice": v, **score_voice(sig, returns, horizon, max_lead)} for v, sig in signals.items()]
    df = pd.DataFrame(rows)
    df = df.sort_values(["weight", "brier_skill", "voice"], ascending=[False, False, True]).reset_index(drop=True)
    df["as_of"] = as_of
    return df


# ------------------------------------------------------- synthetic demonstration
def _demo_signals(rng, returns: np.ndarray, horizon: int):
    """Three archetypes: an early-and-right voice, a reactor, and pure noise."""
    n = len(returns)
    fwd = _forward_cumret(returns, horizon)

    def early(skill: float) -> np.ndarray:
        s = np.zeros(n)
        for t in range(n - horizon):
            if rng.uniform() < 0.5:  # silent half the days
                continue
            call = np.sign(fwd[t]) if not np.isnan(fwd[t]) else 0.0
            s[t] = call if rng.uniform() < skill else -call
        return s

    def reactor() -> np.ndarray:
        s = np.zeros(n)
        for t in range(1, n):
            if rng.uniform() < 0.5:
                s[t] = np.sign(returns[t - 1])  # echoes yesterday — late, not early
        return s

    def noise() -> np.ndarray:
        return rng.choice([-1.0, 0.0, 0.0, 1.0], size=n)

    return {"@early_sharp": early(0.82), "@reactor": reactor(), "@noise": noise()}


def voice_leaderboard_report(seed: int = 0, as_of: str = "synthetic", n_periods: int = 200,
                             horizon: int = 3) -> dict:
    """A deterministic 'ahead of the curve' leaderboard on synthetic calls."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0, 0.02, n_periods)
    signals = _demo_signals(rng, returns, horizon)
    lb = score_voices(signals, returns, as_of, horizon=horizon)
    return {"as_of": as_of, "rows": lb.to_dict("records")}
