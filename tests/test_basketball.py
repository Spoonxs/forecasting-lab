import numpy as np
import pytest

from forecasting_lab.eval import brier_score, summary
from forecasting_lab.sports.basketball import BasketballElo, synthetic_season


def test_home_advantage_shifts_probability():
    m = BasketballElo()
    # equal teams: home team should be favored by the home bonus
    p_home = m.predict_proba("A", "B")
    assert p_home > 0.5
    assert abs(m.predict_proba("A", "B", neutral=True) - 0.5) < 1e-12


def test_update_zero_sum_and_direction():
    m = BasketballElo()
    m.update("A", "B", 110, 100)
    assert m.rating("A") > 1500 > m.rating("B")
    assert abs((m.rating("A") - 1500) + (m.rating("B") - 1500)) < 1e-9


def test_blowout_moves_more_than_squeaker():
    m1, m2 = BasketballElo(), BasketballElo()
    m1.update("A", "B", 101, 100)  # 1-point win
    m2.update("A", "B", 130, 100)  # 30-point blowout
    assert (m2.rating("A") - 1500) > (m1.rating("A") - 1500)


def test_mov_multiplier_dampens_favorite_blowouts():
    m = BasketballElo()
    # same margin, but a heavy favorite winning big is less informative
    underdog_mult = m._mov_multiplier(20, -200.0)
    favorite_mult = m._mov_multiplier(20, +200.0)
    assert underdog_mult > favorite_mult


def test_ties_rejected():
    m = BasketballElo()
    with pytest.raises(ValueError):
        m.update("A", "B", 100, 100)


def test_season_reversion_pulls_toward_mean():
    m = BasketballElo(season_reversion=0.25)
    m.ratings["A"] = 1700.0
    m.new_season()
    assert m.rating("A") == pytest.approx(1650.0)


def test_fit_beats_home_base_rate_and_is_calibrated():
    games = synthetic_season(n_teams=30, n_games=3000, n_seasons=2, seed=4)
    m = BasketballElo()
    preds = m.fit(games)
    ev = preds[preds["min_games"] >= 15]
    y, p = ev["y"].to_numpy(), ev["p_home"].to_numpy()
    s = summary(y, p)
    # the honest baseline is "always predict the home base rate", ~60%
    base = brier_score(y, np.full_like(p, y.mean()))
    assert 0.52 < y.mean() < 0.68  # sanity: home advantage exists in the data
    assert s["brier"] < base
    assert s["brier_skill_score"] > 0.05
    assert s["ece"] < 0.06  # calibrated, not just discriminative
