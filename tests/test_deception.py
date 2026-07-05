"""V7 — the Larcker-Zakolyukina deception scorer (MASTER_PLAN §3).

Properties pinned: monotone in deception markers, speaker-specific categories
(extreme positives are a CEO effect, negation a CFO effect), degenerate input
safety, OOS skill under the blocked CV on labeled synthetic narratives, the
shuffled-label null pinning ~0, and the honest caveat travelling with every
report (classification skill, NOT a return edge).
"""

from __future__ import annotations

import numpy as np

from forecasting_lab.ml.cv import PurgedWalkForwardCV
from forecasting_lab.signals.deception import (
    _Platt,
    auc,
    category_rates,
    deception_score,
    deception_skill_report,
    synthetic_narratives,
)


def test_score_is_monotone_in_deception_markers():
    base = "revenue was solid and margins were steady across the quarter"
    loaded = base + " you know everybody knows this was fantastic you know tremendous"
    assert deception_score(loaded) > deception_score(base)
    # and stacking more markers keeps pushing it up
    more = loaded + " as you know it was phenomenal and incredible you know"
    assert deception_score(more, speaker="ceo") > deception_score(loaded, speaker="ceo")


def test_speaker_specific_categories():
    extreme = "the quarter was fantastic incredible phenomenal"
    filler = "the quarter was reported in the segment column"
    # extreme positives push the CEO composite, not the CFO one
    ceo_delta = deception_score(extreme, "ceo") - deception_score(filler, "ceo")
    cfo_delta = deception_score(extreme, "cfo") - deception_score(filler, "cfo")
    assert ceo_delta > cfo_delta
    # negation is a CFO effect
    negation = "no we did not and never would"
    assert (deception_score(negation, "cfo") - deception_score(filler, "cfo")) > (
        deception_score(negation, "ceo") - deception_score(filler, "ceo")
    )


def test_degenerate_input_is_safe_and_validated():
    assert deception_score("") == 0.0
    assert all(v == 0.0 for v in category_rates("").values())
    try:
        deception_score("text", speaker="cto")
        raise AssertionError("invalid speaker must raise")
    except ValueError:
        pass


def test_signal_scores_oos_and_noise_pins_zero():
    sig = deception_skill_report(seed=0, strength=1.0)
    assert sig["oos_auc"] > 0.8
    assert sig["brier_skill_vs_base"] > 0.2
    nul = deception_skill_report(seed=0, strength=0.0)
    assert abs(nul["oos_auc"] - 0.5) < 0.12
    assert abs(nul["brier_skill_vs_base"]) < 0.05
    assert "not a return edge" in sig["caveat"].lower()


def test_shuffled_labels_pin_zero_skill():
    """The direct leakage guard: real marker-laden texts, labels torn off."""
    texts, labels = synthetic_narratives(n=240, seed=1, strength=1.0)
    rng = np.random.default_rng(9)
    shuffled = labels.copy()
    rng.shuffle(shuffled)
    scores = np.array([deception_score(t) for t in texts])
    times = np.arange(len(texts))
    cv = PurgedWalkForwardCV(n_splits=4, horizon=1)
    ys, ps = [], []
    for train_idx, test_idx in cv.split(times):
        platt = _Platt().fit(scores[train_idx], shuffled[train_idx])
        ys.append(shuffled[test_idx])
        ps.append(platt.predict(scores[test_idx]))
    y, p = np.concatenate(ys), np.concatenate(ps)
    base = float(y.mean())
    skill = 1.0 - float(np.mean((p - y) ** 2)) / float(np.mean((base - y) ** 2))
    assert abs(skill) < 0.05, f"shuffled labels manufactured skill: {skill}"


def test_auc_is_rank_based_and_handles_one_class():
    assert auc(np.array([1, 1, 0, 0]), np.array([0.9, 0.8, 0.2, 0.1])) == 1.0
    assert auc(np.array([1, 1]), np.array([0.9, 0.8])) == 0.5  # one class -> random
