"""Watcher templates — "describe what to watch", deterministically (P6d §5).

The Rallies agents shape with our honesty: five TEMPLATES, each a pure
function on injected data, so what fires is reproducible and testable — no
free-text LLM promises (an LLM may later PROPOSE configs; this code runs
them). Every firing is a dated event carrying the stated reason and a content
hash of the exact inputs behind it. Every event is dated by ITS SOURCE's own
date — never the wall clock — and a missing source is an honest, stated skip,
never a fabricated trigger.

Templates:
- ``earnings_proximity`` — a watchlist name reports within N days (fires only
  when an earnings-date source exists; none is connected yet — stated skip);
- ``squeeze_trigger`` — a stated store metric (default: the Reg-SHO daily
  short-volume ratio, the squeeze fuel gauge) crossing a stated threshold;
- ``insider_cluster`` — the V10 distinct-insider cluster-buy count at/over a
  stated minimum;
- ``verdict_change`` — today's artifact vs the prior one: a label change, or a
  score move at/over a stated threshold (the materiality rule);
- ``macro_flip`` — the recession nowcast crossing its stated line either way.

Events land in the alerts digest AND the site feed (both read the JSON this
module writes). PUBLIC data only — watchers never see holdings.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..calibration_log.audit import content_hash
from ..config import PATHS

WATCHER_KINDS = ("earnings_proximity", "squeeze_trigger", "insider_cluster",
                 "verdict_change", "macro_flip")
DEFAULT_CONFIG = {
    "earnings_proximity": {"enabled": True, "days": 3},
    "squeeze_trigger": {"enabled": True, "metric": "short_volume_ratio", "threshold": 0.6},
    "insider_cluster": {"enabled": True, "min_insiders": 3},
    "verdict_change": {"enabled": True, "score_move": 0.15},
    "macro_flip": {"enabled": True, "line": 0.5},
}


def load_config(path: Path | str | None = None) -> dict:
    """data/watchers.json over the defaults; unknown kinds are ignored."""
    path = Path(path) if path else (PATHS.root / "data" / "watchers.json")
    cfg = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}
    try:
        user = json.loads(Path(path).read_text(encoding="utf-8"))
        for kind, opts in user.items():
            if kind in cfg and isinstance(opts, dict):
                cfg[kind].update(opts)
    except (OSError, json.JSONDecodeError, AttributeError):
        pass  # missing/invalid config -> the stated defaults
    return cfg


def _event(kind: str, on: str, reason: str, inputs: dict, symbol: str | None = None) -> dict:
    ev = {"kind": kind, "date": on, "symbol": symbol, "reason": reason,
          "inputs": inputs, "sha256": content_hash(inputs)}
    return ev


# ---------------------------------------------------------------- templates
def earnings_proximity_events(watchlist: list[str], earnings_days: dict,
                              on: str, days: int = 3) -> list[dict]:
    """``earnings_days``: symbol -> days until the report (as of ``on``)."""
    out = []
    for sym in watchlist:
        d = earnings_days.get(sym)
        if d is not None and 0 <= d <= days:
            out.append(_event("earnings_proximity", on,
                              f"{sym} reports in {d}d — the setup may reprice on the print",
                              {"symbol": sym, "days_until": d, "window": days}, symbol=sym))
    return out


def squeeze_trigger_events(scores: dict, on: str, threshold: float,
                           metric: str = "short_volume_ratio") -> list[dict]:
    out = []
    for sym, score in sorted(scores.items()):
        if score >= threshold:
            out.append(_event("squeeze_trigger", on,
                              f"{sym} {metric} {score:.2f} at/over the {threshold:.2f} trigger",
                              {"symbol": sym, "metric": metric, "value": float(score),
                               "threshold": threshold}, symbol=sym))
    return out


def insider_cluster_events(clusters: dict, on: str, min_insiders: int = 3) -> list[dict]:
    """``clusters``: symbol -> distinct insiders buying (the V10 store metric)."""
    out = []
    for sym, n in sorted(clusters.items()):
        if n >= min_insiders:
            out.append(_event("insider_cluster", on,
                              f"{sym}: {int(n)} distinct insiders bought within the window",
                              {"symbol": sym, "n_insiders": int(n),
                               "min_insiders": min_insiders}, symbol=sym))
    return out


def verdict_change_events(payload: dict, prior: dict | None, score_move: float = 0.15) -> list[dict]:
    """A label change, or a score move >= ``score_move``, between two artifacts."""
    if not prior:
        return []
    on = payload.get("as_of", "")
    out = []
    for sym, row in payload.get("verdicts", {}).items():
        old = prior.get("verdicts", {}).get(sym)
        if not old:
            continue
        moved = abs(row.get("score", 0.0) - old.get("score", 0.0))
        if row.get("label") != old.get("label"):
            out.append(_event("verdict_change", on,
                              f"{sym}: {old.get('label')} -> {row.get('label')} "
                              f"(score {old.get('score', 0):+.2f} -> {row.get('score', 0):+.2f})",
                              {"symbol": sym, "from": old.get("label"), "to": row.get("label"),
                               "score_from": old.get("score"), "score_to": row.get("score")},
                              symbol=sym))
        elif moved >= score_move:
            out.append(_event("verdict_change", on,
                              f"{sym}: score moved {row.get('score', 0) - old.get('score', 0):+.2f} "
                              f"(label unchanged: {row.get('label')})",
                              {"symbol": sym, "label": row.get("label"),
                               "score_from": old.get("score"), "score_to": row.get("score"),
                               "threshold": score_move}, symbol=sym))
    return out


def macro_flip_events(prob_now: float, prob_prior: float, on: str, line: float = 0.5) -> list[dict]:
    crossed_up = prob_prior < line <= prob_now
    crossed_down = prob_now < line <= prob_prior
    if not (crossed_up or crossed_down):
        return []
    direction = "above" if crossed_up else "back below"
    return [_event("macro_flip", on,
                   f"recession nowcast crossed {direction} the {line:.0%} line "
                   f"({prob_prior:.0%} -> {prob_now:.0%})",
                   {"prob_now": prob_now, "prob_prior": prob_prior, "line": line})]


# ------------------------------------------------------------------ runner
def run_watchers(config: dict | None = None, *, verdicts_dir=None,
                 inputs_dir=None, store=None, watchlist=None) -> dict:
    """Gather each template's real source and run it. A missing source is an
    honest, stated skip. Every event is dated by its source's own date."""
    cfg = config or load_config()
    events: list[dict] = []
    skips: list[dict] = []

    def skip(kind: str, why: str) -> None:
        skips.append({"kind": kind, "reason": why})

    # earnings proximity: no earnings-date connector exists yet — stated skip
    if cfg["earnings_proximity"]["enabled"]:
        skip("earnings_proximity", "no earnings-date source connected yet — "
                                   "the template is tested and waiting")

    # squeeze trigger + insider clusters: the tidy store's dated facts
    if store is None:
        from ..sources.store import TidyStore

        store = TidyStore()
    for kind, metric_key in (("squeeze_trigger", cfg["squeeze_trigger"]["metric"]),
                             ("insider_cluster", "insider_cluster_buys")):
        if not cfg[kind]["enabled"]:
            continue
        day, values = _store_latest_dated(store, metric_key)
        if not values:
            skip(kind, f"no '{metric_key}' facts in the store yet")
        elif kind == "squeeze_trigger":
            events += squeeze_trigger_events(values, day, cfg[kind]["threshold"],
                                             metric=metric_key)
        else:
            events += insider_cluster_events(values, day, cfg[kind]["min_insiders"])

    # verdict changes: today's artifact vs the prior one
    if cfg["verdict_change"]["enabled"]:
        from .verdicts import load_latest_verdicts

        loaded = load_latest_verdicts(verdicts_dir)
        if loaded.get("empty"):
            skip("verdict_change", "no verdict artifact yet")
        elif not loaded.get("prior"):
            skip("verdict_change", "only one artifact — nothing to compare until tomorrow")
        else:
            events += verdict_change_events(loaded["payload"], loaded["prior"],
                                            cfg["verdict_change"]["score_move"])

    # macro flip: the two newest nowcast sidecars
    if cfg["macro_flip"]["enabled"]:
        probs = _macro_probs(inputs_dir)
        if len(probs) < 2:
            skip("macro_flip", "fewer than two macro-nowcast sidecars — no crossing to detect")
        else:
            (_, p0), (d1, p1) = probs[-2], probs[-1]
            events += macro_flip_events(p1, p0, d1, cfg["macro_flip"]["line"])

    return {"events": events, "skips": skips}


