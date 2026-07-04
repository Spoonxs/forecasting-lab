# Consolidated plan — 16 Claude-trading builds, distilled into an honest roadmap

*Deep research across 16 Reddit threads (r/ClaudeAI, r/ClaudeCode) on people building
AI trading / forecasting systems with Claude. Scraped in full via Firecrawl → Redlib
mirrors (post + comments), extracted by four parallel readers, synthesized here against
this lab's existing modules and the six CLAUDE.md guardrails. 2026-07-03.*

The corpus divides cleanly: **the builds show what to make; the comment sections show
why almost all of them are wrong.** The sharpest quant content in every thread is a
skeptic in the replies, not the OP. This plan keeps the reusable engineering and adopts
the critiques *as tests* — which is exactly the lab's existing thesis ("the methodology
is the moat"). Nothing here changes the cardinal rule: **the LLM proposes, deterministic
code decides; paper-first; nothing touches real money until the promotion gate clears.**

---

## 1. The corpus at a glance

| # | Post (short) | What it is | Result claimed | Honest? |
|---|---|---|---|---|
| 01 | Claude Prophet / Open Prophet — 100k options | Claude Code + Alpaca MCP, SQLite vector "decisive actions", `wait`/time tools | +7.6% vs +4.52%, 1 mo, **paper** | Partly — OP says "not proving an edge" |
| 02 | 35k-line credit-spread scanner | Python screen → GPT-4o-mini qualitative score | none (never traded) | Honest about no results |
| 03 | "150 hours later" credit-spread scanner | Python EV screen on ~520 optionable names → CSV/Sheets, Raspberry Pi | none | Honest; caught own PoP math bug |
| 04 | Day-trading via chart screenshots | Manual chat, VWAP/EMA/ADX, no automation | ~breakeven, −$150/4mo | **Very honest** — "LLM bad as a live tool" |
| 05 | "What are people actually doing?" | Discussion thread | anecdotes only | Skeptical/cynical consensus |
| 06 | Session Tracker plugin | Claude Code hooks + Haiku session summaries | n/a (dev utility) | Honest utility |
| 07 | mkash25 Plaid dashboard | Plaid → RSI/MACD/BB enrich → Sonnet JSON advice | none, advisory-only | **Honest** — audit trail, no execution |
| 08 | Klaus Kode | Claude Code SDK agent that builds streaming data apps | n/a (tooling) | Honest tooling |
| 09 | crowdintel — every Polymarket wallet | 1.3B trades on-chain → Postgres MCP, NL→SQL, insider radar | forensic stats | Mixed — **retracted a z-score bug**, promo-heavy |
| 10 | rallies.ai arena — real money to N models | Identical harness+prompt per model, 50+ tools, autopilot copy-trade | 5/N beat S&P, 2 positive, 4 mo | Mixed — concedes tiny-n, conflict of interest |
| 11 | Temple GPT+Claude bot → web app | Next.js, Tastytrade, gate→score→explain, Greeks, VRP thesis | $400→$1.2k/8mo then **1 trade wiped it** | Mixed — admits first double was luck |
| 12 | Opus evaluates 547 reddit recs | Multi-agent blind scoring, out-of-training holdout | AI +5.2% vs +2.4% OOS | Partly — repo reportedly has no Claude calls |
| 13 | margincall.io — 122k-line simulator | TS+Rust/WASM, GARCH, Black-Scholes, procedural econ | n/a (a game) | Honest; **`Sarithis` 30-bug taxonomy in replies** |
| 14 | OpenInsider-MCP | 16-tool MCP: EDGAR Form 4/8-K, FINRA short interest, Reg SHO | n/a (data layer) | **Honest** — raw data, no interpretation |
| 15 | Penny-stock bot in 48h | GCP serverless, Gemini, Kelly sizing, Alpaca paper | none, no repo | Weak — showcase, zero numbers |
| 16 | claudefolio wealth advisor | yfinance+FRED+ECB+Brave → Claude CLI, Telegram, memory | none, advisory | **Honest** — tracks if past recs worked |

---

## 2. The recurring anti-patterns (the scar list everyone hit)

Every one of these is already a CLAUDE.md guardrail. The corpus is empirical proof they
are the exact failure modes — cite these when tempted to cut a corner.

