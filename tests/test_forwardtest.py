import numpy as np
import pandas as pd

from forecasting_lab.forwardtest.ledger import ForwardLedger
from forecasting_lab.sim.strategies import BuyHold, Momentum


def _dated_prices(n=200, k=8, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    data = {f"A{i}": 100 * np.cumprod(1 + rng.normal(0.0004, 0.02, n)) for i in range(k)}
    return pd.DataFrame(data, index=idx)


def test_backfill_seeds_curve_then_live_extends(tmp_path):
    prices = _dated_prices()
    led = ForwardLedger(strategies=[Momentum(60, 3), BuyHold()], path=tmp_path / "l.json")
    steps = led.backfill(prices, every=10, start=130)
    assert steps > 0
    # every strategy has a backfilled curve, all marks labeled backfill
    curves = led.curves()
    assert set(curves) == {"momentum_60d", "buy_hold"}
    assert all(pt["phase"] == "backfill" for pt in curves["buy_hold"])
    assert led.live_started() is None  # no live marks yet

    # a later live step extends the curve and is labeled live
    later = _dated_prices(n=210)  # 10 more bdays
    led.step(later, on_date="2025-10-15", phase="live")
    assert led.live_started() == "2025-10-15"
    assert led.curves()["buy_hold"][-1]["phase"] == "live"


def test_backfill_is_idempotent(tmp_path):
    prices = _dated_prices()
    led = ForwardLedger(strategies=[BuyHold()], path=tmp_path / "l.json")
    assert led.backfill(prices) > 0
    assert led.backfill(prices) == 0  # second call is a no-op (never double-counts)


def test_mark_to_market_matches_hand_computation(tmp_path):
    # two bars: buy-hold equal-weight, no cost -> equity == mean price ratio
    idx = pd.to_datetime(["2025-01-02", "2025-01-03"])
    prices = pd.DataFrame({"X": [100.0, 110.0], "Y": [100.0, 90.0]}, index=idx)
    led = ForwardLedger(strategies=[BuyHold()], cost_bps=0.0, path=tmp_path / "l.json")
    led.step(prices.iloc[:1], on_date="2025-01-02", phase="live")  # record at day 1
    led.step(prices, on_date="2025-01-03", phase="live")           # mark at day 2
    curve = led.curves()["buy_hold"]
    # equal weight of +10% and -10% = 0% -> equity stays ~1.0
    assert abs(curve[-1]["equity"] - 1.0) < 1e-9


def test_persistence_round_trip(tmp_path):
    prices = _dated_prices()
    p = tmp_path / "l.json"
    led = ForwardLedger(strategies=[Momentum(60, 3)], path=p)
    led.backfill(prices)
    led.save()
    reloaded = ForwardLedger(strategies=[Momentum(60, 3)], path=p)
    assert reloaded.curves()["momentum_60d"] == led.curves()["momentum_60d"]


def test_leaderboard_separates_live_from_total(tmp_path):
    prices = _dated_prices()
    led = ForwardLedger(strategies=[BuyHold()], path=tmp_path / "l.json")
    led.backfill(prices)
    led.step(_dated_prices(n=205), on_date="2025-10-20", phase="live")
    board = led.leaderboard()
    assert {"strategy", "equity", "total_return", "live_return", "live_marks"} <= set(board.columns)
    assert board.iloc[0]["live_marks"] >= 1