def _store_latest_dated(store, metric: str) -> tuple[str, dict]:
    """(day, entity -> value) for the newest day of a store metric; ('', {})
    when the store has none."""
    try:
        df = store.load()
        sub = df[df["metric"] == metric] if not df.empty else df
        if sub.empty:
            return "", {}
        day = str(sub["date"].max())
        rows = sub[sub["date"] == day]
        return day, {str(e): float(v) for e, v in
                     zip(rows["entity"], rows["value"], strict=False)}
    except Exception:  # noqa: BLE001 - a broken store is a skip, not a crash
        return "", {}


def _macro_probs(inputs_dir=None) -> list[tuple[str, float]]:
    """Dated recession probabilities from every macro-nowcast JSON sidecar.
    The date comes from the PAYLOAD's own fields (as_of / date / freshness
    stamp) before the filename (Codex review) — a renamed or regenerated file
    can't re-date its source."""
    out_dir = Path(inputs_dir) if inputs_dir else PATHS.inputs
    out = []
    for path in sorted(out_dir.glob("*-macro-nowcast.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            prob = payload.get("recession_prob_12m")
            if prob is None:
                continue
            day = str(payload.get("as_of") or payload.get("date")
                      or payload.get("freshness", {}).get("fetched_at", "")
                      or path.name)[:10]
            out.append((day, float(prob)))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    out.sort()
    return out


def write_watchers_feed(result: dict, out_dir=None) -> Path | None:
    """File the run as ``inputs/<date>-watchers.json`` (the site feed + the
    alerts source). Dated by the newest event, else skipped (None) — a run
    with no dated content writes nothing rather than a wall-clock file."""
    dates = [e["date"] for e in result.get("events", []) if e.get("date")]
    if not dates:
        return None
    out_dir = Path(out_dir) if out_dir else PATHS.inputs
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{max(dates)}-watchers.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    return path
