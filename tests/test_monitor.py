from datetime import date

from pytest import approx

from forecasting_lab.markets.monitor import (
    DivergencePipeline,
    kalshi_yes_price,
    poly_yes_price,
)


def test_kalshi_yes_price_cents_conversion():
    assert kalshi_yes_price({"yes_bid": 40, "yes_ask": 44}) == 0.42
    assert kalshi_yes_price({"yes_bid": 0, "yes_ask": 44, "last_price": 41}) == 0.41
    assert kalshi_yes_price({}) is None


def test_kalshi_yes_price_dollars_fields_take_precedence():
    # the current API ships string-dollar fields; cents fields may be None
    m = {"yes_bid_dollars": "0.4000", "yes_ask_dollars": "0.4400", "yes_bid": None, "yes_ask": None}
    assert kalshi_yes_price(m) == approx(0.42)
    # all-zero dollar quotes mean an empty book, not a $0 price
    assert kalshi_yes_price({"yes_bid_dollars": "0.0000", "yes_ask_dollars": "0.0000",
                             "last_price_dollars": "0.0000"}) is None
    assert kalshi_yes_price({"last_price_dollars": "0.6100"}) == 0.61


def test_poly_yes_price_json_string_gotcha():
    # Gamma returns outcomePrices as a JSON *string* of stringified floats
    assert poly_yes_price({"outcomePrices": '["0.45", "0.55"]'}) == 0.45
    assert poly_yes_price({"outcomePrices": ["0.3", "0.7"]}) == 0.3
    assert poly_yes_price({"lastTradePrice": "0.62"}) == 0.62
    assert poly_yes_price({"bestBid": "0.40", "bestAsk": "0.44"}) == approx(0.42)
    assert poly_yes_price({}) is None


class _StubKalshi:
    def events(self, **params):
        return [
            # binary event: one nested market -> matchable
            {
                "title": "Fed cuts rates in March 2026?",
                "markets": [{"yes_bid_dollars": "0.3800", "yes_ask_dollars": "0.4200"}],
            },
            {
                "title": "CPI above 3% in June 2026?",
                "markets": [{"yes_bid": 21, "yes_ask": 23}],  # legacy cents shape
            },
            # multi-market event (e.g. "who wins?") -> skipped by the pipeline
            {
                "title": "Who will win the election?",
                "markets": [{"yes_bid_dollars": "0.5000"}, {"yes_bid_dollars": "0.3000"}],
            },
        ]


class _StubPoly:
    def markets(self, **params):
        return [
            {"question": "Will the Fed cut rates in March 2026?", "outcomePrices": '["0.46", "0.54"]'},
            {"question": "Completely unrelated market", "outcomePrices": '["0.50", "0.50"]'},
        ]


def test_pipeline_end_to_end_writes_digest(tmp_path):
    pipe = DivergencePipeline(kalshi=_StubKalshi(), polymarket=_StubPoly(), match_threshold=0.4)
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    assert path.name == "2026-07-01-market-divergence.md"
    text = path.read_text(encoding="utf-8")
    # Fed pair: kalshi 0.40 vs poly 0.46 -> 0.06 gross, ~0.02 fee -> flagged
    assert "Fed cuts rates in March 2026?" in text
    assert "buy_kalshi" in text
    # the unrelated market must not appear as a match
    assert "Completely unrelated" not in text.split("Coverage")[0]
    assert "Not financial advice" in text
    # 3 stub events, but the multi-market one is skipped -> 2 binary events
    assert "2 Kalshi binary events and 2 Polymarket" in text


def test_pipeline_handles_empty_venues(tmp_path):
    class _Empty:
        def events(self, **params):
            return []

    pipe = DivergencePipeline(kalshi=_Empty(), polymarket=_StubPoly())
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    assert "no priced markets" in path.read_text(encoding="utf-8")
