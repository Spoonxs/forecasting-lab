"""V1 — the Sarithis leakage/cost injection suite (MASTER_PLAN §3).

Each test encodes one bug class from the ~30-bug taxonomy a practitioner (u/Sarithis,
r/ClaudeAI 1s2lyu2) catalogued after four months of LLM-written trading code — bugs that
"could either tank the Sharpe or boost it by orders of magnitude" while the code was
called "rock solid and realistic". The pattern throughout: implement the deliberately
BUGGY variant inline, show the injection corrupts the metric (so this suite would catch
it), then pin the honest invariant on our implementation.

Two of these tests exposed real bugs in our own execution layer when first written
(immortal positions on rebalance; silent stale-price marks) — fixed in the same commit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecasting_lab.agent_trader.execution import (
    ExecutionLayer,
    Order,
    PaperBroker,
    RiskLimits,
)
from forecasting_lab.backtest import walk_forward_backtest
from forecasting_lab.backtest.costs import kalshi_taker_fee, kalshi_taker_fee_raw
from forecasting_lab.backtest.engine import max_drawdown
from forecasting_lab.ml import forward_return, lag_features
from forecasting_lab.sim.engine import Arena


def _noise_panel(seed: int = 0, periods: int = 120, names: int = 20) -> pd.DataFrame:
    """A panel whose returns are iid noise — any 'skill' on it is a bug."""
    rng = np.random.default_rng(seed)
    rows = [
        {"date": t, "ticker": i, "ret": rng.normal(0, 0.02)}
        for t in range(periods)
        for i in range(names)
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- signal timing


def test_same_bar_rank_and_trade_is_lookahead():
    """Bug: 'ranked instruments using today's price then traded at today's price'.

    Scoring a bar by the very return you then realise manufactures a monster Sharpe
    on pure noise; the honest pipeline (score known BEFORE the return) shows ~none.
    """
    panel = _noise_panel(seed=1)
    buggy = panel.assign(score=panel["ret"], fwd_return=panel["ret"])
    honest = lag_features(panel.assign(score=panel["ret"]), "score",
                          entity_col="ticker", date_col="date")
    honest = honest.assign(fwd_return=honest["ret"]).dropna(subset=["score"])

    sharpe_buggy = walk_forward_backtest(buggy, long_short=True).stats["sharpe"]
    sharpe_honest = walk_forward_backtest(honest, long_short=True).stats["sharpe"]
    assert sharpe_buggy > 3.0, "injection failed to manufacture fake skill"
    assert abs(sharpe_honest) < 1.5, f"lagged scoring shows phantom skill: {sharpe_honest}"


def test_regime_filter_must_not_use_current_day():
    """Bug: 'regime filter used current-day data to decide whether to trade today'."""
    rng = np.random.default_rng(2)
    market = pd.Series(rng.normal(0, 0.01, 4000))
    buggy = market[market > 0]                # decides with today's return -> only up days
    honest = market[market.shift(1) > 0]      # decides with yesterday's -> no information
    assert buggy.mean() > 0.005, "injection failed"
    assert abs(honest.mean()) < 0.001, f"lagged regime should carry ~no edge: {honest.mean()}"


def test_returns_paired_by_date_not_list_position():
    """Bug: 'paired returns by position in a list instead of matching dates'.

    Property pinned: the backtester's result is invariant to row order — pairing
    happens by (date, score, fwd_return) columns, never by position.
    """
    panel = (
        _noise_panel(seed=3)
        .assign(score=lambda d: d["ret"].shift(20), fwd_return=lambda d: d["ret"])
        .dropna(subset=["score"])  # unique float scores: no ties to hide behind
    )
    shuffled = panel.sample(frac=1.0, random_state=7)
    a = walk_forward_backtest(panel, seed=11).stats
    b = walk_forward_backtest(shuffled, seed=11).stats
    assert abs(a["sharpe"] - b["sharpe"]) < 1e-9
    assert a["n_periods"] == b["n_periods"]


# ---------------------------------------------------------------- stale prices


def test_stale_price_marks_are_flagged_not_silent():
    """Bug: 'positions with no current data were never exited and became immortal'.

    A held symbol missing from the price feed must be *visible* at mark time —
    silently valuing it at entry hides every loss it takes from then on.
    """
    b = PaperBroker(cash=10_000.0)
    b.submit(Order("GHOST", "buy", 100, "o1"), 10.0)
    b.mark({"GHOST": 10.0})
    assert b.last_mark_missing == []
    b.mark({})  # feed drops the symbol
    assert b.last_mark_missing == ["GHOST"], "stale mark must be flagged loudly"


def test_no_immortal_positions_on_rebalance():
    """Bug (found in OUR code by this test): a held symbol absent from the target
    dict was never exited — an immortal position. Absent now means weight zero."""
    prices = {"A": 10.0, "B": 10.0}
    b = PaperBroker(cash=10_000.0)
    ex = ExecutionLayer(b, RiskLimits(), prices)
    ex.rebalance({"B": 0.2}, "run1")
    assert "B" in b.positions
    ex.rebalance({"A": 0.2}, "run2")  # B not mentioned -> must be exited, not kept
    assert "B" not in b.positions, "held position absent from targets became immortal"


def test_unexitable_position_is_loud_and_blocks_nothing_silently():
    """Bug: 'failed exits didn't block new entries, so the portfolio exceeded its
    size limit'. When an exit cannot fill (no price), the failure must be recorded
    in the result notes — never swallowed."""
    b = PaperBroker(cash=10_000.0)
    b.submit(Order("B", "buy", 50, "o0"), 10.0)
    ex = ExecutionLayer(b, RiskLimits(), prices={"A": 10.0})  # B has no price today
    r = ex.rebalance({"A": 0.2}, "run1")
    assert any("B" in n and "no price" in n for n in r.notes), r.notes
    assert "B" in b.positions  # kept (cannot fill) but visible in the notes


# ------------------------------------------------------------------- data bugs


def test_ghost_weekend_bars_from_utc_alignment():
    """Bug: 'daily bars were UTC-aligned, creating ghost trading days every Sunday'.

    First demonstrate the trap is real (a UTC resample of an exchange trading
    evening session mints weekend bars), then pin our convention: labels count
    ROWS per entity, so calendar gaps change nothing.
    """
    # the trap: Friday 23:00 New York = Saturday 03:00/04:00 UTC -> a Saturday "bar"
    ts = pd.date_range("2026-01-02 23:00", periods=5, freq="7D", tz="America/New_York")
    utc_days = ts.tz_convert("UTC").normalize()
    assert (utc_days.dayofweek >= 5).any(), "UTC alignment should mint weekend bars"

    # our convention: forward_return shifts by rows within each entity — inserting a
    # weekend calendar gap between the same rows leaves every label identical.
    prices = [100.0, 101.0, 99.0, 102.0, 103.0]
    contiguous = pd.DataFrame({
        "ticker": "A", "date": pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07",
                                               "2026-01-08", "2026-01-09"]),
        "close": prices,
    })
    gapped = contiguous.assign(date=pd.to_datetime(
        ["2026-01-08", "2026-01-09", "2026-01-12", "2026-01-13", "2026-01-14"]))  # weekend gap
    lab_a = forward_return(contiguous, horizon=1)["fwd_return"]
    lab_b = forward_return(gapped, horizon=1)["fwd_return"]
    assert np.allclose(lab_a.dropna(), lab_b.dropna())


def test_zero_is_a_value_not_missing():
    """Bug: 'zero price treated as missing due to Python truthiness (0.0 is falsy)'."""
    values = [0.012, 0.0, -0.007, 0.0]
    buggy = [v for v in values if v]  # the classic truthiness filter
    assert len(buggy) == 2, "injection failed"

    panel = pd.DataFrame({
        "date": [0, 0, 1, 1], "ticker": ["A", "B", "A", "B"],
        "score": [0.0, 1.0, 0.0, 1.0],        # a legit zero score
        "fwd_return": [0.0, 0.01, 0.0, -0.01],  # and a legit zero return
    })
    bt = walk_forward_backtest(panel, top_frac=0.5, long_short=False, baselines=False)
    assert bt.stats["n_periods"] == 2, "rows with 0.0 values were dropped as missing"


# --------------------------------------------------------------- fee/cost bugs


def test_fee_rounding_never_undercharges():
    """Bug: 'exchange fees were undercharged by ~55%' / 'overcharged by ~45%'.

    Kalshi's schedule rounds UP to the next cent. Nearest-cent rounding (the easy
    mistake) undercharges — show it, then pin ours to the schedule exactly.
    """
    grid = np.linspace(0.01, 0.99, 99)
    undercharged = 0
    for p in grid:
        raw = kalshi_taker_fee_raw(float(p))
        ours = kalshi_taker_fee(float(p))
        nearest = round(raw * 100.0) / 100.0
        assert ours >= raw - 1e-12, "fee below the un-rounded schedule = undercharging"
        assert ours == np.ceil(raw * 100.0 - 1e-12) / 100.0
        if nearest < ours:
            undercharged += 1
    assert undercharged > 0, "injection failed: nearest-rounding never undercharged"
    # symmetry + the 50c peak, straight from the schedule
    assert abs(kalshi_taker_fee_raw(0.3) - kalshi_taker_fee_raw(0.7)) < 1e-12
    assert kalshi_taker_fee_raw(0.5) >= max(kalshi_taker_fee_raw(float(p)) for p in grid)


def test_turnover_cost_charged_on_change_only():
    """Bug family: fees mis-applied per event. A constant-weight strategy must pay
    turnover cost once (entering), then never again."""

    class Hold:
        name = "hold"
        description = "static book"

        def target_weights(self, history, bar):
            return {history.columns[0]: 0.5}

    arena = Arena([Hold()], seed=5, n_assets=3, n_bars=200, cost_bps=20.0,
                  warmup=10, state_path="data/sim/_test_sarithis_arena.json")
    arena.run(50)
    rets = np.asarray(arena.returns["hold"])
    prices = arena.prices.iloc[:, 0]
    # bar t decides, bar t+1 realises: gross = 0.5 * next-bar return, no cost after entry
    for k in range(1, 10):
        bar = 10 + k
        gross = 0.5 * (prices.iloc[bar + 1] / prices.iloc[bar] - 1.0)
        assert abs(rets[k] - gross) < 1e-12, "cost charged with zero turnover"
    assert rets[0] < 0.5 * (prices.iloc[11] / prices.iloc[10] - 1.0), "entry paid no cost"
    arena.reset()


# ------------------------------------------------------------- accounting bugs


def test_first_day_is_in_sharpe_and_drawdown():
    """Bug: 'Sharpe and drawdown calculation omitted the first trading day'."""
    panel = pd.DataFrame({
        "date": np.repeat(np.arange(4), 2),
        "ticker": list("AB") * 4,
        "score": [1.0, 0.0] * 4,
        "fwd_return": [-0.5, -0.5] + [0.01, 0.0] * 3,  # the crash IS the first period
    })
    bt = walk_forward_backtest(panel, top_frac=0.5, long_short=False, baselines=False)
    assert bt.stats["n_periods"] == 4
    assert bt.stats["max_drawdown"] <= -0.45, "first-day crash missing from drawdown"
    # buggy variant: dropping the first period hides the crash entirely
    buggy_dd = max_drawdown((1.0 + bt.returns.iloc[1:]).cumprod())
    assert buggy_dd > -0.05, "injection failed"


def test_risk_check_uses_market_mark_not_fill_price():
    """Bug: 'margin check after a fill used the fill price instead of the market
    mark price'. Our kill switch must see marked-to-market equity."""
    b = PaperBroker(cash=100_000.0, cost_bps=0.0)
    b.submit(Order("AAA", "buy", 1000, "o1"), 100.0)  # all-in at 100
    b.mark({"AAA": 100.0})
    crashed = {"AAA": 80.0}  # market now 20% lower than the fill
    ex = ExecutionLayer(b, RiskLimits(daily_drawdown_kill=0.08), crashed)
    fill_price_equity = b.cash + b.positions["AAA"].qty * b.positions["AAA"].avg_price
    assert fill_price_equity >= 100_000.0 - 1e-6, "injection failed: fill-price equity sees no loss"
    r = ex.rebalance({"AAA": 0.5}, "run2")
    assert r.halted is True, "kill switch ignored the market mark"
