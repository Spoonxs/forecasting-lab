"""A tiny on-disk JSON cache with TTL.

Use it to avoid re-hitting flaky public endpoints while iterating on parsing, and
to be a polite scraper. Keys are hashed to safe filenames under ``cache/``.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..config import PATHS


class DiskCache:
    """JSON values keyed by arbitrary strings, expiring after ``ttl`` seconds."""

    def __init__(self, namespace: str = "default", ttl: int = 300, root: Path | None = None):
        self.ttl = ttl
        self.dir = (root or PATHS.cache) / namespace
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.dir / f"{digest}.json"

    def get(self, key: str, *, now: float | None = None) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        now = time.time() if now is None else now
        if self.ttl >= 0 and now - payload.get("_ts", 0) > self.ttl:
            return None
        return payload.get("value")

    def set(self, key: str, value: Any, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"_ts": now, "value": value}), encoding="utf-8")
        tmp.replace(path)  # atomic-ish on the same filesystem

    def get_or_set(self, key: str, producer: Callable[[], Any]) -> Any:
        hit = self.get(key)
        if hit is not None:
            return hit
        value = producer()
        self.set(key, value)
        return value


def cached_json(namespace: str, key: str, producer: Callable[[], Any], ttl: int = 300) -> Any:
    """Module-level convenience around :class:`DiskCache`."""
    return DiskCache(namespace=namespace, ttl=ttl).get_or_set(key, producer)
