"""The four-move pipeline pattern as a tiny base class.

Subclass and implement :meth:`fetch` and :meth:`process`; :meth:`store` defaults
to writing a dated digest into ``inputs/``. :meth:`run` wires them together.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date as _date
from pathlib import Path
from typing import Any

from .digest import write_dated_note


class Pipeline(ABC):
    """invoke -> fetch -> process -> store."""

    #: filename slug for the dated digest, e.g. "market-divergence".
    slug: str = "digest"

    @abstractmethod
    def fetch(self) -> Any:
        """Pull raw data from the source(s)."""

    @abstractmethod
    def process(self, raw: Any) -> str:
        """Turn raw data into the Markdown body of a digest."""

    def store(self, body: str, on: _date | None = None, out_dir: Path | None = None) -> Path:
        return write_dated_note(self.slug, body, on=on, out_dir=out_dir)

    def run(self, on: _date | None = None, out_dir: Path | None = None) -> Path:
        raw = self.fetch()
        body = self.process(raw)
        return self.store(body, on=on, out_dir=out_dir)
