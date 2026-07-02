"""Transaction-cost models.

Kalshi publishes its fee schedule, so we model it exactly. The general taker fee
is ``0.07 * contracts * price * (1 - price)``, rounded up to the next cent. That
peaks at $0.0175/contract (rounding to $0.02) at the 50c midpoint and shrinks
toward the ends — which is why a divergence edge has to clear *more* fee in the
middle of the book than at the extremes. Maker (resting) orders are free.

Polymarket charges no per-trade fee on the CLOB (gas on Polygon only), so its
default trading fee is zero; model gas separately if you need to.
"""

from __future__ import annotations

import math

KALSHI_FEE_RATE = 0.07


def kalshi_taker_fee_raw(price: float, contracts: float = 1.0) -> float:
    """Un-rounded Kalshi taker fee in dollars. Peaks at 0.0175/contract at p=0.5."""
    if not 0.0 <= price <= 1.0:
        raise ValueError("price must be a probability in [0, 1]")
    return KALSHI_FEE_RATE * contracts * price * (1.0 - price)


def kalshi_taker_fee(price: float, contracts: float = 1.0) -> float:
    """Kalshi taker fee in dollars, rounded up to the next cent (their schedule)."""
    raw = kalshi_taker_fee_raw(price, contracts)
    return math.ceil(raw * 100.0) / 100.0


def polymarket_fee(notional: float = 0.0, fee_bps: float = 0.0) -> float:
    """Polymarket CLOB trading fee. Zero by default (gas is separate)."""
    return abs(notional) * fee_bps / 1e4


def slippage_cost(notional: float, slippage_bps: float = 0.0) -> float:
    """Linear slippage model in basis points of notional traded."""
    return abs(notional) * slippage_bps / 1e4
