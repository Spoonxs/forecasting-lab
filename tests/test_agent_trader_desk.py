"""The Agent desk: it actually picks stocks from the live movers, bets on the live
prediction markets, records a blotter, and accrues real (paper) P&L across runs."""

from __future__ import annotations

from forecasting_lab.agent_trader.desk import AgentLedger, build_desk


def _movers():
    return {"movers": [{"ticker": "NVDA", "last": 100.0, "momentum": 1.2, "ret_5d": 0.03,
                        "ret_60d": 0.4, "pct_from_high": -0.02, "volume_spike": 1.8}]}


def _edges():
    return {"live": {"poly": [{"event": "Will X win?", "yes": 0.30}],
                     "kalshi": [{"event": "Will Y happen?", "yes": 0.60}]}}


def test_desk_picks_stocks_and_market_bets(tmp_path):
    d = build_desk(_movers(), _edges(), "2026-07-03", ledger=AgentLedger(tmp_path / "l.json"))
    assert d["n_stocks"] == 1 and d["n_markets"] == 2
    assert any(p["name"] == "NVDA" and p["side"] == "long" for p in d["picks"])
    assert any(p["kind"] == "market" and p["side"] in ("YES", "NO") for p in d["picks"])
    assert len(d["blotter"]) >= 1  # it announced what it did


def test_pnl_accrues_when_the_price_moves(tmp_path):
    led = AgentLedger(tmp_path / "l.json")
    build_desk({"movers": [{"ticker": "NVDA", "last": 100.0, "momentum": 1.0}]}, {}, "d1", ledger=led)
    d = build_desk({"movers": [{"ticker": "NVDA", "last": 110.0, "momentum": 1.0}]}, {}, "d2", ledger=led)
    nvda = next(p for p in d["picks"] if p["name"] == "NVDA")
    assert nvda["entry"] == 100.0 and nvda["mark"] == 110.0
    assert abs(nvda["pnl"] - 0.10) < 1e-6  # +10% accrued from the real move


def test_desk_degrades_with_no_data():
    d = build_desk({}, {}, "d1")
    assert d["n_stocks"] == 0 and d["picks"] == [] and d["equity"] == 100_000.0
