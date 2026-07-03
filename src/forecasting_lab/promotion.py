"""The paper -> live promotion gate — a DECISION, never an order.

This is the phase where the lab actively refuses to do the reckless thing. A
strategy earns the right to be *considered* for real money only if it clears
**six** out-of-sample gates at once; the gate returns a pass/fail and a signed,
dated record explaining exactly why. It does **not** connect to a broker, size a
live position, or place a trade — connecting a broker and risking capital is the
operator's decision, made with a paper-first dry run, at the operator's risk. The
gate's whole job is to make that decision honest and evidence-based instead of a
vibe. Not financial advice.

The six gates (all must hold, out-of-sample):
  1. Deflated Sharpe > 1.0     (real after the multiple-testing penalty)
  2. PBO < 0.2                 (probability of backtest overfitting, CSCV)
  3. >= N real forward marks   (enough genuine out-of-sample evidence)
  4. Brier-skill-vs-market > 0 (beats the market's own price, not a coin flip)
  5. Survives costs + turnover (net-of-fee return positive, turnover under cap)
  6. Risk gate                 (fractional-Kelly <= 1/4, per-name & drawdown &
                                capital caps — the drawdown cap is the kill switch)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import PATHS


@dataclass(frozen=True)
class GateThresholds:
    min_deflated_sharpe: float = 1.0
    max_pbo: float = 0.2
    min_live_marks: int = 20
    min_brier_skill_vs_market: float = 0.0  # must be strictly positive
    max_turnover: float = 2.0
    kelly_cap: float = 0.25                 # fractional Kelly, at most a quarter
    max_name_weight: float = 0.25
    max_drawdown: float = 0.25              # the kill switch
    max_gross_exposure: float = 1.0         # capital cap: no leverage


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PromotionRecord:
    strategy: str
    as_of: str
    passed: bool
    checks: tuple[Check, ...]
    rationale: str
    signature: str

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "as_of": self.as_of,
            "passed": self.passed,
            "checks": [asdict(c) for c in self.checks],
            "rationale": self.rationale,
            "signature": self.signature,
        }


def _signature(strategy: str, as_of: str, checks: list[Check], passed: bool) -> str:
    """A deterministic content signature — the record is tamper-evident, not crypto-signed."""
    payload = json.dumps(
        {"strategy": strategy, "as_of": as_of, "passed": passed,
         "checks": [[c.name, c.passed, c.detail] for c in checks]},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def evaluate_promotion(strategy: str, metrics: dict, as_of: str,
                       thresholds: GateThresholds | None = None) -> PromotionRecord:
    """Run the six gates on a strategy's out-of-sample metrics and return a record.

    ``metrics`` keys (all optional; a missing one fails conservatively): deflated_sharpe,
    pbo, live_marks, brier_skill_vs_market, net_return, turnover, kelly_fraction,
    max_name_weight, max_drawdown, gross_exposure.
    """
    t = thresholds or GateThresholds()
    m = metrics
    checks: list[Check] = []

    ds = float(m.get("deflated_sharpe", 0.0))
    checks.append(Check("Deflated Sharpe", ds > t.min_deflated_sharpe,
                        f"deflated Sharpe {ds:.2f} (need > {t.min_deflated_sharpe})"))

    pbo = float(m.get("pbo", 1.0))
    checks.append(Check("Overfitting (PBO)", pbo < t.max_pbo,
                        f"PBO {pbo:.2f} (need < {t.max_pbo})"))

    marks = int(m.get("live_marks", 0))
    checks.append(Check("Real forward marks", marks >= t.min_live_marks,
                        f"{marks} live marks (need >= {t.min_live_marks})"))

    bs = float(m.get("brier_skill_vs_market", -1.0))
    checks.append(Check("Beats the market", bs > t.min_brier_skill_vs_market,
                        f"Brier-skill-vs-market {bs:+.3f} (need > {t.min_brier_skill_vs_market:.2f})"))

    net = float(m.get("net_return", -1.0))
    turn = float(m.get("turnover", 1e9))
    checks.append(Check("Survives costs + turnover", net > 0.0 and turn <= t.max_turnover,
                        f"net-of-cost return {net:+.1%}, turnover {turn:.2f} (cap {t.max_turnover})"))

    kelly = float(m.get("kelly_fraction", 1.0))
    name_w = float(m.get("max_name_weight", 1.0))
    dd = abs(float(m.get("max_drawdown", 1.0)))
    gross = float(m.get("gross_exposure", 1e9))
    risk_ok = (kelly <= t.kelly_cap and name_w <= t.max_name_weight
               and dd <= t.max_drawdown and gross <= t.max_gross_exposure)
    checks.append(Check("Risk gate", risk_ok,
                        f"Kelly {kelly:.2f} (<= {t.kelly_cap}), per-name {name_w:.2f} (<= {t.max_name_weight}), "
                        f"drawdown {dd:.0%} (<= {t.max_drawdown:.0%}), gross {gross:.2f} (<= {t.max_gross_exposure})"))

    passed = all(c.passed for c in checks)
    n_pass = sum(c.passed for c in checks)
    if passed:
        rationale = (f"PROMOTE {strategy}: all {len(checks)} gates cleared out-of-sample. "
                     "A human decision and a paper-first dry run are still required before any live capital.")
    else:
        failed = [c.name for c in checks if not c.passed]
        rationale = (f"HOLD {strategy}: {n_pass}/{len(checks)} gates passed; "
                     f"blocked by {', '.join(failed)}. Stays on paper.")
    sig = _signature(strategy, as_of, checks, passed)
    return PromotionRecord(strategy, as_of, passed, tuple(checks), rationale, sig)


def write_promotion_record(record: PromotionRecord, path: Path | str | None = None) -> Path:
    """Append a signed, dated promotion record to the (JSONL) promotions log."""
    path = Path(path) if path else PATHS.root / "promotions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict()) + "\n")
    return path
