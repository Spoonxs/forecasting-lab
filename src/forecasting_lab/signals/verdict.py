"""The verdict engine — the platform's scoring contract (P6a, PLATFORM_PLAN §1/§9).

A deterministic composite over the lab's existing evidence components produces a
Rallies-scale label (STRONG BUY / BUY / HOLD / TRIM / AVOID) — but the label is
GATED by the four-dial confidence budget (Codex round-1, adopted):

    expected-return lean · drawdown risk · data confidence · model confidence

Below the data-confidence floor there is no Buy/Trim theater: the verdict is
**INSUFFICIENT EVIDENCE**, a first-class label that names exactly what's
missing. Profiles (horizon x goal x risk) re-weight the components
deterministically — the same evidence honestly reads differently for a
6-month trader and a decade-long preserver. A "preserve" profile raises the
cash (HYSA) bar: equities must clear the risk-free yield, not zero.

Corporate actions: prices must be split-adjusted before returns are computed
(:func:`adjusted_returns` — a 4:1 split is not a −75% crash), and a delisted
instrument is INSUFFICIENT EVIDENCE by definition, never a stale verdict.

Everything here is a pure function of its inputs: no wall clock, no network,
no hidden state. Missing components are EXCLUDED and NAMED — never imputed.
This module is the single source of truth; the machine-readable contract that
TIER LIVE's JS mirror consumes is exported from these same tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LABELS = ("STRONG BUY", "BUY", "HOLD", "TRIM", "AVOID")
INSUFFICIENT = "INSUFFICIENT EVIDENCE"

#: base component weights (renormalized over whatever is actually present)
BASE_WEIGHTS: dict[str, float] = {
    "backtest": 0.22,      # walk-forward strategy performance on this name, WITH costs
    "trend": 0.20,         # trend/momentum composite
    "residual_momentum": 0.14,
    "squeeze": 0.08,
    "macro": 0.14,         # regime: recession nowcast / rates context
    "yield": 0.12,         # dividend / distribution yield lean
    "news": 0.10,          # tone — deliberately MINOR (noisy; headlines link out)
}

#: multiplicative profile adjustments (missing key = 1.0)
HORIZON_MULT: dict[str, dict[str, float]] = {
    "0-1y": {"trend": 1.6, "residual_momentum": 1.4, "news": 1.5, "squeeze": 1.5,
             "macro": 0.7, "backtest": 0.9, "yield": 0.5},
    "1-5y": {},
    "5y+": {"trend": 0.6, "residual_momentum": 0.7, "news": 0.4, "squeeze": 0.3,
            "macro": 1.3, "backtest": 1.25, "yield": 1.3},
}
#: exact-year anchors (P10-4): each bucket's multipliers apply AT its anchor
#: year; in between, every component multiplier interpolates LINEARLY. The
#: buckets stay the labeled surface; the years are the continuous engine.
HORIZON_ANCHORS_YEARS: dict[str, float] = {"0-1y": 0.5, "1-5y": 3.0, "5y+": 10.0}
HORIZON_YEARS_MAX = 30.0


def horizon_multipliers_for_years(years: float) -> dict[str, float]:
    """Per-component multipliers for an EXACT horizon: linear interpolation
    between the bucket anchors, clamped to [0, 30] years (beyond the last
    anchor the 5y+ profile holds — nothing is extrapolated)."""
    y = max(0.0, min(HORIZON_YEARS_MAX, float(years)))
    anchors = sorted(HORIZON_ANCHORS_YEARS.items(), key=lambda kv: kv[1])
    names = set()
    for _, m in HORIZON_MULT.items():
        names |= set(m)
    if y <= anchors[0][1]:
        return {n: HORIZON_MULT[anchors[0][0]].get(n, 1.0) for n in names}
    if y >= anchors[-1][1]:
        return {n: HORIZON_MULT[anchors[-1][0]].get(n, 1.0) for n in names}
    for (lo_b, lo_y), (hi_b, hi_y) in zip(anchors, anchors[1:], strict=False):
        if lo_y <= y <= hi_y:
            t = (y - lo_y) / (hi_y - lo_y)
            return {n: (1 - t) * HORIZON_MULT[lo_b].get(n, 1.0)
                       + t * HORIZON_MULT[hi_b].get(n, 1.0) for n in names}
    return dict.fromkeys(names, 1.0)  # pragma: no cover - unreachable


GOAL_MULT: dict[str, dict[str, float]] = {
    "grow": {},
    "income": {"yield": 1.8, "trend": 0.8, "squeeze": 0.5},
    "preserve": {"squeeze": 0.3, "news": 0.6, "macro": 1.3},
}

#: label thresholds on the weighted score (monotone by construction)
THRESHOLDS = ((0.45, "STRONG BUY"), (0.15, "BUY"), (-0.15, "HOLD"), (-0.45, "TRIM"))

#: gates
DATA_CONFIDENCE_FLOOR = 0.40
MODEL_CONFIDENCE_FLOOR = 0.20  # below this OOS-skill confidence: no verdict either
MIN_WEIGHT_COVERAGE = 0.45   # if less than this of the base weight is present -> insufficient
DEFAULT_MODEL_CONFIDENCE = 0.5
#: drawdown penalty per unit of drawdown-risk dial, by risk appetite
RISK_DD_PENALTY = {"low": 0.50, "med": 0.30, "high": 0.15}
#: preserve raises the cash bar: score must clear yield_pct * this factor
PRESERVE_HYSA_BAR_PER_PCT = 0.05


@dataclass(frozen=True)
class Profile:
    horizon: str = "1-5y"   # "0-1y" | "1-5y" | "5y+"
    goal: str = "grow"      # "grow" | "income" | "preserve"
    risk: str = "med"       # "low" | "med" | "high"

    def __post_init__(self) -> None:
        if self.horizon not in HORIZON_MULT:
            raise ValueError(f"unknown horizon {self.horizon!r}")
        if self.goal not in GOAL_MULT:
            raise ValueError(f"unknown goal {self.goal!r}")
        if self.risk not in RISK_DD_PENALTY:
            raise ValueError(f"unknown risk {self.risk!r}")


@dataclass(frozen=True)
class Component:
    """One piece of evidence: a signed lean in [-1, 1] and its own confidence."""

    name: str
    score: float        # signed lean, clamped to [-1, 1]
    confidence: float   # 0..1 — data quality/freshness for THIS component
    detail: str = ""

    def __post_init__(self) -> None:
        if not -1.0 <= float(self.score) <= 1.0:
            raise ValueError(f"{self.name}: score must be in [-1, 1]")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(f"{self.name}: confidence must be in [0, 1]")


@dataclass(frozen=True)
class Verdict:
    label: str
    score: float
    dials: dict            # expected_return, drawdown_risk, data_confidence, model_confidence
    weights_used: dict     # component -> effective (renormalized) weight
    missing: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)
    profile: Profile = field(default_factory=Profile)

    @property
    def insufficient(self) -> bool:
        return self.label == INSUFFICIENT


def profile_weights(profile: Profile) -> dict[str, float]:
    """The contract's effective base weights for a profile (pre-renormalization)."""
    out = {}
    hmult = HORIZON_MULT[profile.horizon]
    gmult = GOAL_MULT[profile.goal]
    for name, base in BASE_WEIGHTS.items():
        out[name] = base * hmult.get(name, 1.0) * gmult.get(name, 1.0)
    return out


