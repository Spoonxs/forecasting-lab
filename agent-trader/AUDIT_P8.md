# AUDIT_P8 — The Honest Gap Audit & Remediation Program (P8–P10 + R1–R30)

*Authored 2026-07-12 from a measured audit of the live platform, with a Codex
planning consult (its corrections adopted and marked). This is the governing
doc for phases P8–P10 and the thirty review passes. When this doc and the code
disagree, the code is ground truth — update this doc.*

## 1. The audit — measured answers to the operator's questions

**Q: Can you trust its picks / is it a good recommender?**
**A: There are currently NO picks.** The 2026-07-11 nightly artifact rates
**0 of 540 symbols** — every verdict is INSUFFICIENT EVIDENCE and 525/540
carry ZERO components. The honesty gates (coverage ≥45% of weight, confidence
floors) are working exactly as designed; the evidence pipeline feeding them is
starved. Root causes, confirmed in code:
- `pipeline/verdicts.default_component_provider` supplies only **trend** (from
  the trending sidecar, ~15–25 names) and **macro** — but the macro JSON
  sidecar is **never written** (`cli/macro.py --digest` files markdown only).
- **backtest, residual momentum, squeeze, yield, news** are never computed
  nightly, though the machinery exists: `sim.data.real_market` (real Yahoo
  closes), `signals` composites, `ml.factors` residual momentum,
  `sources.instruments.hysa_yield_pct` (FRED), the Reg-SHO store, trending
  headlines.
- Consequence: the regret ledger — the credibility instrument — is empty.
  Nothing is trustable until P8 ships and horizons accrue. The verdicts remain
  the operator's research opinions, never financial advice to anyone else.

**Q: Is it hyperspecific to timeline / risk tolerance?**
A: Bucketed, not specific. horizon(0-1y/1-5y/5y+) × goal × risk × account
works end-to-end (27-profile matrix, client-side relabeling, tax lens). No
exact-year horizons, dollar goals, or contribution planning → P10-4.

**Q: Does it have everything Rallies / Stock Taper / Intel Desk had?**
A: The SHAPES are all there (research sub-tabs, ratings scaffold, arena book
tables with receipts, Brier scorecard, claim-tape receipts, benchmarks always
on the board, question chips, agent templates). The DATA DEPTH is not: no live
prices on pages, no fundamentals (SEC XBRL `companyfacts` is free and unused),
analyst consensus is an honest n/a scaffold (no reliable free source), chat is
CLI-only, watcher config is a raw JSON file → P10.

**Q: Modern UI/UX — GSAP/three.js-grade? Does the landing hit the Sakura bar?**
A: No. App pages are a clean Stock Taper skin but static; the landing is 7KB
of canvas particles — nowhere near Sakura's WebGL depth and scroll
choreography. Was a deliberate no-external-deps constraint; the operator now
wants the glow-up. Resolution: **vendor** GSAP (free license since the Webflow
acquisition) + three.js (MIT) into `site/vendor/` — self-hosted keeps the
no-external-fetch rule → P9.

## 2. Codex consult — corrections adopted

Codex's headline: *"P8 may produce ratings, but not trustworthy ratings"*
without an operational-rigor layer. Adopted:
- **Acceptance gates** per nightly run: % rated, % ≥45% weight coverage,
  median component count, provider-failure count, stale-artifact count.
- **Run manifest** beside every artifact: universe version, per-component
  availability counts, missingness reasons per symbol class.
- **Incremental fetching**: full 1y panel once → trailing ~10d nightly →
  weekly full refresh (corporate actions); chunked 25–50 symbols, backoff +
  jitter, circuit breaker; a failed chunk marks only its symbols unavailable.
- **Point-in-time rules**: never score same-day before close; components only
  from data dated ≤ as_of; walk-forward only; fundamentals by filing
  ACCEPTANCE date; FRED revisions acknowledged (vintage data if historical
  point-in-time claims are ever made).
- **Coverage dashboard**: the site must show WHY a name is unrated, not just
  that it is.
- Versioned sidecar schemas; CI fails loudly on drift. Golden-fixture and
  null-provider tests before any UI work.

## 3. The program

### P8 — MAKE IT ACTUALLY RATE — **BUILT (2026-07-12)**
Live proof on a 60-symbol run: **60/60 rated** (2 STRONG BUY, 18 BUY, 27
HOLD, 10 TRIM, 3 AVOID), gate ok, median 4 components, 0 panel failures,
**27 regret entries opened** anchored to real closes. The full-tier CI run
inherits this via the daily workflow (+ a rolling price-panel cache).

#### the plan as executed
1. **P8-1** macro JSON sidecar from `cli/macro.py --digest` — macro fires for
   every symbol (14% of weight, universally).
