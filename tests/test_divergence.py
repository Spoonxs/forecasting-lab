import pandas as pd

from forecasting_lab.markets.divergence import find_divergences, score_divergence


def test_score_divergence_direction_and_net():
    # Kalshi underprices YES (0.40 vs 0.46) -> buy on Kalshi; gross 0.06, fee 0.02 -> net 0.04
    d = score_divergence("evt", kalshi_yes=0.40, poly_yes=0.46)
    assert d.direction == "buy_kalshi"
    assert abs(d.gross_edge - 0.06) < 1e-9
    assert abs(d.net_edge - (0.06 - d.fee)) < 1e-9
    assert d.flagged

    d2 = score_divergence("evt", kalshi_yes=0.60, poly_yes=0.50)
    assert d2.direction == "buy_poly"


def test_find_divergences_filters_subfee_gaps():
    matched = pd.DataFrame(
        {
            "event": ["A", "B", "C"],
            "kalshi_yes": [0.40, 0.50, 0.61],
            "poly_yes": [0.46, 0.505, 0.60],  # B,C gaps are below the ~2c fee
        }
    )
    flags = find_divergences(matched, threshold=0.0)
    assert list(flags["event"]) == ["A"]
    assert (flags["net_edge"] > 0).all()


def test_find_divergences_sorted_desc():
    matched = pd.DataFrame(
        {
            "event": ["small", "big"],
            "kalshi_yes": [0.40, 0.20],
            "poly_yes": [0.45, 0.45],  # big gap second
        }
    )
    flags = find_divergences(matched, threshold=0.0)
    assert list(flags["event"]) == ["big", "small"]
