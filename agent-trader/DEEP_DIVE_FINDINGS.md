# Deep-dive findings — consolidated (repos + forums + Rallies UI)

*The top-level synthesis of the round-2 deep dive. Detail lives in `DEEP_DIVE_REPOS.md`
(per-repo teardown), `DEEP_DIVE_FORUMS.md` (10-thread comment-level digest), and
`design-reference/rallies/RALLIES_TEARDOWN.md` (full UI teardown + data-quality grade).
Method: 9 repos cloned + read line-level, 10 Reddit threads scraped full comment trees via
Firecrawl→Redlib, Rallies product walked logged-in (Pro) with live data verified against
ground truth. 2026-07-04.*

## 1. Good vs hype — one table

| Source | Verdict | One-line why |
|---|---|---|
| **openfactor** (repo) | ⭐⭐ genuinely good | Correct Barra √cap-WLS + zero-sum constraints + structural as-of leakage control; **Apache-2.0**; weak spot = in-sample semantic gate; zero tests |
| **Velora** (repo) | ⭐ genuinely good | **Refuses fake alpha**, shows survivorship, **machine-checked Mandate gate**; MIT; most honest repo in the set |
| **OpenInsider-MCP** (repo) | ⭐ genuinely good | 16 free insider/short tools, **literature-cited + freshness-caveated**, per-source TTL; MIT |
| **Satellite pipeline** (forum) | ⭐ genuinely good | Honestly self-debunked: SAR 3/3@30 stores → 5/10@100 = noise; "the moat is data not the algorithm" |
| **547-recs experiment** (forum) | ◐ good framing, weak evidence | Real OOS blind test + honest that the crowd beat it; but repo lacks the claimed Claude logic; N tiny |
| **Rallies product** (UI) | ◐ polished, data A− | Broker-connected copilot; live data accurate & cross-verified; blog is SEO filler; Arena transparent-but-ungated |
| **openprophet** (repo) | ◐ great plumbing, risk theatre | Fail-closed order gate + real bracket exits, but **maxPositionPct/spread are prompt-only**; CC BY-NC |
| **get-rich-slow** (repo) | ◐ good infra, naive | Live Kalshi lag scalper; frictionless "shadow" P&L (no fees/slippage); MIT |
| **Buffett / Sonnet-vs-Opus / Prophet-Medium / Temple-Stuart / Stock-Taper-launch** | ◐ demos/hype | Training-data leakage unrefuted; no validated PnL; the honest ones say so themselves |
| **rallies-cli / tenk / klaus-kode / Rallies-MCP post** | ✗ scaffolding/promo | LLM wrappers over closed APIs or off-domain; no methodology |

## 2. Data-quality grades (the "is it good data?" answer)

- **openfactor R2 (open) — B+ for research.** Real, SEC-sourced (shares×close), 1000 US names,
  102 factors, 252-day window, SPY benchmark. **~weekly stale** (`as_of 2026-06-25`, 9 days old
  today), US-1000 only, some NaN gaps, inputs paid/not-redistributed. Great for cross-sectional
  research, unsuitable for intraday.
- **Rallies live product (authed) — A−.** Verified logged-in: NVDA $194.83/$4.72T, AAPL
  $308.63/$4.53T — **identical to Stock Taper's independent figures** → accurate; current-day
  "as of". One inconsistency: research page P/E 29.70 vs chat P/E 81.2x (different EPS bases).
  Real-time layer is a **closed backend**; providers undisclosed in-app.
- **Rallies blog — C (SEO filler).** ~15 posts all dated the same day, template explainers.
- **Vendor-inherited accuracy bugs seen elsewhere:** Stock Taper (FMP) showed a non-existent
  congressman + AI-cartoon CEO portraits — a reminder that **vendor data carries errors your UI
  inherits.**

## 3. New ideas / improvements → mapped to lab module + guardrail

Ranked by leverage. (Extends `SOURCES_ROUND2_ASSESSMENT.md`; new items marked ✚.)

