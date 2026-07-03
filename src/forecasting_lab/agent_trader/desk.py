"""The Agent desk — a paper book on REAL data, so the site shows the agent *doing* things.

It picks stocks from the live trending movers and takes paper positions on the live
Kalshi/Polymarket odds (betting YES/NO by the recalibrated fair value), records each open
in a persistent ledger, marks everything to the current data, and emits a trade blotter.
Honest by construction: **paper only**, a simple deterministic rule (not proven alpha),
and P&L accrues over runs like the forward study — on the first sighting a position is flat
because it was just opened.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import PATHS
from ..eval.recalibration import default_fair_value
from ..predictions import mover_prediction


@dataclass
class Pick:
    kind: str          # "stock" | "market"
    name: str
    side: str          # "long" | "YES" | "NO"
    prob: float        # the agent's odds
    entry: float
    mark: float
    pnl: float         # stock: return; market: implied-prob move in the bet's favour
    move: float        # the name's recent move (colour for the heatmap) — real market data
    thesis: str
    opened: str


class AgentLedger:
    """Persists each open (entry price + date) so P&L accrues across runs."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else PATHS.data / "agent" / "ledger.json"

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, d: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(d), encoding="utf-8")


def build_desk(movers: dict, market_edges: dict, as_of: str, *, ledger: AgentLedger | None = None,
               capital: float = 100_000.0, k_stocks: int = 5, k_markets: int = 6) -> dict:
    """The agent's current book from real movers + real odds, marked to market."""
    led = ledger.load() if ledger else {}
    blotter: list[str] = []
    picks: list[Pick] = []

    # --- stock picks from the live trending scan ---
    for c in ((movers or {}).get("movers") or [])[:k_stocks]:
        t, last = c.get("ticker"), c.get("last")
        if not t or last is None:
            continue
        pred = mover_prediction(c)
        key = f"stock:{t}"
        rec = led.get(key)
        if rec is None:
            led[key] = {"entry": float(last), "opened": as_of}
            why = " + ".join(d.feature for d in pred.drivers[:2])
            blotter.append(f"BUY {t} @ ${float(last):,.2f} — {why}")
        entry = float(led[key]["entry"])
        pnl = float(last) / entry - 1.0 if entry else 0.0
        move = float(c.get("ret_5d", 0) or 0)  # recent move — real market data, colours the heatmap
        picks.append(Pick("stock", t, "long", round(pred.probability, 3), entry, float(last),
                          round(pnl, 4), round(move, 4), pred.label, led[key]["opened"]))

    # --- paper bets on the live prediction markets ---
    live = (market_edges or {}).get("live") or {}
    half = k_markets // 2
    markets = (live.get("poly") or [])[:half] + (live.get("kalshi") or [])[:k_markets - half]
    for m in markets:
        ev, yes = m.get("event"), m.get("yes")
        if not ev or yes is None:
            continue
        fair = default_fair_value(float(yes))
        side = "YES" if fair >= float(yes) else "NO"
        key = f"mkt:{ev[:70]}"
        rec = led.get(key)
        if rec is None:
            led[key] = {"entry": float(yes), "opened": as_of, "side": side}
            blotter.append(f"BET {side} · '{ev[:44]}' @ {float(yes):.0%} (fair {fair:.0%})")
        entry = float(led[key]["entry"])
        side = led[key].get("side", side)
        pnl = (float(yes) - entry) if side == "YES" else (entry - float(yes))
        edge = (fair - float(yes)) if side == "YES" else (float(yes) - fair)
        picks.append(Pick("market", ev, side, round(fair, 3), entry, float(yes),
                          round(pnl, 4), round(edge, 4), f"fair {fair:.0%} vs entry {entry:.0%}", led[key]["opened"]))

    if ledger:
        ledger.save(led)

    stock_pnls = [p.pnl for p in picks if p.kind == "stock"]
    avg = sum(stock_pnls) / len(stock_pnls) if stock_pnls else 0.0
    equity = capital * (1.0 + avg)
    return {
        "as_of": as_of,
        "capital": capital,
        "equity": round(equity, 2),
        "return": round(avg, 4),
        "n_stocks": len(stock_pnls),
        "n_markets": len([p for p in picks if p.kind == "market"]),
        "picks": [asdict(p) for p in picks],
        "blotter": blotter[-8:],
    }
