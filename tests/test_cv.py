import numpy as np
import pytest

from forecasting_lab.ml import PurgedWalkForwardCV


def test_purge_gap_and_disjoint():
    times = np.repeat(np.arange(60), 3)  # 60 periods, 3 names each (a panel)
    cv = PurgedWalkForwardCV(n_splits=5, horizon=4)
    folds = list(cv.split(times))
    assert len(folds) >= 4
    for train_idx, test_idx in folds:
        tr, te = times[train_idx], times[test_idx]
        # train strictly before test, with a purge gap of at least `horizon`
        assert tr.max() <= te.min() - 4 - 1
        # no period appears in both train and test
        assert set(tr).isdisjoint(set(te))


def test_expanding_train_grows():
    times = np.arange(50)
    cv = PurgedWalkForwardCV(n_splits=5, horizon=1, expanding=True)
    sizes = [len(tr) for tr, _ in cv.split(times)]
    assert sizes == sorted(sizes)  # monotonically non-decreasing training sets


def test_embargo_excludes_post_test_in_rolling():
    times = np.arange(60)
    cv = PurgedWalkForwardCV(n_splits=5, horizon=2, embargo=3, expanding=False)
    for train_idx, test_idx in cv.split(times):
        tr, te = times[train_idx], times[test_idx]
        post = tr[tr > te.max()]
        if post.size:  # any post-test training points respect the embargo + purge
            assert post.min() > te.max() + 3 + 2


def test_requires_enough_periods():
    cv = PurgedWalkForwardCV(n_splits=5)
    with pytest.raises(ValueError):
        list(cv.split(np.arange(3)))
