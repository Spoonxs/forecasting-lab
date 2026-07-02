# Project: Forecasting & Market Analytics Lab

A research platform for forecasting real-world events using prediction markets, sports models, and market microstructure, with an alt-data signal layer underneath. The flagship technical-depth project: the same skill stack quant firms screen for, and the alt-data layer is what turns a dashboard into something with an edge.

Companion docs: `signal-monitoring.md` is the alt-data and monitoring layer (what to scrape, track, and automate), and `ml-system-design.md` is the modeling layer above it. This file is the platform; those two are the data and the model.

## Implemented in this repo

This brief is now backed by working code (`src/forecasting_lab/`, see `CLAUDE.md`):

| This brief | Module |
|---|---|
| Polymarket / Kalshi clients, title matching, live cross-venue monitor | `markets/` (`polymarket.py`, `kalshi.py`, `matching.py`, `divergence.py`, `monitor.py`) |
| Tennis Elo (global + surface), Monte Carlo brackets, Sackmann loader | `sports/` (`elo.py`, `simulate.py`, `tennis_data.py`) |
| Brier / log loss / calibration | `eval/` (`metrics.py`, `calibration.py`) |
| VectorBT/Backtrader-style walk-forward + costs | `backtest/` (`engine.py`, `costs.py`) |
| The public calibration track record | `calibration_log/` |

Run it: `python -m forecasting_lab.cli.elo_backtest --synthetic` (or `--years 2022 2023`).

---

## Data sources (all verified, with the gotchas)

### Prediction markets

**Polymarket** splits across three public REST surfaces plus a WebSocket (docs at docs.polymarket.com). On Polygon, USDC.e settlement, UMA optimistic oracle.
- Gamma API: `https://gamma-api.polymarket.com`, fully public, no auth. Market and event metadata; the endpoints you live in are `/markets` and `/events`. This is where you get token IDs, end dates, volume, descriptions.
- CLOB API: `https://clob.polymarket.com`. Order book and prices are public; order placement is authenticated via wallet signing with the official `py-clob-client`. The read-only client in this repo (`markets/polymarket.py`) hits the live CLOB surface — `/book`, `/midpoint`, `/price?token_id=` — and coerces the string prices to floats; verify exact paths against docs.polymarket.com as they evolve.
- Data API: `https://data-api.polymarket.com`. User positions, trade history, and (as of 2026) the trader leaderboard.
- Gotchas that silently invert your numbers: prices come back as JSON strings not floats, the `side` parameter meaning is easy to flip, order-book arrays have a specific ordering, and public endpoints are rate-limited and flaky under load. Cache aggressively.

**Kalshi** is one unified REST API (docs at docs.kalshi.com), CFTC-regulated. Base `https://api.elections.kalshi.com/trade-api/v2`, endpoints grouped as `/markets`, `/events`, `/orders`, `/portfolio`.
- Market data is public; trading needs an API key pair with per-request RSA-PSS signatures in `KALSHI-ACCESS-KEY` / `KALSHI-ACCESS-TIMESTAMP` / `KALSHI-ACCESS-SIGNATURE` headers. Sign the path without query params.
- Rate limit is roughly 10 req/s per key; a 429 means back off with exponential retry. Maker (resting limit) orders are free; taker fees peak near $0.0175/contract at the 50c midpoint and shrink toward the ends. There is a demo environment, test against it first. WebSocket for real-time book updates.

**Cross-venue edge:** the same real-world event is often listed on both Kalshi and Polymarket. Price divergence between the two (after fees) is a clean, concrete signal to build a screener around.

### Sports (tennis as the first sport, Elo works well there)

Jeff Sackmann / Tennis Abstract on GitHub is the canonical free dataset:
- `JeffSackmann/tennis_atp`: `atp_matches_YYYY.csv` per season, plus player file and rankings. There is a `matches_data_dictionary.txt` that spells out columns.
- `JeffSackmann/tennis_wta`, `tennis_pointbypoint`, `tennis_slam_pointbypoint`, and the Match Charting Project (`tennis_MatchChartingProject`) for shot-by-shot data.
- License: Creative Commons Attribution-NonCommercial-ShareAlike 4.0. That means attribution is required and commercial use is not permitted. Fine for a research/portfolio project; if the lab ever turns commercial you cannot use this data commercially, so design that boundary in from the start.

