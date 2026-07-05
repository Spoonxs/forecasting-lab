# MASTER PLAN — the consolidated build roadmap

*The single plan that consolidates the entire research program (3 rounds: 24 forum
threads, 12 repos line-level, 7 live products walked — Rallies/Stock Taper/Engo
logged-in — plus the L-Z 2012 paper full-text, videos, pastebins, and an independent
verification pass). Everything below is evidence-backed; provenance lives in the docs
listed in §6. Design direction per the operator: **Rallies UI + Stock Taper are the
primary models — use their UI the most**; Intel Desk contributes proof *mechanics* only;
Engo contributes arena/gate *honesty* only. 2026-07-05.*

**The one-line thesis (unchanged, now field-proven):** every competitor either has
beautiful surfaces with zero epistemics (LangAlpha, Rallies, Stock Taper) or real
honesty with niche surfaces (Engo, Intel Desk). Nobody has both. We build the honest
core we already have, wearing the UI people love.

---

## §1 — Product: surfaces & information architecture (Rallies-style)

Adopt Rallies' **feature-per-surface IA** — one crisp surface per job, top-level nav:

| Surface | Job | Powered by (already computed) |
|---|---|---|
| **Today** (`index.html` home) | The daily read: what moved, what the desk did, headline calibration | digests, `AgentLedger`, `calibration_log` |
| **Movers** | Trending names: sparkline cards, peer strips, snapshot tables | `signals/trending`, `sources/*` |
| **Odds** | Live Kalshi/Polymarket picks as evidence cards | `markets/monitor`, `eval/recalibration`, `predictions.py` |
| **Edges** | Edge research triaged into action buckets | `markets/leadlag`, `signals/attention`+`squeeze`, `eval/skill` |
| **Arena** | Strategy race vs benchmark with the gate stated | `sim/`, `eval/deflated`, `forwardtest/` |
| **Scorecard** (`scorecard.html`, NEW) | Public Brier ledger — hits, misses, open horizons | `calibration_log/`, `forwardtest/` |
| **Desk** (`agent.html`) | The live agent terminal | `agent_trader/*` |
| **Macro / Watch** | Recession nowcast · media voices leaderboard | `macro/`, `media/voices` |

Single-file no-build HTML stays; nav can be one page with sticky sections (current
model) rendered in the Rallies layout rhythm — a separate page only where it earns it
(`scorecard.html`, `agent.html`).

## §2 — Design system: Stock Taper skin × Rallies layout

**Skin (Stock Taper — the visual language):** cream `#FBF7EB` paper · white cards with
`#E5E5E5` hairlines · **IBM Plex Mono everywhere** · muted green `#2F7D31` / brick
`#C6392C` · eyebrow tags + heavy uppercase H3s · **one mascot per surface** (🛰️ desk ·
🦅 edges · ⚖️ arena · 🎯 odds · 📡 alerts · 🏛️ congress/insider) · plain-English
question-led sections.

**Layout & components (Rallies — the structure):** generous SaaS spacing and
card-grid rhythm · **peer strips** (horizontal scroll of related names with live %
chips) · **position-level book tables** (ticker · alloc% · P&L · P&L% · notional ·
entry) · **research sub-tab pattern** (Chart / Financials / Insiders / Analyst /
Politicians → our per-entity anchors) · **suggested-question chips** that deep-link to
sections · **filtered activity feed** (All · Fills · Bets · Resolves · Alerts) ·
**visible multi-step plan** in any agent answer ("Building a plan · 4 checks…") + an
"AI can make mistakes" line · **Discover-style theme baskets** (squeeze basket,
momentum basket — honest, already-computed composites).

**Stock Taper components to use heavily:** market-snapshot tables (Buy=green/Sell=red
chips) · financial tables with **▲/▼ per cell** + Quarterly/Annually toggles ·
**"What's going well? / What's concerning?"** pairs under every data panel (text from
`predictions.py` drivers + caveats) · **verdict-header breakdown modal** (`Overall:
Strong · Trend: Improving` + plain-English Q&A rows) · 5-yr-trend-style accordion
("the lab explained") · compare tool with per-dimension verdicts (strategy-vs-strategy)
· evidence-thesis card (WHY NOW → EVIDENCE cited → WATCH FOR ↑ → RED FLAGS ↓ →
confidence dots) — this is `predictions.py` rendered.

