import numpy as np
import pandas as pd

from forecasting_lab.signals import (
    build_signal_digest,
    flag_candidates,
    momentum_composite,
    squeeze_composite,
)
from forecasting_lab.signals.composites import composite_score


def test_composite_orders_by_weighted_z():
    df = pd.DataFrame({"ticker": ["A", "B", "C"], "f1": [1.0, 2.0, 3.0], "f2": [3.0, 2.0, 1.0]})
    out = composite_score(df, {"f1": 1.0, "f2": 1.0})
    # f2 is f1 reversed, so equal-weighted z(f1)+z(f2) cancels -> all composites ~0
    assert out["composite"].std() < 1e-9
    # weight only f1 and the highest-f1 name (C) ranks first
    out2 = composite_score(df, {"f1": 1.0})
    assert out2.iloc[0]["ticker"] == "C"


def test_missing_feature_is_neutral_not_error():
    df = pd.DataFrame({"ticker": ["A", "B"], "f1": [1.0, 2.0]})
    out = composite_score(df, {"f1": 1.0, "absent": 5.0})  # absent ignored
    assert "composite" in out.columns


def test_flag_candidates_top_decile():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"ticker": [f"T{i}" for i in range(50)], "short_pct_float": rng.uniform(0, 40, 50)})
    sq = squeeze_composite(df)
    flagged = flag_candidates(sq, "squeeze", threshold=0.9)
    assert 1 <= len(flagged) <= 7  # ~top decile of 50


def test_digest_has_disclaimer_and_sections():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "short_pct_float": [10, 20, 30],
            "rel_strength": [30, 60, 90],
        }
    )
    digest = build_signal_digest(squeeze_composite(df), momentum_composite(df), top=3)
    assert "Not financial advice" in digest
    assert "Squeeze candidates" in digest and "Momentum candidates" in digest
