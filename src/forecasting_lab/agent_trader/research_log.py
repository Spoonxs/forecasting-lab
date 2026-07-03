"""Turn a pasted analyst JSON block into a LOGGED, SCORED forecast — the missing loop.

An LLM stock report feels rigorous but you never learn if it's right. This records each
call's probability that the name **beats the S&P over its horizon**, then — once the
horizon passes — marks it against the real outcome and scores it (Brier + skill vs a coin
flip + hit rate). After ~20 calls you know whether the process beats the market instead of
trusting a confident memo. Deterministic: dates and prices are passed in, never read from
the wall or hallucinated.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ..config import PATHS

BENCHMARK = "^GSPC"  # S&P 500
COLUMNS = ["ticker", "as_of", "horizon_days", "prob_beats_spx", "price", "call",
           "fair_value_base", "thesis", "resolved", "stock_return", "spx_return", "outcome"]


def parse_block(block: str | dict) -> dict:
    """Parse the analyst JSON block into a normalized record. Raises on the essentials."""
    d = json.loads(block) if isinstance(block, str) else dict(block)
    prob = float(d["prob_beats_SPX_12mo"])
    if not 0.0 <= prob <= 1.0:
        raise ValueError(f"prob_beats_SPX_12mo must be in [0,1], got {prob}")
    if not d.get("ticker") or not d.get("as_of"):
        raise ValueError("ticker and as_of are required")
    fv = d.get("fair_value") or {}
    return {
        "ticker": str(d["ticker"]).upper(),
        "as_of": str(d["as_of"]),
        "horizon_days": int(d.get("horizon_days", 365)),
        "prob_beats_spx": prob,
        "price": float(d.get("price", 0) or 0),
        "call": str(d.get("call", "")),
        "fair_value_base": float(fv.get("base", 0) or 0),
        "thesis": str(d.get("one_line_thesis", "")),
        "resolved": False,
        "stock_return": None,
        "spx_return": None,
        "outcome": None,
    }


class ResearchLog:
    """A CSV of research calls, resolvable against real stock-vs-benchmark outcomes."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else PATHS.root / "research_log.csv"

    def to_frame(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=COLUMNS)
        return pd.read_csv(self.path)

    def record(self, block: str | dict) -> dict:
        """Log a call (idempotent on ticker+as_of — a re-record replaces the prior one)."""
        row = parse_block(block)
        df = self.to_frame()
        if not df.empty:
            df = df[~((df["ticker"] == row["ticker"]) & (df["as_of"] == row["as_of"]))]
        out = pd.concat([df, pd.DataFrame([row])], ignore_index=True)[COLUMNS]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(self.path, index=False)
        return row

    def resolve(self, price_at, today: str) -> int:
        """Mark matured calls: outcome=1 if the stock beat the S&P over the horizon.

        ``price_at(symbol, iso_date) -> float | None`` supplies prices (inject a live source
        or a stub). Returns how many rows were newly resolved."""
        df = self.to_frame()
        if df.empty:
            return 0
        today_d = date.fromisoformat(today)
        n = 0
        for i, r in df.iterrows():
            if bool(r.get("resolved")):
                continue
            end = (date.fromisoformat(str(r["as_of"])) + timedelta(days=int(r["horizon_days"]))).isoformat()
            if date.fromisoformat(end) > today_d:
                continue  # not matured yet
            p0, p1 = price_at(r["ticker"], str(r["as_of"])), price_at(r["ticker"], end)
            b0, b1 = price_at(BENCHMARK, str(r["as_of"])), price_at(BENCHMARK, end)
            if None in (p0, p1, b0, b1) or not p0 or not b0:
                continue
            sret, bret = p1 / p0 - 1.0, b1 / b0 - 1.0
            df.at[i, "stock_return"] = round(sret, 4)
            df.at[i, "spx_return"] = round(bret, 4)
            df.at[i, "outcome"] = int(sret > bret)
            df.at[i, "resolved"] = True
            n += 1
        if n:
            df[COLUMNS].to_csv(self.path, index=False)
        return n

    def score(self) -> dict:
        """Brier + skill-vs-coinflip + hit rate over resolved calls."""
        df = self.to_frame()
        res = df[df["resolved"] == True] if not df.empty else df  # noqa: E712
        if res.empty:
            return {"n": 0}
        p = res["prob_beats_spx"].to_numpy(dtype=float)
        y = res["outcome"].to_numpy(dtype=float)
        brier = float(((p - y) ** 2).mean())
        hit = float((((p > 0.5).astype(int)) == y.astype(int)).mean())
        return {
            "n": int(len(res)),
            "brier": round(brier, 4),
            "brier_skill_vs_coinflip": round(1.0 - brier / 0.25, 4),  # 0.25 = Brier of always-0.5
            "hit_rate": round(hit, 4),
            "avg_prob": round(float(p.mean()), 3),
            "win_rate": round(float(y.mean()), 3),
        }


def record_research(block: str | dict, path: Path | str | None = None) -> dict:
    """One-shot: log a pasted research JSON block to the default research log."""
    return ResearchLog(path).record(block)


def default_price_at(symbol: str, iso_date: str) -> float | None:
    """Closing price on or before ``iso_date`` via Yahoo; None when unavailable (blocked)."""
    try:
        from ..signals.trending import TrendingFetcher

        hist = TrendingFetcher().daily_history(symbol, range_="5y")
        if hist.empty:
            return None
        d = hist["date"].astype(str).str[:10]
        on = hist[d <= iso_date]
        return float(on["close"].iloc[-1]) if not on.empty else None
    except Exception:  # noqa: BLE001 - resolution is best-effort; skip when the feed is blocked
        return None


def main(argv=None) -> int:
    """CLI: `python -m forecasting_lab.agent_trader.research_log --json '{...}'`."""
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Log a pasted analyst JSON block as a scored forecast.")
    ap.add_argument("--json", help="the analyst JSON block (or omit to read from stdin)")
    ap.add_argument("--resolve", metavar="TODAY", help="resolve matured calls as of YYYY-MM-DD (live prices)")
    ap.add_argument("--score", action="store_true", help="print the running score and exit")
    args = ap.parse_args(argv)
    log = ResearchLog()
    if args.resolve:
        n = log.resolve(default_price_at, today=args.resolve)
        print(f"resolved {n} matured call(s)")
    if args.score or args.resolve:
        print("score:", json.dumps(log.score()))
        return 0
    raw = args.json or sys.stdin.read()
    row = log.record(raw)
    print(f"logged {row['ticker']} @ {row['as_of']}: P(beats S&P)={row['prob_beats_spx']:.0%}, call={row['call']}")
    print("running score:", json.dumps(log.score()))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
