"""Connector health — the freshness surface (P6d §6).

One honest row per recurring feed: when it last produced a dated artifact and
whether that age is inside its stated budget. Statuses: ``ok`` (inside the
fresh budget), ``degraded`` (aging — the connector may be rate-limited or
blocked; downstream surfaces still render but say so), ``stale`` (past the
honesty budget — treat the derived numbers as history, not signal), and
``never`` (no artifact yet — stated, not hidden). Ages come from the
artifacts' own dates; ``now`` is passed in at the boundary so nothing in here
reads the wall clock.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..config import PATHS

#: (display name, inputs/ slug, ok-budget days, degraded-budget days)
FEEDS = [
    ("Trending scanner", "trending-stocks", 2, 7),
    ("Cross-venue divergence", "market-divergence", 2, 7),
    ("Macro nowcast", "macro-nowcast", 7, 21),
    ("Signal composites", "signal-digest", 7, 21),
    ("Media watch", "media-watch", 7, 21),
    ("Research sweep", "research-digest", 7, 30),
    ("Watcher feed", "watchers", 2, 7),
]
#: (display name, tidy-store metric, ok days, degraded days)
STORE_METRICS = [
    ("Reg-SHO short volume", "short_volume_ratio", 5, 15),
    ("Insider cluster buys", "insider_cluster_buys", 7, 21),
]


def _latest_input_date(slug: str, inputs_dir: Path) -> str | None:
    """Newest dated ``inputs/YYYY-MM-DD-<slug>.*`` (json or md)."""
    dates = [p.name[:10] for p in inputs_dir.glob(f"*-{slug}.*")
             if p.suffix in (".json", ".md")]
    return max(dates) if dates else None


def _store_latest_date(store, metric: str) -> str | None:
    try:
        df = store.load()
        sub = df[df["metric"] == metric] if not df.empty else df
        return None if sub.empty else str(sub["date"].max())
    except Exception:  # noqa: BLE001 - an unreadable store is "never", not a crash
        return None


def _row(name: str, source: str, last: str | None, now: date,
         ok_days: int, degraded_days: int) -> dict:
    if last is None:
        return {"name": name, "source": source, "last": None, "age_days": None,
                "status": "never", "note": "never fetched — the surface says so too"}
    try:
        age = (now - date.fromisoformat(last[:10])).days
    except ValueError:
        return {"name": name, "source": source, "last": last, "age_days": None,
                "status": "stale", "note": "unparseable date stamp — treated as stale"}
    if age < 0:
        return {"name": name, "source": source, "last": last, "age_days": age,
                "status": "degraded", "note": "stamped in the future — clock or stamp bug"}
    status = "ok" if age <= ok_days else ("degraded" if age <= degraded_days else "stale")
    note = {"ok": f"fresh (≤{ok_days}d budget)",
            "degraded": f"aging — over the {ok_days}d budget, under {degraded_days}d",
            "stale": f"over the {degraded_days}d honesty budget — history, not signal"}[status]
    return {"name": name, "source": source, "last": last, "age_days": age,
            "status": status, "note": note}


def connector_health(now: date | str, *, inputs_dir: Path | str | None = None,
                     verdicts_dir: Path | str | None = None, store=None) -> list[dict]:
    """One dated, budgeted status row per recurring connector. ``now`` is the
    caller's clock (the boundary); everything else is read from artifact dates."""
    now = date.fromisoformat(str(now)[:10]) if not isinstance(now, date) else now
    inputs_dir = Path(inputs_dir) if inputs_dir else PATHS.inputs
    rows = [_row(name, f"inputs/{slug}", _latest_input_date(slug, inputs_dir),
                 now, ok_d, deg_d)
            for name, slug, ok_d, deg_d in FEEDS]

    vdir = Path(verdicts_dir) if verdicts_dir else (PATHS.root / "data" / "verdicts")
    dated = sorted(p.name[:10] for p in vdir.glob("2*.json")) if vdir.exists() else []
    rows.append(_row("Verdict build", "data/verdicts", dated[-1] if dated else None,
                     now, 2, 7))

    if store is None:
        from ..sources.store import TidyStore

        store = TidyStore()
    rows += [_row(name, f"store/{metric}", _store_latest_date(store, metric),
                  now, ok_d, deg_d)
             for name, metric, ok_d, deg_d in STORE_METRICS]
    return rows