### Alt-data signal layer (the differentiator)

The tracker that just shows odds is a commodity. The alt-data feed underneath is what gives it edge. Full detail in `signal-monitoring.md`; the short version:
- Quiver Quantitative: `quiverquant` pip package, around $10/month, free tier is delayed. Covers congressional trades, lobbying, government contracts, insider transactions, off-exchange short volume, and r/wallstreetbets sentiment, all mapped to tickers.
- Raw and free: congressional disclosures at `efdsearch.senate.gov` (Senate) and `disclosures-clerk.house.gov` (House). You parse them yourself. Capitol Trades has a good UI but no public API.
- Honest caveat on the alpha: the STOCK Act gives members up to 45 days to disclose, so this data is structurally late. Academic work shows congressional portfolios have beaten the S&P historically, but the disclosure lag caps how much real-time edge a retail pipeline can extract. Treat it as one feature, not a money printer.

---

## Models

- Tennis: maintain global plus surface-specific Elo (Hard, Clay, Grass). Standard Elo logistic function for win probability, a tunable surface-blending parameter, a K-factor (FiveThirtyEight-style starting points are a fine default). Model matches as Bernoulli trials on the predicted probability; use Monte Carlo to simulate full tournaments and get bracket-level distributions.
- Evaluation: Brier score and log loss on a held-out, time-forward test set, plus a calibration plot. Accuracy is the wrong headline metric; a model that just picks the higher seed already looks good because favorites win most tennis matches.
- For anything beyond Elo (cross-sectional ML on the market data), follow `ml-system-design.md`: gradient-boosted trees, purged walk-forward CV, survivorship-bias-free data.

---

## Backtesting stack

Pick by the shape of the job, not by hype:
- VectorBT (`vectorbt.dev`, `pip install vectorbt`): vectorized over NumPy with Numba acceleration. Runs thousands of parameter combinations in seconds and has a built-in walk-forward optimization split. This is your research-speed engine for sweeps.
- Backtrader: event-driven, steps bar by bar like live trading, handles commissions, slippage, and stops out of the box. Use it for realistic execution simulation of a chosen strategy.
- Backtesting.py for quick prototyping, NautilusTrader if you ever go production/real-money, Zipline-Reloaded plus pyfolio for factor-style research.
- Practical path: prototype and sweep in VectorBT, then re-run the survivor in Backtrader with realistic costs before believing anything.

---

## Guardrails (this is what separates real from curve-fit)

- Time-respecting splits only. Never random splits on a time series.
- Walk-forward validation, evaluate strictly out of sample.
- Model transaction costs and slippage. A frictionless backtest is a fantasy, and on Kalshi/Polymarket the fee structure is known, so there is no excuse.
- No look-ahead bias in the feature pipeline. The most common silent bug is using data that would not have existed at decision time.
- Calibration over accuracy. Track Brier score. Be skeptical of any "X% accuracy" claim until you know the base rate it is beating.

---

## Calibration track record (the credibility artifact)

Separate from the lab, keep a public forecasting log: every prediction with your probability estimate, scored over time with a Brier score, on Kalshi or Polymarket US. A clean, honest calibration record is the single most credible thing you can put in front of a quant recruiter, more than any backtest.

---

## Plan (status-mapped; the code is ground truth)

Phase 1 — the engine ✅ *(built and tested; see `CLAUDE.md` for the map)*
- Baseline models + scoring: tennis Elo, Brier/log-loss/reliability, the calibration log.
- Venue clients (Polymarket, Kalshi), cross-venue matching + divergence monitor
  (`flab-divergence --live` fetches both venues, auto-matches, files a digest).
- Purged walk-forward CV, cost models, backtester vs honest baselines, signal composites.
- Storage is dated digests + cached CSVs, **not Postgres** — the original plan's DB adds
  ops burden with no research payoff at this scale; revisit only if intraday history
  accumulation becomes a real need.

