"""The four-move pipeline pattern as a tiny base class.

Subclass and implement :meth:`fetch` and :meth:`process`; :meth:`store` defaults
to writing a dated digest into ``inputs/``. :meth:`run` wires them together.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date as _date
from pathlib import Path
from typing import Any

from .digest import write_dated_data, write_dated_note


class Pipeline(ABC):
    """invoke -> fetch -> process -> store."""

    #: filename slug for the dated digest, e.g. "market-divergence".
    slug: str = "digest"

    #: optional machine-readable payload a subclass sets during ``process`` — when
    #: present, ``store`` also writes ``inputs/<date>-<slug>.json`` for the dashboard.
    _data: dict | None = None

    #: optional ISO-8601 fetch time a subclass sets during ``fetch`` (see
    #: ``pipeline.freshness.stamp``) — when present, ``store`` writes it into the
    #: JSON sidecar so every downstream reader can see how old the data is.
    _fetched_at: str | None = None

    @abstractmethod
    def fetch(self) -> Any:
        """Pull raw data from the source(s)."""

    @abstractmethod
    def process(self, raw: Any) -> str:
        """Turn raw data into the Markdown body of a digest."""

    def store(self, body: str, on: _date | None = None, out_dir: Path | None = None) -> Path:
        path = write_dated_note(self.slug, body, on=on, out_dir=out_dir)
        if self._data is not None:
            if self._fetched_at is not None:
                self._data.setdefault("freshness", {})["fetched_at"] = self._fetched_at
            write_dated_data(self.slug, self._data, on=on, out_dir=out_dir)
        return path

    def run(self, on: _date | None = None, out_dir: Path | None = None) -> Path:
        raw = self.fetch()
        body = self.process(raw)
        return self.store(body, on=on, out_dir=out_dir)