def adjusted_returns(closes, split_ratios=None) -> np.ndarray:
    """Daily returns from closes, corrected for splits so a 4:1 split reads ~0.

    ``split_ratios``: optional dict {index_of_split_day: ratio} — the close on
    that day is in post-split units, so the day's return multiplies by ratio.
    """
    p = np.asarray(closes, dtype=float)
    if len(p) < 2:
        return np.array([])
    rets = p[1:] / p[:-1] - 1.0
    for idx, ratio in (split_ratios or {}).items():
        if 1 <= idx < len(p):
            rets[idx - 1] = (p[idx] * float(ratio)) / p[idx - 1] - 1.0
    return rets


def compute_verdict(
    components: dict[str, Component],
    profile: Profile | None = None,
    *,
    drawdown_risk: float = 0.0,          # 0..1 (e.g. |max drawdown| over the window)
    model_confidence: float | None = None,  # 0..1 from OOS skill; None -> derived floor 0.5
    hysa_yield_pct: float | None = None,
    delisted: bool = False,
) -> Verdict:
    """The scoring contract. Pure; every exclusion is named; gates before labels.

    Gate order (also exported in :func:`scoring_contract`): delisted ->
    weight coverage -> data confidence -> model confidence -> label.
    The lean is CONFIDENCE-WEIGHTED: a component's pull is weight x confidence,
    so evidence you can't trust cannot move the number (Codex code review).
    """
    profile = profile or Profile()
    # dial inputs are part of the contract — validate them loudly (Codex review)
    dd = float(drawdown_risk)
    if not 0.0 <= dd <= 1.0 or dd != dd:
        raise ValueError(f"drawdown_risk must be in [0, 1], got {drawdown_risk!r}")
    if model_confidence is not None and not 0.0 <= float(model_confidence) <= 1.0:
        raise ValueError(f"model_confidence must be in [0, 1], got {model_confidence!r}")
    if hysa_yield_pct is not None and float(hysa_yield_pct) < 0.0:
        raise ValueError(f"hysa_yield_pct must be >= 0, got {hysa_yield_pct!r}")
    model_conf = DEFAULT_MODEL_CONFIDENCE if model_confidence is None else float(model_confidence)

    if delisted:
        return Verdict(INSUFFICIENT, 0.0,
                       {"expected_return": 0.0, "drawdown_risk": 1.0,
                        "data_confidence": 0.0, "model_confidence": 0.0},
                       {}, missing=("instrument delisted — no live market",),
                       reasons=("delisted instruments get no verdict",), profile=profile)

    weights = profile_weights(profile)
    present = {n: c for n, c in components.items() if c is not None and n in weights}
    missing = tuple(sorted(set(weights) - set(present)))

    total_base = sum(weights.values())
    covered = sum(weights[n] for n in present)
    coverage = covered / total_base if total_base else 0.0

    if not present or coverage < MIN_WEIGHT_COVERAGE:
        return Verdict(
            INSUFFICIENT, 0.0,
            {"expected_return": 0.0, "drawdown_risk": round(dd, 4),
             "data_confidence": 0.0, "model_confidence": round(model_conf, 4)},
            {}, missing=missing or ("no components provided",),
            reasons=(f"only {coverage:.0%} of the evidence weight is available "
                     f"(floor {MIN_WEIGHT_COVERAGE:.0%})",),
            profile=profile,
        )

    # data confidence: base-weighted mean of component confidences
    data_conf = float(sum(weights[n] * float(present[n].confidence) for n in present) / covered)
    # the lean is confidence-weighted: pull_i = weight_i * confidence_i, then
    # renormalized — zero-confidence evidence cannot move the number
    conf_weight = {n: weights[n] * float(present[n].confidence) for n in present}
    conf_total = sum(conf_weight.values())
    if conf_total <= 0.0:
        used = {n: 0.0 for n in present}
        lean = 0.0
    else:
        used = {n: w / conf_total for n, w in conf_weight.items()}
        lean = float(sum(used[n] * float(present[n].score) for n in present))

    if data_conf < DATA_CONFIDENCE_FLOOR:
        weak = tuple(sorted(n for n in present if present[n].confidence < DATA_CONFIDENCE_FLOOR))
        return Verdict(
            INSUFFICIENT, round(lean, 4),
            {"expected_return": round(lean, 4), "drawdown_risk": round(dd, 4),
             "data_confidence": round(data_conf, 4), "model_confidence": round(model_conf, 4)},
            used, missing=missing + tuple(f"low-confidence: {n}" for n in weak),
            reasons=(f"data confidence {data_conf:.0%} is below the "
                     f"{DATA_CONFIDENCE_FLOOR:.0%} floor",),
            profile=profile,
        )

    if model_conf < MODEL_CONFIDENCE_FLOOR:
        return Verdict(
            INSUFFICIENT, round(lean, 4),
            {"expected_return": round(lean, 4), "drawdown_risk": round(dd, 4),
             "data_confidence": round(data_conf, 4), "model_confidence": round(model_conf, 4)},
            used, missing=missing + ("model unproven out-of-sample",),
            reasons=(f"model confidence {model_conf:.0%} is below the "
                     f"{MODEL_CONFIDENCE_FLOOR:.0%} floor — no verdict on an unproven model",),
            profile=profile,
        )

    # the score the label reads: lean minus the risk-appetite drawdown penalty,
    # minus the cash bar when the goal is preservation
    score = lean - RISK_DD_PENALTY[profile.risk] * dd
    reasons: list[str] = []
    if profile.goal == "preserve" and hysa_yield_pct is not None:
        bar = PRESERVE_HYSA_BAR_PER_PCT * float(hysa_yield_pct)
        score -= bar
        reasons.append(f"preserve profile: score must clear the cash bar "
                       f"({hysa_yield_pct:.2f}% HYSA -> -{bar:.2f})")

    label = "AVOID"
    for threshold, name in THRESHOLDS:
        if score >= threshold:
            label = name
            break

    if missing:
        reasons.append("excluded (no data): " + ", ".join(missing))

    return Verdict(
        label, round(score, 4),
        {"expected_return": round(lean, 4),
         "drawdown_risk": round(dd, 4),
         "data_confidence": round(data_conf, 4),
         "model_confidence": round(model_conf, 4)},
        {n: round(w, 4) for n, w in used.items()},
        missing=missing, reasons=tuple(reasons), profile=profile,
    )