2. **P8-2** the price panel: cached/chunked/backoff close-panel fetcher over
   the tier (reuses `sim.data.real_market`'s Yahoo path), incremental nightly,
   weekly full refresh, fetch receipts, per-chunk failure isolation, prices
   labeled as_of/source/adjusted/fetched_at. Cache in `data/prices/`
   (gitignored, CI-cached).
3. **P8-3** the real provider (`pipeline/providers.py`): trend + backtest
   (walk-forward momentum lean, caveated "not yet calibrated") + residual
   momentum (OOS rank-IC gated) + yield (FRED) + news tone + squeeze (store).
   Run manifest written beside the artifact.
4. **P8-4** acceptance gates + the "Why is X unrated?" coverage panel; schema
   versioning. **Gate: ≥60% of the S&P tier rated; regret entries open the
   same night.**
5. **P8-5** golden-fixture/null/deterministic-snapshot tests; docs; push; CI
   green.

### P9 — THE GLOW-UP — **BUILT (2026-07-12)**
Vendored GSAP 3.12.5 + three r160 (licenses committed, served locally); the
landing rebuilt to the storyboard (WebGL card-field hero + wireframe price
surface, ScrollTrigger scenes over REAL artifact numbers, glassy
backdrop-blur nav, twin vertical rails, grain, poster + 2D fallbacks, one
kill-switch); app pages carry the restrained layer. Budgets recorded:
landing HTML 19.6KB (<60KB), JS bundle ~215KB gz (<250KB). Codex fidelity
verdict: techniques 1/2/4/6 at comparable depth; the flagged gaps (glassy
nav, blend-multiply, second rail, mote count) fixed in P9-4.
1. **P9-1** vendor gsap + ScrollTrigger + three (licenses committed); shared
   `motion.js` with a reduced-motion kill-switch; restrained app-page
   micro-interactions (Stock Taper restraint — drama is landing-only).
2. **P9-2** the Sakura-bar landing: three.js generative hero, GSAP scroll
   choreography (verdict card assembles → dials fill → arena race → regret
   receipts), film grain, display serif, 4070 Ti-generated assets. Budgets:
   LCP <2.5s, landing JS <250KB gz; full no-JS/reduced-motion fallback = the
   current static landing. Codex fidelity pass vs SAKURA_TEARDOWN.
3. **P9-3** app polish: hero numbers ease in, gauges sweep, row reveals — no
   fake shimmer over data we already have.

### P10 — PARITY DEPTH
1. **P10-1** in-site chat: client-side deterministic mirror of flab-ask's six
   intents on `desk.html`, Rallies question chips, receipts identical, no LLM.
2. **P10-2** fundamentals tab: SEC XBRL companyfacts (free; ~10 req/s fair
   access; bulk ZIP path available) → revenue/EPS/margins/FCF on ticker pages,
   dated by filing acceptance date.
3. **P10-3** watcher-builder UI (Rallies agent-builder shape): edits the
   committed `data/watchers.json` semantics client-side, emits JSON to commit.
4. **P10-4** profile depth: exact-year horizon (interpolated multipliers,
   contract-exported), optional dollar goal + monthly contribution → honest
   HYSA-baseline compounding comparison (labeled arithmetic, not prediction).
5. **P10-5** live quotes: operator deploys the built CF worker (decision
   recorded 2026-07-12); then TIER LIVE wired fully and verified live.

### R1–R30 — the single-aspect review passes (after P10)
One pass per aspect: audit (Claude + Codex) → fix → pin → one commit
`review(rN-<aspect>)`. Exit: zero open findings, or explicitly waived here
with a written reason.

| # | Aspect | Status |
|---|--------|--------|
| R1 | Data coverage | open |
| R2 | Data freshness | open |
| R3 | Provider failure behavior | open |
| R4 | Point-in-time / lookahead | open |
| R5 | Recommender calibration | open |
| R6 | Missingness/null semantics | open |
| R7 | Receipt completeness | open |
| R8 | Regret-ledger math re-verify | open |
| R9 | Backtest validity | open |
| R10 | Universe/ticker hygiene | open |
| R11 | Fundamentals correctness | open |
| R12 | News-tone quality | open |
| R13 | Chat answer grounding | open |
| R14 | Watcher alert quality | open |
| R15 | Privacy / localStorage | open |
| R16 | XSS / artifact injection | open |
| R17 | CSP / security headers | open |
| R18 | Accessibility + contrast | open |
| R19 | Mobile ergonomics | open |
| R20 | Navigation / search IA | open |
| R21 | Table density / sorting | open |
| R22 | Chart readability | open |
| R23 | Empty / loading / failure states | open |
| R24 | Copy / honesty-language drift | open |
| R25 | Motion / reduced-motion | open |
| R26 | Landing perf budget | open |
| R27 | App-page perf budget | open |
| R28 | Artifact size / repo bloat | open |
| R29 | CI / nightly reliability | open |
| R30 | Docs / runbook accuracy | open |

## 4. Mechanics
Per-phase /goal pastes; ≥1 commit per numbered item; property tests, never
golden numbers; pytest + ruff green per commit; Codex review per commit with a
`Codex-Review:` trailer; push + CI green per phase.
