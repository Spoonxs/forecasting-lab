import pytest

from forecasting_lab.macro.nowcast import recession_probability
from forecasting_lab.sports.soccer import (
    SoccerElo,
    evaluate_rps,
    match_probs,
    ranked_probability_score,
    synthetic_league,
)


# ---- soccer ------------------------------------------------------------
def test_match_probs_sum_to_one_and_favor_home():
    p = match_probs(1600, 1500, home_adv=60, nu=1.05)
    assert abs(sum(p) - 1.0) < 1e-12
    assert p[0] > p[2]  # stronger + home advantage -> home most likely
    even = match_probs(1500, 1500, home_adv=0, nu=1.05)
    assert even[0] == pytest.approx(even[2])  # symmetric on neutral even match


def test_rps_rewards_sharp_correct_forecasts():
    # confident-correct beats uniform beats confident-wrong
    sharp_right = ranked_probability_score([0.8, 0.15, 0.05], 0)
    uniform = ranked_probability_score([1 / 3, 1 / 3, 1 / 3], 0)
    sharp_wrong = ranked_probability_score([0.05, 0.15, 0.8], 0)
    assert sharp_right < uniform < sharp_wrong


def test_draw_parameter_controls_draw_probability():
    low = match_probs(1500, 1500, 0, nu=0.3)[1]
    high = match_probs(1500, 1500, 0, nu=1.5)[1]
    assert high > low


def test_fit_beats_baseline_with_realistic_rates():
    league = synthetic_league(n_teams=20, n_seasons=3, seed=1)
    preds = SoccerElo().fit(league)
    ev = preds[preds["min_games"] >= 10]
    r = evaluate_rps(ev)
    assert r["rps"] < r["rps_baseline"]
    assert r["rps_skill"] > 0.05
    # league-realistic outcome mix
    assert 0.40 < r["base_rates"]["home"] < 0.50
    assert 0.18 < r["base_rates"]["draw"] < 0.30


# ---- macro -------------------------------------------------------------
def test_recession_probability_monotonic_and_bounded():
    # inverted curve -> higher odds than a steep positive curve
    inverted = recession_probability(-1.0)
    flat = recession_probability(0.0)
    steep = recession_probability(2.5)
    assert inverted > flat > steep
    assert 0.0 < steep < inverted < 1.0


def test_recession_probability_reasonable_levels():
    # a flat curve (spread 0) sits near the model's ~30% base
    assert 0.25 < recession_probability(0.0) < 0.35
    # deep inversion is alarming but still a probability
    assert recession_probability(-1.5) > 0.6
