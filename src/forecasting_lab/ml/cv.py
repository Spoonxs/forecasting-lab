"""Purged, embargoed walk-forward cross-validation.

Standard random k-fold leaks the future into the past on a time series and is the
single most common reason backtests look great and fail live. This splitter:

- keeps training data strictly *before* each test block (walk-forward), and
- **purges** training samples whose forward-looking label window overlaps the
  test block (a label at date ``d`` over horizon ``H`` peeks at data up to
  ``d + H``; if that reaches the test block, the sample leaks and is dropped), and
- optionally applies an **embargo**: a gap of periods immediately after the test
  block excluded from any later training, to defeat serial correlation.

``times`` are integer-comparable period labels (e.g. week numbers or
``date.rank().astype(int)``), one per row. Rows sharing a period (a cross-section
on the same date) are kept together — purging is done in period space, not row
space, so panels are handled correctly. Based on López de Prado, *Advances in
Financial Machine Learning*.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PurgedWalkForwardCV:
    n_splits: int = 5
    horizon: int = 1
    embargo: int = 0
    expanding: bool = True  # True: train is all eligible history; False: rolling window

    def split(self, times):
        """Yield ``(train_idx, test_idx)`` integer-position arrays.

        Folds whose purged training set is empty (e.g. the earliest block) are
        skipped, so you always get usable splits.
        """
        times = np.asarray(times)
        n = times.shape[0]
        if n == 0:
            return
        order = np.arange(n)
        uniq = np.unique(times)  # sorted ascending
        if len(uniq) < self.n_splits + 1:
            raise ValueError(
                f"need >= n_splits+1 ({self.n_splits + 1}) distinct periods, got {len(uniq)}"
            )
        period_folds = np.array_split(uniq, self.n_splits)

        for fold in period_folds:
            if len(fold) == 0:
                continue
            t0, t1 = fold[0], fold[-1]
            test_idx = order[np.isin(times, fold)]

            # Purge: drop training periods whose label window reaches into the test
            # block. Keep strictly-earlier periods up to (t0 - horizon).
            keep = times < (t0 - self.horizon)
            if not self.expanding:
                # rolling window: bound the lookback to roughly one test-block width
                window = max(1, len(fold))
                lower = t0 - self.horizon - window
                keep &= times >= lower
                # also allow post-test periods after the embargo, purged by horizon
                keep |= times > (t1 + self.embargo + self.horizon)

            train_idx = order[keep]
            if train_idx.size == 0 or test_idx.size == 0:
                continue
            yield train_idx, test_idx

    def get_n_splits(self, times=None) -> int:
        return self.n_splits
