"""Arena strategies.

A strategy is a callable object: given price history *up to and including* the
current bar, return target portfolio weights (long-only here, summing to <= 1;
the remainder sits in cash). The engine applies those weights to the **next**
bar's returns — the interface makes look-ahead structurally impossible, because
the next bar simply isn't in the frame a strategy receives.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd


class Strategy(Protocol):
    name: str

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        """Weights to hold over the NEXT bar. ``prices`` ends at the current bar."""
        ...


def _top_k_equal(scores: pd.Series, k: int) -> dict[str, float]:
    picks = scores.nlargest(k).index
    return {name: 1.0 / k for name in picks}


class Momentum:
    """Long the top-k assets by trailing ``lookback``-bar return."""

    kind = "trend"
    blurb = "Buy what's been rising. Holds the {k} strongest names over the last {lookback} bars — rides trends, gives back gains at turns."

    def __init__(self, lookback: int = 60, k: int = 3):
        self.lookback, self.k = lookback, k
        self.name = f"momentum_{lookback}d"
        self.description = self.blurb.format(k=k, lookback=lookback)

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        if len(prices) <= self.lookback:
            return {}
        ret = prices.iloc[-1] / prices.iloc[-self.lookback - 1] - 1.0
        return _top_k_equal(ret, self.k)


class MeanReversion:
    """Long the k biggest short-term losers (betting on a bounce)."""

    kind = "contrarian"
    blurb = "Buy what just fell. Holds the {k} biggest {lookback}-bar losers, betting on a bounce — churns hard, so costs bite."

    def __init__(self, lookback: int = 5, k: int = 3):
        self.lookback, self.k = lookback, k
        self.name = f"meanrev_{lookback}d"
        self.description = self.blurb.format(k=k, lookback=lookback)

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        if len(prices) <= self.lookback:
            return {}
        ret = prices.iloc[-1] / prices.iloc[-self.lookback - 1] - 1.0
        return _top_k_equal(-ret, self.k)


class Breakout:
    """Long assets at/near their trailing high — trend continuation."""

    kind = "trend"
    blurb = "Buy new highs. Holds names within {tol:.0%} of their {window}-bar high — a classic breakout rule, cousin of momentum."

    def __init__(self, window: int = 120, tolerance: float = 0.02, k: int = 3):
        self.window, self.tolerance, self.k = window, tolerance, k
        self.name = f"breakout_{window}d"
        self.description = self.blurb.format(tol=tolerance, window=window)

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        if len(prices) <= self.window:
            return {}
        recent = prices.iloc[-self.window:]
        closeness = prices.iloc[-1] / recent.max() - 1.0  # 0 = at the high
        near = closeness[closeness >= -self.tolerance]
        if near.empty:
            return {}
        picks = near.nlargest(min(self.k, len(near))).index
        return {name: 1.0 / len(picks) for name in picks}


class VolTarget:
    """Inverse-volatility weights across all assets (risk-parity-lite)."""

    kind = "risk"
    blurb = "Own everything, calm names bigger. Weights inversely to {lookback}-bar volatility — smooths the ride, doesn't pick winners."

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.name = f"voltarget_{lookback}d"
        self.description = self.blurb.format(lookback=lookback)

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        if len(prices) <= self.lookback + 1:
            return {}
        rets = prices.iloc[-self.lookback - 1:].pct_change().dropna()
        vol = rets.std()
        inv = 1.0 / vol.replace(0, np.nan)
        inv = inv.dropna()
        if inv.empty:
            return {}
        weights = inv / inv.sum()
        return weights.to_dict()


class BuyHold:
    """Equal-weight everything, always. The honest do-nothing baseline."""

    name = "buy_hold"
    kind = "baseline"
    description = "Own the whole market, equal-weight, never trade. The bar every strategy must clear after costs."

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        n = prices.shape[1]
        return {name: 1.0 / n for name in prices.columns}


class RandomPicks:
    """Random k assets each bar, seeded by bar index — deterministic across
    resumes (the same bar always draws the same picks)."""

    kind = "baseline"
    description = "Pick names by coin flip. The null hypothesis — if a strategy can't beat this, it has no skill."

    def __init__(self, k: int = 3, seed: int = 0):
        self.k, self.seed = k, seed
        self.name = "random"

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        rng = np.random.default_rng(self.seed + bar)
        cols = list(prices.columns)
        picks = rng.choice(cols, size=min(self.k, len(cols)), replace=False)
        return {name: 1.0 / len(picks) for name in picks}


def default_strategies() -> list:
    """The standard arena lineup: four ideas + two baselines."""
    return [
        Momentum(60, 3),
        MeanReversion(5, 3),
        Breakout(120, 0.02, 3),
        VolTarget(20),
        BuyHold(),
        RandomPicks(3),
    ]


ALL_STRATEGIES = {s.name: s for s in default_strategies()}
