"""Agent investing team (see agent-trader/PLAN.md).

An autonomous, disciplined trading team built ON TOP of the forecasting lab's honesty
core. Cardinal rule: the LLM proposes, deterministic code decides; guardrails are
refusing tools in the execution layer, never prompt text; nothing touches real money
until the promotion gate clears on real forward marks.

P0 lives here: `daily_brief` — the cheap, cached data-aggregation layer an MCP tool
exposes. No LLM or broker code in this package's data layer.
"""

from __future__ import annotations

from .board import render_account
from .brief import BriefSection, DailyBrief, build_brief, daily_brief, default_fetchers
from .execution import ExecutionLayer, Order, PaperBroker, RebalanceResult, RiskLimits
from .fleet import fleet_report, fleet_verdict, promotable_variants, score_fleet
from .gate import gate_fleet_top
from .ladder import LadderState, advance, can_advance
from .loop import run_once
from .team import StrategyProposal, run_cycle

__all__ = [
    # P0 data brief
    "DailyBrief", "BriefSection", "build_brief", "daily_brief", "default_fetchers",
    # P1 team (propose, don't decide)
    "StrategyProposal", "run_cycle",
    # P2 execution layer + paper broker
    "PaperBroker", "ExecutionLayer", "RiskLimits", "Order", "RebalanceResult",
    # P3 parallel fleet, scored for multiple testing
    "score_fleet", "fleet_report", "promotable_variants", "fleet_verdict",
    # P4 promotion gate adapter
    "gate_fleet_top",
    # P5 autonomous run loop
    "run_once",
    # P6 go-live ladder + live board
    "LadderState", "advance", "can_advance", "render_account",
]
