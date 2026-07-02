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


class MLRanker:
    """A learned strategy: a gradient-boosted ranker, retrained walk-forward.

    Each retrain builds a leak-free panel from the price history it can see
    (momentum, short reversal, volatility, distance-from-high per name), labels it
    with the *forward relative* return, self-tunes its hyper-parameters once by
    out-of-sample rank IC (purged walk-forward), then longs the top-k names its
    model predicts will outperform next. The only learner in the field — every
    other strategy is a fixed rule, so this is the head-to-head test of whether
    ML earns its keep after costs.
    """

    kind = "ml"
    name = "ml_ranker"
    description = (
        "A machine-learning model (gradient-boosted trees) retrained as it goes on "
        "price features - trend, reversal, volatility, distance from highs - and tuned "
        "by leak-free walk-forward validation. Longs the names it predicts will lead."
    )

    _FEATURES = ("m20", "m60", "rev5", "vol20", "dist_high")

    def __init__(self, k: int = 3, horizon: int = 10, retrain: int = 25,
                 warmup: int = 200, params: dict | None = None):
        self.k, self.horizon, self.retrain, self.warmup = k, horizon, retrain, warmup
        self.params = params
        self._model = None
        self._last_fit = -10 ** 9
        self._tuned = False

    def _feature_frames(self, close: pd.DataFrame) -> dict[str, pd.DataFrame]:
        rets = close.pct_change()
        return {
            "m20": close / close.shift(20) - 1.0,
            "m60": close / close.shift(60) - 1.0,
            "rev5": -(close / close.shift(5) - 1.0),
            "vol20": rets.rolling(20).std(),
            "dist_high": close / close.rolling(120, min_periods=60).max() - 1.0,
        }

    def _panel(self, close: pd.DataFrame) -> pd.DataFrame:
        """Long panel of features + forward-relative-return label, leak-free."""
        from functools import reduce

        feats = self._feature_frames(close)
        fwd = close.shift(-self.horizon) / close - 1.0
        fwd_rel = fwd.sub(fwd.mean(axis=1), axis=0)

        def melt(wide: pd.DataFrame, name: str) -> pd.DataFrame:
            return (
                wide.reset_index(names="period")
                .melt(id_vars="period", var_name="ticker", value_name=name)
            )

        frames = [melt(w, name) for name, w in feats.items()]
        frames.append(melt(fwd_rel, "label"))
        return reduce(lambda a, b: a.merge(b, on=["period", "ticker"]), frames)

    def _refit(self, close: pd.DataFrame, bar: int) -> None:
        from ..ml.ranker import CrossSectionalRanker

        panel = self._panel(close)
        cols = list(self._FEATURES)
        train = panel.dropna(subset=cols + ["label"])
        if len(train) < 200 or train["period"].nunique() < 6:
            self._model = None
            return
        if self.params is None and not self._tuned:
            # one-time self-tune on the leak-free panel it can currently see
            from ..ml.tune import tune_ranker

            try:
                self.params, _ = tune_ranker(train, cols, "label")
            except (ValueError, ZeroDivisionError):
                self.params = {}
            self._tuned = True
        self._model = CrossSectionalRanker(**(self.params or {})).fit(train[cols], train["label"])
        self._last_fit = bar

    def target_weights(self, prices: pd.DataFrame, bar: int) -> dict[str, float]:
        if len(prices) < self.warmup:
            return {}
        close = prices.astype(float)
        if self._model is None or bar - self._last_fit >= self.retrain:
            self._refit(close, bar)
        if self._model is None:
            return {}
        feats = self._feature_frames(close)
        current = pd.DataFrame({name: w.iloc[-1] for name, w in feats.items()})
        current = current.dropna()
        if current.empty:
            return {}
        scores = pd.Series(self._model.predict(current[list(self._FEATURES)]), index=current.index)
        picks = scores.nlargest(min(self.k, len(scores))).index
        return {name: 1.0 / len(picks) for name in picks}


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
    """The standard arena lineup: four rule ideas + one ML learner + two baselines."""
    return [
        Momentum(60, 3),
        MeanReversion(5, 3),
        Breakout(120, 0.02, 3),
        VolTarget(20),
        MLRanker(k=3),
        BuyHold(),
        RandomPicks(3),
    ]


ALL_STRATEGIES = {s.name: s for s in default_strategies()}
