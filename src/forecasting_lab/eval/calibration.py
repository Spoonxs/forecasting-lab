"""Calibration curves and plotting.

A reliability diagram is the single most credible artifact in the lab: it shows
whether "30%" really happens 30% of the time. Plotting requires matplotlib;
:func:`calibration_curve_data` is pure numpy and always available.
"""

from __future__ import annotations

import numpy as np

from .metrics import expected_calibration_error, reliability_table


def calibration_curve_data(y_true, y_prob, n_bins: int = 10):
    """Return ``(mean_pred, frac_pos, counts)`` for non-empty bins, for plotting."""
    table = reliability_table(y_true, y_prob, n_bins=n_bins)
    table = table[table["count"] > 0]
    return (
        table["mean_pred"].to_numpy(),
        table["frac_pos"].to_numpy(),
        table["count"].to_numpy(),
    )


def plot_calibration(y_true, y_prob, n_bins: int = 10, title: str | None = None, save_path=None):
    """Draw a reliability diagram with a prediction histogram underneath.

    Returns the matplotlib Figure. Raises ImportError with a clear message if
    matplotlib is not installed (it is an optional ``[viz]`` extra).
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError("plotting needs matplotlib: pip install 'forecasting-lab[viz]'") from exc

    mean_pred, frac_pos, counts = calibration_curve_data(y_true, y_prob, n_bins=n_bins)
    ece = expected_calibration_error(y_true, y_prob, n_bins=n_bins)

    fig, (ax, axh) = plt.subplots(
        2, 1, figsize=(6, 7), height_ratios=[3, 1], constrained_layout=True
    )
    ax.plot([0, 1], [0, 1], "--", color="grey", label="perfect")
    ax.plot(mean_pred, frac_pos, "o-", label="model")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed frequency")
    ax.set_title(title or f"Reliability diagram (ECE={ece:.3f})")
    ax.legend(loc="upper left")

    axh.hist(np.clip(np.asarray(y_prob, dtype=float), 0, 1), bins=n_bins, range=(0, 1))
    axh.set_xlim(0, 1)
    axh.set_xlabel("predicted probability")
    axh.set_ylabel("count")

    if save_path is not None:
        fig.savefig(save_path, dpi=120)
    return fig
