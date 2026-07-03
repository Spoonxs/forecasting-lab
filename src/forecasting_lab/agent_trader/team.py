"""P1 — the agent team: research and PROPOSE, never decide or execute.

The team turns a daily brief into a *proposal to change the versioned, deterministic
strategy* — not an order. Scout finds catalysts, Analyst forms a thesis as a calibrated
`Prediction` (odds + evidence), the Risk officer can veto, the Red team argues the bear
case, and the Portfolio manager writes the proposed config diff for **human sign-off**.
Nothing here touches a broker or places a trade (pinned in tests); the deterministic
strategy engine executes later, on its own.

Model judgment enters through an injected ``Judge`` — the Claude Agent SDK in production,
a deterministic stub in tests — so a full cycle runs offline and reproducibly. That's the
cardinal rule made structural: the LLM proposes, deterministic code decides.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..predictions import Driver, Prediction
from .brief import DailyBrief

# A judge maps (role, context) -> a structured judgment dict.
Judge = Callable[[str, dict], dict]


@dataclass(frozen=True)
class StrategyProposal:
    """A proposed diff to the versioned strategy config — reviewed by a human, then the
    deterministic engine runs it. The team can never set ``approved``."""

    ticker: str
    as_of: str
    from_version: str
    changes: dict            # e.g. {"NVDA": 0.10} target-weight change
    rationale: str
    prediction: Prediction   # the analyst's calibrated odds + evidence
    risk_veto: bool
    risk_reason: str
    red_team: str
    approved: bool = False   # flipped by a human sign-off, never by the team


def _prediction_from(out: dict) -> Prediction:
    drivers = tuple(Driver(str(f), float(v), float(c)) for f, v, c in out.get("drivers", []))
    if not drivers:
        drivers = (Driver("analyst thesis", 1.0, 1.0),)
    return Prediction(
        probability=float(out.get("prob", 0.5)),
        drivers=drivers,
        caveat=str(out.get("caveat", "Analyst thesis — a proposal for human review, not a trade.")),
        label=str(out.get("thesis", "")),
    )


def run_cycle(brief: DailyBrief, judge: Judge, current_version: str = "v0",
              limits: dict | None = None) -> StrategyProposal:
    """One team cycle over a brief → a StrategyProposal (never an order)."""
    ctx = {"brief": brief.to_dict()}
    scout = judge("scout", ctx)
    analyst = judge("analyst", {**ctx, "catalysts": scout.get("catalysts", [])})
    pred = _prediction_from(analyst)
    risk = judge("risk", {"prediction": pred.pct(), "limits": limits or {}})
    red = judge("red_team", {"thesis": pred.label})
    pm = judge("portfolio_manager", {"prediction": pred.pct(), "risk": risk, "red_team": red})
    return StrategyProposal(
        ticker=brief.ticker,
        as_of=brief.as_of,
        from_version=current_version,
        changes=dict(pm.get("changes", {})),
        rationale=str(pm.get("rationale", "")),
        prediction=pred,
        risk_veto=bool(risk.get("veto", False)),
        risk_reason=str(risk.get("reason", "")),
        red_team=str(red.get("counter", "")),
        approved=False,
    )
