# Project Add-on: Signal Monitoring (the watchlist scanner)

The alt-data and monitoring layer of the Forecasting & Market Analytics Lab. It ingests sources, computes signal composites, and files a dated digest of flagged tickers into `inputs/`. It surfaces candidates for analysis. It is not a buy signal, and it is not financial advice.

> **Implemented in this repo:** `signals/` computes the two composites (`squeeze_composite`, `momentum_composite`, kept separate) and `write_signal_digest` files the dated note. The "spike, not the level" z-score is `ml.features.zscore_velocity`. Try it: `python -m forecasting_lab.cli.signal_scan --demo`.
> The **live automation** is `signals/trending.py` (`flab-trending`): Yahoo trending tickers + 6-month charts + Google News headlines → fast-money (GME shape) and secular-momentum (NVIDIA shape) rankings filed as a dated digest. Free short interest is too stale to be in the fast composite — by design, per the latency caveats below.

## Frame it right: two phenomena, two signal sets

- Squeeze / meme (GME type): short-term, driven by positioning and crowd velocity. Signals are short interest, social velocity, and options/gamma.
- Secular momentum (NVIDIA type): multi-year, driven by fundamentals and a theme. Signals are earnings acceleration, analyst revisions, and relative strength.

Track them as two separate composites. The data for one barely informs the other.

---

## Squeeze signals (GME type)

- Short interest % of float and days-to-cover. The classic setup. Sources: FINRA (free, reported bi-monthly with a ~2-week lag), Fintel and ChartExchange (free-ish web), Ortex and S3 Partners (paid, closer to real-time). Free data is lagged; real-time short interest costs money.
- Social velocity, the spike not the level. Reddit mention rate on r/wallstreetbets and ticker-specific subs, StockTwits message volume, X cashtag velocity. Compute a z-score against each ticker's own baseline; a 5x jump matters, a high steady level does not.
- Options and gamma. Unusual call volume, call/put ratio, and gamma exposure (dealer hedging fueled GME's move). Sources: paid flow (Unusual Whales) or raw options chains you process yourself.
- Volume spike versus average daily volume.
- Off-exchange / dark-pool short volume. Sources: FINRA ADF, or Quiver's off-exchange short feed.

## Momentum signals (NVIDIA type)

- Earnings acceleration and guidance raises. Sources: SEC EDGAR 8-K / 10-Q (free, full-text searchable), fundamentals APIs (Alpha Vantage, Financial Modeling Prep, free tiers, verify current limits).
- Analyst EPS estimate revisions. Upward revisions are one of the more durable predictive factors.
- Price momentum and relative strength. New highs, high RS versus the market.
- Institutional and insider accumulation. 13F filings (free, but 45-day lag) and Form 4 insider buys.
- Theme and alt-data. Hiring surges from job postings, web traffic, app downloads, supply-chain mentions. This is where a real edge on the next NVIDIA lives, and it is research-heavy, not a one-line scrape.

---

## What to scrape vs. pull via API vs. automate

Scrape (no good free API):
- Reddit subreddit mention velocity (append `.json` to URLs, or PRAW), StockTwits, short-interest aggregator pages.

Pull via API (free or freemium):
- SEC EDGAR: free, full-text filing search. The single best free fundamental source.
- FINRA short interest: free, bi-monthly.
- yfinance: free price and volume.
- Alpha Vantage / Financial Modeling Prep: fundamentals, free tiers (verify current).
- Quiver Quantitative (~$10/mo): WSB sentiment, off-exchange short volume, congressional trades, insider transactions, all ticker-mapped.

Automate:
- A daily (or intraday) scan computes both composites, flags tickers crossing thresholds, and writes a dated digest into `inputs/`. This is the pipeline pattern pointed at market data. Keep the squeeze ranking and the momentum ranking separate.

---

## The caveats, read these before trusting any flag

- It surfaces candidates, not buys. Most flagged tickers do nothing. Treat every flag as "look closer," never "enter."
- Latency caps how "live" this is. Short interest is bi-monthly and lagged, 13F and congressional data are 45 days behind. Genuinely real-time short interest requires a paid feed.
- Reflexivity. By the time a name is loud on WSB, the easy move is usually gone. The edge is the early velocity spike, not the peak.
- This is calibration and research, not a money printer. Log every "this looks like a setup" call with a probability, score it later with a Brier score, and let the record tell you whether the signal means anything. Same discipline as the rest of the lab.
- The legal line. Building a detector is fine. Trading on material non-public information, or coordinating or front-running a pump, is not.

## Crypto parallel (your earlier interest)

Same shape, faster and more adversarial. New-token velocity and liquidity from Birdeye, risk flags from rugcheck, holder concentration, deployer-wallet history. A detector is a legitimate build; aping the signal is the slot machine.

## Build order

Start with the free, low-latency, high-signal sources: SEC EDGAR, yfinance, Reddit mention velocity, and FINRA short interest. Compute the two composites, file a daily digest, and run your calibration log against it for a month. Add paid real-time feeds (Ortex, options flow) only once the free version has proven the signal is worth paying for.

---

*Not financial advice. A research and monitoring tool, not a recommendation engine.*
*Last updated: June 2026*
