"""Compose a short alert from the freshest digests.

Reads the newest ``inputs/*-<slug>.md`` for each pipeline, pulls the top flagged
rows, and builds a compact message — the "here's what moved today" ping. Kept
plain-text (ASCII) so it renders anywhere, including a Windows console.
"""

from __future__ import annotations

import re as _re
from datetime import date as _date

from ..config import PATHS


def _clean(text) -> str:
    """Alerts are plain text, but Discord embeds render markdown and file-based
    feed text isn't trusted — strip anything a downstream renderer could treat
    as markup (Codex review), and cap the length."""
    return _re.sub(r"[<>&*_`\[\]#|]", "", str(text or ""))[:200]


def _newest(slug: str):
    files = sorted(PATHS.inputs.glob(f"*-{slug}.md"))
    return files[-1] if files else None


def _first_table_first_column(text: str, limit: int) -> list[str]:
    """First column of the first markdown table's data rows (skips header+rule)."""
    rows: list[str] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("|") and "---" in line:
            in_table = True  # the separator row: data starts next
            continue
        if in_table:
            if not line.startswith("|"):
                break
            first = line.strip("|").split("|")[0].strip()
            if first:
                rows.append(first)
            if len(rows) >= limit:
                break
    return rows


def _top(slug: str, limit: int = 3) -> list[str]:
    path = _newest(slug)
    if not path:
        return []
    return _first_table_first_column(path.read_text(encoding="utf-8"), limit)


def _gather(on: _date) -> tuple[list[tuple[str, list[str]]], bool]:
    """Collect (section_title, items) blocks from the freshest digests."""
    sections: list[tuple[str, list[str]]] = []
    flagged = False

    div = _top("market-divergence")
    if div:
        flagged = True
        sections.append(("Cross-venue divergence flags", div))

    fast = _top("trending-stocks")
    if fast:
        flagged = True
        sections.append(("Trending stocks (fast money)", fast))

    media = _top("media-watch")
    if media:
        sections.append(("Most-named by media", media))

    # watcher events (P6d): the dated feed the templates filed — flagged, since
    # every event already crossed a stated threshold
    try:
        from ..pipeline.digest import read_latest_data

        watch_events = (read_latest_data("watchers") or {}).get("events", [])
        if watch_events:
            flagged = True
            sections.append(("Watchers fired",
                             [f"{_clean(e.get('kind'))}: {_clean(e.get('reason'))}"
                              for e in watch_events[:5]]))
    except Exception:  # noqa: BLE001 - the alert must send even if the feed is unreadable
        pass

    try:
        from ..forwardtest import ForwardLedger

        board = ForwardLedger().leaderboard()
        if not board.empty:
            row = board.iloc[0]
            sections.append(("Forward-study leader", [f"{row['strategy']}  ({row['equity']:.2f}x)"]))
    except Exception:  # noqa: BLE001 - the alert must send even if the ledger is missing
        pass

    return sections, flagged


def build_alert(on: _date | None = None) -> tuple[str, str, list[dict]]:
    """Return ``(title, readable_text, discord_fields)``.

    ``readable_text`` is a clean, scannable block for Telegram / the local log;
    ``discord_fields`` renders each section as its own titled block in the embed."""
    on = on or _date.today()
    title = f"Forecasting Lab - {on.isoformat()}"
    sections, flagged = _gather(on)

    body_lines: list[str] = []
    fields: list[dict] = []
    for name, items in sections:
        body_lines.append(name.upper())
        body_lines.extend(f"  - {it}" for it in items)
        body_lines.append("")
        fields.append({"name": name, "value": "\n".join(f"- {it}" for it in items)[:1024], "inline": False})

    # "Quiet day" = no *flagged* signals (divergence/trending); the forward-study
    # leader still shows as context, so note the quiet state explicitly.
    if not flagged:
        note = "Quiet day - nothing crossed the thresholds."
        body_lines.append(note)
        fields.append({"name": "Status", "value": note, "inline": False})

    body = "\n".join(body_lines).strip() or "Quiet day - nothing crossed the thresholds."
    text = f"{title}\n\n{body}\n\n(candidates, not advice)"
    return title, text, fields


def compose_alert(on: _date | None = None) -> str:
    """The readable text version (for callers/tests that want a single string)."""
    return build_alert(on)[1]


def has_flags(on: _date | None = None) -> bool:
    """True if any *flagged* signal (divergence/trending) is present today —
    used by ``--only-if-flagged`` to stay quiet on nothing days."""
    return _gather(on or _date.today())[1]
