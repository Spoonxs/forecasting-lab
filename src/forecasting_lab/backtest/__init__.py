"""Backtesting: realistic costs and walk-forward evaluation.

A frictionless backtest is a fantasy. On Kalshi/Polymarket the fee structure is
known, so there is no excuse not to model it. See ``project-forecasting-lab.md``
and ``ml-system-design.md`` (compare against honest baselines).
"""

from .costs import (
    kalshi_taker_fee,
    kalshi_taker_fee_raw,
    polymarket_fee,
    slippage_cost,
)
from .engine import BacktestResult, walk_forward_backtest

__all__ = [
    "kalshi_taker_fee",
    "kalshi_taker_fee_raw",
    "polymarket_fee",
    "slippage_cost",
    "walk_forward_backtest",
    "BacktestResult",
]