1. **Paper fills ≠ live fills.** (01, 15) "Paper trading gives you favorable fills,
   especially with options… slippage is worse than the calculations." Every showcase
   omitted adverse selection. → Guardrail #3 (model costs); promotion gate "survives
   costs+turnover." **Our `sim/` is honestly labeled a daily-bar sim, not an order book —
   keep it that way and never imply fills are real.**
2. **Luck worn as skill, tiny n.** (10, 11, 12, 01) 4-month down-market windows, n=1 per
   model, "coin-flipping-monkey" survivorship. Post 11's headline double was "pure luck /
   GPT hallucination"; a single later trade wiped 8 months of gains. → Guardrail #4 +
   `eval/deflated` (deflated Sharpe, PBO/CSCV). **This is the single most-repeated
   critique in the corpus and precisely what our credibility core exists to catch.**
3. **Backtest leakage is unavoidable for LLM agents.** (10, 12) The models memorized
   historical prices/events; any backtest on known dates is look-ahead. A statistician in
   (10) and multiple in (12) hammer this. → Guardrail #1/#2; **the answer is our
   `forwardtest/` genuine-forward marking, not backtesting an LLM.** Anonymization tactic
   worth noting: replace dates with round numbers, price with relative change.
4. **Hallucinated inputs and hallucinated tests.** (02, 03, 04, 11) Fabricated IV/vol
   numbers; AFRM "support $40" while strikes are $72.5/$80; a silently-wrong PoP formula
   for a week; GPT "inserting imaginary volatility numbers"; and LLMs faking a passing
   test with truncated "…". → Fix codified in (02): **run the test loop *outside* the LLM
   and feed results to a fresh instance.** Our property-tests + PostToolUse pytest hook
   already enforce this; extend the discipline to any data the agent reports.
5. **Double-counting / independence violations.** (09) crowdintel's headline z-score of
   20.87 was wrong — it counted each order *fill* as a separate bet, and the z-score
   assumed independence across correlated outcomes. → Guardrail #2; **Bayesian-shrunk win
   rates + correlation-aware stats** belong in `eval`.
6. **Non-stationarity / regime change.** (13, 15) "Nailed it for a week, then failed
   miserably — market dynamics change." GARCH "looks perfect then misses regime changes."
   → Purged walk-forward + the forward study over one-shot backtests.
7. **Copy-trading is latency-dead.** (09) By the time an on-chain bet is visible the edge
   is gone — "pennies in front of a steamroller." → Treat wallet-forensics as a
   **defensive toxicity/adverse-selection map, not a copy-list.**
8. **Correlated-agent systemic risk & reflexivity.** (10) Thousands of agents reading the
   same signals → correlated drawdowns; models holding GOOGL/NVDA (their own makers). →
   A genuinely novel metric worth adding: **cross-strategy correlation** as a risk gauge.
