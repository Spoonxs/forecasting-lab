# Verification report — independent re-check of every source (2026-07-04)

*A second-model pass that re-verified the entire research program against PRIMARY
sources: all 26 raw thread captures re-read against the digests, all repo claims
re-grepped on the code on disk, live sites re-fetched, the 3 YouTube videos transcribed,
the LinkedIn post captured for the first time, the 2 pastebins analyzed for the first
time, and 3 never-analyzed repos torn down. Verdict up front: **the digests are reliable
on substance — every load-bearing number and architecture claim checked out verbatim —
but 4 items were wrong, several citations were smeared across threads, and a few caveats
had been shaved.** All corrections below are applied to the docs in this commit.*

## 1. What was verified clean (spot checks passed)

- **Repo claims, re-grepped by hand on disk:** openfactor `as_of_price_matrix`
  (`src/openfactor/model/factor_returns.py:14`, used `:43` with `return_row+1`) and the
  **in-sample** semantic gate (`accepted = after_var < before_var`, `llm/semantic.py:254`);
  0 test files; Apache-2.0 ✓. Velora `KNOWN_RULE_TYPES` (`mandate.py:32-34`) and the
  "KEIN (Fake-)Alpha" refusal (`performance.py:301`); MIT ✓. openprophet `maxOrderValue`
  enforced (`mcp-server.js:1113-1118` throws) while `maxPositionPct` exists **only** as
  schema text (`:940`) + config default — prompt-only cap confirmed; CC BY-NC ✓.
  OpenInsider-MCP: exactly **16** registered tools; MIT ✓.
- **Live:** openfactor R2 `latest.json` still `2026-06-25` (staleness grade holds);
  **engo.capital live page literally contains** "deflated Sharpe", "1 − PBO", "forward
  paper", "survives the gate? Everything starts as paper" — the north-star claims are real.
- **The academic paper** (newsrc/07 abstract): restatement labels, OOS-only, "better than
  random by 6%–16%", and all linguistic markers verified near-verbatim.
- **The Medium writeup:** $107,648/+7.6%, peak +20.4%, max DD −22.4%, ±$14.5k/$15.1k
  best/worst, all disclaimers — verified exactly.
- **Every headline forum number** (+37/+19.5, +5.2/+2.4/−10.8, −19.7% risk-awareness gap,
  35-pt vs 2-pt, 3/3→5/10, FMP fake-congressman bug, krani1's empty-repo accusation) —
  present in the raw captures.
- **Thin captures are genuinely thin threads, not truncation** (06=7 comments, 07=13,
  08=10, 15=23 w/ removed comments).

## 2. Corrections applied (things the digests got WRONG)

1. **Temple-Stuart's repo is PUBLIC, not private** — the clone retry succeeded (the
   77-file view was a truncated Windows checkout; full tree = **928 files**). Fixed in
   `DEEP_DIVE_REPOS.md`, `DEEP_DIVE_FORUMS.md`, `DEEP_DIVE_GOAL_PROMPT.md`. Full teardown
   now in §4 below.
2. **The AFRM hallucination example was garbled**: real raw content (thread 02, not 04)
   is an AFRM $72.5/$80 credit spread whose analysis cites a price "last seen near
   **$47.86**" (internally incoherent) — there is no "support $40" anywhere. Fixed in
   `CONSOLIDATED_RESEARCH_PLAN.md` anti-pattern 4.
3. **Rallies' OP never conceded a conflict of interest** — challenged, never replied. COI
   is evident, not conceded. Fixed in the corpus table.
4. **"One trade wiped 8 months of gains" overstated** — it wiped the *new system's*
   live-test progress (~1 month). Fixed in anti-pattern 2.
5. **"Penny-stock full-Kelly is a blow-up" had no raw source** — the thread only says
   "applies Kelly Criterion"; the blow-up warning is *our* guardrail inference. Relabeled
   as such in §5 of the consolidated plan.
6. **"6–16% edge" mislabeled** — the paper's 6–16% is *classification accuracy above
   chance*, not a return/trading edge. Fixed in `SOURCES_ROUND2_ASSESSMENT.md` and
   `MASTER_CONTEXT_PROMPT.md`.
7. **Video mislabel in the source map:** `tr-k9jMS_Vc` is **"Reddit Beat AI at Picking
   Stocks. Then I Ran It Again."** (the 547-recs video), *not* the satellite video. No
   satellite video was ever in the list.

