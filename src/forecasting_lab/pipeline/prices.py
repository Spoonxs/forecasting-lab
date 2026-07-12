"""The price panel — cached daily closes for the verdict tier (P8-2).

The audit's enabling fix: the verdict provider needs a year of closes for
~540 names nightly, and Yahoo's chart API is unofficial — so the panel is
built to be POLITE and SELF-HEALING rather than fast:

- one CSV per symbol under ``data/prices/`` (gitignored; CI-cached) plus a
  ``panel_meta.json`` manifest — every series labeled with ``last_date``,
  ``fetched_at``, ``source``, ``adjusted``;
- **incremental by default**: full 1y pull only when a symbol has no cache;
  otherwise a trailing pull merged onto the cache; a fresh-today cache is
  skipped entirely;
- **corporate-action self-heal**: if the overlap between cached and fresh
  closes disagrees by >1%, the cache is thrown away and refetched in full
  (splits/dividends re-adjust history);
- **failure isolation**: a symbol that fails is recorded and skipped — and a
  run of consecutive failures opens a circuit breaker that marks the rest
  "not attempted" instead of hammering a down API;
- adjusted closes preferred (Yahoo ``adjclose``) with the choice labeled.

``now`` is always passed in at the boundary — nothing here reads the wall
clock. The run returns a receipt; the provider treats missing series as
missing components, never as zeros.
"""

from __future__ import annotations

import json
import random
import time
from datetime import date
from pathlib import Path

import pandas as pd

from ..config import PATHS

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
FULL_RANGE = "1y"
INCREMENTAL_RANGE = "1mo"
FRESH_DAYS = 0          # only a cache already carrying TODAY's close skips the
                        # fetch (Codex review: yesterday's cache must still pull)
MIN_ROWS = 120          # a usable series for the provider
OVERLAP_TOLERANCE = 0.01
CIRCUIT_BREAK_AFTER = 8  # consecutive failures -> stop hammering
PACING_SECONDS = 0.25    # polite gap between requests (+ jitter)


def panel_dir(root: Path | str | None = None) -> Path:
    return Path(root) if root else (PATHS.data / "prices")


# ------------------------------------------------------------------ fetch
def _fetch_history(http, symbol: str, range_: str) -> tuple[pd.Series, bool] | None:
    """(daily closes, adjusted?) for one symbol — adjusted closes preferred,
    raw close as the labeled fallback. None on any failure."""
    data = http.get_json(CHART_URL.format(symbol=symbol),
                         params={"range": range_, "interval": "1d"})
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return None
    stamps = result.get("timestamp") or []
    ind = result.get("indicators", {})
    adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
    raw = (ind.get("quote") or [{}])[0].get("close")
    closes = adj if adj else raw
    if not stamps or not closes:
        return None
    s = pd.Series(closes, index=pd.to_datetime(stamps, unit="s").date, dtype=float)
    s = s.dropna()
    s.index = [d.isoformat() for d in s.index]
    return (s, bool(adj)) if len(s) else None


# ------------------------------------------------------------------ cache
def _load_series(path: Path) -> pd.Series | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path, dtype={"date": str, "close": float})
    if frame.empty:
        return None
    return pd.Series(frame["close"].to_numpy(), index=frame["date"].tolist())


def _save_series(path: Path, series: pd.Series) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": series.index, "close": series.to_numpy()}).to_csv(
        path, index=False)


def _merge(cached: pd.Series, fresh: pd.Series) -> tuple[pd.Series, bool]:
    """Union of the two, fresh values winning on overlap. Returns (merged,
    overlap_ok): overlap_ok False means the histories disagree materially —
    a corporate action re-adjusted the past and a full refetch is needed."""
    overlap = [d for d in fresh.index if d in cached.index]
    for d in overlap:
        old, new = float(cached[d]), float(fresh[d])
        if old > 0 and abs(new / old - 1.0) > OVERLAP_TOLERANCE:
            return cached, False
    merged = pd.concat([cached[~cached.index.isin(fresh.index)], fresh])
    return merged.sort_index(), True


