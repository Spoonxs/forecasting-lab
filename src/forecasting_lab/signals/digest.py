"""Render and file the daily signal digest.

Surfaces the top squeeze and momentum candidates as two *separate* rankings, with
the standing caveat front and center. The digest is a research artifact: pair it
with the calibration log so the record — not a hunch — tells you whether a flag
means anything.
"""

from __future__ import annotations

from datetime import date as _date
from pathlib import Path

import pandas as pd

from ..pipeline.digest import render_digest, write_dated_note

DISCLAIMER = (
    "Surfaces candidates, not buys. Most flagged tickers do nothing — treat every "
    "flag as 'look closer', never 'enter'. Not financial advice."
)


def _table(scored: pd.DataFrame, score_col: str, ticker_col: str, top: int) -> str:
    cols = [ticker_col, score_col, score_col + "_rank"]
    cols = [c for c in cols if c in scored.columns]
    head = scored.sort_values(score_col, ascending=False).head(top)[cols]
    if head.empty:
        return "_no candidates_"
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in head.iterrows():
        cells = [
            f"{row[c]:.3f}" if isinstance(row[c], float) else str(row[c]) for c in cols
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_signal_digest(
    squeeze_scored: pd.DataFrame,
    momentum_scored: pd.DataFrame,
    ticker_col: str = "ticker",
    top: int = 10,
    on: _date | None = None,
) -> str:
    """Render the digest Markdown from two scored frames."""
    sections = {
        "Squeeze candidates (GME type)": _table(squeeze_scored, "squeeze", ticker_col, top),
        "Momentum candidates (NVIDIA type)": _table(
            momentum_scored, "momentum", ticker_col, top
        ),
    }
    return render_digest(
        "Signal Monitoring Digest", sections, on=on, disclaimer=DISCLAIMER
    )


def write_signal_digest(
    squeeze_scored: pd.DataFrame,
    momentum_scored: pd.DataFrame,
    ticker_col: str = "ticker",
    top: int = 10,
    on: _date | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Build and file the digest as ``inputs/YYYY-MM-DD-signal-digest.md``."""
    body = build_signal_digest(squeeze_scored, momentum_scored, ticker_col, top, on)
    return write_dated_note("signal-digest", body, on=on, out_dir=out_dir)
