# CLAUDE.md — Forecasting & Market Analytics Lab

A research platform for forecasting real-world events with prediction markets,
sports Elo, and an alt-data signal layer underneath. **The methodology is the
moat, not the data volume.** This is a research and skill-building system — **not**
a recommendation engine and **not financial advice**.

The briefs (`project-forecasting-lab.md` and siblings) carry the *goal and the
domain knowledge*. The `src/forecasting_lab/` package is the *working
implementation*. When a brief and the code disagree, **the code is ground truth** —
update the brief. **The consolidated build roadmap is `agent-trader/MASTER_PLAN.md`**
(design: Rallies UI + Stock Taper skin; rigor track V1–V10; phases P1–P5) — distilled
from a 3-round research program whose findings live in `agent-trader/*.md` and
`design-reference/*` (independently verified: `agent-trader/VERIFICATION_REPORT.md`).

## Non-negotiable guardrails (what separates real from curve-fit)
1. **Time-respecting splits only.** Never random k-fold on a time series. Use
   `ml.PurgedWalkForwardCV` (purge + embargo). This is the single most common way
   backtests look great and fail live.
2. **No look-ahead / leakage.** Every feature must be known as-of the decision
   date. Lag end-of-day features before trading that same close
   (`ml.features.lag_features`).
3. **Model costs.** Kalshi/Polymarket fee structures are known (`backtest.costs`).
   A frictionless backtest is a fantasy; there is no excuse here.
4. **Calibration over accuracy.** Track Brier score + a reliability diagram
   (`eval`), never a bare "% accuracy". Always beat the base-rate baseline.
5. **Survivorship-bias-free data** for any cross-sectional study — free yfinance
   fails this (delisted names are gone).
6. **The legal line.** Building detectors is fine. Trading on material non-public
   information, or coordinating / front-running a pump, is not.

If you write code that violates one of these, **stop and flag it**. These bugs are
silent, and naming and avoiding them *is* the quant skill this project trains.
(Worked example already in the repo: the Elo loser-update bug that passed a naive
"it ranks players correctly" check but blew calibration apart — caught only by the
reliability diagram. See `tests/test_elo.py::test_fit_beats_base_rate_and_is_calibrated`.)

