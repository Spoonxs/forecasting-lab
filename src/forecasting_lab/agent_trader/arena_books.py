"""The AI arena books — Claude vs Codex, raced honestly (P6c section D).

Two AI-built paper books compete on the platform, Rallies-shaped and
Engo-honest:

- **Claude's book** is generated DETERMINISTICALLY from the verdict artifact:
  the top attractive names, weights proportional to score and clipped to the
  written mandate, a stated thesis per pick. Same artifact -> same book ->
  same audit hash.
- **Codex's book** comes from the local ``codex`` CLI when available; a book
  that violates the mandate or fails to parse is REJECTED loudly and the last
  committed artifact renders WITH its original date (staleness computed at
  read, never persisted).
- Every book is an immutable, content-hashed JSON with a **written mandate**
  (fixed caps, scheduled rebalance windows only, costs modeled, no lookahead).
- The :class:`ArenaLedger` marks books forward: picks are dated BEFORE marks
  (entry prices are the first close AFTER the book date — lookahead is
  structurally impossible), rebalances are dated events with receipts, cash
  earns the recorded HYSA yield, and turnover costs are charged.
- **Benchmarks (SPY, HYSA) are always on the board**; a book stays
  ``incubating`` until it has a 7-day track record (Engo honesty); open
  bring-your-own-model slots are real, never fake competitors.

Paper money only — there is no brokerage code here, and none may be added.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ..calibration_log.audit import canonical_json, content_hash
from ..config import PATHS

ATTRACTIVE = ("STRONG BUY", "BUY")
NOTIONAL = 100_000.0  # paper dollars per book, stated on the page
INCUBATION_DAYS = 7   # Engo: no label but "incubating" before a week of marks
BOOK_MANDATE = {
    "max_position_pct": 0.25,
    "min_cash_pct": 0.05,
    "rebalance": "scheduled windows only — with the nightly build, never intraday",
    "cost_bps_per_turnover": 10.0,
    "cash_yield": "idle cash earns the recorded HYSA yield",
    "no_lookahead": "picks are dated before marks; entries fill at the NEXT close",
    "paper_only": True,
}
OPEN_SLOTS = [
    {"owner": "gemini", "status": "open slot", "note": "bring your own model — drops in with a key"},
    {"owner": "grok", "status": "open slot", "note": "bring your own model — drops in with a key"},
    {"owner": "operator", "status": "open slot", "note": "your portfolio can join the race"},
]


def _finish(book: dict) -> dict:
    """Freeze a book: attach the mandate + its content hash (immutable)."""
    book["mandate"] = BOOK_MANDATE
    book["sha256"] = content_hash({k: v for k, v in book.items() if k != "sha256"})
    return book


def _legal(picks: list[dict]) -> tuple[bool, str]:
    """A book is mandate-legal or it doesn't race."""
    if not picks:
        return False, "no picks survived validation — an empty book doesn't race"
    total = 0.0
    for p in picks:
        w = p.get("weight")
        if not p.get("symbol") or not isinstance(w, (int, float)) or w <= 0:
            return False, f"malformed pick: {p!r}"
        if w > BOOK_MANDATE["max_position_pct"] + 1e-9:
            return False, f"{p['symbol']} at {w:.0%} exceeds the {BOOK_MANDATE['max_position_pct']:.0%} cap"
        total += w
    if total > 1.0 - BOOK_MANDATE["min_cash_pct"] + 1e-9:
        return False, f"invested {total:.0%} leaves less than the {BOOK_MANDATE['min_cash_pct']:.0%} cash floor"
    return True, ""


def claude_book(payload: dict, top_n: int = 6) -> dict:
    """Claude's book, deterministically from the verdicts: top attractive names,
    weight proportional to score, clipped to the cap, remainder to cash."""
    scored = sorted(((s, r) for s, r in payload.get("verdicts", {}).items()
                     if r.get("label") in ATTRACTIVE and r.get("score", 0) > 0),
                    key=lambda kv: (-kv[1]["score"], kv[0]))[:top_n]
    budget = 1.0 - BOOK_MANDATE["min_cash_pct"]
    total = sum(r["score"] for _, r in scored) or 1.0
    picks = [{
        "symbol": s,
        "weight": round(min(BOOK_MANDATE["max_position_pct"], budget * r["score"] / total), 4),
        "thesis": f"{r['label']} at {r['score']:+.2f} on the four-dial verdict — "
                  "sized to conviction, capped by the mandate.",
    } for s, r in scored]
    book = {"owner": "claude", "as_of": payload.get("as_of", ""), "picks": picks,
            "cash": round(1.0 - sum(p["weight"] for p in picks), 4),
            "thesis": "Hold the engine's highest-conviction attractive verdicts; "
                      "let cash earn the HYSA yield when conviction is thin."}
    return _finish(book)


