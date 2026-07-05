"""P5 — the autonomous run loop: one unattended cycle, safe to kill and restart.

Schedule ``run_once`` (cron / systemd timer / a Claude routine) and the system trades on
its own — no human present. The autonomy is real, the discipline is structural:

    reconcile FROM the broker (source of truth after a crash)
      → build the daily brief
      → the team PROPOSES the next strategy version (queued for human sign-off, NOT applied)
      → run the CURRENTLY-APPROVED deterministic strategy → target weights
      → the execution layer vets every order (refusing tool) + idempotent fills
      → mark to market → append a snapshot to the ledger → return it

The LLM never executes; the deterministic strategy does. A re-run with the same ``run_id``
double-submits nothing; a crash mid-cycle is healed by the reconcile step on the next wake.
Runs on paper at full autonomy for weeks before any real capital.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .brief import DailyBrief, build_brief
from .execution import (
    ExecutionLayer,
    PaperBroker,
    RebalanceResult,
    RiskLimits,
    reconcile_from_broker,
)
from .mandate import Rule, check_mandate
from .team import Judge, run_cycle

# The approved, deterministic strategy: brief -> target weights. Injected (this is the
# thing the LLM proposes changes to, never the LLM itself).
Strategy = Callable[[DailyBrief], dict]


def _current_weights(broker: PaperBroker, prices: dict[str, float]) -> dict[str, float]:
    equity = broker.equity(prices)
    if equity <= 0:
        return {}
    return {
        s: (p.qty * prices.get(s, p.avg_price)) / equity for s, p in broker.positions.items()
    }


def append_snapshot(path: Path | str, snapshot: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot) + "\n")
    return path


def run_once(*, ticker: str, judge: Judge, strategy: Strategy, broker: PaperBroker,
             limits: RiskLimits, prices: dict[str, float], run_id: str,
             fetchers: dict | None = None, current_version: str = "v0",
             ledger_path: Path | str | None = None,
             mandate_rules: list[Rule] | None = None,
             sectors: dict[str, str] | None = None,
             audit=None, forecast_log=None, pick_builder=None) -> dict:
    """One unattended cycle → a snapshot. Idempotent on ``run_id``; the LLM never trades.

    V8 hooks: ``audit`` (a ``calibration_log.AuditTrail``) persists the exact
    as-of inputs behind this cycle, keyed by ``run_id``, and the snapshot carries
    their hash; ``pick_builder(brief) -> [Prediction]`` + ``forecast_log`` (a
    ``ForecastLog``) file every pick into the public Brier-scored log so it
    auto-resolves and scores against base rate like everything else.
    """
    # 1. the broker is the source of truth (survive a crash between submit and DB-write)
    reconciled = reconcile_from_broker(broker)

    # 2. the day's brief
    brief = build_brief(ticker, run_id, fetchers or {"price": lambda t: {"last": prices.get(t)}})

    # 3. the team proposes the next version — QUEUED, not applied
    proposal = run_cycle(brief, judge, current_version=current_version)

    # 4. the APPROVED deterministic strategy decides target weights (not the LLM)
    targets = strategy(brief)

    # 5. the mandate check — a BLOCK means no rebalance happens at all
    mandate_report = None
    if mandate_rules:
        mandate_report = check_mandate(
            targets, mandate_rules,
            current_weights=_current_weights(broker, prices), sectors=sectors,
        )

    # 6. execution layer: guardrails as refusing tools + idempotent fills
    if mandate_report is not None and mandate_report.blocked:
        result = RebalanceResult(
            [], halted=True,
            notes=[f"mandate BLOCK: {v}" for v in mandate_report.violations],
        )
    else:
        result = ExecutionLayer(broker, limits, prices).rebalance(targets, run_id)

    # 7. mark + snapshot
    equity = broker.mark(prices)
    snapshot = {
        "run_id": run_id,
        "version_live": current_version,
        "equity": round(equity, 2),
        "halted": result.halted,
        "fills": len([f for f in result.fills if f.status == "filled"]),
        "reconciled_positions": len(reconciled),
        "positions": {s: round(p.qty, 4) for s, p in broker.positions.items()},
        "proposal_queued": {"from_version": proposal.from_version,
                            "changes": proposal.changes, "approved": proposal.approved},
        "notes": result.notes,
    }
    if mandate_report is not None:
        snapshot["mandate"] = {
            "status": mandate_report.status,
            "violations": mandate_report.violations,
            "warnings": mandate_report.warnings,
            "skipped": mandate_report.skipped,
        }

    # V8a: the exact as-of inputs behind this cycle, persisted + hashed
    if audit is not None:
        inputs = {
            "run_id": run_id,
            "ticker": ticker,
            "prices": {k: float(v) for k, v in prices.items()},
            "targets": {k: float(v) for k, v in targets.items()},
            "version_live": current_version,
            "mandate_status": None if mandate_report is None else mandate_report.status,
        }
        snapshot["inputs_sha256"] = audit.record(run_id, inputs, on=run_id)

    # V8b: picks flow into the public Brier-scored forecast log
    if forecast_log is not None and pick_builder is not None:
        ids = []
        for pick in pick_builder(brief):
            note = f"run:{run_id}"
            if "inputs_sha256" in snapshot:
                note += f" audit:{snapshot['inputs_sha256'][:12]}"
            ids.append(forecast_log.record(
                question=pick.label or f"{ticker} pick",
                prob=float(pick.probability),
                venue="agent-desk",
                market_prob=pick.market_implied_prob,
                notes=note,
            ))
        snapshot["forecast_ids"] = ids

    if ledger_path is not None:
        append_snapshot(ledger_path, snapshot)
    return snapshot
