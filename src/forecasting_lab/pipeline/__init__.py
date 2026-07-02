"""The reusable ingestion pipeline: invoke -> fetch -> process -> store.

Set it up once and point it at different sources (markets, papers, signals); each
run files a dated digest into ``inputs/``. Build a pipeline only for things that
recur — one-off lookups are cheaper to just ask. See ``master-index.md`` and
``data-automation.md``.
"""

from .base import Pipeline
from .digest import dated_note_path, render_digest, write_dated_note

__all__ = ["Pipeline", "render_digest", "write_dated_note", "dated_note_path"]
