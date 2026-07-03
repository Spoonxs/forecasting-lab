# PLAN.md — From paper testing to an honest edge

The goal: turn the lab from "well-calibrated but simulated" into a system that
**finds candidate edges, states each pick's odds with direct evidence, backtests
and paper-trades them under strict anti-overfitting rules, and only then — behind
a hard promotion gate — is a human allowed to risk real money.**

## The honest frame (read first)

- **Calibration ≠ profit.** Being right 30% of the time when you say 30% is table
  stakes; an *edge* means beating the market price after fees. Most rigorous
  attempts find little to none. A clean study that says "no edge" is a *success*.
- **Live money is a human decision with real downside.** This plan builds the
  *evidence and the gate*, not auto-execution. Connecting a broker and sizing risk
  is the operator's call, at the operator's risk. Not financial advice.
- **Evidence is grounded in the research** (`memory` + prior session): the strong
  *leading* signals are **signed/large order flow, cross-venue divergence, and the
  acceleration of attention**; volume levels, follower counts, and raw Elo lag.
  "Ahead-of-the-curve" voices are found by **track record vs. the market price**
  and **timing lead**, not by follower count.

---

## Phase 0 — The evidence layer (foundation, do first)

Make every surfaced pick carry `{prob, edge_vs_market, drivers[], caveat}`.
- A `Prediction` dataclass: probability, the market's implied prob, the signed
  edge, a ranked list of `(feature, value, contribution)` drivers, and a caveat.
- Dashboard renders it per §7 of `design.md`: odds + an expandable "why".
- **Acceptance:** no pick renders without a probability and ≥1 driver; property
  test asserts it.

## Phase 1 — Edge features (evidence-backed, leak-free)

Each ships with a leak-free property test and is scored **Brier/skill vs. the
market price** under `PurgedWalkForwardCV`, never random k-fold.
1. **Cross-venue divergence + lead-lag** — extend `markets/monitor`: matched-event
   implied-prob gap + which venue moved first (rolling lead-lag). Plumbing exists.
2. **Attention-acceleration z-score** — persist per-entity mention counts
   (Google News + Reddit + ~100 voices), compute *rate-of-change* z vs. the
   entity's own baseline, lagged 1 day. Accrues over days like the forward study.
3. **Squeeze-setup composite** — short-interest %float + days-to-cover (free FINRA)
   gated by a volume/gap ignition trigger (the real GameStop shape; fires only when
   both the standing condition and the trigger are present).
4. **Favorite-longshot recalibration** — a free calibration map on raw market odds
   from realized base rates by price bucket.

## Phase 2 — Data pipeline scale (thousands of sources)

- Add sources: FINRA short interest, an options-chain feed (gamma), more
  prediction-market venues, an X/Twitter finance-voice list, more sports leagues.
- **Persistence**: dated sidecars already exist; add a small tidy store so velocity
  / track-record features have history to read (the thing that makes signals work).
- Keep the failure-tolerant orchestrator; every new source degrades honestly.
- **Acceptance:** `flab-sources` reports the expanded count; each new source has a
  connector test and an honest-degradation path.

## Phase 3 — "Who's ahead of the curve" (the Hasan-of-investing feature)

- Log every tracked voice's named tickers/positions with a timestamp.
- Score each voice by **Brier-vs-market at call time** and **timing lead**
  (cross-correlation of their mentions vs. subsequent returns).
- A public **"Early & right" leaderboard**: rank voices by realized track record,
  decay the weight when they regress. Weight by *record*, never by followers.
- **Acceptance:** a voice with random calls scores ~0; the leaderboard is
  reproducible and dated.

## Phase 4 — Backtest → paper → live promotion gate

A strategy may **not** be promoted toward live money unless ALL hold, out-of-sample:
- Deflated Sharpe > **1.0** after the multiple-testing penalty (`eval/deflated`).
- PBO (CSCV) < **0.2**.
- Positive **Brier-skill-vs-market** on ≥ N resolved forward marks (real, not backfilled).
- Survives full modeled costs (`backtest/costs`) and a turnover cap.
- Passes a **risk gate**: position sizing (fractional Kelly ≤ ¼), max per-name
  exposure, a drawdown **kill switch**, and a hard capital cap.
- A signed, dated "promotion record" in the calibration log explaining *why*.

Only after that is broker wiring even *considered* — and that step is the
operator's, with a paper-first dry run. The system's job is to make the gate
honest, not to pull the trigger.

## Phase 5 — UI / motion / evidence surfacing

- Apply `design.md`: editorial + tasteful CSS/SVG motion (chart draw-on, KPI
  count-up), evidence "why" expanders, a "best picks right now" lead module that
  ranks candidates across stocks / sports / markets by edge — each with odds + why.
- Verify every change with browser screenshots (desktop + mobile).

---

## Working rules (every phase)
- Property test per feature (monotonic / zero-sum / calibrated / **leak-free**).
- `pytest` + `ruff check src tests` green before "done".
- Deterministic (explicit seeds, no wall-clock in logic).
- Update `CLAUDE.md` when code and briefs disagree (code is ground truth).
- Guardrails in `CLAUDE.md` are non-negotiable; if a change violates one, stop and flag it.
