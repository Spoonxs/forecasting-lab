"""Kalshi client (one unified REST API, CFTC-regulated).

Base: ``https://api.elections.kalshi.com/trade-api/v2``. Market data is public;
trading needs an API key pair with per-request RSA-PSS signatures.

Signing (the part that's easy to get wrong):
- Message to sign = ``timestamp_ms + METHOD + path`` where ``path`` excludes the
  query string.
- Signature = base64( RSA-PSS-SHA256( message ) ), MGF1-SHA256, salt length =
  digest length.
- Headers: ``KALSHI-ACCESS-KEY`` (key id), ``KALSHI-ACCESS-TIMESTAMP`` (ms),
  ``KALSHI-ACCESS-SIGNATURE``.

Rate limit is ~10 req/s per key; a 429 means back off. Test against the demo
environment first. Fees live in :mod:`forecasting_lab.backtest.costs`.
"""

from __future__ import annotations

import base64
import time
from typing import Any
from urllib.parse import urlsplit

from ..config import get_settings
from ..utils.http import HttpClient

PROD_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"


class KalshiSigner:
    """Signs requests with an RSA private key (PEM). Needs ``cryptography``."""

    def __init__(self, private_key_pem: bytes | str, key_id: str):
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Kalshi signing needs cryptography: pip install 'forecasting-lab[markets]'"
            ) from exc
        if isinstance(private_key_pem, str):
            private_key_pem = private_key_pem.encode("utf-8")
        self._key = load_pem_private_key(private_key_pem, password=None)
        self.key_id = key_id

    @classmethod
    def from_file(cls, path: str, key_id: str) -> KalshiSigner:
        with open(path, "rb") as fh:
            return cls(fh.read(), key_id)

    def sign(self, message: str) -> str:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        signature = self._key.sign(
            message.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def message(timestamp_ms: str, method: str, path: str) -> str:
        """Canonical string to sign: timestamp + METHOD + path (no query)."""
        return f"{timestamp_ms}{method.upper()}{path}"

    def headers(self, method: str, path: str, timestamp_ms: str | None = None) -> dict[str, str]:
        ts = timestamp_ms or str(int(time.time() * 1000))
        sig = self.sign(self.message(ts, method, path))
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sig,
        }


class KalshiClient:
    """Read-mostly Kalshi client. Signs requests when a signer is supplied."""

    def __init__(
        self,
        base: str = PROD_BASE,
        signer: KalshiSigner | None = None,
        http: HttpClient | None = None,
    ):
        self.base = base.rstrip("/")
        self.base_path = urlsplit(self.base).path  # e.g. /trade-api/v2
        self.signer = signer
        self.http = http or HttpClient()
        self._min_interval = get_settings().kalshi_min_interval
        self._last_call = 0.0

    @classmethod
    def from_settings(cls, demo: bool = False) -> KalshiClient:
        """Build a client, attaching a signer if KALSHI_* env vars are present."""
        s = get_settings()
        signer = None
        if s.kalshi_api_key_id and s.kalshi_private_key_path:
            signer = KalshiSigner.from_file(s.kalshi_private_key_path, s.kalshi_api_key_id)
        return cls(base=DEMO_BASE if demo else PROD_BASE, signer=signer)

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    def get(self, endpoint: str, params: dict | None = None, *, auth: bool = False) -> Any:
        """GET ``endpoint`` (e.g. ``/markets``). Signs when ``auth`` and a signer exist."""
        self._throttle()
        endpoint = "/" + endpoint.lstrip("/")
        url = self.base + endpoint
        headers = {}
        if auth:
            if self.signer is None:
                raise RuntimeError("authenticated call requires a KalshiSigner")
            # Sign the path WITHOUT query params.
            headers = self.signer.headers("GET", self.base_path + endpoint)
        return self.http.get_json(url, params=params or None, headers=headers or None)

    def markets(self, *, max_pages: int = 10, **params: Any) -> list[dict]:
        """List markets, following cursor pagination up to ``limit`` results.

        Kalshi serves at most 1000 per page and the front pages are dominated by
        unquoted multi-leg markets, so a single page rarely covers the book.
        """
        limit = params.get("limit")
        out: list[dict] = []
        cursor: str | None = None
        for _ in range(max_pages):
            page_params = dict(params)
            if limit:
                page_params["limit"] = min(int(limit), 1000)  # API max per page
            if cursor:
                page_params["cursor"] = cursor
            resp = self.get("/markets", params=page_params)
            out.extend(resp.get("markets", []))
            cursor = resp.get("cursor")
            if not cursor or (limit and len(out) >= limit):
                break
        return out[:limit] if limit else out

    def events(self, *, max_pages: int = 10, **params: Any) -> list[dict]:
        """List events, following cursor pagination up to ``limit`` results.

        Pass ``with_nested_markets="true"`` to embed each event's markets —
        binary (single-market) events are the cross-venue matching surface.
        """
        limit = params.get("limit")
        out: list[dict] = []
        cursor: str | None = None
        for _ in range(max_pages):
            page_params = dict(params)
            if limit:
                page_params["limit"] = min(int(limit), 200)  # API max per page
            if cursor:
                page_params["cursor"] = cursor
            resp = self.get("/events", params=page_params)
            out.extend(resp.get("events", []))
            cursor = resp.get("cursor")
            if not cursor or (limit and len(out) >= limit):
                break
        return out[:limit] if limit else out

    def market(self, ticker: str) -> dict:
        return self.get(f"/markets/{ticker}").get("market", {})
