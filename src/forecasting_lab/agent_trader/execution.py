"""P2 — the execution layer: guardrails that REFUSE, plus real-money plumbing.

This is the chokepoint between a strategy's target weights and the broker, and the
place these systems actually blow up. Every limit is enforced here as a *refusing
tool*, not a prompt: an over-sized or over-exposed order is resized or rejected, and
the daily-drawdown **kill switch** halts the whole rebalance — no agent (or human at
2am) can talk past it. It also carries the operator scar list: **idempotent** fills
(a retried run double-submits nothing via ``client_order_id``), **reconcile-from-
broker** (the broker is the source of truth after a crash), and **split adjustment**
(a 4:1 split must not read as a −75% crash and fire an exit).

The ``PaperBroker`` is a deterministic simulation (modeled costs, injected prices) —
no real broker SDK here (pinned in tests). Real execution is a later, gated, human-
confirmed swap of this interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskLimits:
    max_name_weight: float = 0.25      # per-name cap
    max_gross_exposure: float = 1.0    # no leverage
    kelly_cap: float = 0.25            # fractional Kelly
    daily_drawdown_kill: float = 0.08  # halt if down > 8% from the intraday high
    cost_bps: float = 5.0


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float


@dataclass(frozen=True)
class Order:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    client_order_id: str
    stop_loss: float | None = None


@dataclass(frozen=True)
class Fill:
    client_order_id: str
    symbol: str
    side: str
    qty: float
    price: float
    cost: float
    status: str  # "filled" | "duplicate"


@dataclass(frozen=True)
class RebalanceResult:
    fills: list[Fill]
    halted: bool
    notes: list[str] = field(default_factory=list)


class PaperBroker:
    """A deterministic paper broker: cash + positions, idempotent fills, modeled costs."""

    def __init__(self, cash: float = 100_000.0, cost_bps: float = 5.0):
        self.start_cash = cash
        self.cash = cash
        self.cost_bps = cost_bps
        self.positions: dict[str, Position] = {}
        self._filled: dict[str, Fill] = {}  # client_order_id -> Fill (idempotency ledger)
        self.equity_high = cash
        #: symbols whose last mark had no live price (valued at entry — stale, flagged).
        self.last_mark_missing: list[str] = []

    def equity(self, prices: dict[str, float]) -> float:
        mkt = sum(p.qty * prices.get(p.symbol, p.avg_price) for p in self.positions.values())
        return self.cash + mkt

    def mark(self, prices: dict[str, float]) -> float:
        # a held symbol with no price is valued at entry — that staleness must be
        # LOUD, or the position's every loss is invisible (an "immortal" position)
        self.last_mark_missing = sorted(s for s in self.positions if s not in prices)
        eq = self.equity(prices)
        self.equity_high = max(self.equity_high, eq)
        return eq

    def submit(self, order: Order, price: float) -> Fill:
        if order.client_order_id in self._filled:  # idempotent: never double-submit
            prior = self._filled[order.client_order_id]
            return Fill(prior.client_order_id, prior.symbol, prior.side, prior.qty,
                        prior.price, prior.cost, "duplicate")
        cost = abs(order.qty) * price * self.cost_bps / 1e4
        signed = order.qty if order.side == "buy" else -order.qty
        self.cash -= signed * price + cost
        pos = self.positions.get(order.symbol)
        new_qty = (pos.qty if pos else 0.0) + signed
        if abs(new_qty) < 1e-9:
            self.positions.pop(order.symbol, None)
        else:
            avg = price if pos is None or (pos.qty >= 0) != (new_qty >= 0) else pos.avg_price
            self.positions[order.symbol] = Position(order.symbol, new_qty, avg)
        fill = Fill(order.client_order_id, order.symbol, order.side, abs(order.qty), price, cost, "filled")
        self._filled[order.client_order_id] = fill
        return fill

    def apply_split(self, symbol: str, ratio: float) -> None:
        """Adjust a holding for an N:1 split — shares ×ratio, cost ÷ratio, value unchanged."""
        pos = self.positions.get(symbol)
        if pos:
            self.positions[symbol] = Position(symbol, pos.qty * ratio, pos.avg_price / ratio)


def reconcile_from_broker(broker: PaperBroker) -> dict[str, Position]:
    """The broker is the source of truth after a crash between submit and DB-write."""
    return {s: Position(p.symbol, p.qty, p.avg_price) for s, p in broker.positions.items()}


def split_adjusted_day_change(prev_close: float, price: float, split_ratio: float = 1.0) -> float:
    """Day change that accounts for a split, so a 4:1 split reads ~0, not −75%."""
    return (price * split_ratio) / prev_close - 1.0


class ExecutionLayer:
    """Vets and executes target weights against hard limits — the refusing chokepoint."""

    def __init__(self, broker: PaperBroker, limits: RiskLimits, prices: dict[str, float]):
        self.broker = broker
        self.limits = limits
        self.prices = prices

    def kill_switch_tripped(self, equity: float) -> bool:
        high = self.broker.equity_high
        return high > 0 and (high - equity) / high > self.limits.daily_drawdown_kill

    def _capped_targets(self, targets: dict[str, float]) -> tuple[dict[str, float], list[str]]:
        notes: list[str] = []
        capped = {}
        for sym, w in targets.items():
            cw = min(max(w, 0.0), self.limits.max_name_weight)
            if cw != w:
                notes.append(f"{sym}: resized {w:.2f} -> {cw:.2f} (per-name cap)")
            capped[sym] = cw
        gross = sum(capped.values())
        if gross > self.limits.max_gross_exposure and gross > 0:
            scale = self.limits.max_gross_exposure / gross
            capped = {s: w * scale for s, w in capped.items()}
            notes.append(f"gross {gross:.2f} -> {self.limits.max_gross_exposure:.2f} (leverage cap)")
        return capped, notes

    def rebalance(self, targets: dict[str, float], run_id: str) -> RebalanceResult:
        equity = self.broker.mark(self.prices)
        if self.kill_switch_tripped(equity):
            return RebalanceResult([], halted=True, notes=["kill switch: daily drawdown limit breached — HALT"])
        # full rebalance: a held symbol absent from the targets means weight ZERO —
        # anything else leaves "immortal" positions that are never exited
        implied = {s: 0.0 for s in self.broker.positions if s not in targets}
        capped, notes = self._capped_targets({**implied, **targets})
        for sym in self.broker.last_mark_missing:
            notes.append(f"{sym}: stale mark — no live price, valued at entry (flagged)")
        fills: list[Fill] = []
        # exits first, so freed capital is real before new entries are sized
        for sym, w in sorted(capped.items(), key=lambda kv: kv[1]):
            price = self.prices.get(sym)
            held = self.broker.positions.get(sym)
            if price is None:
                if held is not None:
                    notes.append(f"{sym}: cannot exit — no price today (position kept, flagged)")
                else:
                    notes.append(f"{sym}: skipped — no price today")
                continue
            target_qty = (w * equity) / price
            delta = target_qty - (held.qty if held else 0.0)
            if abs(delta) * price < 1.0:  # skip dust
                continue
            side = "buy" if delta > 0 else "sell"
            order = Order(sym, side, abs(delta), client_order_id=f"{run_id}:{sym}",
                          stop_loss=price * 0.92 if side == "buy" else None)
            fills.append(self.broker.submit(order, price))
        return RebalanceResult(fills, halted=False, notes=notes)
