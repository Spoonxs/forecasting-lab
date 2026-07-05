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

import hashlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskLimits:
    max_name_weight: float = 0.25      # per-name cap
    max_gross_exposure: float = 1.0    # no leverage
    kelly_cap: float = 0.25            # fractional Kelly
    daily_drawdown_kill: float = 0.08  # halt if down > 8% from the intraday high
    cost_bps: float = 5.0
    max_spread_pct: float = 0.10       # refuse orders when (ask-bid)/mid exceeds this
    max_pending_age: int = 3           # wait-then-cancel: cycles before an unfilled limit expires


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
    take_profit: float | None = None
    limit: float | None = None   # fill at limit or better, never worse; None = marketable
    bid: float | None = None     # optional quote for the spread gate
    ask: float | None = None

    def payload_hash(self) -> str:
        """Content hash of what the order DOES — the idempotency key's substance.
        A retried identical order dedupes; a changed one under the same id is a bug."""
        blob = f"{self.symbol}|{self.side}|{round(self.qty, 9)}|{self.limit}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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

    def __init__(self, cash: float = 100_000.0, cost_bps: float = 5.0,
                 max_spread_pct: float = 0.10):
        self.start_cash = cash
        self.cash = cash
        self.cost_bps = cost_bps
        self.max_spread_pct = max_spread_pct
        self.positions: dict[str, Position] = {}
        self._filled: dict[str, Fill] = {}  # client_order_id -> Fill (idempotency ledger)
        self._payload: dict[str, str] = {}  # client_order_id -> content hash (mismatch guard)
        self.pending: dict[str, tuple[Order, int]] = {}  # unfilled limits: order, cycles waited
        self.brackets: dict[str, tuple[float | None, float | None]] = {}  # symbol -> (stop, tp)
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
        coid = order.client_order_id
        # content-hash idempotency: nothing under a known id EVER re-executes; an
        # identical retry dedupes quietly, a CHANGED payload dedupes LOUDLY (the
        # status names the mismatch) — never a silent dedupe, never a double fill
        payload = order.payload_hash()
        if coid in self._filled:
            prior = self._filled[coid]
            status = "duplicate"
            if self._payload.get(coid) != payload:
                status = "duplicate:PAYLOAD-MISMATCH — same id, different order; refused"
            return Fill(prior.client_order_id, prior.symbol, prior.side, prior.qty,
                        prior.price, prior.cost, status)
        if coid in self._payload and self._payload[coid] != payload:
            # known (pending) id resubmitted with different content — refuse it
            return Fill(coid, order.symbol, order.side, 0.0, 0.0, 0.0,
                        "rejected:PAYLOAD-MISMATCH — same id, different order")
        self._payload[coid] = payload

        # spread gate: a quote that's 10%+ of mid wide is a market you don't cross
        if order.bid is not None and order.ask is not None:
            mid = (order.bid + order.ask) / 2.0
            if mid <= 0 or (order.ask - order.bid) / mid > self.max_spread_pct:
                return Fill(coid, order.symbol, order.side, 0.0, 0.0, 0.0,
                            f"rejected:spread>{self.max_spread_pct:.0%}-of-mid")

        # limit semantics: fill at limit or better, never worse; unmarketable waits
        if order.limit is not None:
            marketable = price <= order.limit if order.side == "buy" else price >= order.limit
            if not marketable:
                if coid not in self.pending:
                    self.pending[coid] = (order, 0)
                return Fill(coid, order.symbol, order.side, 0.0, 0.0, 0.0, "pending")

        return self._fill(order, price)

    def _fill(self, order: Order, price: float) -> Fill:
        cost = abs(order.qty) * price * self.cost_bps / 1e4
        signed = order.qty if order.side == "buy" else -order.qty
        self.cash -= signed * price + cost
        pos = self.positions.get(order.symbol)
        new_qty = (pos.qty if pos else 0.0) + signed
        if abs(new_qty) < 1e-9:
            self.positions.pop(order.symbol, None)
            self.brackets.pop(order.symbol, None)
        else:
            avg = price if pos is None or (pos.qty >= 0) != (new_qty >= 0) else pos.avg_price
            self.positions[order.symbol] = Position(order.symbol, new_qty, avg)
            if order.stop_loss is not None or order.take_profit is not None:
                self.brackets[order.symbol] = (order.stop_loss, order.take_profit)
        fill = Fill(order.client_order_id, order.symbol, order.side, abs(order.qty), price, cost, "filled")
        self._filled[order.client_order_id] = fill
        self.pending.pop(order.client_order_id, None)
        return fill

    def sweep_pending(self, prices: dict[str, float], max_age: int = 3) -> tuple[list[Fill], list[str]]:
        """Retry unfilled limit orders against today's prices; expire the stale.

        Wait-then-cancel: an order unfilled after ``max_age`` cycles expires with
        a LOUD note instead of chasing the market — never a silent drop.
        """
        fills: list[Fill] = []
        notes: list[str] = []
        for coid, (order, age) in list(self.pending.items()):
            price = prices.get(order.symbol)
            marketable = (
                price is not None
                and order.limit is not None
                and (price <= order.limit if order.side == "buy" else price >= order.limit)
            )
            if marketable:
                fills.append(self._fill(order, float(price)))
                continue
            if age + 1 >= max_age:
                self.pending.pop(coid, None)
                notes.append(
                    f"{order.symbol}: limit {order.side} {coid} expired unfilled after "
                    f"{age + 1} cycles (wait-then-cancel — not chasing)"
                )
            else:
                self.pending[coid] = (order, age + 1)
        return fills, notes

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

    def __init__(self, broker: PaperBroker, limits: RiskLimits, prices: dict[str, float],
                 quotes: dict[str, tuple[float, float]] | None = None,
                 decision_service=None):
        self.broker = broker
        self.limits = limits
        self.prices = prices
        self.quotes = quotes or {}          # symbol -> (bid, ask) for the spread gate
        self.decision_service = decision_service  # healthcheck: orders FAIL CLOSED without it
        broker.max_spread_pct = limits.max_spread_pct

    def kill_switch_tripped(self, equity: float) -> bool:
        high = self.broker.equity_high
        return high > 0 and (high - equity) / high > self.limits.daily_drawdown_kill

    def _check_service(self) -> None:
        """Fail CLOSED: if the decision service is unreachable or unhealthy, every
        order path throws. (The kill switch stays independent of this check.)"""
        if self.decision_service is None:
            return
        try:
            healthy = bool(self.decision_service())
        except Exception as exc:
            raise RuntimeError(f"decision service unreachable — failing closed: {exc}") from exc
        if not healthy:
            raise RuntimeError("decision service reports unhealthy — failing closed, no orders")

    def bracket_exits(self, run_id: str) -> tuple[list[Fill], list[str]]:
        """Deterministic stop-loss / take-profit exits, checked against the MARK
        price (never the fill price) each cycle."""
        fills: list[Fill] = []
        notes: list[str] = []
        for sym, (stop, tp) in list(self.broker.brackets.items()):
            pos = self.broker.positions.get(sym)
            mark = self.prices.get(sym)
            if pos is None or mark is None or pos.qty <= 0:
                continue
            reason = None
            if stop is not None and mark <= stop:
                reason = f"stop-loss {stop:g}"
            elif tp is not None and mark >= tp:
                reason = f"take-profit {tp:g}"
            if reason:
                order = Order(sym, "sell", pos.qty, client_order_id=f"{run_id}:bracket:{sym}")
                fills.append(self.broker.submit(order, float(mark)))
                notes.append(f"{sym}: bracket exit at mark {mark:g} ({reason})")
        return fills, notes

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
        self._check_service()  # fail closed BEFORE any order is built
        fills: list[Fill] = []
        # deterministic bracket exits first (checked on marks), then retry/expire
        # yesterday's unfilled limits (wait-then-cancel), then today's targets
        bracket_fills, notes = self.bracket_exits(run_id)
        fills.extend(bracket_fills)
        swept, sweep_notes = self.broker.sweep_pending(self.prices, self.limits.max_pending_age)
        fills.extend(swept)
        notes.extend(sweep_notes)
        # full rebalance: a held symbol absent from the targets means weight ZERO —
        # anything else leaves "immortal" positions that are never exited
        implied = {s: 0.0 for s in self.broker.positions if s not in targets}
        capped, cap_notes = self._capped_targets({**implied, **targets})
        notes.extend(cap_notes)
        for sym in self.broker.last_mark_missing:
            notes.append(f"{sym}: stale mark — no live price, valued at entry (flagged)")
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
            bid, ask = self.quotes.get(sym, (None, None))
            order = Order(sym, side, abs(delta), client_order_id=f"{run_id}:{sym}",
                          stop_loss=price * 0.92 if side == "buy" else None,
                          limit=price,  # all orders limit-priced: fill at limit or better
                          bid=bid, ask=ask)
            fill = self.broker.submit(order, price)
            fills.append(fill)
            if fill.status.startswith("rejected"):
                notes.append(f"{sym}: order refused — {fill.status}")
        return RebalanceResult(fills, halted=False, notes=notes)
