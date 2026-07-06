"""TIER FULL verdict computation — the nightly artifact build (P6a step 3).

``flab-verdicts`` renders the full-depth tier: S&P 500 + core ETFs + the latest
trending names + the operator's ``data/watchlist.json`` (~1k symbols). For each,
components are gathered from whatever evidence is actually available — offline
that is honestly little, and the verdict engine says INSUFFICIENT EVIDENCE
rather than inventing a lean. Three artifacts land per run:

- ``data/verdicts/<date>.json`` — every symbol's components, dials, and the
  per-profile label matrix, written as canonical JSON and content-hashed into
  the audit trail (``replay()`` reproduces the bytes or fails loudly);
- ``data/verdicts/contract.json`` — the machine-readable scoring contract,
  exported from the engine's OWN tables (the TIER LIVE JS mirror consumes this
  file and never re-hardcodes a number);
- ``data/ai_opinions/{claude,codex}.json`` — immutable dated opinion artifacts.
  Claude's is generated deterministically from the verdict drivers. Codex's is
  produced by ``codex exec`` when the CLI is available; otherwise the LAST
  committed artifact keeps rendering WITH its date — staleness stated, never
  silent.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date as _date
from pathlib import Path

from ..calibration_log.audit import AuditTrail, canonical_json, content_hash
from ..config import PATHS
from ..signals.verdict import (
    GOAL_MULT,
    HORIZON_MULT,
    Component,
    Profile,
    compute_verdict,
    scoring_contract,
)
from ..sources.instruments import CORE_ETFS, InstrumentRegistry

#: provider signature: symbol -> {component_name: Component | None}
ComponentProvider = Callable[[str], dict[str, Component]]


def default_watchlist_path() -> Path:
    return PATHS.root / "data" / "watchlist.json"


def load_watchlist(path: Path | str | None = None) -> list[str]:
    """Operator watchlist symbols; [] when absent/malformed (never a crash)."""
    path = Path(path) if path is not None else default_watchlist_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        symbols = payload.get("symbols", []) if isinstance(payload, dict) else []
        return [str(s).strip().upper() for s in symbols if str(s).strip()]
    except (OSError, json.JSONDecodeError):
        return []


def tier_full_symbols(
    registry: InstrumentRegistry | None = None,
    watchlist_path: Path | str | None = None,
    trending: list[str] | None = None,
) -> list[str]:
    """The nightly full-depth tier: S&P 500 + core ETFs + trending + watchlist.

    Deduplicated, registry-validated (unknown symbols are dropped — the tier
    never contains names the universe can't identify), deterministic order.
    """
    registry = registry or InstrumentRegistry()
    from ..sources.universe import equity_universe

    symbols: list[str] = []
    seen: set[str] = set()
    for group in (list(CORE_ETFS), load_watchlist(watchlist_path),
                  trending if trending is not None else _latest_trending(),
                  equity_universe()):
        for raw in group:
            inst = registry.get(raw)
            if inst is None or inst.symbol in seen:
                continue
            seen.add(inst.symbol)
            symbols.append(inst.symbol)
    return symbols


def _latest_trending() -> list[str]:
    try:
        from .digest import read_latest_data

        payload = read_latest_data("trending-stocks") or {}
        return [c.get("ticker", "") for c in payload.get("movers", [])]
    except Exception:  # pragma: no cover - defensive
        return []


def default_component_provider(symbol: str) -> dict[str, Component]:
    """Offline-honest default: only evidence that actually exists locally.

    The trending sidecar supplies a trend component for scanned names; the
    macro sidecar supplies the regime for everything. Everything else is
    absent — and the engine will say so. Live builds (cloud) swap in a richer
    provider; the CONTRACT stays identical.
    """
    out: dict[str, Component] = {}
    try:
        from .digest import read_latest_data

        movers = (read_latest_data("trending-stocks") or {}).get("movers", [])
        card = next((c for c in movers
                     if str(c.get("ticker", "")).upper() == symbol.upper()), None)
        if card is not None and card.get("momentum") is not None:
            score = max(-1.0, min(1.0, float(card["momentum"]) / 3.0))
            out["trend"] = Component("trend", score, 0.7,
                                     f"trend composite {card['momentum']:+.2f}")
        macro = read_latest_data("macro-nowcast") or {}
        prob = macro.get("recession_prob_12m")
        if prob is not None:
            out["macro"] = Component("macro", max(-1.0, min(1.0, 0.5 - float(prob))),
                                     0.7, f"recession odds {float(prob):.0%}")
    except Exception:  # pragma: no cover - defensive
        pass
    return out


PROFILE_MATRIX = [
    Profile(horizon=h, goal=g)
    for h in sorted(HORIZON_MULT) for g in sorted(GOAL_MULT)
]


def build_verdicts(
    symbols: list[str],
    provider: ComponentProvider | None = None,
    *,
    hysa_yield_pct: float | None = None,
    on: _date | None = None,
) -> dict:
    """The tier-full payload: per symbol, components + default verdict + the
    label matrix across all nine horizon x goal profiles."""
    provider = provider or default_component_provider
    on = on or _date.today()
    rows: dict[str, dict] = {}
    for symbol in symbols:
        components = {k: v for k, v in provider(symbol).items() if v is not None}
        default = compute_verdict(components, hysa_yield_pct=hysa_yield_pct)
        matrix = {
            f"{p.horizon}|{p.goal}": compute_verdict(
                components, p, hysa_yield_pct=hysa_yield_pct
            ).label
            for p in PROFILE_MATRIX
        }
        rows[symbol] = {
            "components": {
                n: {"score": c.score, "confidence": c.confidence, "detail": c.detail}
                for n, c in components.items()
            },
            "label": default.label,
            "score": default.score,
            "dials": default.dials,
            "missing": list(default.missing),
            "reasons": list(default.reasons),
            "labels_by_profile": matrix,
        }
    return {
        "as_of": on.isoformat(),
        "tier": "full",
        "hysa_yield_pct": hysa_yield_pct,
        "n_symbols": len(rows),
        "verdicts": rows,
    }


def write_verdicts(
    payload: dict,
    out_dir: Path | str | None = None,
    audit: AuditTrail | None = None,
) -> tuple[Path, str]:
    """Write the dated artifact + contract.json, audit-hash the payload."""
    out_dir = Path(out_dir) if out_dir is not None else PATHS.root / "data" / "verdicts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{payload['as_of']}.json"
    path.write_text(canonical_json(payload), encoding="utf-8")
    (out_dir / "contract.json").write_text(canonical_json(scoring_contract()), encoding="utf-8")
    trail = audit or AuditTrail(out_dir / "audit.jsonl")
    sha = trail.record(f"verdicts:{payload['as_of']}", payload, on=payload["as_of"])
    return path, sha


# ------------------------------------------------------------- AI opinions


def write_claude_opinion(
    payload: dict,
    out_dir: Path | str | None = None,
    top_n: int = 10,
) -> Path:
    """Claude's dated opinion artifact, generated DETERMINISTICALLY from the
    verdict drivers (no API call): the top-N scored names with the evidence
    restated and the honest caveat. Immutable: one file per date."""
    out_dir = Path(out_dir) if out_dir is not None else PATHS.root / "data" / "ai_opinions"
    out_dir.mkdir(parents=True, exist_ok=True)
    scored = [(s, r) for s, r in payload["verdicts"].items()
              if r["label"] not in ("INSUFFICIENT EVIDENCE",)]
    scored.sort(key=lambda kv: kv[1]["score"], reverse=True)
    picks = [{
        "symbol": s,
        "label": r["label"],
        "score": r["score"],
        "because": [f"{n}: {c['detail'] or c['score']}" for n, c in r["components"].items()],
    } for s, r in scored[:top_n]]
    artifact = {
        "model": "claude",
        "as_of": payload["as_of"],
        "picks": picks,
        "caveat": ("Deterministic restatement of the verdict engine's evidence — "
                   "a research opinion, scored on the public ledger, not advice."),
    }
    path = out_dir / f"claude-{payload['as_of']}.json"
    path.write_text(canonical_json(artifact), encoding="utf-8")
    (out_dir / "claude.json").write_text(canonical_json(artifact), encoding="utf-8")
    return path


def codex_opinion(
    payload: dict,
    out_dir: Path | str | None = None,
    runner: Callable[[str], str] | None = None,
) -> dict:
    """Codex's opinion artifact. ``runner`` executes the codex CLI and returns
    its text; when unavailable (None result / raise), the LAST committed
    artifact is returned unchanged WITH its original date and a stale flag —
    honest staleness, never silence, never a fabricated refresh."""
    out_dir = Path(out_dir) if out_dir is not None else PATHS.root / "data" / "ai_opinions"
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / "codex.json"
    # NOTE (Codex review): the persisted artifact NEVER contains a "stale"
    # field — staleness is computed at read time from as_of vs the build date,
    # so a file on disk can't claim freshness it doesn't have.
    if runner is not None:
        try:
            summary = {s: r["label"] for s, r in list(payload["verdicts"].items())[:40]}
            text = runner(
                "You are Codex, the second AI on an investment research platform. "
                "Given these deterministic verdicts (symbol -> label), give your "
                "terse opinion: top 5 agreements, top 3 disagreements with one-line "
                "reasons. JSON verdicts: " + json.dumps(summary)
            )
            if text and text.strip():
                artifact = {"model": "codex", "as_of": payload["as_of"],
                            "opinion": text.strip()[:4000]}
                (out_dir / f"codex-{payload['as_of']}.json").write_text(
                    canonical_json(artifact), encoding="utf-8")
                latest.write_text(canonical_json(artifact), encoding="utf-8")
                return {**artifact, "stale": False}
        except Exception:  # noqa: BLE001 - fall through to the committed artifact
            pass
    if latest.exists():
        try:
            prior = json.loads(latest.read_text(encoding="utf-8"))
            return {**prior, "stale": prior.get("as_of") != payload["as_of"]}
        except (OSError, json.JSONDecodeError):
            pass
    return {"model": "codex", "as_of": None, "opinion": None, "stale": True,
            "note": "no codex opinion committed yet — runs when the CLI is available"}


def load_latest_verdicts(out_dir: Path | str | None = None) -> dict:
    """The newest ``data/verdicts/<date>.json`` + the contract + the artifact's
    audit hash, for the pages to render. ``{"empty": True}`` when none exists —
    the pages then degrade honestly (no verdicts yet)."""
    out_dir = Path(out_dir) if out_dir is not None else PATHS.root / "data" / "verdicts"
    dated = sorted(out_dir.glob("2*.json")) if out_dir.exists() else []
    if not dated:
        return {"empty": True}
    try:
        payload = json.loads(dated[-1].read_text(encoding="utf-8"))
        contract_path = out_dir / "contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.exists() \
            else scoring_contract()
    except (OSError, json.JSONDecodeError):
        return {"empty": True}
    return {
        "empty": False,
        "payload": payload,
        "contract": contract,
        "audit_sha": content_hash(payload),
        "prior": _prior_payload(dated),
    }


def _prior_payload(dated: list[Path]) -> dict | None:
    """The second-newest artifact, for the materiality change feed (None if only one)."""
    if len(dated) < 2:
        return None
    try:
        return json.loads(dated[-2].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def verify_contract_roundtrip(out_dir: Path | str | None = None) -> bool:
    """The written contract.json must equal the engine's live export, byte-for-byte."""
    out_dir = Path(out_dir) if out_dir is not None else PATHS.root / "data" / "verdicts"
    written = (out_dir / "contract.json").read_text(encoding="utf-8")
    return written == canonical_json(scoring_contract()) and \
        content_hash(json.loads(written)) == content_hash(scoring_contract())
