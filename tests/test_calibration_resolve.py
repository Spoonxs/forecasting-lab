from forecasting_lab.calibration_log import ForecastLog
from forecasting_lab.calibration_log import resolve as resolvemod


def test_resolve_open_uses_resolver_and_scores(tmp_path):
    log = ForecastLog(tmp_path / "cal.csv")
    log.record("Fed cuts in March?", 0.35, venue="Kalshi", market_id="KXFED-MAR", market_prob=0.40)
    log.record("Turnout > 60%?", 0.70, venue="Polymarket", market_id="0xabc", market_prob=0.66)
    log.record("no market id", 0.5)  # should be skipped by resolve_open

    # a resolver that settles only the Kalshi one
    def resolver(venue, market_id):
        return 1 if market_id == "KXFED-MAR" else None

    n = log.resolve_open(resolver)
    assert n == 1
    resolved = log.resolved()
    assert len(resolved) == 1 and int(resolved.iloc[0]["outcome"]) == 1
    # persisted across reload
    assert ForecastLog(tmp_path / "cal.csv").resolved().shape[0] == 1


def test_beat_market_score(tmp_path):
    log = ForecastLog(tmp_path / "c.csv")
    # you said 0.8 (right), market said 0.6; event happened -> you beat the market
    fid1 = log.record("A", 0.80, venue="Kalshi", market_id="m1", market_prob=0.60)
    fid2 = log.record("B", 0.20, venue="Kalshi", market_id="m2", market_prob=0.40)
    log.resolve(fid1, 1)
    log.resolve(fid2, 0)  # you said 0.20 (closer to 0), market 0.40 -> you beat it again
    b = log.beat_market_score()
    assert b["n"] == 2
    assert b["model_brier"] < b["market_brier"]
    assert b["brier_skill_vs_market"] > 0
    assert b["beat_rate"] == 1.0


def test_beat_market_ignores_rows_without_market_prob(tmp_path):
    log = ForecastLog(tmp_path / "c.csv")
    fid = log.record("no market price", 0.5)
    log.resolve(fid, 1)
    assert log.beat_market_score()["n"] == 0


def test_venue_resolver_dispatch(monkeypatch):
    monkeypatch.setattr(resolvemod, "kalshi_outcome", lambda t: 1)
    monkeypatch.setattr(resolvemod, "poly_outcome", lambda m: 0)
    assert resolvemod.venue_resolver("Kalshi", "KX") == 1
    assert resolvemod.venue_resolver("Polymarket", "0x") == 0
    assert resolvemod.venue_resolver("unknown", "x") is None


def test_kalshi_outcome_reads_result(monkeypatch):
    import forecasting_lab.markets.kalshi as kalshi

    class _Client:
        def __init__(self, *a, **k):
            pass

        def market(self, ticker):
            return {"status": "settled", "result": "yes"}

    monkeypatch.setattr(kalshi, "KalshiClient", _Client)
    assert resolvemod.kalshi_outcome("KX") == 1

    class _Open(_Client):
        def market(self, ticker):
            return {"status": "active", "result": ""}

    monkeypatch.setattr(kalshi, "KalshiClient", _Open)
    assert resolvemod.kalshi_outcome("KX") is None