# ------------------------------------------------------------------ update
def update_panel(symbols: list[str], *, now: date, http=None,
                 root: Path | str | None = None, full: bool = False,
                 pacing: float = PACING_SECONDS) -> dict:
    """Bring the panel up to date for ``symbols``. Returns the run receipt:
    {updated, refetched, skipped_fresh, failed: [{symbol, reason}],
    not_attempted: [...], as_of}. Never raises for a symbol failure."""
    if http is None:
        from ..utils.http import HttpClient

        http = HttpClient()
    root = panel_dir(root)
    meta_path = root / "panel_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}

    receipt = {"as_of": now.isoformat(), "updated": 0, "refetched": 0,
               "skipped_fresh": 0, "failed": [], "not_attempted": []}
    consecutive_failures = 0
    for i, sym in enumerate(symbols):
        if consecutive_failures >= CIRCUIT_BREAK_AFTER:
            receipt["not_attempted"] = list(symbols[i:])
            break
        path = root / f"{sym.upper().replace('/', '_')}.csv"
        # a corrupt cache file or manifest date is that SYMBOL's problem, never
        # the run's (Codex review) — treat it as uncached and refetch in full
        try:
            cached = None if full else _load_series(path)
            last = meta.get(sym, {}).get("last_date")
            fresh_enough = (cached is not None and last
                            and (now - date.fromisoformat(last)).days <= FRESH_DAYS)
        except Exception:  # noqa: BLE001 - corruption -> refetch, not a crash
            cached, fresh_enough = None, False
        if fresh_enough:
            receipt["skipped_fresh"] += 1
            continue
        try:
            if pacing and i:
                time.sleep(pacing + random.random() * pacing)  # noqa: S311 - jitter, not crypto
            fetched = _fetch_history(http, sym,
                                     FULL_RANGE if cached is None else INCREMENTAL_RANGE)
        except Exception as exc:  # noqa: BLE001 - one bad symbol never sinks the run
            receipt["failed"].append({"symbol": sym,
                                      "reason": f"{type(exc).__name__}: {exc}"[:120]})
            consecutive_failures += 1
            continue
        fresh, adjusted = fetched if fetched else (None, False)
        if fresh is None or fresh.empty:
            receipt["failed"].append({"symbol": sym, "reason": "no usable history"})
            consecutive_failures += 1
            continue
        # point-in-time by construction (Codex review): rows dated after `now`
        # never enter the cache, so panel_frame can't leak the future
        fresh = fresh[[d <= now.isoformat() for d in fresh.index]]
        if fresh.empty:
            receipt["failed"].append({"symbol": sym, "reason": "only future-dated rows"})
            consecutive_failures += 1
            continue
        # NOTE: the counter resets only after the symbol FULLY succeeds (below)
        # — a good incremental fetch followed by a failed corporate-action
        # refetch is still a failure and must count toward the breaker
        if cached is None:
            merged, kind = fresh, "updated"
        else:
            merged, overlap_ok = _merge(cached, fresh)
            if not overlap_ok:
                try:  # corporate action re-adjusted the past: full refetch, self-heal
                    refetched = _fetch_history(http, sym, FULL_RANGE)
                except Exception:  # noqa: BLE001
                    refetched = None
                fresh_full, adjusted = refetched if refetched else (None, adjusted)
                if fresh_full is not None and not fresh_full.empty:
                    fresh_full = fresh_full[[d <= now.isoformat() for d in fresh_full.index]]
                if fresh_full is None or fresh_full.empty:
                    receipt["failed"].append({"symbol": sym,
                                              "reason": "overlap mismatch and full refetch failed"})
                    consecutive_failures += 1  # a hammering refetch loop must trip the breaker too
                    continue
                merged, kind = fresh_full, "refetched"
            else:
                merged, kind = merged, "updated"
        _save_series(path, merged)
        meta[sym] = {"last_date": merged.index[-1], "rows": int(len(merged)),
                     "fetched_at": now.isoformat(), "source": "yahoo-chart",
                     "adjusted": bool(adjusted)}
        receipt[kind] += 1
        consecutive_failures = 0

    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")
    return receipt


def panel_frame(symbols: list[str], *, root: Path | str | None = None,
                min_rows: int = MIN_ROWS) -> pd.DataFrame:
    """The aligned close panel for the provider: one column per symbol with a
    usable history; short/missing series are simply absent (missing evidence,
    never zeros)."""
    root = panel_dir(root)
    series = {}
    for sym in symbols:
        s = _load_series(root / f"{sym.upper().replace('/', '_')}.csv")
        if s is not None and len(s) >= min_rows:
            series[sym] = s
    if not series:
        return pd.DataFrame()
    frame = pd.DataFrame(series)
    frame.index.name = "date"
    return frame.sort_index()


def stale_symbols(symbols: list[str], *, now: date,
                  root: Path | str | None = None, max_age_days: int = 5) -> list[str]:
    """Symbols whose cache is older than the budget (or absent) — what the
    coverage manifest reports as 'price data stale/missing'."""
    root = panel_dir(root)
    meta_path = root / "panel_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    out = []
    for sym in symbols:
        last = meta.get(sym, {}).get("last_date")
        if not last or (now - date.fromisoformat(last)).days > max_age_days:
            out.append(sym)
    return out


def weekly_full_refresh_due(*, now: date, root: Path | str | None = None) -> bool:
    """True when the panel hasn't had a FULL refresh in 7 days (corporate
    actions re-adjust history; the incremental path can't see old rows)."""
    marker = panel_dir(root) / "last_full_refresh.txt"
    if not marker.exists():
        return True
    try:
        return (now - date.fromisoformat(marker.read_text(encoding="utf-8").strip())).days >= 7
    except (OSError, ValueError):
        return True


def mark_full_refresh(*, now: date, root: Path | str | None = None) -> None:
    marker = panel_dir(root) / "last_full_refresh.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(now.isoformat(), encoding="utf-8")


def _future_guard(frame: pd.DataFrame, as_of: date) -> pd.DataFrame:
    """Point-in-time pin: nothing dated after ``as_of`` may reach a score."""
    return frame[frame.index <= as_of.isoformat()]
