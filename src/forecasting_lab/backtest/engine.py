"""A small, honest cross-sectional walk-forward backtester.

At each rebalance date it ranks names by a score, goes long the top fraction
(and optionally short the bottom fraction), and realises the forward return minus
costs. It always reports the same strategy against two honest baselines —
equal-weight ("buy everything") and random selection — because a strategy that
doesn't beat those after costs isn't a strategy. See ``ml-system-design.md``.

This is deliberately simple (no leverage, no position sizing, full rebalance each
period). It is a research yardstick, not an execution simulator — re-run a
survivor in an event-driven engine (Backtrader) with real fills before believing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    """Worst peak-to-trough fractional decline of an equity curve (<= 0)."""
    if len(equity) == 0:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def _stats(returns: pd.Series, periods_per_year: int) -> dict:
    returns = returns.dropna()
    if returns.empty:
        return {"n_periods": 0}
    equity = (1.0 + returns).cumprod()
    vol = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    ann_vol = vol * np.sqrt(periods_per_year)
    ann_return = float(returns.mean()) * periods_per_year
    return {
        "n_periods": int(len(returns)),
        "total_return": float(equity.iloc[-1] - 1.0),
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": float(ann_return / ann_vol) if ann_vol > 0 else 0.0,
        "max_drawdown": max_drawdown(equity),
        "hit_rate": float((returns > 0).mean()),
        "mean_period_return": float(returns.mean()),
    }


@dataclass
class BacktestResult:
    returns: pd.Series
    equity: pd.Series
    stats: dict
    baselines: dict[str, dict] = field(default_factory=dict)

    def summary(self) -> pd.DataFrame:
        """Strategy vs baselines as a tidy table."""
        rows = {"strategy": self.stats, **self.baselines}
        return pd.DataFrame(rows).T


def _select_return(group: pd.DataFrame, score: np.ndarray, k: int, fwd: np.ndarray, long_short: bool) -> float:
    order = np.argsort(score)
    longs = order[-k:]
    long_ret = float(np.mean(fwd[longs]))
    if not long_short:
        return long_ret
    shorts = order[:k]
    return long_ret - float(np.mean(fwd[shorts]))


def walk_forward_backtest(
    panel: pd.DataFrame,
    *,
    date_col: str = "date",
    score_col: str = "score",
    fwd_return_col: str = "fwd_return",
    top_frac: float = 0.2,
    long_short: bool = True,
    cost: float = 0.0,
    periods_per_year: int = 52,
    seed: int = 0,
    baselines: bool = True,
) -> BacktestResult:
    """Run the backtest. ``cost`` is a flat per-period round-trip cost in return
    units (e.g. 0.001 = 10 bps) subtracted from every period's gross return."""
    rng = np.random.default_rng(seed)
    dates = []
    strat, base_ew, base_rand = [], [], []

    for date, group in panel.groupby(date_col, sort=True):
        g = group.dropna(subset=[score_col, fwd_return_col])
        n = len(g)
        if n < 2:
            continue
        k = max(1, int(n * top_frac))
        score = g[score_col].to_numpy()
        fwd = g[fwd_return_col].to_numpy()

        dates.append(date)
        strat.append(_select_return(g, score, k, fwd, long_short) - cost)
        if baselines:
            base_ew.append(float(np.mean(fwd)))  # buy everything, no cost
            rand_score = rng.random(n)
            base_rand.append(_select_return(g, rand_score, k, fwd, long_short) - cost)

    returns = pd.Series(strat, index=pd.Index(dates, name=date_col), name="strategy")
    equity = (1.0 + returns).cumprod()
    result = BacktestResult(returns=returns, equity=equity, stats=_stats(returns, periods_per_year))
    if baselines:
        result.baselines = {
            "equal_weight": _stats(pd.Series(base_ew, index=returns.index), periods_per_year),
            "random": _stats(pd.Series(base_rand, index=returns.index), periods_per_year),
        }
    return result
