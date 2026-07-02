# Forecasting Lab: ML System Design

How to turn the signal-monitoring layer into a real machine-learning system. The honest version, where the methodology is the moat, not the data volume.

This is a research and skill-building system, not a recommendation engine, and not financial advice. Built rigorously, it is exactly the skill quant research and PhD committees reward, regardless of whether it ever prints money.

> **Implemented in this repo:** `ml/` carries the methodology — `PurgedWalkForwardCV` (purge + embargo), `features` (cross-sectional rank/z-score, lagging), `labels` (forward-return + triple-barrier), and `CrossSectionalRanker` (LightGBM → sklearn → ridge). `backtest/` compares against the honest baselines. The leakage traps below each map to a property test in `tests/`.

## What "more data" buys, and what it doesn't

- Helps: variance reduction, feature coverage, more regimes seen.
- Does not fix: non-stationarity (patterns change over time), data leakage (using info you wouldn't have had at decision time), survivorship bias (delisted tickers missing from the dataset), low signal-to-noise. These are the killers, and they are methodology problems, not volume problems.

## The rare-event problem (read first)

GME-magnitude events happen a handful of times per decade. There is no training set for them. You cannot supervise a model to predict an event with five lifetime examples. So reframe the target to something learnable:
- Cross-sectional ranking: predict which stocks outperform over horizon H. Standard quant setup, cleanest.
- Anomaly detection: unsupervised, flag unusual states for a human to investigate.
- The model gives elevated probability of a moderate move, not the jackpot. Accept that and it becomes useful.

## Problem framing

- Target: start with cross-sectional ranking (forward relative return over horizon H). It sidesteps the class-imbalance trap of binary "abnormal move" labels.
- Horizon: short (days to weeks) for squeeze-type, long (months) for momentum-type. Two separate models, two separate feature sets.
- Pick the short-horizon cross-sectional ranker first; it is the most tractable.

## Data layer (the "extreme data," done right)

- Price and volume: survivorship-bias-free is non-negotiable. Free yfinance fails this because delisted names are gone. Use CRSP (free via DePaul's library if available, the academic standard), Polygon.io flat files, Norgate Data, or Nasdaq Data Link.
- Fundamentals: SEC EDGAR (free, full-text), Financial Modeling Prep / Alpha Vantage.
- Alt-data: the signal-monitoring sources, short interest (FINRA), social velocity (Reddit, StockTwits), options, off-exchange short (Quiver).
- Point-in-time discipline: every feature must be as-of the decision date, with no restated values. This is where leakage creeps in silently. If a fundamental was revised later, the model must see only what was known then.

## Features

- From the composites: short interest % of float, days-to-cover, social velocity z-scores, options skew, volume anomalies, price momentum and relative strength, earnings surprise, analyst revisions.
- Cross-sectional normalization: rank or z-score features within each date, so the model learns relative position, not absolute levels that drift.
- Lag everything correctly. A feature computed from end-of-day data cannot be used to trade that same day's close.

## Labels

- Forward returns over the horizon. Consider the triple-barrier method (profit-take, stop, time limit) for path-aware labels rather than fixed-horizon returns.
- Handle imbalance honestly if you use any classification target; do not let accuracy on a 95%-negative dataset fool you.

## Model choice

- Start with gradient-boosted trees (LightGBM or XGBoost) on the cross-sectional features. On tabular market data, GBMs beat deep nets in practice. This is the real state of the art for alpha, not a compromise.
- "Extreme data plus a large neural network" is usually the wrong first instinct for this data type.
- Sequence models (LSTM, Transformer) only if there is genuine sequential structure and enough data, and even then they rarely beat well-engineered GBMs here.

## Validation (the part that decides whether any of it is real)

- Purged, embargoed walk-forward cross-validation (combinatorial purged CV). Standard random k-fold leaks the future into the past on time series and is the single most common reason backtests look great and fail live.
- Touch the out-of-time test set once. Every peek is a chance to overfit to it.
- Deflated Sharpe ratio, or otherwise correct for multiple testing. Try enough features and one "works" by chance.
- Calibration over accuracy. A model that says 30% and is right 30% of the time is more useful than a confident one that is miscalibrated.

## Backtest

- Realistic transaction costs, slippage, and capacity limits. Walk-forward only.
- Compare against honest baselines: random selection, buy-and-hold, and a simple momentum rule. If you do not beat simple momentum after costs, you do not have a model.

## The methodology traps (the actual moat)

These are what separate a real attempt from a self-deluding backtest, and naming and avoiding them is the quant skill itself:
- Look-ahead bias and data leakage.
- Survivorship bias.
- Improper cross-validation on time series.
- Overfitting and multiple-testing.
- Non-stationarity and regime change.
- Class imbalance on rare-event targets.
- Label leakage from restated data.

## Resources

- Marcos López de Prado, *Advances in Financial Machine Learning*. The reference for purged CV, triple-barrier labeling, meta-labeling, feature importance, and why most financial ML backtests are false. Read this before building.
- Libraries: scikit-learn, LightGBM / XGBoost, mlfinlab (implements López de Prado's methods; check current licensing), pandas, and the backtesting stack from the lab (VectorBT, Backtrader).
- Data: CRSP, Polygon.io, Norgate, Nasdaq Data Link for survivorship-bias-free history.
- Experiment tracking: MLflow or Weights & Biases, so every run's data, features, and parameters are logged and reproducible.

## What success honestly looks like

Most rigorous attempts find little to no edge after costs. That is the expected outcome, and it is still a win, because the honest pipeline plus a calibration log is the portfolio and credential, regardless of P&L. A clean, leak-free, walk-forward-validated study is the thing that signals quant-research ability. A backtest with a 4.0 Sharpe is the thing that signals you leaked.

## Build order

1. Survivorship-bias-free data plus point-in-time features. The unglamorous 80% of the work, and the part that determines whether the rest is real.
2. A simple LightGBM cross-sectional ranker, horizon of a few weeks.
3. Purged walk-forward CV plus a calibration curve.
4. An honest backtest against the baselines.
5. Only then add alt-data features, the longer-horizon momentum model, and any fancier architecture.

## A note on the RL / fine-tuning thread

GRPO, RULER, and ART (from the earlier tools) are a different paradigm, for training agents that take actions, not for cross-sectional alpha prediction. They are a separate path and not the tool for this system. Don't reach for them here just because they're new.

---

*Not financial advice. A research and skill-building system, not a recommendation engine.*
*Last updated: June 2026*
