"""The prediction-evidence contract (design.md §7, PLAN.md Phase 0).

Every pick the lab surfaces must carry three things: a **probability/odds**, the
**evidence** behind it (the drivers, with their values and signed push), and an
honest **caveat**. A number with no rationale — or a rationale with no number — is
a bug, enforced here: a :class:`Prediction` refuses to exist without a valid
probability and at least one driver.

These are deterministic pure functions of already-known features, so they're
leak-free by construction (no future data enters). Probabilities on the stock
side are *heuristic leans*, not yet calibrated — the caveat says so, and later
phases score them Brier-vs-market before any of it is trusted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Driver:
    """One piece of evidence: a named feature, its value, and its signed push."""

    feature: str
    value: float
    contribution: float  # signed: >0 pushes toward the call, <0 against


@dataclass(frozen=True)
class Prediction:
    """A pick with its odds and the evidence for them. Cannot exist without both."""

    probability: float
    drivers: tuple[Driver, ...]
    caveat: str
    label: str = ""
    market_implied_prob: float | None = None
    kind: str = "signal"  # "signal" (model lean) or "market" (a venue's own price)

    def __post_init__(self) -> None:
        if self.probability is None or not (0.0 <= float(self.probability) <= 1.0):
            raise ValueError(f"probability must be in [0, 1], got {self.probability!r}")
        if not self.drivers:
            raise ValueError("a prediction needs at least one driver (evidence)")

    @property
    def edge_vs_market(self) -> float | None:
        """Model probability minus the market's implied probability (None if no market)."""
        if self.market_implied_prob is None:
            return None
        return round(self.probability - self.market_implied_prob, 4)

    def pct(self) -> str:
        return f"{round(self.probability * 100)}%"

    def american_odds(self) -> str:
        """Fair American odds from the probability (context, not a price)."""
        p = min(max(self.probability, 1e-6), 1 - 1e-6)
        if p >= 0.5:
            return f"−{round(100 * p / (1 - p))}"  # favorite, real minus
        return f"+{round(100 * (1 - p) / p)}"


def logistic(x: float, k: float = 0.6) -> float:
    """Squash a signed score into (0, 1)."""
    return 1.0 / (1.0 + math.exp(-k * x))


def mover_prediction(card: dict) -> Prediction:
    """A heuristic continuation lean for a trending stock, with its drivers."""
    score = float(card.get("momentum", 0.0) or 0.0)
    p = logistic(score)
    drivers: list[Driver] = []
    if card.get("ret_60d") is not None:
        v = float(card["ret_60d"])
        drivers.append(Driver("60-day trend", v, v))
    if card.get("ret_5d") is not None:
        v = float(card["ret_5d"])
        drivers.append(Driver("5-day move", v, v))
    if card.get("pct_from_high") is not None:
        v = float(card["pct_from_high"])
        drivers.append(Driver("distance from high", v, -abs(v)))
    if card.get("volume_spike") is not None:
        v = float(card["volume_spike"])
        drivers.append(Driver("volume vs 20-day", v, v - 1.0))
    accel = card.get("attention_accel")
    if accel is not None and abs(float(accel)) > 1e-9:
        drivers.append(Driver("attention acceleration (z)", float(accel), float(accel)))
    drivers.append(Driver("trend composite (z)", score, score))
    return Prediction(
        probability=p,
        drivers=tuple(drivers),
        caveat="Heuristic continuation lean from the trend composite — not yet calibrated. "
               "A research signal to look closer, not advice.",
        label=f"{card.get('ticker', '')} keeps trending up",
        kind="signal",
    )


def market_prediction(event: str, yes: float, venue: str, *, gap: float | None = None,
                      similarity: float | None = None, fair_value: float | None = None) -> Prediction:
    """A prediction-market pick. Odds = the venue's live YES price, unless a
    recalibrated ``fair_value`` is supplied (favorite-longshot correction), in which
    case the pick's probability is the fair value and the edge vs. the market shows."""
    yes = min(max(float(yes), 0.0), 1.0)
    model_p = min(max(float(fair_value), 0.0), 1.0) if fair_value is not None else yes
    drivers = [
        Driver(f"{venue} live YES price", yes, 0.0),
        Driver("among the most-traded (liquidity)", 1.0, 0.0),
    ]
    if gap is not None:
        drivers.append(Driver("cross-venue price gap", float(gap), float(gap)))
    caveat = ("This is the market's own price; the lab has no independent model for this "
              "question yet, so there is no claimed edge.")
    if fair_value is not None:
        caveat = ("Fair value applies a default favorite-longshot correction to the market "
                  "price; it is replaced by a fit on your resolved markets as they accrue.")
    return Prediction(
        probability=model_p,
        drivers=tuple(drivers),
        caveat=caveat,
        label=event,
        market_implied_prob=yes,
        kind="market",
    )
