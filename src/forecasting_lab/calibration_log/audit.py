"""The snapshot audit trail — every pick carries the inputs behind it (V8).

The field lesson (thread-verified twice): a track record you can't REPLAY is a
narrative. Each decision the loop records gets the exact as-of input blob that
produced it — prices, targets, signals, freshness stamps — persisted as
canonical JSON next to the pick, keyed and content-hashed. "Canonical" means
sorted keys and fixed separators, so a later replay reproduces the bytes (and
the hash) exactly or fails loudly; there is no "roughly the same inputs".
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical_json(obj) -> str:
    """Deterministic JSON: sorted keys, fixed separators, no NaN smuggling."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


class AuditTrail:
    """Append-only JSONL of ``(key, inputs, sha256)`` records."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def record(self, key: str, inputs: dict, on: str = "") -> str:
        """Persist the input blob behind one decision; returns its sha256."""
        sha = content_hash(inputs)
        row = {"key": key, "on": on, "sha256": sha, "inputs": inputs}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(canonical_json(row) + "\n")
        return sha

    def replay(self, key: str) -> tuple[dict, str]:
        """The exact inputs behind ``key`` (latest record), verified against the
        stored hash. Raises KeyError if unknown, ValueError if the bytes no
        longer hash to what was recorded (tampering or corruption — loud)."""
        found: dict | None = None
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    if row.get("key") == key:
                        found = row
        if found is None:
            raise KeyError(f"no audit record for {key!r}")
        sha = content_hash(found["inputs"])
        if sha != found["sha256"]:
            raise ValueError(f"audit record {key!r} fails its hash — corrupted or edited")
        return found["inputs"], sha