9. **"S&P 500 has no edge left."** (11) Large-cap US is thoroughly covered; the only
   defensible edge is a *documented, structural* one (Post 11's volatility risk premium),
   not "AI finds alpha." → Our honest framing; beat a base-rate baseline or say nothing.

---

## 3. Honest primitives worth adopting → mapped to our modules

Ranked by leverage. Each maps to an existing module and a guardrail, so it extends the
lab rather than bolting on a new silo.

| Primitive (source posts) | Adopt into | Why it's honest / what it buys |
|---|---|---|
| **Read-only Postgres/SQL MCP over a facts ledger; NL→SQL** (09) | `sources/store.TidyStore`, calibration analysis | Ask questions of our dated `(date,entity,metric,value)` facts; agent writes the query, code runs it. LLM proposes, code executes. |
| **Recommendation → later-resolution track-record loop + memory** (16, 03, 02) | `calibration_log/`, `media/voices` | The best idea in the corpus and we already have the spine. Every pick logged, auto-resolved, Brier-scored vs base rate. Validates building it out. |
| **Blind reasoning-quality scoring (strip social proof), multi-dim rubric, per-dim return attribution** (12) | `predictions.py` drivers, `media/voices` | Score argument quality, not popularity; then attribute realized return to each dimension. Finding: "risk-awareness" was the *worst* return predictor — legible risk is already priced. |
| **Out-of-training-window holdout as the honest test** (12, 10) | `forwardtest/`, `ml.PurgedWalkForwardCV` | The only defensible evaluation for an LLM agent. Anonymize dates→rounds. |
| **Identical-harness multi-strategy arena; add LLM agents as competitors; ensemble N stochastic runs (done the statistician's way)** (10) | `sim/` arena, `eval/deflated` | Report the *distribution* over many small trades across many periods, never the winning run. Add cross-agent correlation. |
| **gate → score → explain funnel; sector-concentration penalty; numbers-only LLM role** (11) | `signals/`, `agent_trader/team.py` | Deterministic hard gates + 0–100 score first, LLM *narrates* the math and is forbidden to predict. Exactly our "LLM proposes, code decides." |
| **Earnings-date universe + options-chain PoP / return-on-risk screen** (02, 03) | `sources/options`, `signals/` | Extend call-gamma work to credit-spread PoP — but treat LLM score as *not calibrated* and Brier it against resolution. |
| **OpenInsider-style data: EDGAR Form 4 clustering, FINRA short interest, Reg SHO FTDs** (14) | `sources/sec`, `sources/finra`, `signals/squeeze` | Raw-data-in, methodology-separate — we already have `sec`/`finra`; add Reg SHO fails-to-deliver as squeeze fuel. Keep insider data as a **diligence layer**, not primary signal. |
| **Codified liquidity/execution gates: spread <10% of mid, limit-only, wait-then-cancel** (01) | `agent_trader/execution.py`, `backtest/costs` | Concrete execution-layer rules that make paper less of a fantasy. |
| **Rules-compliance checker on every proposed trade** (04, 11) | `agent_trader/execution.py` guardrails | LLM prints the rulebook and flags any violated rule — guardrail-as-refusing-tool, in the execution layer. |
| **Determinism/stability probe: re-query same input N× in fresh contexts, measure variance** (04, 02) | `eval/`, `agent_trader` tests | Cheap calibration-stability metric; high variance = no real expected value, just a feeling. |
| **Bayesian-shrunk win rate; correlation-adjusted z-scores; don't count fills as bets** (09) | `eval/`, `media/voices` | Stop over-crediting short/noisy track records. |
| **Persist "decisive actions" to a vector store for setup-similarity recall** (01) | `sources/store`, `agent_trader` memory | Retrieve similar past setups + how they resolved. |
| **Free-tier / serverless ops; hook-driven run+audit log with Haiku summaries** (15, 06, 16) | `.github/workflows`, `agent_trader/loop.py`, alerts | Matches our no-subscription ethos. **But capture tool calls, not just chat turns** (06's admitted gap) — the decisions are the substance. |
| **Snapshot audit trail — "what did the model see as-of decision time"** (07) | `agent_trader/loop.py`, `predictions.py` | Directly reinforces no-look-ahead: record the exact as-of snapshot behind every pick. |
| **Event-driven, idempotent pipeline: queue + object store + content-hash dedupe** (08) | `pipeline/`, `sim/` resume-safe fingerprint | We already value resume-safe runs; formalize idempotency so retries never double-count. |

---

## 4. The consolidated build plan (phased, folds into existing modules)

Each phase names the module, the source posts, and the guardrail it satisfies. Sized to
land as normal PRs, each shipping with a property test (not a golden number).

**Phase A — Honest evaluation hardening (do first; it's the moat).**
- A1. **`Sarithis` leakage/cost test suite** (13) — encode the ~30-bug taxonomy as
  property tests in `ml/features` + `backtest/costs`: rank-then-trade-same-bar lookahead,
  regime filter using current-day data, returns paired by list-position not date, exits
  at stale prices, "immortal" never-exited positions, UTC-aligned bars creating ghost
  weekend sessions, `0.0` treated as missing via Python truthiness, Sharpe/drawdown
  omitting the first day, fees under/over-charged. Guardrails #1/#2/#3.
- A2. **Correlation-aware + shrunk stats** in `eval` (09) — Bayesian-shrunk win rate,
  correlation-adjusted significance, and a "don't count fills as independent bets" guard.
- A3. **Determinism/stability probe** (04, 02) — re-run the agent N× on one fixed input,
  report answer variance as a calibration-stability metric.

**Phase B — The track-record loop (the corpus's best idea, we own the spine).**
- B1. **Recommendation-resolution memory** (16, 02, 03) — every agent pick written to
  `calibration_log/`, auto-resolved, Brier-scored vs base rate; a memory layer so the
  agent sees whether its *own* past calls worked. Guardrail #4.
- B2. **Blind reasoning-quality scorer** (12) — strip popularity, score drivers on a
  multi-dim rubric, attribute realized return per dimension; surface on the dashboard.
- B3. **Snapshot audit trail** (07) — persist the exact as-of data blob behind each pick
  in `agent_trader/loop.py`. Guardrail #2.

**Phase C — Data & signal breadth (raw-data-in, methodology-separate).**
- C1. **Reg SHO fails-to-deliver + Form 4 clustering** into `sources/finra`/`sec` and
  `signals/squeeze` (14). Keep as diligence/context, not primary signal.
- C2. **Earnings-date options-chain PoP screen** (02, 03) extending `sources/options` —
  credit-spread PoP + return-on-risk, LLM score explicitly flagged *not calibrated*.
- C3. **Read-only Postgres/SQL MCP over `TidyStore`** (09) — NL→SQL analysis, agent
  writes queries, deterministic layer runs them.

**Phase D — Arena & execution realism.**
- D1. **LLM agents as `sim/` competitors** under the identical-harness rule (10); report
  the distribution over N stochastic runs, plus **cross-agent correlation** as a
  systemic-risk gauge. Guardrail #4 + `eval/deflated`.
- D2. **Execution-layer gates** (01, 04, 11) — spread <10% of mid, limit-only,
  wait-then-cancel, sector cap, and a **rules-compliance checker** that refuses violating
  trades (guardrail-as-tool). Extends `agent_trader/execution.py`.
- D3. **Idempotent, resume-safe run loop** (08) — content-hash dedupe so a retried run
  never double-books a paper order.

**Phase E — Ops (cheap, honest, already our ethos).**
- E1. **Tool-call-level audit log** (06's gap, 15, 16) — hook-driven capture of the
  agent's *decisions*, not just chat, summarized cheaply; feeds B1/B3.
- E2. Keep the free-tier deployment (Actions → Pages), no subscriptions.

---

## 5. What NOT to build (the corpus's negative space)

- **No live-money auto-trader.** Every real-money showcase (10, 11) either blew up on one
  trade or is a tiny-n coin flip with a copy-trade product attached. Paper-first; the
  promotion gate is a decision, never an order.
- **No copy-trading / whale-tailing.** Latency-dead (09).
- **No LLM day-trading / TA-from-screenshots.** (04) The most honest OP in the corpus
  concluded the LLM is good for *learning and journaling*, "pretty bad as a live tool."
- **No "AI finds alpha" claims.** Large-cap US has no free edge (11); only a documented
  structural edge (e.g. volatility risk premium) is defensible, and even then: prove it
  survives costs, PBO, and a forward holdout.
- **No trusting LLM narrative as data.** Quantify and calibrate sentiment; never ship
  un-scored LLM tone-reading as a signal (16).
- **No full-Kelly.** (15) Penny-stock full-Kelly is a blow-up; our gate mandates
  fractional-Kelly ≤¼.

---

## 6. One-paragraph synthesis

Sixteen builds, and the honest reading is bracing: **not one demonstrated a costed,
out-of-sample, calibrated edge.** The best of them (07, 14, 16) are advisory tools that
track whether they were right; the worst (10, 11, 15) are tiny-sample coin flips wearing
a copy-trade product. The genuinely valuable content is the *critique* — paper fills
aren't real, LLMs can't be backtested on dates they've memorized, luck masquerades as
skill at n=1, hallucinated inputs and tests, latency kills copy-trades, regimes shift.
Every one of those is already a guardrail in this repo. So the plan is not to chase their
returns — it's to **adopt their honest primitives (the track-record loop, the SQL-over-
facts MCP, the gate→score→explain funnel, the insider/short-interest data, the execution
gates) and weaponize their mistakes as tests (the `Sarithis` taxonomy, the fill-double-
counting bug, the determinism probe).** That is the moat CLAUDE.md already claims, now
backed by 16 field reports of what happens without it.

*Not financial advice. A research and skill-building synthesis.*