def codex_book(payload: dict, out_dir: Path | str | None = None,
               runner: Callable[[str], str] | None = None) -> dict | None:
    """Codex's book via the local CLI; illegal or unparseable output is
    rejected loudly and the last committed artifact renders WITH its date.
    Returns None (an open slot) when neither exists. The persisted artifact
    never carries a staleness flag — that is computed at read time."""
    out_dir = Path(out_dir) if out_dir is not None else PATHS.root / "data" / "arena"
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / "codex-book.json"
    if runner is not None:
        try:
            menu = {s: {"label": r["label"], "score": r["score"]}
                    for s, r in payload.get("verdicts", {}).items()
                    if r.get("label") in ATTRACTIVE}
            text = runner(
                "You are Codex, racing Claude on a paper-trading arena. Build a book "
                "from ONLY these rated names. Mandate: max 25% per position, keep >=5% "
                "cash, at most 8 picks. Reply with ONLY JSON: {\"picks\": [{\"symbol\": "
                "..., \"weight\": 0.0-0.25, \"thesis\": \"one line\"}], \"thesis\": "
                "\"one line for the whole book\"}. Rated names: " + json.dumps(menu)
            )
            raw = text[text.index("{"): text.rindex("}") + 1]
            parsed = json.loads(raw)
            # validated against the ATTRACTIVE menu actually offered — a HOLD or
            # INSUFFICIENT name in the wider artifact is not race-eligible
            picks = [{"symbol": str(p["symbol"]).upper(), "weight": float(p["weight"]),
                      "thesis": str(p.get("thesis", ""))[:300]}
                     for p in parsed.get("picks", [])[:8]
                     if str(p.get("symbol", "")).upper() in menu]
            ok, why = _legal(picks)
            if not ok:
                raise ValueError(f"codex book rejected — {why}")
            book = _finish({"owner": "codex", "as_of": payload.get("as_of", ""),
                            "picks": picks,
                            "cash": round(1.0 - sum(p["weight"] for p in picks), 4),
                            "thesis": str(parsed.get("thesis", ""))[:300]})
            (out_dir / f"codex-book-{book['as_of']}.json").write_text(
                canonical_json(book), encoding="utf-8")
            latest.write_text(canonical_json(book), encoding="utf-8")
            return book
        except Exception:  # noqa: BLE001 - fall through to the committed artifact
            pass
    if latest.exists():
        return json.loads(latest.read_text(encoding="utf-8"))  # renders WITH its date
    return None


# --------------------------------------------------------------- the race
def _days(d0: str, d1: str) -> int:
    return (date.fromisoformat(d1) - date.fromisoformat(d0)).days


