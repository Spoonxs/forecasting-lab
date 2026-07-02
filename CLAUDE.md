# CLAUDE.md — Forecasting & Market Analytics Lab

A research platform for forecasting real-world events with prediction markets,
sports Elo, and an alt-data signal layer underneath. **The methodology is the
moat, not the data volume.** This is a research and skill-building system — **not**
a recommendation engine and **not financial advice**.

The briefs (`project-forecasting-lab.md` and siblings) carry the *goal and the
domain knowledge*. The `src/forecasting_lab/` package is the *working
implementation*. When a brief and the code disagree, **the code is ground truth** —
update the brief.

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
- `eval/` — Brier, log loss, reliability, ECE, Murphy decomposition, calibration plot; `deflated` = probabilistic/deflated Sharpe + PBO (CSCV) for multiple-testing & overfitting honesty. The credibility core.
- `sports/` — tennis Elo (surface, 538 K), NBA Elo (`basketball`: home edge + MOV), soccer Elo (`soccer`: Davidson 3-outcome draw model, RPS, **real loader** via football-data.co.uk); synthetic generators; Monte Carlo brackets.
- `markets/` — Polymarket + Kalshi clients (JSON-string / dollars-cents payload quirks, pagination), title `matching`, live cross-venue `monitor.DivergencePipeline` (`flab-divergence --live`). `monitor` also emits a JSON sidecar for the dashboard: per-venue **live YES odds** on the most-traded markets + any matched/flagged cross-venue pairs.
- `ml/` — cross-sectional features, forward-return / triple-barrier labels, **purged walk-forward CV**, GBM ranker (LightGBM → sklearn → ridge fallback), `tune` (grid search scored by out-of-sample **rank IC** under the purged CV — null features → ~0 IC, pinned in tests). The ranker competes live in the arena as the `ml_ranker` strategy (self-tunes on first fit).
- `macro/` — FRED yield-curve recession nowcast (Estrella-Mishkin probit, `flab-macro`), calibration-tested.
- `sources/` — the 500+ tracked universe: `universe` (S&P 500 live + bundled fallback), `sec` (proper-UA EDGAR — a working port), `fred`, `social` (Reddit, honest degradation), `registry` (counts, `flab-sources`).
- `backtest/` — exact cost models (Kalshi fee peaks $0.0175 @ 0.5) + walk-forward backtester vs honest baselines.
- `signals/` — squeeze and momentum composites (ranked *separately*); `trending` = the live NVIDIA/GME-shape scanner (Yahoo trending + charts + Google News, `flab-trending`). Emits a JSON sidecar with per-ticker **price sparklines** + scores for the dashboard mover cards.
- `sim/` — the strategy arena: persistent bar-based paper-trading race (four rules + the `MLRanker` learner + two baselines; plain-language `description`; turnover costs; resume-safe fingerprint; `flab-sim`). Daily bars, not an order-book sim — honestly labeled.
- `forwardtest/` — the **forward study**: records each strategy's real-basket picks per run and marks the prior snapshot to market on the next (genuinely out-of-sample; backfill seeds, live marks accrue; `flab-forward`). The "watch strategies play out over time" artifact.
- `media/` — media watch: ~100-voice `watchlist`, YouTube RSS/yt-dlp (`youtube`), name→ticker + theme `entities`, finance-lexicon `sentiment` (tone), buzz digest (`watch`, `flab-watch`). Cloud-ready, degrades locally.
- `dashboard/` — `flab-dashboard` renders `site/index.html`: a single-file, **interactive** research tool (light theme, one teal accent, hand-rolled SVG, system fonts, small vanilla JS — always renders). Sticky section nav (scroll-spy); a "what's moving now" board with **price sparklines** + % moves + signal bars; **live prediction-market odds** side by side; **sortable** strategy/odds tables with inline bars; the `ml_ranker` surfaced against the rule strategies; "updated N ago" clock + 30-min meta-refresh. Every section leads with a plain-English question; jargon (calibration/PBO/deflated Sharpe) is translated, not shown. Content is never JS-gated; reduced-motion respected.
- `alerts/` — free phone alerts (`flab-alert`): Telegram bot / Discord webhook (both free) with a zero-config `inputs/alerts.log` fallback; composes a daily summary from the latest digests. Last job in `flab-run-all`.
- `calibration_log/` — the public, Brier-scored forecasting log; **auto-resolves** from Kalshi/Polymarket settlement (`resolve`) and scores you **against the market** (beat-the-closing-line). The portfolio piece.
- `pipeline/` — the invoke→fetch→process→store pattern; `research.py` = live arXiv q-fin sweep (`flab-research`, explainable keyword ranking); files dated digests into `inputs/`.
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
