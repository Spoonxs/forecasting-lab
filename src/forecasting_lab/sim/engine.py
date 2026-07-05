"""The arena engine: bar-by-bar competition with persistent state.

Loop per bar ``t``: each strategy sees prices up to ``t`` and returns target
weights; the engine charges turnover cost on the weight change, then realises
bar ``t+1``'s returns. Weights never touch the bar they were computed from —
look-ahead is impossible by construction.

State (bar cursor, equity curves, current weights) is a JSON file under
``data/sim/``. Because the synthetic market regenerates deterministically from
its seed, resuming from state and running N more bars is *exactly* equivalent to
having run them in one session — a property the tests pin down.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import PATHS
from .data import synthetic_market
from .strategies import default_strategies


def _stats(returns: np.ndarray, periods_per_year: int = 252) -> dict:
    if len(returns) == 0:
        return {"bars": 0, "total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    equity = np.cumprod(1.0 + returns)
    # include the 1.0 starting capital in the peak so a first-bar crash counts
    curve = np.concatenate(([1.0], equity))
    running_max = np.maximum.accumulate(curve)
    drawdown = float(np.min(curve / running_max - 1.0))
    vol = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    ann_ret = float(np.mean(returns)) * periods_per_year
    ann_vol = vol * np.sqrt(periods_per_year)
    return {
        "bars": int(len(returns)),
        "total_return": float(equity[-1] - 1.0),
        "sharpe": ann_ret / ann_vol if ann_vol > 0 else 0.0,
        "max_drawdown": drawdown,
    }


class Arena:
    """Run a lineup of strategies over one market, resumably."""

    def __init__(
        self,
        strategies: list | None = None,
        prices: pd.DataFrame | None = None,
        *,
        seed: int = 0,
        n_assets: int = 12,
        n_bars: int = 2000,
        cost_bps: float = 10.0,
        warmup: int = 130,
        state_path: Path | str | None = None,
    ):
        self.strategies = strategies if strategies is not None else default_strategies()
        self.seed, self.n_assets, self.n_bars = seed, n_assets, n_bars
        self.prices = (
            prices if prices is not None else synthetic_market(n_assets, n_bars, seed=seed)
        )
        self.cost = cost_bps / 1e4
        self.warmup = warmup
        self.state_path = Path(state_path) if state_path else PATHS.data / "sim" / "arena_state.json"

        self.bar = warmup  # cursor: the next bar whose weights get computed
        self.returns: dict[str, list[float]] = {s.name: [] for s in self.strategies}
        self.weights: dict[str, dict[str, float]] = {s.name: {} for s in self.strategies}

    # ---- persistence -----------------------------------------------------
    def _fingerprint(self) -> list[float]:
        """A few exact price points — resuming against different prices (changed
        generator params, different real data) must start fresh, not corrupt."""
        return [
            round(float(self.prices.iloc[0, 0]), 8),
            round(float(self.prices.iloc[len(self.prices) // 2, -1]), 8),
            round(float(self.prices.iloc[-1, -1]), 8),
        ]

    def load(self) -> bool:
        """Restore state if a compatible save exists. Returns True on resume."""
        if not self.state_path.exists():
            return False
        blob = json.loads(self.state_path.read_text(encoding="utf-8"))
        if (
            blob.get("seed") != self.seed
            or blob.get("n_assets") != self.n_assets
            or blob.get("fingerprint") != self._fingerprint()
        ):
            return False  # different market -> start fresh
        self.bar = blob["bar"]
        saved_returns = blob["returns"]
        saved_weights = blob["weights"]
        for s in self.strategies:
            self.returns[s.name] = saved_returns.get(s.name, [])
            self.weights[s.name] = saved_weights.get(s.name, {})
        return True

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        blob = {
            "seed": self.seed,
            "n_assets": self.n_assets,
            "fingerprint": self._fingerprint(),
            "bar": self.bar,
            "returns": self.returns,
            "weights": self.weights,
        }
        self.state_path.write_text(json.dumps(blob), encoding="utf-8")

    def reset(self) -> None:
        if self.state_path.exists():
            self.state_path.unlink()

    # ---- simulation --------------------------------------------------------
    def step(self) -> bool:
        """Advance one bar. Returns False when the market is exhausted."""
        if self.bar + 1 >= len(self.prices):
            return False
        history = self.prices.iloc[: self.bar + 1]  # up to and incl. current bar
        next_returns = self.prices.iloc[self.bar + 1] / self.prices.iloc[self.bar] - 1.0

        for s in self.strategies:
            target = s.target_weights(history, self.bar)
            prev = self.weights[s.name]
            turnover = sum(
                abs(target.get(k, 0.0) - prev.get(k, 0.0)) for k in set(target) | set(prev)
            )
            gross = sum(w * next_returns.get(name, 0.0) for name, w in target.items())
            self.returns[s.name].append(float(gross - self.cost * turnover / 2.0))
            self.weights[s.name] = target

        self.bar += 1
        return True

    def run(self, bars: int) -> int:
        """Advance up to ``bars`` bars; returns how many actually ran."""
        done = 0
        for _ in range(bars):
            if not self.step():
                break
            done += 1
        return done

    # ---- reporting ---------------------------------------------------------
    def leaderboard(self) -> pd.DataFrame:
        from ..eval.deflated import deflated_sharpe_across

        # deflate each strategy's Sharpe against the cross-strategy dispersion
        deflated = deflated_sharpe_across({n: r for n, r in self.returns.items() if r})
        rows = {}
        for name, rets in self.returns.items():
            stats = _stats(np.asarray(rets, dtype=float))
            stats["deflated_sharpe"] = deflated.get(name, 0.0)
            rows[name] = stats
        board = pd.DataFrame(rows).T.sort_values("sharpe", ascending=False)
        board.index.name = "strategy"
        return board

    def returns_frame(self) -> pd.DataFrame:
        """Per-strategy return series as a (periods x strategies) frame."""
        return pd.DataFrame({name: rets for name, rets in self.returns.items() if rets})

    def crowding(self) -> dict:
        """The systemic-risk gauge: mean pairwise correlation across the lineup.
        A board of 'different' strategies sharing one bet is one strategy with
        extra steps — the flag says so next to the leaderboard."""
        from ..agent_trader.fleet import fleet_correlation

        return fleet_correlation({n: r for n, r in self.returns.items() if r})

    def overfitting_pbo(self, n_splits: int = 10) -> float:
        """Probability the arena's in-sample winner is overfit (CSCV). 0 if too few bars."""
        from ..eval.deflated import pbo_cscv

        frame = self.returns_frame()
        if frame.shape[0] < 20 or frame.shape[1] < 2:
            return 0.0
        return pbo_cscv(frame.to_numpy(), n_splits=n_splits)

    def equity_curves(self) -> pd.DataFrame:
        curves = {
            name: np.cumprod(1.0 + np.asarray(rets, dtype=float))
            for name, rets in self.returns.items()
            if rets
        }
        return pd.DataFrame(curves)