1. **✚ openfactor factor/residual layer, but gated by OUR CV.** Adopt (Apache-2.0)
   `constrained_lstsq` zero-sum purification, `as_of_price_matrix`/`rolling_exposures`, and
   MAD-winsorize+z-score prep as a leakage-free feature layer for the GBM ranker. **Crucially,
   replace its in-sample `after_var < before_var` factor-accept gate with
   `ml.PurgedWalkForwardCV` + `eval.brier_skill_vs`/deflated-Sharpe** before admitting any
   factor. → `ml/features`, `ml/` ranker. Guardrails #1, #2.
2. **✚ Velora `mandate.py` validator, verbatim in spirit.** A deterministic rule engine
   (max_position%, min_cash%, max_sector%, forbidden tickers) that returns pass/warn/**block**
   on every proposal, computed on **invested** capital, sells always pass, missing-data→skip. →
   `agent_trader/execution.py`. Plus Velora's **"refuse to compute a metric you can't compute
   point-in-time"** (no alpha without stored entry-date benchmark) → `eval`/`predictions.py`.
   Guardrail (risk gate) + #4.
3. **✚ OpenInsider-MCP data patterns.** Add Reg-SHO daily short volume + FTDs + Form-4 cluster
   buys to `sources/finra`/`sec`, and copy its **literature-cited, freshness-caveated tool
   descriptions + per-source TTL/rate-pace** discipline. → `sources/`, `signals/squeeze`.
   Guardrail #2 (freshness) + #6-adjacent honesty.
4. **✚ openprophet fail-closed order gate + bracket exits.** For the agent-trader execution
   layer: if the decision service is unreachable, **order tools throw** (fail closed); real
   STOP/LIMIT/trailing bracket management in deterministic code. Keep the deterministic decider
   between proposal and order. → `agent_trader/execution.py`. Cardinal rule.
5. **✚ "Risk-awareness is a negative return predictor" hypothesis.** From the 547-recs thread:
   legible/documented risks are already priced in (favorite-longshot / efficient-market echo).
   Test it as a feature-sign check in `eval/recalibration` — does a "risk-section richness"
   score correlate negatively with forward return under purged CV? Genuinely novel, testable.
6. **✚ Data-freshness audit layer (from the "scanner lying by omission" thread + as a defense
   against LLM coding agents).** Every datum carries fetch-time + age; a check fails loudly past
   its as-of budget; steps surface raw output. Prevents an agent silently caching/faking "live"
   data. → `pipeline/`. Guardrail #2.
7. **Engo Arena remains the north-star** (from round 1, reinforced): the Rallies Arena is a
   *transparent demo with no gate*; **Engo publishes the gate** (deflated Sharpe / 1−PBO /
   family-FDR / forward-paper / "0 survive → 100% SPY"). Add **fleet-level FDR** + the
   **hold-benchmark-when-nothing-survives** default to `fleet.py`/`promotion.py`. → `eval/deflated`.
8. **Subagent-isolation anti-leakage** (Buffett thread) for any LLM scoring (`media/voices`,
   `research_log`): score anonymized inputs in isolated context. Guardrail #2.

## 4. The meta-lesson (what every source confirms)

Across 9 repos and 10 threads, **the single recurring, unrefuted objection is LLM
training-data leakage / look-ahead** — you cannot backtest an LLM on dates it has memorized;
genuine forward paper is the only honest path (`forwardtest/`). The practitioner consensus is
**"the moat is the data, not the model"** (parking-lot data is dead; credit-card/web-scrape at
millions/yr is table stakes). And **almost nobody reports validated PnL or statistical
significance** — the community's own demands ("stat-sig? random-portfolio null? report
drawdown, not just returns; N is tiny; one backtest is noise") are a plain-English restatement
of exactly what `eval/deflated` + the promotion gate already enforce. The three genuinely good
sources (openfactor, Velora, OpenInsider-MCP) are good *precisely because* they respect
as-of/point-in-time, refuse fake metrics, and document their limits — the same discipline this
lab is built on. Adopt their concrete pieces; keep the conscience.

*Not financial advice. A research and skill-building synthesis.*
