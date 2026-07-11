"""The regret ledger — every surfaced recommendation scored against the four
honest baselines (P6c section C; operator decision §11).

"Profitable" means beating what you would have done otherwise. Each attractive
verdict the platform surfaces (STRONG BUY / BUY) is recorded with its entry
prices and, once the horizon has elapsed, resolved against:

- **SPY** — just buying the market,
- **HYSA** — parking it in cash at the recorded yield,
- **equal-weight** — naively equal-weighting the whole rated basket,
- **do-nothing** — a 0% return.

Entries are dated, canonical-JSON content-hashed at record time (V8 style) and
verified on every load — a tampered ledger fails loudly, and an entry can never
see its exit prices. Missing exit data leaves an entry open with an honest
``n/a``; nothing is ever fabricated. Before any horizon resolves, the summary
says exactly that: "no resolved horizons yet".
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..config import PATHS
from .audit import content_hash

ATTRACTIVE = ("STRONG BUY", "BUY")
BASELINES = ("spy", "hysa", "equal_weight", "do_nothing")


def _days_between(d0: str, d1: str) -> int:
    return (date.fromisoformat(d1) - date.fromisoformat(d0)).days


def _ret(p0, p1) -> float | None:
    if p0 and p1 and p0 > 0:
        return p1 / p0 - 1.0
    return None


class RegretLedger:
    """Dated, audit-hashed, replayable record of surfaced recommendations."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else (PATHS.data / "regret" / "ledger.json")
        self.entries: list[dict] = []
        if self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))
            self.verify()

    # ---- recording (entry side never sees the future) --------------------
    def record(self, on: str, recommendations: list[dict], prices: dict,
               spy_price: float | None = None, hysa_yield_pct: float | None = None,
               horizon_days: int = 30, basket_symbols: list[str] | None = None) -> list[str]:
        """Open one tracked entry per attractive recommendation.

        ``prices`` maps symbol -> close as of ``on``. The equal-weight basket
        is frozen at entry from ``basket_symbols`` (the RATED universe — Codex
        review: never every ticker that happens to be in the price dict),
        defaulting to the priced symbols. A rec without an entry price is
        skipped (never guessed); a symbol with an open entry at this horizon
        isn't re-opened. Returns the new entry ids."""
        open_keys = {(r["entry"]["symbol"], r["entry"]["horizon_days"])
                     for r in self.entries if "resolution" not in r}
        basket_syms = (sorted({str(s).strip().upper() for s in basket_symbols})
                       if basket_symbols is not None else sorted(prices))
        basket = {s: float(prices[s]) for s in basket_syms if prices.get(s)}
        ids = []
        for rec in recommendations:
            sym = str(rec.get("symbol", "")).strip().upper()
            label = rec.get("label")
            if not sym or label not in ATTRACTIVE or (sym, horizon_days) in open_keys:
                continue
            entry_price = prices.get(sym)
            if not entry_price:
                continue  # no entry anchor -> honestly untrackable, skipped
            entry = {
                "date": on, "symbol": sym, "label": label,
                "score": rec.get("score"), "horizon_days": horizon_days,
                "price": float(entry_price),
                "spy": float(spy_price) if spy_price else None,
                "hysa_yield_pct": float(hysa_yield_pct) if hysa_yield_pct is not None else None,
                "basket": basket,
            }
            row = {"id": f"{on}:{sym}:{horizon_days}d", "entry": entry,
                   "sha256": content_hash(entry)}
            self.entries.append(row)
            open_keys.add((sym, horizon_days))
            ids.append(row["id"])
        return ids

    def record_from_verdicts(self, payload: dict, prices: dict,
                             spy_price: float | None = None,
                             horizon_days: int = 30) -> list[str]:
        """Record every attractive verdict in a P6a artifact payload. The
        equal-weight basket is the RATED universe (INSUFFICIENT excluded),
        never whatever else happens to be in the price dict (Codex review)."""
        verdicts = payload.get("verdicts", {})
        recs = [{"symbol": s, "label": r.get("label"), "score": r.get("score")}
                for s, r in verdicts.items()]
        rated = [s for s, r in verdicts.items()
                 if not str(r.get("label", "")).upper().startswith("INSUFFICIENT")]
        return self.record(payload.get("as_of", ""), recs, prices,
                           spy_price=spy_price,
                           hysa_yield_pct=payload.get("hysa_yield_pct"),
                           horizon_days=horizon_days, basket_symbols=rated)

    def update_from_build(self, payload: dict, prices: dict,
                          price_date: str | None,
                          spy_price: float | None = None) -> dict:
        """The nightly wiring, honestly dated (Codex review): entries open only
        when the closes carry the SAME date as the artifact — stale sidecar
        closes never masquerade as today's entry anchors — and resolutions are
        marked at the closes' OWN date, never the build's."""
        opened: list[str] = []
        resolved: list[dict] = []
        if prices and price_date and price_date == payload.get("as_of"):
            opened = self.record_from_verdicts(payload, prices, spy_price=spy_price)
        if prices and price_date:
            resolved = self.resolve(price_date, prices, spy_price=spy_price)
        return {"opened": opened, "resolved": resolved}

    # ---- resolution (marks arrive later; entries are immutable) ----------
    def resolve(self, on: str, prices: dict, spy_price: float | None = None) -> list[dict]:
        """Resolve every open entry whose horizon has elapsed by ``on``. An
        entry missing its exit price stays open (n/a, never fabricated)."""
        resolved = []
        for row in self.entries:
            if "resolution" in row:
                continue
            e = row["entry"]
            days = _days_between(e["date"], on)
            if days < e["horizon_days"]:
                continue
            rec_ret = _ret(e["price"], prices.get(e["symbol"]))
            if rec_ret is None:
                continue  # no exit mark yet -> stays open
            spy_ret = _ret(e["spy"], spy_price)
            hysa_ret = (e["hysa_yield_pct"] / 100.0 * days / 365.0
                        if e["hysa_yield_pct"] is not None else None)
            # equal-weight demands the FULL frozen basket (Codex review): a
            # partial average silently reweights the baseline — that's a
            # different baseline, so missing any member renders n/a instead.
            ew = [_ret(p0, prices.get(s)) for s, p0 in e["basket"].items()]
            ew_ret = (sum(ew) / len(ew)) if ew and all(r is not None for r in ew) else None
            baselines = {"spy": spy_ret, "hysa": hysa_ret,
                         "equal_weight": ew_ret, "do_nothing": 0.0}
            resolution = {
                "date": on, "days": days, "return": round(rec_ret, 6),
                "baselines": {k: (round(v, 6) if v is not None else None)
                              for k, v in baselines.items()},
                "edge_vs": {k: (round(rec_ret - v, 6) if v is not None else None)
                            for k, v in baselines.items()},
                "beat": {k: (rec_ret > v if v is not None else None)
                         for k, v in baselines.items()},
            }
            row["resolution"] = resolution
            row["resolution_sha256"] = content_hash(resolution)
            resolved.append(row)
        return resolved

    # ---- integrity / persistence -----------------------------------------
    def verify(self) -> None:
        """Every entry (and resolution) must still hash to what was recorded."""
        for row in self.entries:
            if content_hash(row["entry"]) != row["sha256"]:
                raise ValueError(f"regret entry {row['id']!r} fails its hash — edited or corrupt")
            if "resolution" in row and content_hash(row["resolution"]) != row["resolution_sha256"]:
                raise ValueError(f"regret resolution {row['id']!r} fails its hash")

    def save(self) -> None:
        self.verify()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, sort_keys=True), encoding="utf-8")

    # ---- the honest scoreboard --------------------------------------------
    def summary(self) -> dict:
        """Beat-rates + mean edge per baseline over RESOLVED entries only, with
        an honest denominator per baseline (missing baselines don't count as
        wins or losses). Empty -> says so."""
        resolved = [r for r in self.entries if "resolution" in r]
        out = {"recorded": len(self.entries), "resolved": len(resolved),
               "open": len(self.entries) - len(resolved), "baselines": {}}
        if not resolved:
            out["note"] = "no resolved horizons yet"
            return out
        for b in BASELINES:
            marks = [(r["resolution"]["edge_vs"][b], r["resolution"]["beat"][b])
                     for r in resolved if r["resolution"]["beat"][b] is not None]
            if not marks:
                out["baselines"][b] = {"n": 0, "beat_rate": None, "mean_edge": None}
                continue
            out["baselines"][b] = {
                "n": len(marks),
                "beat_rate": round(sum(1 for _, w in marks if w) / len(marks), 4),
                "mean_edge": round(sum(e for e, _ in marks) / len(marks), 6),
            }
        return out
