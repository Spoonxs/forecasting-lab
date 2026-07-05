"""The data-freshness audit layer (MASTER_PLAN V3).

The field lesson this encodes (verified twice over): the scanner that "quietly
built a cache and numerous fallbacks on your live data" — and the same author's
own earlier code carrying ``use_cached=True`` into a live pipeline. Stale data
pretending to be live is worse than no data, because every number downstream
still *looks* right.

Three parts:
- every fetched datum carries ``fetched_at`` (:func:`stamp`);
- a :class:`FreshnessBudget` fails LOUDLY (:class:`StaleDataError`) when data is
  older than its as-of budget — silence is the bug;
- :class:`DataConfidence` reports what fraction of a record was imputed rather
  than observed, so a proxy-filled fundamental can never pass as a measured one.

All checks take explicit timestamps — no wall-clock inside logic (repo
convention); callers stamp at the I/O boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


class StaleDataError(RuntimeError):
    """Data outlived its freshness budget — refuse to compute on it silently."""


def _as_datetime(value: datetime | str) -> datetime:
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def stamp(payload: dict, fetched_at: datetime | str) -> dict:
    """Return ``payload`` with its fetch time attached (ISO-8601, UTC)."""
    out = dict(payload)
    out["fetched_at"] = _as_datetime(fetched_at).isoformat()
    return out


def age_seconds(fetched_at: datetime | str, now: datetime | str) -> float:
    """Age of a datum at ``now``. Negative ages (future stamps) are an error."""
    age = (_as_datetime(now) - _as_datetime(fetched_at)).total_seconds()
    if age < 0:
        raise StaleDataError(f"fetched_at is in the future by {-age:.0f}s — clock or stamp bug")
    return age


@dataclass(frozen=True)
class FreshnessBudget:
    """How old a source's data may be before computing on it becomes dishonest."""

    max_age_seconds: float
    source: str = "data"

    def check(self, fetched_at: datetime | str, now: datetime | str) -> float:
        """Return the age if within budget; raise :class:`StaleDataError` if not."""
        age = age_seconds(fetched_at, now)
        if age > self.max_age_seconds:
            raise StaleDataError(
                f"{self.source}: data is {age:.0f}s old, budget is "
                f"{self.max_age_seconds:.0f}s — refusing to compute on stale data"
            )
        return age

    def is_fresh(self, fetched_at: datetime | str, now: datetime | str) -> bool:
        try:
            self.check(fetched_at, now)
        except StaleDataError:
            return False
        return True


@dataclass(frozen=True)
class DataConfidence:
    """What fraction of a record was observed vs imputed/proxied."""

    total_fields: int
    imputed_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_fields <= 0:
            raise ValueError("total_fields must be positive")
        if len(self.imputed_fields) > self.total_fields:
            raise ValueError("more imputed fields than fields")

    @property
    def confidence(self) -> float:
        return 1.0 - len(self.imputed_fields) / self.total_fields

    def as_dict(self) -> dict:
        return {
            "confidence": round(self.confidence, 4),
            "imputed_fields": list(self.imputed_fields),
            "total_fields": self.total_fields,
        }
