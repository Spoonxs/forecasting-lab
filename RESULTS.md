# Results & Honest Analysis

The point of this lab isn't a headline Sharpe — it's a **leak-free, cost-aware,
calibration-scored** research pipeline whose numbers you can trust. This page is
the running writeup: what the models show, how the claims are defended, and what
is real vs. synthetic vs. blocked. It updates as the daily cloud job accrues a
real track record. *Not financial advice.*

## Headline numbers

| Model | Metric | Result | Baseline | Data |
|---|---|---|---|---|
| Tennis Elo | Brier | **0.194** | 0.250 base rate | synthetic (real via `--years` in cloud) |
| Tennis Elo | ECE | **0.018** | — | calibrated |
| NBA Elo | Brier | 0.227 | 0.243 home base rate | synthetic |
| Soccer Elo | ranked prob score | **0.211** | 0.232 climatology | **real EPL 23/24** (380 matches) |
| Strategy arena | momentum: Sharpe 2.35 / **deflated 0.88** / PBO 0.11 | beats random & buy-hold | — | synthetic |
| Cross-venue | live flags after fees | surfaced, mostly reject on review | — | **live** Kalshi/Polymarket |

Every score sits next to the baseline it must beat, because "accuracy" without a
base rate is theater.

## Edge features (Phase 1) — out-of-sample skill, honestly benchmarked

Four leading-signal features, each scored **out-of-sample under purged
walk-forward CV** on a deterministic synthetic benchmark (seed 0), and each
property-tested so **pure noise scores ~0** (it cannot manufacture positive
skill). The numbers below prove the signal is *real and leak-free* when it's
present; they are **not** a claim of live P&L — real-world skill accrues as data
fills and is expected to be far smaller.

| Edge feature | OOS Brier-skill | vs. baseline | live status |
|---|---|---|---|
| Cross-venue lead-lag (laggard→leader convergence) | **+0.108** | 0.5 coin flip | live on matched Kalshi/Polymarket pairs |
| Attention acceleration (mentions rising vs own baseline) | **+0.157** | 0.5 base rate | accruing (persisted mention store) |
| Squeeze setup (short-interest × ignition) | **+0.203** | base-rate climatology | dormant — short-interest feed is Phase 2 |
| Favorite-longshot recalibration | **+0.030** | raw market price | live on market picks (default correction) |

Reproduce: `python -c "from forecasting_lab.markets.leadlag import leadlag_skill_report; print(leadlag_skill_report())"` (and the `*_skill_report` in `signals.attention`, `signals.squeeze`, `eval.recalibration`). Pinned in `tests/test_edges.py`. Each feature is surfaced on the dashboard with its odds + the evidence (drivers) behind it.

## How the claims are defended (the actual contribution)

- **Purged, embargoed walk-forward CV** — no future leaks into the past.
- **Null-signal leakage guard** — feed pure-noise features and the pipeline
  produces ~zero out-of-sample skill (`tests/test_leakage.py`). If it manufactured
  skill from noise, that test would fail. It doesn't.
- **Deflated Sharpe + PBO** — the arena reports each strategy's Sharpe *deflated*
  for having raced six strategies, and a Probability of Backtest Overfitting
  (CSCV). A high PBO is the tell that the "winner" is luck.
- **Beat-the-closing-line** — the calibration log scores your probabilities
  *against the market's price*, not just the base rate. `brier_skill_vs_market > 0`
  is the only real evidence of edge; being merely calibrated is not.
- **Exact costs** — Kalshi's fee (peaks $0.0175/contract at 0.5) and turnover
  costs are modeled; a frictionless backtest is a fantasy.
- **A real bug, caught the honest way** — an early Elo update inflated rating
  spread 13x and wrecked calibration while still *ranking* players correctly. The
  reliability diagram caught what an accuracy check missed. That's the whole skill.

## What's real, synthetic, or blocked (no pretending)

- **Live and verified:** Kalshi + Polymarket prices and settlement, Yahoo
  trending/charts, Google News, arXiv, FRED macro, SEC EDGAR (with a contact UA),
  ~100-channel media watch, the forward paper-trading study, Discord alerts, and
  the daily GitHub Actions run that publishes the dashboard.
- **Synthetic here, real in the cloud:** tennis/NBA data (Sackmann is blocked on
  the dev sandbox but reachable on GitHub runners); soccer has a real loader
  (football-data.co.uk).
- **Deliberately not built:** a vector-DB/RAG layer — there's no corpus to justify
  it yet (see `data-automation.md`). Point-in-time survivorship-free equity data —
  the universe is current-membership, fine for a live scanner, wrong for a
  cross-sectional backtest (flagged in code).

## Does it make money? (the honest read)

Probably not a money printer, and that was never the bar. Trend/theme momentum is
a real, documented factor, so being early and informed is a genuine (if small,
crowded, risky) edge — not fantasy. But after vig, fees, capacity, and the
multiple-testing penalty, most rigorous attempts find little to no edge, and a
clean study that says so is a *stronger* signal to a quant desk than a suspicious
4.0 Sharpe. The deliverable is the **calibration track record** and the
methodology, not the P&L. See the balanced breakdown in `project-forecasting-lab.md`.

## Reproduce

```bash
pip install -e ".[all]"
pytest                                   # 158 property + leakage tests
python -m forecasting_lab.cli.elo_backtest --synthetic
python -m forecasting_lab.cli.sim run --bars 250     # arena + deflated Sharpe + PBO
python -m forecasting_lab.cli.run_all                # the full daily pipeline
```

## Status

Cloud automation is live (daily GitHub Actions → dashboard on Pages → Discord
alert). The most valuable ongoing work is simply letting the **forward study** and
the **auto-resolving calibration log** accumulate real out-of-sample marks — in a
few weeks this page gets real numbers to replace the synthetic ones.

---
*Last updated: 2026-07-02. A research and skill-building system, not a
recommendation engine, and not financial advice.*
