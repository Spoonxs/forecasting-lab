# Forecasting & Market Analytics Lab

A research platform for forecasting real-world events using **prediction markets**,
**sports Elo models**, and an **alt-data signal layer** underneath — with the
rigor (leak-free validation, realistic costs, calibration scoring) that quant
research actually rewards.

> The methodology is the moat, not the data volume. This is a research and
> skill-building system — **not** a recommendation engine, and **not financial
> advice.**

It ships as both a set of **briefs** (the domain knowledge and plan) and a working,
tested **Python package** (`forecasting_lab`). Start with [`CLAUDE.md`](CLAUDE.md)
for the map and the non-negotiable guardrails.

## What's inside

| Layer | Module | What it does |
|---|---|---|
| Evaluation | `forecasting_lab.eval` | Brier, log loss, reliability/ECE, Murphy decomposition, calibration plots |
| Sports | `forecasting_lab.sports` | Tennis Elo (surface), **NBA Elo** (home edge + margin-of-victory), **soccer Elo** (3-outcome draw model), Monte Carlo brackets |
| Macro | `forecasting_lab.macro` | FRED yield-curve recession nowcast (Estrella-Mishkin probit) |
| Sources | `forecasting_lab.sources` | 600+ tracked universe: S&P 500, SEC EDGAR, FRED, Reddit, arXiv, ~100 media voices — with a coverage report |
| Media | `forecasting_lab.media` | ~100-channel watch list (`@handle` auto-resolving), YouTube RSS/yt-dlp + Google News → ticker/theme buzz (`flab-watch`) |
| Forward study | `forecasting_lab.forwardtest` | Records real-basket picks each run, marks them to market on the next — a live out-of-sample study (`flab-forward`) |
| Automation | `flab-run-all` + `flab-cron` + `.github/workflows/daily.yml` | One failure-tolerant orchestrator; a local daily OS task, **or** a cloud GitHub Actions cron that runs the pipelines and publishes the dashboard to Pages |
| Markets | `forecasting_lab.markets` | Polymarket + Kalshi clients (string-price fix, RSA-PSS signing, pagination), title matching + live cross-venue divergence monitor |
| ML | `forecasting_lab.ml` | Cross-sectional features/labels, **purged walk-forward CV**, GBM ranker |
| Backtest | `forecasting_lab.backtest` | Exact Kalshi/Polymarket cost models, walk-forward backtester vs honest baselines |
| Signals | `forecasting_lab.signals` | Squeeze + momentum composites, plus the **live trending-stocks scanner** (Yahoo trending/charts + Google News) for NVIDIA/GME shapes |
| Arena | `forecasting_lab.sim` | Persistent paper-trading race: strategies vs honest baselines, turnover costs, resumable state |
| Dashboard | `forecasting_lab.dashboard` | Single-file amber-terminal dashboard (hand-rolled SVG) of the whole lab |
| Track record | `forecasting_lab.calibration_log` | A public, Brier-scored forecasting log — the credibility artifact |
| Pipeline | `forecasting_lab.pipeline` | invoke→fetch→process→store; files dated digests into `inputs/` |

## Quickstart

```bash
pip install -e ".[all]"      # core is light (numpy/pandas); ml/markets/viz are extras
pytest                       # 143 tests, a few seconds, no network needed
```

Run the headline demo — fit a **time-forward** tennis Elo on synthetic data and
score its calibration:

```bash
python -m forecasting_lab.cli.elo_backtest --synthetic
```
```
Evaluated on 3,798 matches (surface_weight=0.5, K=538):
  Brier score        0.1941   (base-rate baseline 0.2496)
  Brier skill score  +0.2222   (>0 beats climatology)
  Log loss           0.5717
  ECE                0.0145   (calibration error; lower better)
  Accuracy @ 0.5     0.7019   (context only - favorites win a lot)
```

Real ATP/WTA history (downloads & caches [Jeff Sackmann](https://github.com/JeffSackmann/tennis_atp)
CSVs — CC BY-NC-SA, non-commercial):

```bash
flab-elo --years 2021 2022 2023 --tour atp --plot reliability.png \
         --simulate Djokovic Alcaraz Sinner Medvedev
```

Other CLIs:

```bash
flab-elo --sport nba --synthetic            # NBA Elo: home advantage + margin-of-victory
flab-elo --sport soccer --synthetic         # soccer Elo: 3-outcome Davidson draw model (RPS)
flab-macro                                   # live yield-curve recession probability (FRED)
flab-trending                               # scan trending stocks for GME/NVIDIA shapes -> inputs/
flab-sim run --bars 250                     # advance the persistent strategy arena (resumes)
flab-research                               # sweep recent arXiv q-fin papers, ranked -> inputs/
flab-sources                                # report the 500+ tracked-source coverage
flab-dashboard --open                       # build site/index.html (the amber-terminal lab view)
flab-watch                                  # ~100 key voices (YouTube+news) -> ticker/theme buzz
flab-alert --setup                           # how to add a free Discord webhook (1 min)
flab-alert --test                            # send a test ping to Discord/Telegram/local
flab-run-all                                 # run EVERY pipeline, rebuild dashboard, send alert
flab-cron install --time 07:30              # schedule flab-run-all daily (real OS task, $0)
```

**Running it free (no subscription):** the local scheduled task above, or the free
GitHub Actions cron (`.github/workflows/daily.yml` → Pages), or a free-forever
Oracle Cloud Always Free VM. Alerts post to a free Discord webhook (recommended)
or Telegram bot, or fall back to `inputs/alerts.log`. See `data-automation.md`.

## Design principles (the guardrails)

1. **Time-respecting splits only** — `ml.PurgedWalkForwardCV` (purge + embargo), never random k-fold.
2. **No look-ahead / leakage** — features are as-of the decision date; lag EOD data.
3. **Model costs** — Kalshi/Polymarket fees are known; a frictionless backtest is a fantasy.
4. **Calibration over accuracy** — Brier + reliability diagrams, always beat the base rate.
5. **Survivorship-bias-free data** for cross-sectional studies.

See [`CLAUDE.md`](CLAUDE.md) for the full operating doc and [`project-forecasting-lab.md`](project-forecasting-lab.md)
for the hub brief.

## Repo layout

```
forecasting-lab/
├── CLAUDE.md                  operating doc: guardrails, repo map, conventions
├── *.md                       the briefs (domain knowledge, plan, learning path)
├── src/forecasting_lab/       the package (eval, sports, markets, ml, backtest, signals, ...)
├── tests/                     143 property-based tests
├── inputs/                    dated research digests land here (gitignored)
├── pyproject.toml             packaging + extras + console scripts
└── requirements.txt
```

## Development

```bash
pytest                        # run the suite
ruff check src tests          # lint
```

Every model/metric ships with a **property test** (monotonic, zero-sum,
calibrated, leak-free), not just a golden number — because the silent
leakage/calibration bugs are the whole point of the exercise.

---
*Not financial advice. Data sources carry their own licenses (Sackmann tennis data
is CC BY-NC-SA — research/non-commercial only).*
