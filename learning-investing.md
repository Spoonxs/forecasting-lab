# Learning: Investing & Financial Decisions

The education layer of the lab. The models measure whether you can *forecast*;
this file is about whether you can *keep and grow money* — and those are very
different skills. Read tier 0 and 1 before believing anything a backtest says.

**The uncomfortable truth first.** The large majority of active retail traders
underperform a boring index fund after costs; the academic evidence on this is
one-sided. This lab exists to build *skill* (the thing quant firms hire) — the
default place for actual savings is tier 1, not a strategy from the arena.

---

## Tier 0 — Foundations (do these before any investing)

1. **High-interest debt first.** Paying off a 24% APR card is a guaranteed,
   tax-free 24% return. No strategy in this repo beats it.
2. **Emergency fund** — 3-6 months of expenses, liquid. This is what lets every
   other decision be unforced.
3. **Tax-advantaged accounts before taxable** (in the US: 401(k) to the match →
   Roth/Traditional IRA → HSA if eligible → back to 401(k)). The match is an
   instant 50-100% return; nothing else comes close.
4. **Insurance for catastrophes only** — health, liability, term life if someone
   depends on you. Never insure what you can afford to lose.

## Tier 1 — The passive core (where actual wealth compounds)

- **Broad, cheap index funds** (total-market or S&P 500, expense ratio < 0.1%).
  Costs compound exactly like returns, in reverse: 1% annual fees ≈ a quarter of
  your final wealth over 40 years.
- **Time in market beats timing the market.** Missing the 10 best days per
  decade roughly halves returns; those days cluster next to the worst ones, so
  you cannot dodge one without the other.
- **Automate it** and stop looking. The behavior gap (buying high in euphoria,
  selling low in panic) costs the average fund investor more than fees do.
- Reading: John Bogle, *The Little Book of Common Sense Investing*; JL Collins,
  *The Simple Path to Wealth*; the Bogleheads wiki (free).

## Tier 2 — How markets actually work

- Burton Malkiel, *A Random Walk Down Wall Street* — why most patterns are noise.
- Efficient markets *and their limits*: prices embed public information fast,
  but slow-moving factors (value, momentum, carry) have persisted. Whether they
  survive *your* costs is the only question that matters.
- Howard Marks, *The Most Important Thing* — risk is not volatility; it is the
  probability of permanent loss.
- Morgan Housel, *The Psychology of Money* — the behavior half of the problem.

## Tier 3 — The quant canon (the lab's methodology sources)

- Marcos López de Prado, *Advances in Financial Machine Learning* — purged CV,
  triple-barrier labels, why most backtests are false. The repo's `ml/` module
  implements its core ideas.
- Grinold & Kahn, *Active Portfolio Management* — the fundamental law: skill ×
  breadth, information coefficients. Why tiny edges need many independent bets.
- Antti Ilmanen, *Expected Returns* — the encyclopedia of where returns come from.
- AQR's research library (free) — factor investing at near-academic quality.
- `flab-research` sweeps the current arXiv tail into `inputs/` weekly.

## Tier 4 — Forecasting & decision quality (the lab's soul)

- Philip Tetlock, *Superforecasting* — calibration, base rates, belief updating;
  the entire reason `calibration_log/` exists.
- Annie Duke, *Thinking in Bets* — resulting (judging decisions by outcomes) is
  the amateur's tell; judge process instead.
- Daniel Kahneman, *Thinking, Fast and Slow* — the bias catalogue.
- Practice loop: log forecasts with probabilities (`flab-calibration record`),
  resolve them, and let the Brier score — not memory — tell you if you're good.

## Rules that survive contact with real money

1. Paying off expensive debt beats every strategy in this repo.
2. Costs and taxes compound; minimize both before optimizing anything else.
3. Never trade money you cannot lose entirely; position size assuming you're wrong.
4. Edge is measured (calibration log, walk-forward, after costs), never felt.
5. If a strategy's pitch involves a Discord, a course, or urgency — it's the product, you're the exit liquidity.
6. The market can stay irrational longer than you can stay solvent (leverage kills).
7. When in doubt, the answer is the boring index fund.

---

*Education, not financial advice. The lab measures forecasting skill; your
savings belong in tier 1 unless measured edge says otherwise — and it almost
never will.*
