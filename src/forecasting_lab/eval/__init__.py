"""Evaluation: calibration over accuracy.

Track Brier score and log loss on a held-out, time-forward test set, and always
compare against the base-rate climatology. Accuracy is the wrong headline metric —
a model that just picks the favorite looks good because favorites win most of the
time. See ``project-forecasting-lab.md`` and ``ml-system-design.md``.
"""

from .honest_stats import (
    alpha_vs_benchmark,
    cluster_outcomes,
    format_metric,
    independent_bets,
    shrunk_win_rate,
    win_rate_zscore,
)
from .metrics import (
    brier_decomposition,
    brier_score,
    brier_skill_score,
    expected_calibration_error,
    log_loss,
    maximum_calibration_error,
    reliability_table,
    summary,
)

__all__ = [
    "brier_score",
    "log_loss",
    "brier_skill_score",
    "brier_decomposition",
    "reliability_table",
    "expected_calibration_error",
    "maximum_calibration_error",
    "summary",
    "shrunk_win_rate",
    "cluster_outcomes",
    "win_rate_zscore",
    "independent_bets",
    "alpha_vs_benchmark",
    "format_metric",
]
