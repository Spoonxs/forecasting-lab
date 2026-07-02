"""Resilient HTTP client.

Public market endpoints (Polymarket especially) are rate-limited and flaky under
load, so every request goes through a session with exponential backoff and a real
User-Agent (Reddit and some venues reject empty/default agents). See
``project-forecasting-lab.md`` and ``claude-stack-resources.md`` for the gotchas.
"""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import get_settings


def build_session(
    *,
    user_agent: str | None = None,
    max_retries: int | None = None,
    backoff: float | None = None,
) -> requests.Session:
    """A requests.Session that retries idempotent calls with exponential backoff."""
    s = get_settings()
    retry_kwargs = dict(
        total=max_retries if max_retries is not None else s.http_max_retries,
        backoff_factor=backoff if backoff is not None else s.http_backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    # backoff_jitter (urllib3 >= 2) spreads retries so a fleet of daily jobs and
    # 100+ channel pulls don't hammer a throttling host in lockstep.
    try:
        retries = Retry(backoff_jitter=0.5, **retry_kwargs)
    except TypeError:  # older urllib3 without backoff_jitter
        retries = Retry(**retry_kwargs)
    adapter = HTTPAdapter(max_retries=retries)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": user_agent or s.user_agent})
    return session


class HttpClient:
    """Thin wrapper holding a retrying session and a default timeout."""

    def __init__(self, *, user_agent: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.session = build_session(user_agent=user_agent)
        self.timeout = timeout if timeout is not None else settings.http_timeout

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        resp = self.session.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    def get_json(self, url: str, **kwargs: Any) -> Any:
        return self.get(url, **kwargs).json()

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        resp = self.session.post(url, **kwargs)
        resp.raise_for_status()
        return resp


_DEFAULT: HttpClient | None = None


def _default_client() -> HttpClient:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = HttpClient()
    return _DEFAULT


def get_json(url: str, **kwargs: Any) -> Any:
    """Convenience one-shot GET returning parsed JSON via the shared client."""
    return _default_client().get_json(url, **kwargs)
