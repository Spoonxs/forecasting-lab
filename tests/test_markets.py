import base64

import pytest

from forecasting_lab.backtest.costs import (
    kalshi_taker_fee,
    kalshi_taker_fee_raw,
    polymarket_fee,
)
from forecasting_lab.markets.kalshi import KalshiSigner
from forecasting_lab.markets.polymarket import PolymarketClient, parse_orderbook, to_float
from forecasting_lab.utils.cache import DiskCache


class _StubHttp:
    """Counts calls and returns a canned JSON payload (no network)."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get_json(self, url, params=None):
        self.calls += 1
        return self.payload


def test_to_float_coercion():
    assert to_float("0.53") == 0.53
    assert to_float("") is None
    assert to_float(None, 0.0) == 0.0
    assert to_float("garbage", -1.0) == -1.0


def test_parse_orderbook_string_prices():
    payload = {
        "asset_id": "tok",
        "bids": [{"price": "0.51", "size": "100"}, {"price": "0.49", "size": "5"}],
        "asks": [{"price": "0.55", "size": "10"}, {"price": "0.58", "size": "2"}],
    }
    q = parse_orderbook(payload)
    assert isinstance(q.best_bid, float) and isinstance(q.best_ask, float)
    assert q.best_bid == 0.51 and q.best_ask == 0.55
    assert abs(q.mid - 0.53) < 1e-12
    assert abs(q.spread - 0.04) < 1e-12


def test_parse_orderbook_empty_side():
    q = parse_orderbook({"asset_id": "t", "bids": [], "asks": []})
    assert q.best_bid is None and q.best_ask is None and q.mid is None


def test_kalshi_fee_peaks_and_rounds():
    assert abs(kalshi_taker_fee_raw(0.5) - 0.0175) < 1e-12
    # symmetric about 0.5
    assert abs(kalshi_taker_fee_raw(0.3) - kalshi_taker_fee_raw(0.7)) < 1e-12
    # fee is largest at the midpoint
    assert kalshi_taker_fee_raw(0.5) > kalshi_taker_fee_raw(0.9)
    # rounds up to the next cent
    assert kalshi_taker_fee(0.5) == 0.02
    assert polymarket_fee(100.0) == 0.0


def test_kalshi_fee_validates_range():
    with pytest.raises(ValueError):
        kalshi_taker_fee_raw(1.5)


def test_kalshi_signature_verifies():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    signer = KalshiSigner(pem, "key-id-123")
    ts, method, path = "1700000000000", "GET", "/trade-api/v2/markets"
    headers = signer.headers(method, path, timestamp_ms=ts)
    assert headers["KALSHI-ACCESS-KEY"] == "key-id-123"
    assert headers["KALSHI-ACCESS-TIMESTAMP"] == ts

    msg = signer.message(ts, method, path)
    assert msg == "1700000000000GET/trade-api/v2/markets"
    # the signature must verify against the public key (round-trip)
    key.public_key().verify(
        base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"]),
        msg.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )


def test_polymarket_metadata_is_cached(tmp_path):
    stub = _StubHttp([{"id": 1}])
    client = PolymarketClient(http=stub, cache=DiskCache("pm", ttl=300, root=tmp_path))
    first = client.markets(active="true")
    second = client.markets(active="true")  # identical params -> from cache
    assert first == second == [{"id": 1}]
    assert stub.calls == 1  # second call did not hit the network


def test_polymarket_prices_are_live(tmp_path):
    stub = _StubHttp({"mid": "0.53"})
    client = PolymarketClient(http=stub, cache=DiskCache("pm2", ttl=300, root=tmp_path))
    assert client.midpoint("tok") == 0.53  # string price coerced to float
    client.midpoint("tok")
    assert stub.calls == 2  # price reads are never cached