## Repo map
Code — `src/forecasting_lab/`:
- `eval/` — Brier, log loss, reliability, ECE, Murphy decomposition, calibration plot; `deflated` = probabilistic/deflated Sharpe + PBO (CSCV) for multiple-testing & overfitting honesty; `honest_stats` = shrunk win rates, fills-are-not-bets clustered significance, and `alpha_vs_benchmark` that renders "n/a" without a stored entry-date anchor (V2/V4). The credibility core. Rigor backstop: `tests/test_sarithis_suite.py` — 12 injection tests encoding the practitioner bug taxonomy (lookahead, stale marks, immortal positions, fee rounding, first-day stats…); it found and fixed 3 real bugs on arrival.
- `predictions.py` — the **prediction-evidence contract** (`design.md` §7): a `Prediction` (probability + `Driver` list + caveat) that *cannot be constructed* without a valid probability and ≥1 driver. Every pick the dashboard surfaces (movers, market odds) renders its odds + an expandable "why"; stock leans are logistic on the trend composite and honestly caveated as *not yet calibrated*.
- `promotion.py` — the **paper→live promotion gate** (Phase 4): a *decision*, never an order. `evaluate_promotion` runs six out-of-sample gates (deflated Sharpe > 1.0, PBO < 0.2, ≥N real forward marks, Brier-skill-vs-market > 0, survives costs+turnover, a risk gate = fractional-Kelly ≤¼ + per-name/drawdown/capital caps) and returns a signed, dated `PromotionRecord` with a written rationale (`write_promotion_record` appends JSONL). Property-tested: a skilled synthetic strategy is PROMOTED, an overfit/lucky one is REJECTED, and the module contains **no brokerage/order-execution code** (asserted). Connecting a broker and risking capital is the operator's call — the gate just makes it honest.
- **Edge features** (Phase 1, `PLAN.md`): `markets/leadlag` (cross-venue convergence), `signals/attention` (persisted mention-velocity z + `AttentionStore`), `signals/squeeze` (short-interest × ignition), `eval/recalibration` (favorite-longshot). Each scored OOS by `eval/skill.brier_skill_vs`/`walk_forward_skill` under purged CV — **noise → ~0 skill pinned** (`tests/test_edges.py`) — and surfaced on the dashboard "Edge research" panel (skill + drivers), with the recalibrated fair-value edge live on market picks.
- `sports/` — tennis Elo (surface, 538 K), NBA Elo (`basketball`: home edge + MOV), soccer Elo (`soccer`: Davidson 3-outcome draw model, RPS, **real loader** via football-data.co.uk); synthetic generators; Monte Carlo brackets.
- `markets/` — Polymarket + Kalshi clients (JSON-string / dollars-cents payload quirks, pagination), title `matching`, live cross-venue `monitor.DivergencePipeline` (`flab-divergence --live`). `monitor` also emits a JSON sidecar for the dashboard: per-venue **live YES odds** on the most-traded markets + any matched/flagged cross-venue pairs.
- `ml/` — cross-sectional features, forward-return / triple-barrier labels, **purged walk-forward CV**, GBM ranker (LightGBM → sklearn → ridge fallback), `tune` (grid search scored by out-of-sample **rank IC** under the purged CV — null features → ~0 IC, pinned in tests), `factors` (V6: zero-sum-constrained WLS factor regression, MAD-winsorize prep, **residual momentum** — accepted only by OOS rank IC, never an in-sample gate; leak test mutates the future). The ranker competes live in the arena as the `ml_ranker` strategy (self-tunes on first fit).
- `macro/` — FRED yield-curve recession nowcast (Estrella-Mishkin probit, `flab-macro`), calibration-tested.
- `sources/` — the 700+ tracked universe: `universe` (S&P 500 live + bundled fallback), `sec` (proper-UA EDGAR — a working port), `fred`, `social` (Reddit, honest degradation), `finra` (short interest %float + days-to-cover — the squeeze fuel gauge), `options` (Yahoo chain → near-spot call-gamma concentration), `x_voices` (curated finance-X handle universe, Nitter best-effort), `insider` (V10: Reg-SHO daily short-volume ratios + Form-4 **distinct-insider cluster buys**, freshness-stamped, filed into the store; FTD deliberately later), `store.TidyStore` (dated `(date,entity,metric,value)` facts so velocity/track-record features have history), `registry` (counts, `flab-sources`). Every connector degrades honestly (None/`[]`/graceful zeros when blocked). More soccer leagues via `sports.soccer.SOCCER_LEAGUES` (football-data.co.uk divisions).
- `backtest/` — exact cost models (Kalshi fee peaks $0.0175 @ 0.5) + walk-forward backtester vs honest baselines.
- `signals/` — squeeze and momentum composites (ranked *separately*; squeeze now takes V10 short-volume/cluster-buy enrichment that helps only when informative and degrades to base exactly); `deception` (V7: Larcker-Zakolyukina lexical scorer, classification skill NOT a return edge, shuffled labels pin ~0); `trending` = the live NVIDIA/GME-shape scanner (Yahoo trending + charts + Google News, `flab-trending`). Emits a JSON sidecar with per-ticker **price sparklines** + scores for the dashboard mover cards.
- `sim/` — the strategy arena: persistent bar-based paper-trading race (four rules + the `MLRanker` learner + two baselines; plain-language `description`; turnover costs; resume-safe fingerprint; `flab-sim`). Daily bars, not an order-book sim — honestly labeled.
- `forwardtest/` — the **forward study**: records each strategy's real-basket picks per run and marks the prior snapshot to market on the next (genuinely out-of-sample; backfill seeds, live marks accrue; `flab-forward`). The "watch strategies play out over time" artifact.
- `media/` — media watch: ~100-voice `watchlist`, YouTube RSS/yt-dlp (`youtube`), name→ticker + theme `entities`, finance-lexicon `sentiment` (tone), buzz digest (`watch`, `flab-watch`); `voices` = the **"ahead of the curve" track-record leaderboard** (Phase 3): scores each voice by Brier-skill-vs-base (right) + cross-correlation timing lead (early), ranks by *record* not followers, decays a regressing reputation. `VoiceLedger` logs dated calls; random calls score ~0 (pinned); surfaced on the dashboard "Ahead of the curve" panel. Cloud-ready, degrades locally.
- `dashboard/` — `flab-dashboard` renders `site/index.html` + `site/scorecard.html` (P4, **built**): single-file no-build pages in the **Stock Taper skin** (cream `#FBF7EB`, IBM Plex Mono w/ system fallback, green/brick `#2F7D31`/`#C6392C`, uppercase eyebrows + headings, our own inline-SVG mascots, "going well / concerning" pairs) on the **Rallies IA** (sticky scroll-spy nav Today→Watch, peer strip, suggested-question chips, "The tape" filtered feed, book table w/ honest `n/a` alloc). Picks render as **evidence-thesis cards** (Why now → Evidence w/ signed pushes → Watch for / Red flags → confidence dots → trust badge w/ freshness) inside the `why` expander; the arena shows **the gate stated in the open** (fleet FDR → survivors or "0 survive → 100% benchmark") + the crowding gauge; the scorecard page leads with the honest denominator and pins the **miss ledger** worst-first. Content never JS-gated; reduced-motion respected; jargon translated; always renders. Design provenance: `design-reference/stocktaper/DESIGNS.md`+`FEATURES.md`. **Layout & IA** → model on Rallies (`design-reference/rallies/`, teardown + authed feature map): feature-per-surface nav, peer strips, position-level book tables, research sub-tabs, suggested-question chips, filtered feeds, visible multi-step agent plans. Rallies + Stock Taper are the two primary UI models (operator preference). **Intel Desk** (`design-reference/inteldesk/`) contributes proof *mechanics only*, restyled into the Stock Taper/Rallies language: the Brier-scored public scorecard with an honest denominator, A/B/C/D source tiers, the claim-tape receipts drawer (contradictions kept on screen), ACT/VERIFY/PRICE/FADE buckets. **Engo** (`design-reference/other-uis/ENGO_TEARDOWN.md`) contributes arena honesty: benchmark always on the board, the gate stated in the open, a 7-day track record before anything is published. Component catalog: `design-reference/SITE_BLUEPRINT.md`. Keep the honest substance (calibration, "why" expanders, not-financial-advice) on every surface.
- `alerts/` — free phone alerts (`flab-alert`): Telegram bot / Discord webhook (both free) with a zero-config `inputs/alerts.log` fallback; composes a daily summary from the latest digests. Last job in `flab-run-all`.
- `calibration_log/` — the public, Brier-scored forecasting log; **auto-resolves** from Kalshi/Polymarket settlement (`resolve`) and scores you **against the market** (beat-the-closing-line); `audit` (V8) = the **snapshot audit trail** — canonical-JSON, content-hashed inputs behind every decision; `replay()` reproduces the bytes or fails loudly. The portfolio piece.
- `pipeline/` — the invoke→fetch→process→store pattern; `research.py` = live arXiv q-fin sweep (`flab-research`, explainable keyword ranking); files dated digests into `inputs/`; `freshness` (V3) = `stamp`/`FreshnessBudget`/`DataConfidence` — stale data raises `StaleDataError` loudly, sidecars carry `fetched_at`, imputed fields are visible.
- `agent_trader/` — the honest agent desk: `execution` (refusing chokepoint: caps, kill switch, spread gate, limit-or-better fills, wait-then-cancel expiry, **fail-closed** decision-service check, content-hash idempotency — changed payload under a known id refuses loudly, bracket stop/take-profit exits on MARKS; V9), `mandate` (V4: deterministic pass/warn/BLOCK — concentration on invested capital, sells always pass, missing data skips loudly), `fleet` (V5: deflated-Sharpe + PBO + **Benjamini-Hochberg fleet FDR**; nothing survives → an explicit `HoldBenchmark` 100%-SPY decision, never an empty dict; crowding gauge on the arena), `loop` (one unattended cycle; LLM proposes, deterministic strategy decides; V8 hooks: audit trail + picks into the Brier log), `team`, `brief`, gate/desk modules.
- `cli/` — `flab-elo` (`--sport nba|soccer`), `flab-signals`, `flab-divergence`, `flab-calibration`, `flab-trending`, `flab-sim`, `flab-forward`, `flab-watch`, `flab-macro`, `flab-research`, `flab-sources`, `flab-alert`, `flab-dashboard`; `flab-run-all` (full daily orchestrator) + `flab-intraday` (fast market-hours subset: resolve/trending/divergence/macro/dashboard) + `flab-cron`. Two cloud workflows: `daily.yml` (full run) and `intraday.yml` (every 30 min during US market hours, shares the `pages` concurrency group). Free hosting: local task, GitHub Actions (→ Pages), or Oracle Always Free — no subscription.

