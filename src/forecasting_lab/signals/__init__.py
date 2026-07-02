"""Alt-data signal layer: the watchlist scanner.

Two phenomena, two separate composites (the data for one barely informs the other):
- Squeeze / meme (GME type): short interest, social velocity, options/gamma.
- Secular momentum (NVIDIA type): earnings acceleration, analyst revisions, RS.

It surfaces *candidates*, not buys. Most flags do nothing. See
``signal-monitoring.md``. Not financial advice.
"""

from .composites import flag_candidates, momentum_composite, squeeze_composite
from .digest import build_signal_digest, write_signal_digest

__all__ = [
    "squeeze_composite",
    "momentum_composite",
    "flag_candidates",
    "build_signal_digest",
    "write_signal_digest",
]

# Default composite weights (sign = direction that raises the score).
SQUEEZE_WEIGHTS = {
    "short_pct_float": 1.0,
    "days_to_cover": 1.0,
    "social_velocity_z": 1.0,
    "volume_spike": 0.75,
    "call_put_ratio": 0.5,
    "borrow_fee": 0.75,
}

MOMENTUM_WEIGHTS = {
    "earnings_accel": 1.0,
    "analyst_revision": 1.0,
    "rel_strength": 1.0,
    "pct_from_52w_high": 0.5,  # closer to high (less negative distance) scores higher
    "rev_growth": 0.75,
}