**Intel Desk contributes mechanics only, restyled into the above skin:** the **trust
badge** (source count + A/B/C/D reliability + freshness) on every pick · the
**claim-tape receipts drawer** (sources w/ tier + timestamps, contradiction kept on
screen, market-reaction, lead-time) as the upgraded "why" expander · the **Brier
scorecard structure** (hit/miss/inconclusive, calibration gate = only closed horizons
count, **miss ledger pinned**, open horizons under audit) · ACT/VERIFY/PRICE/FADE
buckets on Edges · catch-me-up digest modal · the terminal keeps its dark tape +
RISK-READ chip.

**Engo contributes arena honesty:** benchmark line **always on the board** · the gate
stated in the open ("N candidates · M survive FDR ≤5% · else 100% benchmark") ·
**7-day track-record gate before any strategy appears publicly** · deposit/reset-
adjusted return accounting · sealed-vs-public split if we ever share strategies.

## §3 — Verify the algos & features (the rigor track)

Everything below ships as its own commit with a **property test** (never a golden
number); `pytest` + `ruff check src tests` green before done. Ordered:

**V1. Sarithis leakage/cost test suite** → `tests/` over `ml/features`+`backtest`:
encode the ~30-bug taxonomy (rank-then-trade-same-bar, regime filter on current-day
data, returns paired by position not date, stale-price exits, immortal positions,
ghost weekend bars, `0.0`-is-missing truthiness, first-day-omitted Sharpe/DD,
mis-charged fees). *Done when each bug class has a failing-injection test that passes
against our code.*

**V2. Correlation-aware + shrunk stats** → `eval/`: Bayesian-shrunk win rates,
correlation-adjusted significance, fills-are-not-independent-bets guard (the
crowdintel 20.87-z retraction, verified). *Done when tiny-sample and correlated-fill
injections stop inflating skill.*

