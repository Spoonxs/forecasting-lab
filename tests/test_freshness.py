"""V3 — the data-freshness audit layer (MASTER_PLAN §3).

The injection pinned here: stale data flowing silently into a live computation
(the "quietly built a cache on your live data" class). Freshness must be carried
on the datum, budget breaches must RAISE, and imputed fields must be visible.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from forecasting_lab.pipeline import (
    DataConfidence,
    FreshnessBudget,
    Pipeline,
    StaleDataError,
    age_seconds,
    stamp,
)

T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
T0_PLUS_HOUR = datetime(2026, 7, 1, 13, 0, 0, tzinfo=timezone.utc)


def test_stamp_attaches_fetch_time_and_age_is_computable():
    datum = stamp({"price": 101.5}, fetched_at=T0)
    assert datum["price"] == 101.5
    assert age_seconds(datum["fetched_at"], now=T0_PLUS_HOUR) == pytest.approx(3600.0)


def test_budget_breach_raises_loudly_not_silently():
    budget = FreshnessBudget(max_age_seconds=900, source="quotes")
    assert budget.check(T0, now=datetime(2026, 7, 1, 12, 10, tzinfo=timezone.utc)) == pytest.approx(600.0)
    with pytest.raises(StaleDataError, match="quotes.*3600s old.*900s"):
        budget.check(T0, now=T0_PLUS_HOUR)
    assert budget.is_fresh(T0, now=T0_PLUS_HOUR) is False


def test_future_stamps_are_a_bug_not_freshness():
    with pytest.raises(StaleDataError, match="future"):
        age_seconds(T0_PLUS_HOUR, now=T0)


def test_data_confidence_exposes_imputed_fraction():
    dc = DataConfidence(total_fields=8, imputed_fields=("piotroski", "roic"))
    assert dc.confidence == pytest.approx(0.75)
    assert dc.as_dict()["imputed_fields"] == ["piotroski", "roic"]
    with pytest.raises(ValueError):
        DataConfidence(total_fields=1, imputed_fields=("a", "b"))


def test_stale_injection_raises_end_to_end_and_digest_carries_freshness(tmp_path):
    """A pipeline whose fetch returns stale-stamped data must fail its budget
    check inside process(); a fresh run writes fetched_at into the JSON sidecar."""

    class Quotes(Pipeline):
        slug = "test-quotes"

        def __init__(self, fetched_at: datetime, now: datetime):
            self._when, self._now = fetched_at, now

        def fetch(self):
            datum = stamp({"price": 100.0}, fetched_at=self._when)
            self._fetched_at = datum["fetched_at"]
            return datum

        def process(self, raw) -> str:
            FreshnessBudget(max_age_seconds=900, source=self.slug).check(
                raw["fetched_at"], now=self._now
            )
            self._data = {"price": raw["price"]}
            return f"price {raw['price']}"

    with pytest.raises(StaleDataError):  # stale injection: fetched an hour ago
        Quotes(T0, now=T0_PLUS_HOUR).run(on=date(2026, 7, 1), out_dir=tmp_path)

    fresh = Quotes(T0, now=datetime(2026, 7, 1, 12, 5, tzinfo=timezone.utc))
    fresh.run(on=date(2026, 7, 1), out_dir=tmp_path)
    sidecar = json.loads((tmp_path / "2026-07-01-test-quotes.json").read_text(encoding="utf-8"))
    assert sidecar["freshness"]["fetched_at"] == T0.isoformat()