def scoring_contract() -> dict:
    """The machine-readable contract TIER LIVE consumes — exported from the SAME
    tables the engine runs on, so the JS mirror can never drift."""
    return {
        "version": 2,
        "labels": list(LABELS),
        "insufficient_label": INSUFFICIENT,
        "base_weights": dict(BASE_WEIGHTS),
        "horizon_multipliers": {k: dict(v) for k, v in HORIZON_MULT.items()},
        "horizon_anchors_years": dict(HORIZON_ANCHORS_YEARS),
        "horizon_years_max": HORIZON_YEARS_MAX,
        "horizon_interpolation": "linear between anchor years, clamped — beyond "
                                 "the last anchor the 5y+ profile holds; a component "
                                 "missing from a bucket table is implicitly 1.0",
        "goal_multipliers": {k: dict(v) for k, v in GOAL_MULT.items()},
        "thresholds": [[t, name] for t, name in THRESHOLDS],
        "data_confidence_floor": DATA_CONFIDENCE_FLOOR,
        "model_confidence_floor": MODEL_CONFIDENCE_FLOOR,
        "default_model_confidence": DEFAULT_MODEL_CONFIDENCE,
        "min_weight_coverage": MIN_WEIGHT_COVERAGE,
        "risk_drawdown_penalty": dict(RISK_DD_PENALTY),
        "preserve_hysa_bar_per_pct": PRESERVE_HYSA_BAR_PER_PCT,
        # the algorithm itself, spelled out so a JS mirror cannot drift
        # (Codex code review: implicit Python behavior is not a contract)
        "algorithm": {
            "gate_order": ["delisted", "weight_coverage", "data_confidence",
                           "model_confidence", "label"],
            "profile_weight": "w_i = base_weights[i] * horizon_mult.get(i,1) * goal_mult.get(i,1)",
            "coverage": "sum(w_i for present i) / sum(w_i for all i); below min_weight_coverage -> INSUFFICIENT",
            "data_confidence": "sum(w_i * conf_i for present i) / sum(w_i for present i)",
            "lean": "sum(w_i * conf_i * score_i) / sum(w_i * conf_i) — confidence-weighted; zero-confidence evidence has zero pull",
            "score": "lean - risk_drawdown_penalty[risk] * drawdown_risk - (preserve_hysa_bar_per_pct * hysa_yield_pct if goal==preserve and yield known else 0)",
            "label_rule": "first threshold [t, name] with score >= t, top-down; else AVOID",
            "input_ranges": {"component_score": [-1, 1], "component_confidence": [0, 1],
                             "drawdown_risk": [0, 1], "model_confidence": [0, 1],
                             "hysa_yield_pct": ">= 0"},
            "rounding": 4,
        },
        # mutual funds are scored via their ETF twins (P6e §3); the mapping
        # ships IN the contract so no client ever re-hardcodes it
        "mutual_fund_twins": _twin_contract(),
    }


def _twin_contract() -> dict:
    from ..sources.instruments import MUTUAL_FUND_TWINS, fund_twin

    return {f: {k: v for k, v in fund_twin(f).items() if k != "fund"}
            for f in sorted(MUTUAL_FUND_TWINS)}
