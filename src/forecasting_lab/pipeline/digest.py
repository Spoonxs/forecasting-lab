"""Dated-digest rendering and writing.

Digests are plain Markdown filed as ``inputs/YYYY-MM-DD-<slug>.md`` so they drop
straight into an Obsidian vault. Write your own short summaries rather than
storing source text verbatim — cleaner for reuse and avoids copyright issues.

Some pipelines also emit a **structured sidecar** ``inputs/YYYY-MM-DD-<slug>.json``
alongside the Markdown — the machine-readable version the dashboard reads to draw
sparklines, odds bars and sortable tables (the Markdown is for humans/Obsidian,
the JSON is for the UI).
"""

from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path
from typing import Any

from ..config import PATHS


def dated_note_path(slug: str, on: _date | None = None, out_dir: Path | None = None) -> Path:
    on = on or _date.today()
    out_dir = out_dir or PATHS.inputs
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{on.isoformat()}-{slug}.md"


def dated_data_path(slug: str, on: _date | None = None, out_dir: Path | None = None) -> Path:
    on = on or _date.today()
    out_dir = out_dir or PATHS.inputs
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{on.isoformat()}-{slug}.json"


def write_dated_data(slug: str, data: Any, on: _date | None = None, out_dir: Path | None = None) -> Path:
    """Write a structured JSON sidecar next to the Markdown digest."""
    path = dated_data_path(slug, on=on, out_dir=out_dir)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def read_latest_data(slug: str, out_dir: Path | None = None) -> dict | None:
    """Newest ``<date>-<slug>.json`` payload, or None if none exists / unreadable."""
    out_dir = out_dir or PATHS.inputs
    candidates = sorted(out_dir.glob(f"*-{slug}.json"))
    if not candidates:
        return None
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def render_digest(
    title: str,
    sections: dict[str, str],
    on: _date | None = None,
    disclaimer: str | None = None,
) -> str:
    """Render a digest as Markdown. ``sections`` maps headings to body text."""
    on = on or _date.today()
    parts = [f"# {title}", "", f"*Generated: {on.isoformat()}*", ""]
    for heading, body in sections.items():
        parts.append(f"## {heading}")
        parts.append("")
        parts.append(body.rstrip())
        parts.append("")
    if disclaimer:
        parts.append("---")
        parts.append("")
        parts.append(f"*{disclaimer}*")
        parts.append("")
    return "\n".join(parts)


def write_dated_note(
    slug: str,
    body: str,
    on: _date | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Write ``body`` to ``inputs/YYYY-MM-DD-<slug>.md`` and return the path."""
    path = dated_note_path(slug, on=on, out_dir=out_dir)
    path.write_text(body, encoding="utf-8")
    return path
