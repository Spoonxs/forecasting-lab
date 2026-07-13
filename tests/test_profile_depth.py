"""P10-4 — profile depth: exact-year horizons + the honest dollar-goal math.

Pinned: the exact-year multipliers EQUAL the bucket tables at their anchor
years, interpolate monotonically between adjacent anchors for every
component, and clamp at both ends (no extrapolation past 5y+); the anchors
and the interpolation rule ship in the scoring contract. The HYSA projection
matches its closed form, degrades to the plain sum at zero yield, is None
without a yield datum (never a made-up rate), grows monotonically in years
and contributions, and its formula ships in the portfolio contract. The
portfolio page carries the Plan card with the honest wording, all inputs
browser-local.
"""

from __future__ import annotations

import pytest

from forecasting_lab.signals.portfolio import hysa_projection, portfolio_contract
from forecasting_lab.signals.verdict import (
    HORIZON_ANCHORS_YEARS,
    HORIZON_MULT,
    horizon_multipliers_for_years,
    scoring_contract,
)


def test_anchor_years_reproduce_the_bucket_tables_exactly():
    for bucket, year in HORIZON_ANCHORS_YEARS.items():
        m = horizon_multipliers_for_years(year)
        for name, v in m.items():
            assert v == pytest.approx(HORIZON_MULT[bucket].get(name, 1.0)), (bucket, name)


def test_interpolation_is_monotone_between_anchors_and_clamped():
    names = set(HORIZON_MULT["0-1y"]) | set(HORIZON_MULT["5y+"])
    for name in names:
        vals = [horizon_multipliers_for_years(y)[name]
                for y in (0.5, 1.0, 1.75, 2.5, 3.0, 5.0, 7.0, 10.0)]
        diffs = [b - a for a, b in zip(vals, vals[1:], strict=False)]
        assert all(d >= -1e-12 for d in diffs) or all(d <= 1e-12 for d in diffs), name
    # clamped: nothing extrapolates past the anchors
    assert horizon_multipliers_for_years(0.0) == horizon_multipliers_for_years(0.5)
    assert horizon_multipliers_for_years(30.0) == horizon_multipliers_for_years(10.0)
    assert horizon_multipliers_for_years(999.0) == horizon_multipliers_for_years(10.0)
    # midway between 3y and 10y sits strictly between the bucket values
    mid = horizon_multipliers_for_years(6.5)
    assert 1.0 < mid["macro"] < HORIZON_MULT["5y+"]["macro"]
    assert HORIZON_MULT["5y+"]["trend"] < mid["trend"] < 1.0


def test_contract_ships_the_anchors_and_the_rule():
    c = scoring_contract()
    assert c["horizon_anchors_years"] == HORIZON_ANCHORS_YEARS
    assert c["horizon_years_max"] == 30.0
    assert "linear between anchor years" in c["horizon_interpolation"]


def test_hysa_projection_math_and_honesty():
    # closed form: $500/mo at 5% for 10y
    fv = hysa_projection(500, 10, 5.0)
    r, n = 0.05 / 12, 120
    assert fv == pytest.approx(500 * ((1 + r) ** n - 1) / r, abs=0.01)
    assert hysa_projection(500, 10, 0.0) == pytest.approx(500 * 120)  # zero yield: the sum
    assert hysa_projection(500, 10, None) is None                     # no datum: n/a
    assert hysa_projection(0, 10, 5.0) is None and hysa_projection(500, 0, 5.0) is None
    assert hysa_projection(500, 20, 5.0) > hysa_projection(500, 10, 5.0)   # monotone years
    assert hysa_projection(900, 10, 5.0) > hysa_projection(500, 10, 5.0)   # monotone monthly
    assert "not a prediction" in portfolio_contract()["hysa_projection"]


# ------------------------------------------------ Codex code-review fixes pinned
def test_contracts_state_every_edge_case():
    """Codex findings 1+2: consumers can reproduce the edge cases from the
    contract text alone — zero-yield sum, None inputs, sparse-table 1.0."""
    proj = portfolio_contract()["hysa_projection"]
    assert "y == 0 -> FV = monthly * 12 * years" in proj
    assert "None (n/a)" in proj
    interp = scoring_contract()["horizon_interpolation"]
    assert "missing from a bucket table is implicitly 1.0" in interp


def test_mirror_rejects_negative_contributions():
    """Codex finding 3: a typed negative monthly must never show a negative FV."""
    from forecasting_lab.dashboard.portfolio_page import render_portfolio_page

    js = render_portfolio_page({"as_of": "d", "verdicts": {}},
                               hysa_yield_pct=5.0).split("<script>")[-1]
    assert "if(m<0)m=0;" in js


def test_plan_card_renders_with_honest_wording():
    from forecasting_lab.dashboard.portfolio_page import render_portfolio_page

    html = render_portfolio_page({"as_of": "2026-07-12", "verdicts": {}},
                                 hysa_yield_pct=5.0)
    assert 'id="planCard"' in html and 'id="plyears"' in html
    assert "must beat that to be worth the risk" in html
    assert "not guaranteed to persist" in html and "never a prediction" in html
    js = html.split("<script>")[-1]
    assert "Math.pow(1+r,n)" in js                      # the contract's stated formula
    assert "honestly n/a (never a made-up rate)" in js  # no-datum silence
    assert "extra risk is optional" in js               # the goal-reached honesty