class ArenaLedger:
    """Marks the books forward, honestly: dated entries at the NEXT close after
    the book date, rebalance events with receipts, benchmarks always present."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else (PATHS.data / "arena" / "ledger.json")
        self.state: dict[str, dict] = {}
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, sort_keys=True), encoding="utf-8")

    # ---- books enter / rebalance ----------------------------------------
    def upsert_book(self, book: dict) -> None:
        """Adopt a (hashed, dated) book. A changed book is a dated REBALANCE
        event with its receipt; an identical one is a no-op."""
        if not book.get("as_of") or not book.get("sha256"):
            raise ValueError("arena books must be dated and content-hashed")
        st = self.state.get(book["owner"])
        if st and st["book_sha"] == book["sha256"]:
            return
        positions = {p["symbol"]: {"weight": p["weight"], "entry": None, "entry_date": None}
                     for p in book["picks"]}
        old = {s: pos["weight"] for s, pos in (st or {}).get("positions", {}).items()}
        new = {s: pos["weight"] for s, pos in positions.items()}
        turnover = sum(abs(new.get(k, 0.0) - old.get(k, 0.0)) for k in set(old) | set(new))
        event = {"date": book["as_of"], "kind": "rebalance" if st else "created",
                 "sha256": book["sha256"], "turnover": round(turnover, 4)}
        curve = (st or {}).get("curve", [])
        self.state[book["owner"]] = {
            "book_sha": book["sha256"], "as_of": book["as_of"],
            "positions": positions, "cash": book.get("cash", 0.0),
            # prior gains compound through a rebalance: the new snapshot is
            # measured relative to the equity it inherited, never reset to 1.0
            "base": curve[-1]["equity"] if curve else 1.0,
            "cash_accrual": 0.0,
            "pending_cost": BOOK_MANDATE["cost_bps_per_turnover"] / 1e4 * turnover / 2.0 if st else 0.0,
            "curve": curve,
            "events": (st or {}).get("events", []) + [event],
        }

    # ---- daily marks ------------------------------------------------------
    def mark(self, on: str, prices: dict, hysa_yield_pct: float | None = None) -> None:
        """One dated mark: fill entries at the first close AFTER the book date
        (no lookahead), then mark every filled position. Unpriced positions
        stay flat and are flagged — never fabricated. Benchmarks ride along."""
        self._ensure_benchmarks(on)
        for owner, st in self.state.items():
            if owner == "HYSA":
                self._mark_hysa(st, on, hysa_yield_pct)
                continue
            for sym, pos in st["positions"].items():
                if pos["entry"] is None and on > st["as_of"] and prices.get(sym):
                    pos["entry"], pos["entry_date"] = float(prices[sym]), on
            invested = 0.0
            for sym, pos in st["positions"].items():
                if pos["entry"] and prices.get(sym):
                    invested += pos["weight"] * (float(prices[sym]) / pos["entry"])
                else:
                    invested += pos["weight"]  # unfilled/unpriced: flat, flagged in rows()
            last = st["curve"][-1]["date"] if st["curve"] else None
            if hysa_yield_pct is not None and last:
                st["cash_accrual"] += st["cash"] * hysa_yield_pct / 100.0 * max(0, _days(last, on)) / 365.0
            # the turnover toll is PAID OUT OF CASH, so the board's dollars and
            # the ledger's equity are the same accounting, not two stories
            st["cash"] = round(st["cash"] - st["pending_cost"], 10)
            st["pending_cost"] = 0.0
            equity = st.get("base", 1.0) * (invested + st["cash"] + st["cash_accrual"])
            if not st["curve"] or st["curve"][-1]["date"] != on:
                st["curve"].append({"date": on, "equity": round(equity, 6)})

    def _ensure_benchmarks(self, on: str) -> None:
        """SPY and HYSA are ALWAYS on the board (Engo honesty)."""
        if "SPY" not in self.state:
            self.upsert_book(_finish({"owner": "SPY", "as_of": on, "cash": 0.0,
                                      "picks": [{"symbol": "SPY", "weight": 1.0,
                                                 "thesis": "the benchmark: just buy the market"}]}))
        if "HYSA" not in self.state:
            self.state["HYSA"] = {"book_sha": "benchmark", "as_of": on, "positions": {},
                                  "cash": 1.0, "cash_accrual": 0.0, "pending_cost": 0.0,
                                  "curve": [], "events": [{"date": on, "kind": "created",
                                                           "sha256": "benchmark", "turnover": 0.0}]}

    @staticmethod
    def _mark_hysa(st: dict, on: str, hysa_yield_pct: float | None) -> None:
        last = st["curve"][-1]["date"] if st["curve"] else None
        if hysa_yield_pct is not None and last:
            st["cash_accrual"] += hysa_yield_pct / 100.0 * max(0, _days(last, on)) / 365.0
        if not st["curve"] or st["curve"][-1]["date"] != on:
            st["curve"].append({"date": on, "equity": round(1.0 + st["cash_accrual"], 6)})

    # ---- the board ---------------------------------------------------------
    def status(self, owner: str, on: str) -> str:
        """'incubating' until a 7-day track record exists — nothing is labeled
        a winner (or a loser) off three good days."""
        st = self.state.get(owner)
        if not st or not st["curve"]:
            return "incubating"
        return "live" if _days(st["curve"][0]["date"], on) >= INCUBATION_DAYS else "incubating"

    def rows(self, on: str, prices: dict | None = None) -> list[dict]:
        """Rallies-shaped board rows (stock/alloc/entry/notional/worth/P&L per
        position; totals + cash per book) + the open BYOM slots. SPY and HYSA
        benchmark rows are always present."""
        prices = prices or {}
        self._ensure_benchmarks(on)
        out = []
        for owner, st in self.state.items():
            equity = st["curve"][-1]["equity"] if st["curve"] else 1.0
            # dollars scale by the equity the book carried INTO this snapshot —
            # after gains or a rebalance, NOTIONAL*weight alone would fabricate
            # board numbers that disagree with the ledger (Codex review)
            base = st.get("base", 1.0)
            positions = []
            for sym, pos in sorted(st["positions"].items(), key=lambda kv: -kv[1]["weight"]):
                notional = round(NOTIONAL * base * pos["weight"], 2)
                px = prices.get(sym)
                if pos["entry"] and px:
                    worth = round(notional * float(px) / pos["entry"], 2)
                    pnl = round(worth - notional, 2)
                    pnl_pct = round(float(px) / pos["entry"] - 1.0, 4)
                else:
                    worth = pnl = pnl_pct = None  # honest n/a: no entry mark yet
                positions.append({"symbol": sym, "alloc": pos["weight"], "entry": pos["entry"],
                                  "notional": notional, "worth": worth,
                                  "pnl": pnl, "pnl_pct": pnl_pct})
            out.append({
                "owner": owner, "benchmark": owner in ("SPY", "HYSA"),
                "status": "benchmark" if owner in ("SPY", "HYSA") else self.status(owner, on),
                "as_of": st["as_of"], "book_sha": st["book_sha"],
                "positions": positions,
                "cash": round(NOTIONAL * base * (st["cash"] + st["cash_accrual"]), 2),
                "equity": equity,
                "total_pnl": round(NOTIONAL * (equity - 1.0), 2),
                "events": st["events"],
            })
        out.sort(key=lambda r: (r["benchmark"], -r["equity"]))
        return out + [dict(s) for s in OPEN_SLOTS]