**V3. Data-freshness audit layer** → `pipeline/`: every datum carries
`fetched_at`+age; loud failure past its as-of budget; per-source `DataConfidence`
(imputed-fields fraction — Temple-Stuart's one good pattern, verified in code). *Done
when a stale-injection test raises end-to-end.*

**V4. Mandate validator + refuse-uncomputable-metrics** → `agent_trader/execution.py`
+ `eval`/`predictions.py`: deterministic pass/warn/**block** rules (max-position%,
min-cash%, sector caps, forbidden tickers; concentration on *invested* capital; sells
always pass; missing data → skip, never false-block — Velora's `mandate.py`, MIT,
verified at `:32-34`); and refuse any metric not point-in-time computable (no alpha
without a stored entry-date benchmark — Velora `:301`). *Done when a violating
proposal is blocked by code and an un-anchored alpha renders "n/a".*

**V5. Fleet-level FDR + hold-benchmark default** → `agent_trader/fleet.py` +
`promotion.py`: Benjamini-Hochberg-style FDR across the whole strategy fleet on top of
per-strategy deflated-Sharpe/PBO; when nothing survives, the arena's stated allocation
is **100% benchmark** (Engo's "0 survive → 100% SPY", verified live). Add
cross-strategy correlation as a systemic-risk gauge. *Done when a pure-noise fleet
promotes 0 and allocates 100% benchmark; a seeded-skill strategy survives.*

**V6. openfactor factor/residual layer, re-gated** → `ml/`: adopt (Apache-2.0,
verified) the `constrained_lstsq` zero-sum KKT purification, `as_of_price_matrix`
prior-close discipline, MAD-winsorize→z-score prep; consume the free weekly R2
snapshots (1000 US names, 102 factors — grade B+ research data, ~weekly stale, never
intraday). **Replace its in-sample `after_var<before_var` accept gate (verified at
`semantic.py:254`) with `PurgedWalkForwardCV` + `brier_skill_vs`/deflated-Sharpe.**
*Done when residual-ranked IC beats raw-return ranking OOS and null features pin ~0.*

**V7. `signals/deception`** → new: per Larcker-Zakolyukina 2012 (**full text on
disk**, scratchpad `lz2012_fc.md`): restatement labels (3 schemes: material-weakness/
auditor-change/late-filing/8-K · Glass-Lewis · Hennes-Leone-Miller irregularities),
separate CEO/CFO models, the §3 word categories, **AUC vs a random classifier with the
corrected resampled t-test**, scored OOS under purged CV, Brier reported. Expectation
set honestly: 6–16% above-chance *classification* accuracy — a return edge must still
be proven. The "Sonnet-beats-Opus" claim is a hypothesis to test, not evidence. *Done
when shuffled labels pin ~0 skill and the feature shows on Edges with its OOS skill.*

**V8. Track-record loop hardening** → `calibration_log/`+`agent_trader/loop.py`:
every agent pick auto-logged, auto-resolved, Brier-scored vs base rate; **snapshot
audit trail** (the exact as-of data blob behind each pick); blind reasoning-quality
scoring with **subagent isolation** (anonymized inputs, isolated context — the only
defense against training-data leakage, and still the dominant objection everywhere).
Test the **risk-awareness-negative-predictor hypothesis** (legible risks are priced
in) in `eval/recalibration`. *Done when each pick carries snapshot+score and the
hypothesis test runs under purged CV.*

**V9. Execution realism** → `agent_trader/execution.py`: spread <10%-of-mid gate,
limit-only, wait-then-cancel; **fail-closed order tools** (decision service
unreachable → orders throw — openprophet's one good primitive, verified at
`mcp-server.js:1063-1122`); deterministic bracket/trailing exits; content-hash
idempotency so retries never double-book. *Done when a gate-violating or
service-down order attempt is refused in a test.*

**V10. Data breadth** → `sources/`+`signals/squeeze`: Reg-SHO daily short volume +
FTDs + Form-4 cluster-buys (OpenInsider-MCP's endpoints, MIT, all free, freshness
documented per-tool); literature-cited, freshness-caveated descriptions; what-if
**shadow parameter variants** tracked against the same forward marks in
`forwardtest/`. *Done when the new facts land in `TidyStore` dated and lagged.*

## §4 — Build order (phases with done-conditions)

1. **P1 · VERIFY** — V1 V2 V3 V4. The moat hardened first. *Exit: all guardrail
   property tests green.*
2. **P2 · EDGE** — V6 V7 V10 (+V8's hypothesis test). *Exit: each new feature shows
   OOS skill or is honestly pinned at ~0 on the Edges panel.*
3. **P3 · GATE & ARENA** — V5 V8 V9. *Exit: noise-fleet test, benchmark default,
   snapshot trail, fail-closed execution all demonstrated.*
4. **P4 · UI** — the §1/§2 build: Stock Taper skin + Rallies layout reskin of
   `index.html`; `scorecard.html`; evidence cards + trust badges + claim-tape on all
   picks; Engo-style arena board; "going well/concerning" pairs everywhere. *Exit:
   `flab-dashboard` renders the new system; every honest-substance element preserved
   (calibration, why-expanders, not-financial-advice); content never JS-gated.*
5. **P5 · DESK** — terminal upgrades: heartbeat status ("last run / next run"),
   fail-closed pill, mandate desk-notes card, filtered event feed with provenance,
   catch-me-up modal. *Exit: terminal renders live ledger state with trust badges.*

## §5 — What NOT to build (verified negative space)

No live-money auto-trader (every real-money showcase blew up or is tiny-n luck — and
the one "59-0" real-money record is a favorite-longshot streak where one loss erases
~24 wins). No copy-trading (latency-dead). No LLM-as-decider (openprophet's risk caps
were prompt-text theatre — verified). No backtesting LLM agents on memorized dates
(the one unrefuted objection everywhere; `forwardtest/` genuine-OOS only). No
un-scored LLM narrative as signal. No full-Kelly. No fake metrics — if it isn't
point-in-time computable, render "n/a". Cardinal rule everywhere: **LLM proposes,
deterministic code decides; paper until the promotion gate clears + human confirms.**

## §6 — Sources of truth (read before re-deriving anything)

`CONSOLIDATED_RESEARCH_PLAN.md` (round-1, 16 threads) · `SOURCES_ROUND2_ASSESSMENT.md`
+ `DEEP_DIVE_FINDINGS.md`/`_REPOS.md`/`_FORUMS.md` (round-2) · `VERIFICATION_REPORT.md`
(independent re-check; citation caveats + gap closures) · `LANGALPHA_ANALYSIS.md` ·
`design-reference/SITE_BLUEPRINT.md` (35 extracted components) + per-site
`DESIGNS.md`/`FEATURES.md` (stocktaper · inteldesk · rallies) +
`other-uis/ENGO_TEARDOWN.md` · `MASTER_CONTEXT_PROMPT.md` (session handoff).

*Not financial advice. A research and skill-building system.*
