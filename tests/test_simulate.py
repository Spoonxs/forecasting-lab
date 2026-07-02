import pytest

from forecasting_lab.sports.elo import EloModel
from forecasting_lab.sports.simulate import rounds_in_bracket, simulate_tournament


def _model(ratings):
    m = EloModel(surface_weight=0.0)
    m.global_ratings.update(ratings)
    return m


def test_title_probs_form_distribution():
    m = _model({"A": 1800, "B": 1600, "C": 1500, "D": 1400})
    sim = simulate_tournament(m, ["A", "B", "C", "D"], n_sims=20000, seed=0)
    assert abs(sim["p_title"].sum() - 1.0) < 1e-9
    assert (sim["p_title"] >= 0).all()
    # strongest player is the most likely champion
    assert sim["p_title"].idxmax() == "A"
    # reaching the final is at least as likely as winning it
    assert (sim["p_final"] >= sim["p_title"] - 1e-9).all()


def test_equal_ratings_uniform_title():
    m = _model({p: 1500 for p in ["A", "B", "C", "D"]})
    sim = simulate_tournament(m, ["A", "B", "C", "D"], n_sims=40000, seed=1)
    assert sim["p_title"].max() < 0.30  # ~0.25 each, within sampling noise


def test_bracket_size_validation():
    m = _model({"A": 1500, "B": 1500, "C": 1500})
    with pytest.raises(ValueError):
        simulate_tournament(m, ["A", "B", "C"], n_sims=10)  # not a power of two
    with pytest.raises(ValueError):
        simulate_tournament(m, ["A", "A", "B", "C"], n_sims=10)  # duplicate


def test_rounds_in_bracket():
    assert rounds_in_bracket(8) == 3
    assert rounds_in_bracket(128) == 7
