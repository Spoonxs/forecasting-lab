import pandas as pd

from forecasting_lab.markets.matching import (
    match_markets,
    match_titles,
    normalize_title,
    title_similarity,
)


def test_normalize_strips_filler_keeps_criteria():
    tokens = normalize_title("Will the Fed cut rates in March 2026?")
    assert tokens == {"fed", "cut", "rates", "march", "2026"}
    # percent thresholds survive normalisation (they define the market)
    assert "60pct" in normalize_title("Turnout above 60%?")


def test_similarity_recognises_same_event_different_phrasing():
    a = "Will the Fed cut rates in March 2026?"
    b = "Fed rate cut by March 2026"
    c = "Will Trump win Pennsylvania?"
    assert title_similarity(a, b) > 0.5  # same event, different wording
    assert title_similarity(a, c) < 0.2  # unrelated
    assert title_similarity(a, a) == 1.0


def test_match_titles_is_one_to_one_and_best_first():
    left = ["Fed cuts rates in March 2026?", "Trump wins Pennsylvania?"]
    right = [
        "Will the Fed cut rates in March 2026?",
        "Fed rate cut at any 2026 meeting?",  # decoy: similar but worse
        "Trump to win Pennsylvania",
    ]
    pairs = match_titles(left, right, threshold=0.3)
    # each left title matched exactly once, to its best counterpart
    assert len(pairs) == 2
    assert pairs["left"].is_unique and pairs["right"].is_unique
    fed_row = pairs[pairs["left"].str.startswith("Fed")].iloc[0]
    assert fed_row["right"] == "Will the Fed cut rates in March 2026?"


def test_match_markets_produces_screener_table():
    kalshi = pd.DataFrame(
        {
            "title": ["Fed cuts rates in March 2026?", "CPI above 3% in June?"],
            "kalshi_yes": [0.40, 0.22],
        }
    )
    poly = pd.DataFrame(
        {
            "question": ["Will the Fed cut rates in March 2026?", "Something unrelated entirely"],
            "poly_yes": [0.46, 0.50],
        }
    )
    out = match_markets(kalshi, poly, threshold=0.4)
    assert list(out.columns) == ["event", "kalshi_yes", "poly_yes", "poly_event", "similarity"]
    assert len(out) == 1  # the unrelated market must NOT match
    assert out.iloc[0]["kalshi_yes"] == 0.40 and out.iloc[0]["poly_yes"] == 0.46


def test_duplicate_titles_do_not_crash_matching():
    # real feeds repeat titles across re-listed markets; mapping must stay unique
    kalshi = pd.DataFrame(
        {"title": ["Fed cuts rates in March 2026?"] * 2, "kalshi_yes": [0.40, 0.41]}
    )
    poly = pd.DataFrame(
        {"question": ["Will the Fed cut rates in March 2026?"] * 2, "poly_yes": [0.46, 0.47]}
    )
    out = match_markets(kalshi, poly, threshold=0.4)
    assert len(out) == 1
    assert out.iloc[0]["kalshi_yes"] == 0.40  # first occurrence wins


def test_no_matches_returns_empty_frame_with_columns():
    out = match_markets(
        pd.DataFrame({"title": ["A completely unique event"], "kalshi_yes": [0.5]}),
        pd.DataFrame({"question": ["Nothing alike whatsoever"], "poly_yes": [0.5]}),
        threshold=0.5,
    )
    assert out.empty and "kalshi_yes" in out.columns