**Citation-smearing pattern (systemic, now on record):** several claims true in one
thread were cited to two (determinism probe "04,02"→04 only; rules checker "04,11"→04
only; paper-fills quote "01,15"→01 only; regime quote "13,15"→15 only); famous quotes are
splices/condensations of multiple voices (the paper-fills line = two commenters; Pindarr/
jantwel lightly condensed; "quietly built a cache" = title + Claude's own words); the
crowdintel "steamroller"/"toxicity map" language is **pasted Claude output**, not trader
wisdom; and the Buffett-thread financials→identity argument belongs to
`Equivalent_Bet6932` + the OP's own concession, not the top commenter. Meaning was
preserved in all cases; treat "(NN)" citations as approximate.

## 3. Material additions the digests missed

- **Crowd beat the AI over the full year** (+39.8% vs +37.0%) in the 547-recs experiment
  — the AI's win holds only in the out-of-training window; and the −19.7% risk-awareness
  finding carries the OP's own caveat ("27 tickers… directional, not conclusive").
- **The "leakage is unrefuted" thesis slightly overstates**: thread 1 contains an
  unaddressed mitigation ("backtest on OLD LLMs — GPT-4.1 baseline gives a 2-year
  cutoff"), and thread 10 ran a genuine post-cutoff test. Still the dominant objection.
- **The deception video adds:** models were Sonnet **4.5** / Opus **4.5**; the author
  re-ran with more companies and Opus stayed flat (fraud 51 vs stable 53); the exact five
  markers ("you know" deflection, I-vs-we shift, extreme positivity, certainty avoidance,
  rehearsal signals).
- **LinkedIn post (captured for the first time):** get-rich-slow's author claims
  **59-0 over 26 days on real money** — $1,000 → $1,322 (+33%, $318 net *after fees*),
  avg entry 96¢ across 7,012 contracts, MLB-heavy, "projected annualized 4,000%," now
  multi-tenant for friends. Honest read: at 96¢ avg entry, 59-0 is ≈ what fair pricing
  predicts (~0.96⁵⁹ ≈ 9% chance with zero edge — mildly lucky or a small live-lag edge),
  and **one loss erases ~24 wins**; the 4,000% extrapolation ignores tail + capacity. But
  unlike the repo's frictionless shadow P&L, this is a real-money, fees-included record.
- **The pastebins (analyzed for the first time)** are the pre-rewrite Python era of
  Temple-Stuart's scanner: a vibecoded Flask/sqlite accretion dump + a credit-spread
  scanner whose "AI" is **GPT-4o-mini emitting 👍/👎 emoji verdicts** with zero ground
  truth. Most telling: the live pipeline already called
  `fetch_options_chain(..., use_cached=True)` — **the stale-cache-on-live-data pattern he
  later blamed on Claude "quietly lying" existed as his own explicit choice** in his
  earlier code.
- **crowdintel.xyz is currently down/flagged** — HTTPS throws SSL_PROTOCOL_ERROR, HTTP
  trips a safe-browsing "Potential Threat Detected" wall. The 1.7k-upvote promo site did
  not outlast the thread. (Unverifiable at this time; noted, not bypassed.)

## 4. Three repos analyzed for the first time

- **Temple-Stuart/temple-stuart-accounting** (public, 928 files, **BUSL-1.1** → Apache
  in 2028): a personal "financial OS" (Next.js 15/Prisma/Postgres) with the scanner as
  one module. The lettered pipeline is real code (`src/lib/convergence/pipeline.ts`,
  2,363 lines, steps **A→I with ~28 sub-steps** — not A→T as marketed), four scored gates
  (vol-edge/quality/regime/info-edge → composite) and a real circuit-breaker (<2/4 gates
  above 50 → `positionSizePct=0, "NO TRADE"`). The freshness layer is real but modest
  (per-step `fetched_at`, `dataAge` ISO stamps, an honest `DataConfidence` struct with
  `imputed_fields`). "Kelly 1956" is a citation only — sizing is a heuristic score→% map.
  **`outcome-tracker.ts` is a 34-line stub ("for future backtesting")** — zero validation,
  consistent with the OP's own "gates are equally weighted" confession. Uses Claude Haiku
  as a news classifier + Grok sentiment. Adoptable *pattern* (not code — BUSL): the
  per-step freshness/`DataConfidence`/imputed-fields honesty.
- **GaurabAryal/reddit-stock-experiment** (19 files): **krani1's accusation is TRUE** —
  zero `anthropic` imports, zero API calls, zero prompts, no skills/subagents; the README
  falsely claims steps "use Claude" and need `ANTHROPIC_API_KEY`; the AI-scoring steps
  are human-in-the-loop stubs whose outputs (`recommendations_scored.json`) are committed
  but unreproducible. The backtest is yfinance equal-weight top-10 with a single entry
  date and "No transaction costs" in its own footer. **A cautionary exhibit**: exactly the
  narrative≠artifact gap our prediction-evidence contract prevents.
- **mkash25/Claude-powered-AI-native-financial-dashboard** (83 files, MIT): legit and
  as-advertised — real `anthropic` call (`claude-sonnet-4-6`, max_tokens 32768, usage
  accounting printed; ~47K-token claim plausible), numbered-notebook pipeline with cron
  templates and a 623-line install wizard, a security-audit notebook, and
  `06_performance_tracking.ipynb` (hit-rate + confidence-vs-realized tracking of past
  recs — notebook-grade but the right idea). Patterns freely liftable.

## 5. Coverage ledger (nothing left unchecked)

| Source class | Status |
|---|---|
| 24 Reddit threads | all raw-captured + re-read vs digests (16 round-1 + 10 round-2 files; 2 threads appear in both) |
| 12 repos | all cloned + analyzed (incl. Temple-Stuart, GaurabAryal, mkash25 this pass); Temple-Stuart full tree restored |
| Live sites | Stock Taper/Intel Desk/Rallies (walked earlier, Rallies logged-in, data grade A−); engo re-verified live; openfactor R2 re-fetched; margincall/freetradejournal captured; **crowdintel down/flagged** |
| YouTube ×3 | transcripts fetched + read; titles verified; 1 mislabel corrected |
| LinkedIn post | captured + analyzed (first time) — the 59-0 claim |
| Pastebins ×2 | analyzed (first time) — pre-rewrite scanner, GPT-4o-mini scorer, author's own `use_cached=True` |
| Academic paper | abstract verified claim-by-claim |
| Medium writeup | verified number-by-number |

**Bottom line:** the research program's conclusions all stand — no verdict in any table
flips. The corrections are about precision (wrong examples, smeared citations, shaved
caveats, one licence/availability error) plus genuinely new material (Temple-Stuart's
real code, the krani1 confirmation, the 59-0 real-money claim, the pastebin
`use_cached=True` irony). *Not financial advice.*
