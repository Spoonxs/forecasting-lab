"""Yield-curve recession probability + a macro snapshot.

``recession_probability(spread)`` maps the 10Y-3M term spread (percentage points)
to a 12-month-ahead recession probability via a probit, following the
Estrella-Mishkin / NY Fed model form:

    P(recession) = Phi(a + b * spread),  with a > 0, b < 0

so an inverted curve (negative spread) pushes the probability up. Coefficients
are the commonly-cited fitted values (a≈-0.533 on the NY Fed's sign convention);
we expose them so they can be refit. This is a *pure* function — no network — so
it is fully testable; :func:`macro_snapshot` is the live FRED wrapper.
"""

from __future__ import annotations

import math

# NY Fed / Estrella-Mishkin style probit on the 10Y-3M spread (points).
# P = Phi(INTERCEPT + SLOPE * spread); SLOPE < 0 so inversion raises the odds.
INTERCEPT = -0.533
SLOPE = -0.635


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def recession_probability(spread_points: float, intercept: float = INTERCEPT, slope: float = SLOPE) -> float:
    """12-month recession probability from the 10Y-3M spread (in percentage points)."""
    return _normal_cdf(intercept + slope * spread_points)


def macro_snapshot() -> dict:
    """Live macro read from FRED: term spread + recession odds + key levels."""
    from ..sources import fred

    def _latest(sid):
        got = fred.latest(sid)
        return got if got else (None, None)

    spread_date, spread = _latest("T10Y3M")
    snapshot = {
        "term_spread": {"value": spread, "date": spread_date, "series": "T10Y3M"},
        "recession_prob_12m": recession_probability(spread) if spread is not None else None,
        "levels": {},
    }
    for sid, label in [
        ("DGS10", "10Y yield"),
        ("DGS3MO", "3M yield"),
        ("UNRATE", "Unemployment %"),
        ("FEDFUNDS", "Fed funds %"),
        ("VIXCLS", "VIX"),
    ]:
        date, value = _latest(sid)
        snapshot["levels"][label] = {"value": value, "date": date, "series": sid}
    return snapshot
