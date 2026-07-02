import numpy as np

from forecasting_lab.eval import brier_score, summary
from forecasting_lab.sports.elo import EloModel, expected_score
from forecasting_lab.sports.tennis_data import synthetic_matches


def test_expected_score_symmetry_and_monotonic():
    assert abs(expected_score(1500, 1500) - 0.5) < 1e-12
    assert abs(expected_score(1600, 1500) + expected_score(1500, 1600) - 1.0) < 1e-12
    assert expected_score(1700, 1500) > expected_score(1600, 1500) > 0.5


def test_update_is_zero_sum_with_equal_k():
    m = EloModel(k_factor=32, surface_weight=0.0)
    m.global_ratings["A"] = 1600
    m.global_ratings["B"] = 1500
    before = m.rating("A") + m.rating("B")
    m.update("A", "B")
    after = m.rating("A") + m.rating("B")
    assert abs(before - after) < 1e-9  # equal K -> conserved total
    assert m.rating("A") > 1600 and m.rating("B") < 1500  # winner up, loser down


def test_favorite_winning_moves_little():
    # huge favorite beating a huge underdog should barely change ratings
    m = EloModel(k_factor=32, surface_weight=0.0)
    m.global_ratings["Fav"] = 2000
    m.global_ratings["Dog"] = 1200
    m.update("Fav", "Dog")
    assert m.rating("Fav") - 2000 < 1.0  # tiny gain
    # and an upset moves them a lot
    m2 = EloModel(k_factor=32, surface_weight=0.0)
    m2.global_ratings["Fav"] = 2000
    m2.global_ratings["Dog"] = 1200
    m2.update("Dog", "Fav")  # upset
    assert m2.rating("Dog") - 1200 > 25  # big gain


def test_fit_beats_base_rate_and_is_calibrated():
    matches = synthetic_matches(n_players=64, n_matches=6000, seed=3)
    elo = EloModel(surface_weight=0.5)
    preds = elo.fit(matches)
    ev = preds[preds["min_matches"] >= 10]
    y, p = ev["y"].to_numpy(), ev["p_a"].to_numpy()
    s = summary(y, p)
    base = brier_score(y, np.full_like(p, y.mean()))
    assert s["brier"] < base  # skill over climatology
    assert s["brier_skill_score"] > 0.1
    assert s["ece"] < 0.06  # well calibrated (the loser-update bug regression guard)


def test_labels_are_balanced_not_degenerate():
    # canonical A/B ordering must make y non-trivial, not all-ones
    matches = synthetic_matches(n_players=32, n_matches=2000, seed=1)
    preds = EloModel().fit(matches)
    assert 0.4 < preds["y"].mean() < 0.6


def test_surface_weight_zero_ignores_surface():
    m = EloModel(surface_weight=0.0)
    m.global_ratings["A"], m.global_ratings["B"] = 1600, 1500
    m.surface_ratings["Clay"]["A"] = 2000  # should be ignored at weight 0
    p_no_surface = m.predict_proba("A", "B", surface=None)
    p_clay = m.predict_proba("A", "B", surface="Clay")
    assert abs(p_no_surface - p_clay) < 1e-12