Phase 2 — run it on real data (the current phase)
- Tennis: download Sackmann seasons, publish the real calibration numbers.
- Markets: run the divergence monitor on a schedule; log every flagged candidate's
  resolution-criteria check (most "arbs" die there — that log is itself a result).
- Start the public calibration log with real forecasts (`flab-calibration record`).
- Alt-data: ✅ the trending-stocks scanner (`flab-trending`: Yahoo trending + charts +
  Google News) files live GME-shape / NVIDIA-shape digests; next, score a month of
  those digests against the calibration log. The strategy arena (`flab-sim`) races
  strategies vs baselines with persistent state; `flab-dashboard` renders the whole
  lab as one page.

Phase 3 — proof of work
- Public GitHub, 2-3 writeups with real results: the Elo calibration study, the
  divergence screen's honest hit rate, the null-signal leakage guard as methodology.
- A losing model with honest analysis is still a strong writeup. The dashboard
  (`flab-dashboard`) is the front page for it.

## Next forecasting projects (ranked by fit with what's built)

1. **NFL / soccer Elo** — the `basketball.py` machinery (home advantage + MOV +
   season reversion) transfers almost unchanged; soccer needs a draw model
   (Davidson extension). Free data: football-data.co.uk CSVs.
2. **Options-implied probabilities vs prediction markets** — back out event odds
   from listed options (e.g. Fed decisions from rate futures) and screen against
   Kalshi the same way `matching.py` screens Polymarket. Deepest quant skill per
   hour of the list.
3. **Macro nowcasting with FRED** — the FRED CSV API is free and reachable;
   recession/CPI-surprise probabilities, scored in the calibration log against
   Kalshi's macro markets.
4. **Weather calibration benchmark** — NOAA forecasts vs Kalshi weather markets;
   weather is the one domain where forecasters are *known* to be calibrated, so
   it's the perfect control experiment for the log.
5. **Meta-forecasting** — ensemble your own log: does averaging your forecast
   with the market price beat both? (It usually does — that's the extremizing
   literature. Tetlock, ch. 9.)
6. **News-sentiment feature for the trending scanner** — headline counts are in;
   scoring their tone (finance-tuned lexicon, or an LLM judge with a frozen
   prompt) is the next honest increment, validated against forward returns with
   the purged CV that's already here.

Deepen-what-exists candidates: real tennis data on an unblocked network; the
arena gaining position sizing (Kelly fraction) and capacity limits; meta-labeling
(López de Prado ch. 3) on top of the GBM ranker; conformal prediction intervals
on the Elo probabilities.

New, higher-leverage suggestions (post-cloud):
- **Beat-the-closing-line study** — the only honest sports test: log each Elo
  prediction *and* the market's, resolve, and measure whether you beat the close
  after vig. If you don't, you have a calibrated model, not an edge — and knowing
  which is the whole skill.
- **Sentiment, not just count** — score the Reddit/news text (finance lexicon or a
  frozen-prompt LLM judge) and validate the sentiment feature against forward
  returns with the purged CV already here. Count is a weak proxy; tone is the test.
- **Deflated Sharpe / PBO** — implement López de Prado's deflated Sharpe and
  probability-of-backtest-overfitting so the arena reports *how likely its winner
  is luck*. This is the single most credible thing to add.
- **Auto-resolving calibration log** — wire Kalshi/Polymarket resolution back into
  `calibration_log` so forecasts score themselves; that turns the daily cloud job
  into a self-updating public track record (the actual portfolio piece).
- **Regime labels on the arena** — tag each period bull/bear/chop (from the macro
  panel) and report per-regime performance; "momentum wins in trends, dies in
  chop" is a finding, a single Sharpe is not.
- **A second alt-data source with real latency accounting** — options flow or
  FINRA short interest, explicitly modeling the disclosure lag so you never fool
  yourself that stale data was tradable.

## Will this actually make money? (the balanced version)

