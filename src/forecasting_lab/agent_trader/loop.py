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
from .execution import ExecutionLayer, PaperBroker, RiskLimits, reconcile_from_broker
from .team import Judge, run_cycle

# The approved, deterministic strategy: brief -> target weights. Injected (this is the
# thing the LLM proposes changes to, never the LLM itself).
Strategy = Callable[[DailyBrief], dict]


def append_snapshot(path: Path | str, snapshot: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot) + "\n")
    return path


def run_once(*, ticker: str, judge: Judge, strategy: Strategy, broker: PaperBroker,
             limits: RiskLimits, prices: dict[str, float], run_id: str,
             fetchers: dict | None = None, current_version: str = "v0",
             ledger_path: Path | str | None = None) -> dict:
    """One unattended cycle → a snapshot. Idempotent on ``run_id``; the LLM never trades."""
    # 1. the broker is the source of truth (survive a crash between submit and DB-write)
    reconciled = reconcile_from_broker(broker)

    # 2. the day's brief
    brief = build_brief(ticker, run_id, fetchers or {"price": lambda t: {"last": prices.get(t)}})

    # 3. the team proposes the next version — QUEUED, not applied
    proposal = run_cycle(brief, judge, current_version=current_version)

    # 4. the APPROVED deterministic strategy decides target weights (not the LLM)
    targets = strategy(brief)

    # 5. execution layer: guardrails as refusing tools + idempotent fills
    result = ExecutionLayer(broker, limits, prices).rebalance(targets, run_id)

    # 6. mark + snapshot
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
    if ledger_path is not None:
        append_snapshot(ledger_path, snapshot)
    return snapshot
