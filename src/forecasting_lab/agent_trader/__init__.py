"""Agent investing team (see agent-trader/PLAN.md).

An autonomous, disciplined trading team built ON TOP of the forecasting lab's honesty
core. Cardinal rule: the LLM proposes, deterministic code decides; guardrails are
refusing tools in the execution layer, never prompt text; nothing touches real money
until the promotion gate clears on real forward marks.

P0 lives here: `daily_brief` — the cheap, cached data-aggregation layer an MCP tool
exposes. No LLM or broker code in this package's data layer.
"""

from __future__ import annotations

from .brief import BriefSection, DailyBrief, build_brief, daily_brief, default_fetchers
from .execution import ExecutionLayer, Order, PaperBroker, RebalanceResult, RiskLimits
from .team import StrategyProposal, run_cycle

__all__ = ["DailyBrief", "BriefSection", "build_brief", "daily_brief", "default_fetchers",
           "StrategyProposal", "run_cycle",
           "PaperBroker", "ExecutionLayer", "RiskLimits", "Order", "RebalanceResult"]