Briefs (domain knowledge, pulled on demand — not all read every session):
- `project-forecasting-lab.md` — the hub: data sources + gotchas, models, backtesting, guardrails, next-projects roadmap.
- `signal-monitoring.md` — the alt-data layer (squeeze vs momentum, what to scrape/track).
- `ml-system-design.md` — the ML methodology and the seven leakage traps.
- `learning-investing.md` — the education tier list: foundations → index core → quant canon → forecasting psychology. Tier 0-1 before believing any backtest.
- `research-sources.md` — where to mine papers + bulk data at scale.
- `data-automation.md` — the news / ingestion automation.
- `claude-orchestration-plan.md`, `claude-stack-resources.md`, `master-index.md` — workflow, resources, and the index.

## Quickstart
```bash
pip install -e ".[all]"        # or a subset: pip install -e ".[ml,markets,viz]"
pytest                         # 170 tests, a few seconds, no network
python -m forecasting_lab.cli.elo_backtest --synthetic   # headline calibration demo
```
- Real tennis data: `flab-elo --years 2021 2022 2023 --tour atp` (downloads Sackmann CSVs to `data/`, cached). Data is CC BY-NC-SA — research/non-commercial only.
- Secrets (Kalshi key id + PEM path) go in `.env`; see `.env.example`. **Never commit keys.** Market *reads* need no auth.

## Conventions
- Python ≥3.10, `src/` layout, `from __future__ import annotations`. The core stays dependency-light (numpy/pandas/requests/pyyaml); ML, markets, and viz are optional extras so the deterministic core runs in a minimal env.
- Every new model or metric ships with a test that checks a **property** (monotonic, zero-sum, calibrated, leak-free) rather than only a golden number. Run `pytest` and `ruff check src tests` before calling anything done.
- Determinism: pass explicit seeds; never use wall-clock time inside logic.
- New *recurring* source → add a `pipeline.Pipeline` subclass that files a dated digest into `inputs/`. One-off lookups are cheaper to just ask; don't build a pipeline for them.
- Keep this file tight (~150 lines max). Domain detail lives in the briefs — past a couple hundred lines the bottom stops getting read.

*Not financial advice. A research and skill-building system. Last updated: 2026-06-28.*