Honest answer: **a slight, real edge is possible from being early and informed —
but it's hard, risky, and mostly shows up as "lose less / catch more themes",
not a money printer.** The "be in the know before the crowd fully piles in"
thesis (NVIDIA's AI run, GME's squeeze, BTC's cycles) is a real style with a name:
**momentum / theme investing**, one of the most durable, academically documented
factors there is. So it's not fantasy — the honest caveats are *risk* and
*discipline*, not "impossible".

Where the edge can be real (if you're early and disciplined):
- **Theme momentum** — noticing a durable trend (AI infra, GLP-1s, a policy shift)
  while it's still building and riding it. The media-watch + trending layers exist
  exactly to surface these early. Real, but crowded fast, and it round-trips hard
  when the theme breaks — position sizing is what keeps you solvent.
- **Cross-venue divergence** — genuine small arbs exist between Kalshi/Polymarket;
  the catch is most flagged gaps aren't the *same* event on inspection. Treat a
  flag as "investigate", not "free money".
- **Under-covered corners** — thin sports markets, small-cap news the desks ignore.
  Attention, not speed, is the edge here — which is your whole point.

Where it's mostly a trap:
- Chasing a name *after* it's loud (you're the exit liquidity).
- Any single backtest that looks great (multiple-testing: try 6 strategies, one
  wins by luck ~40% of the time — that's why this repo reports baselines + soon
  deflated Sharpe).
- Leverage on a thesis that "has to" work — the market outlasts your solvency.

For a young, risk-tolerant person: a **barbell** is the sane version of your plan —
most of it in the boring index core (tier 1 of `learning-investing.md`), a defined
slice you're willing to lose on high-conviction theme bets, sized so a total loss
is survivable. The lab's job is to make that slice *informed and measured* (the
media watch to catch themes early, the calibration log to prove whether your calls
are actually good, the forward study to watch the strategies play out live) rather
than a hunch. That's the honest edge available to a retail participant — and it's a
real one. Just not a guaranteed one, and this is not financial advice.

<details><summary>The blunter per-component breakdown</summary>

- **Sports Elo** is well-calibrated but the closing line already embeds it. To
  profit you must beat the *market's* probability after the vig (~4-5% hold),
  which a public-data Elo does not reliably do. Edge, if any, is in obscure
  matches with thin markets — and staking discipline, not the model, decides P&L.
- **Cross-venue divergence** is the closest thing to real edge here, but the gaps
  that survive fees are usually gaps for a reason: different resolution criteria,
  withdrawal frictions, or one leg you can't actually fill. Genuine arbs are
  small, fleeting, and capacity-limited. Treat a flag as "investigate", not "free
  money" — and most investigations end in "not actually the same event."
- **The trending scanner** surfaces what's already moving. By the time a name is
  loud, the crowd is your counterparty, not your edge. It's a research lens, not
  a buy list. The academic record on retail momentum-chasing is brutal.
- **The strategy arena** shows momentum "winning" on synthetic and recent real
  data — but that's frictionless-ish backtest territory. Add realistic costs,
  slippage, capacity, and the multiple-testing penalty (you tried six strategies;
  one wins by luck alone ~40% of the time) and the edge shrinks toward zero. That
  shrinkage *is* the lesson.
- **Macro nowcast** is a probability, not a trade. Everyone can see the yield
  curve.

What it IS realistically good for: a **calibration track record** (the credential
quant desks and PhD committees actually reward), fluency in the methodology that
separates real research from curve-fitting, and a portfolio that proves you can
build a leak-free, cost-aware, honestly-evaluated system. Most rigorous attempts
find little to no edge after costs — and a clean study that says so is a *stronger*
signal than a suspiciously good backtest. If you want to grow money, tier 1 of
`learning-investing.md` (index funds) beats everything in this repo. If you want
to grow *skill* — and maybe earn the seat where you trade someone else's capital
with real data and infrastructure — this is the right training ground.

</details>

## References

- Polymarket docs: https://docs.polymarket.com
- Kalshi docs: https://docs.kalshi.com
- Sackmann data: https://github.com/JeffSackmann/tennis_atp (and tennis_wta, tennis_pointbypoint)
- VectorBT: https://vectorbt.dev
- Quiver Quantitative: https://www.quiverquant.com (pip `quiverquant`); raw disclosures: https://efdsearch.senate.gov and https://disclosures-clerk.house.gov

---

*Last updated: June 2026*
