"""The forward-test ledger: record picks now, mark to market later.

State per strategy is a snapshot ``(weights, prices_at_snapshot, as_of)`` plus a
growing equity ``curve``. One :meth:`ForwardLedger.step` per calendar period:

1. if a prior snapshot exists, realize ``sum(w_i * (price_now/price_then - 1))``
   minus turnover cost, and append the compounded equity point;
2. compute fresh target weights on the history up to now, and store the new
   snapshot.

Because step (1) uses only prices that already existed at snapshot time and step
(2) never sees the future, look-ahead is structurally impossible.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..config import PATHS

# A focused basket of high-attention "theme/trend" names — the NVDA/GME/BTC-proxy
# universe where news-driven momentum actually shows up. Kept small so a daily
# real-price pull is fast and reliable.
THEME_BASKET = [
    "NVDA", "AMD", "TSLA", "GME", "AMC", "COIN", "MSTR", "PLTR", "SMCI", "ARM",
    "SOXL", "TQQQ", "MU", "AVGO", "TSM", "META", "AMZN", "GOOGL", "AAPL", "MSFT",
    "NFLX", "RBLX", "HOOD", "SPY", "QQQ",
]


def _weighted_return(weights: dict, then: dict, now: dict) -> float:
    total = 0.0
    for t, w in weights.items():
        p0, p1 = then.get(t), now.get(t)
        if p0 and p1:
            total += w * (p1 / p0 - 1.0)
    return total


def _turnover(old: dict, new: dict) -> float:
    keys = set(old) | set(new)
    return sum(abs(new.get(k, 0.0) - old.get(k, 0.0)) for k in keys)


class ForwardLedger:
    """Real-universe, real-time forward paper-trading across strategies."""

    def __init__(self, strategies=None, cost_bps: float = 10.0, path: Path | str | None = None):
        from ..sim.strategies import default_strategies

        self.strategies = strategies if strategies is not None else default_strategies()
        self.cost = cost_bps / 1e4
        self.path = Path(path) if path else (PATHS.data / "forward" / "ledger.json")
        self.state: dict[str, dict] = {}
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))

    # ---- one observation ------------------------------------------------
    def step(self, prices: pd.DataFrame, on_date: str, phase: str = "live") -> None:
        """Advance one period using ``prices`` (date-indexed real closes, history
        up to and including ``on_date``). Marks the prior snapshot, records a new one."""
        now = {c: float(prices[c].iloc[-1]) for c in prices.columns if pd.notna(prices[c].iloc[-1])}
        for strat in self.strategies:
            st = self.state.setdefault(strat.name, {"weights": {}, "prices": {}, "as_of": None, "curve": []})
            # (1) realize the prior snapshot
            if st["weights"] and st["as_of"] and st["as_of"] != on_date:
                gross = _weighted_return(st["weights"], st["prices"], now)
                target = strat.target_weights(prices, len(prices) - 1)
                cost = self.cost * _turnover(st["weights"], target) / 2.0
                prev_equity = st["curve"][-1]["equity"] if st["curve"] else 1.0
                st["curve"].append({"date": on_date, "equity": prev_equity * (1.0 + gross - cost), "phase": phase})
            # (2) record the new snapshot (weights to hold from now)
            target = strat.target_weights(prices, len(prices) - 1)
            st["weights"] = {k: float(v) for k, v in target.items()}
            st["prices"] = {t: now[t] for t in target if t in now}
            st["as_of"] = on_date
            if not st["curve"]:  # anchor the curve at 1.0
                st["curve"].append({"date": on_date, "equity": 1.0, "phase": phase})

    def backfill(self, prices: pd.DataFrame, every: int = 5, start: int = 130) -> int:
        """Seed a curve by replaying recent real history in ``every``-day steps.

        Labeled ``backfill`` (context, not the study). Returns steps replayed.
        Only runs on a fresh ledger so it never double-counts."""
        if any(st["curve"] for st in self.state.values()):
            return 0
        steps = 0
        for i in range(min(start, len(prices) - 1), len(prices), every):
            window = prices.iloc[: i + 1]
            self.step(window, str(prices.index[i])[:10], phase="backfill")
            steps += 1
        return steps

    # ---- persistence / reporting ---------------------------------------
    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state), encoding="utf-8")

    def leaderboard(self) -> pd.DataFrame:
        rows = []
        for name, st in self.state.items():
            curve = st["curve"]
            live = [c for c in curve if c["phase"] == "live"]
            equity = curve[-1]["equity"] if curve else 1.0
            live_start = live[0]["equity"] if live else equity
            rows.append(
                {
                    "strategy": name,
                    "equity": equity,
                    "total_return": equity - 1.0,
                    "live_return": (equity / live_start - 1.0) if live else 0.0,
                    "live_marks": len(live),
                    "as_of": st["as_of"],
                }
            )
        board = pd.DataFrame(rows)
        return board.sort_values("equity", ascending=False).reset_index(drop=True) if not board.empty else board

    def curves(self) -> dict[str, list[dict]]:
        return {name: st["curve"] for name, st in self.state.items() if st["curve"]}

    def live_started(self) -> str | None:
        for st in self.state.values():
            for pt in st["curve"]:
                if pt["phase"] == "live":
                    return pt["date"]
        return None
