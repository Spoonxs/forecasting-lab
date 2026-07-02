"""Cross-sectional ML: the methodology is the moat, not the data volume.

Start with a cross-sectional ranking target (forward relative return over horizon
H), normalise features within each date, validate with purged/embargoed
walk-forward CV, and judge on calibration — not accuracy. See ``ml-system-design.md``.
"""

from .cv import PurgedWalkForwardCV
from .features import cross_sectional_rank, cross_sectional_zscore, lag_features
from .labels import forward_return, triple_barrier
from .ranker import CrossSectionalRanker

__all__ = [
    "PurgedWalkForwardCV",
    "cross_sectional_rank",
    "cross_sectional_zscore",
    "lag_features",
    "forward_return",
    "triple_barrier",
    "CrossSectionalRanker",
]
