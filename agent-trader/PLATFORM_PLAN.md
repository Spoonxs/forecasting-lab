# PLATFORM PLAN — the investment recommendation platform (P6+)

*Operator decision 2026-07-05: the product is an INVESTMENT RECOMMENDATION
PLATFORM, not a research digest. You pick an instrument — stock, ETF (VOO/QQQ/
SPY/...), mutual fund, or cash (HYSA) — set YOUR timeframe and goals, and get an
evidence-backed recommendation built from backtesting, live signals, news, and
track-record-weighted expert opinion, plus AI opinion from BOTH Claude and Codex.
It evaluates your portfolio, runs an arena of AI-built portfolios (Claude's vs
Codex's, tracked like Rallies' arena), and stays up to date automatically for
years. The rigor stack (P1-P3) is the engine; honesty (calibration, receipts,
"research opinions, not financial advice") stays on every surface.*

**Build references (mirror the structures, our own skin):**
`design-reference/AUTHED_CAPTURES.md` — 18 fresh logged-in interior shots.
Stock Taper = the statement-page shape (verdict-graded stats, going-well/
concerning per statement, "what this implies", institutional sentiment with
named sources, compare tool, news-with-ticker-links). Rallies = the platform
IA (research tabs per ticker, THE RATINGS SCALE = consensus label + price
target + distribution, the ARENA book table, agent builder, chat chips,
portfolio home). Codex (`codex exec`, CLI v0.140 authed) = second AI for idea
generation, code review of every commit, reference-fidelity comparison, and its
own arena portfolio.

## §1 The recommendation engine (deterministic core, AI opinions labeled)
Per instrument, a **RECOMMENDATION CARD**: a Rallies-style scale (Strong Buy /
Buy / Hold / Trim / Avoid — mapped from a deterministic composite score) + a
Stock Taper-style breakdown: each component graded and explained —
1. **Backtest** — our walk-forward strategies on this name, with costs, OOS.
2. **Signals** — trend/momentum composite, residual momentum, squeeze, attention.
3. **Fundamentals frame** — the going-well/concerning pairs per statement
   (revenue/margins/balance-sheet plain English, ▲/▼ per cell).
4. **News** — clickable dated headlines (real links), tone-scored, auto-refreshed.
5. **Expert track record** — `media/voices` leaderboard: what the historically
   RIGHT-and-EARLY voices say about this name (weighted by their Brier record,
   never followers).
6. **Macro regime** — recession nowcast + rates context (matters for HYSA vs equity).
7. **AI opinions, clearly labeled** — Claude's thesis and Codex's thesis,
   generated at build time, each with drivers + caveat, logged to the
   calibration scorecard so their hit-rate accrues publicly.
The verdict is **timeframe-conditional** (§2). Every card carries the trust
badge (sources + freshness), receipts (audit hash), and the disclaimer.

## §2 Timeframe + goals — the profile that re-weights everything
A profile control (persisted locally): **horizon** (0-1y / 1-5y / 5y+),
**goal** (grow / income / preserve), **risk** (low/med/high). Component weights
shift deterministically (short horizon → momentum/news up, fundamentals down;
preserve → HYSA/short-duration surfaced first, drawdown penalty up; income →
yield components). Verdicts re-render client-side from precomputed per-component
scores — one build serves every profile. The profile also drives the portfolio
builder's guardrails (mandate caps by risk level).

## §2b Full-universe coverage (operator requirement: "like Robinhood")
The registry covers **every listed US stock and ETF** (~11k symbols: SEC
company_tickers + Nasdaq Trader nasdaqlisted/otherlisted with the ETF flag),
all searchable. Two verdict tiers, honestly labeled on every card:
- **TIER FULL (nightly)**: S&P 500 + major ETFs + trending + `data/watchlist.json`
  (~1k names) — all components, backtests, audit-hashed artifacts.
- **TIER LIVE (on-demand, any symbol)**: computed in-browser through a free
  Cloudflare Worker (edge-cached quotes/bars, 100k req/day free — the
  low-latency path) running the SAME scoring contract from shipped weights
  JSON; fewer components ⇒ the confidence dials show it and INSUFFICIENT
  EVIDENCE gates identically. Watchlisting a name promotes it to TIER FULL
  on the next nightly build. Worker deploy is optional; without it TIER LIVE
  degrades to "add to watchlist for tomorrow's build" — stated, never silent.

## §3 Instruments beyond stocks
- **ETFs** (VOO QQQ SPY VTI IWM DIA SCHD + sector SPDRs): holdings overlap,
  expense ratio, drawdown/vol profile vs horizon, verdict card like stocks.
- **Mutual funds**: common ones (VTSAX/VFIAX/FXAIX...) mapped to ETF twins,
  expense-ratio deltas called out ("same exposure, 3x the fee").
- **HYSA / cash**: live yield context from FRED (T-bill/EFFR) + a rates table;
  the honest benchmark every risk asset must beat over the user's horizon.
- **Prediction markets** stay as the event-odds surface.

## §4 The portfolio: evaluate mine + AI-built books in the arena
- **My portfolio** (`portfolio.html`): holdings in (form/localStorage or a
  committed JSON), evaluated against the profile: allocation, concentration vs
  the V4 mandate (same thresholds, mirrored client-side), ETF overlap (QQQ⊂VOO),
  per-holding verdicts, book-level crowding, vs-SPY-and-vs-HYSA comparison, and
  deterministic advice lines with reasons.
- **The AI arena** (Rallies arena shape, Engo honesty): **Claude's portfolio**
  and **Codex's portfolio** — each AI states a thesis + picks a book (JSON,
  committed, audit-hashed), marked daily by the forward study; the book table is
  the Rallies layout (stock·alloc·P&L·P&L%·notional·entry, total P&L + cash);
  benchmark rows (SPY, HYSA) always on the board; the fleet gate + 7-day
  track-record rule before a book is labeled anything but "incubating";
  rebalances are dated events with receipts. Operator portfolios can join.

## §5 The agent workflow (Rallies agents shape, our honesty)
"Describe what to watch" → concrete watchers built from existing pipelines:
earnings-date proximity on holdings, squeeze trigger, insider cluster buy on a
held name, verdict downgrades, macro regime flips. Each watcher = a pipeline
rule that lands in the alerts channel (Telegram/Discord already wired) and the
site feed. Templates first (no free-text LLM promises); the LLM proposes new
watcher configs, deterministic code runs them.

## §6 Automation & freshness (works years from now)
- GitHub Actions: existing `daily.yml` (full rebuild incl. AI opinions if keys
  present) + `intraday.yml` every 15-30 min in market hours (news, prices,
  verdict re-scores). Free-tier honest: latency floor is the cron cadence;
  the "updated N ago" clock + freshness stamps say exactly how old data is.
- Codex in automation: local `flab-ai` job uses ChatGPT-auth `codex exec`;
  cloud uses `OPENAI_API_KEY` secret if provided, else Codex panels render
  their last committed opinion with its date (honest staleness, never silent).
- Data: existing free connectors (Yahoo charts/options, FRED, EDGAR, FINRA
  Reg-SHO, football-data) + Google News RSS links; every connector degrades
  honestly; MCPs may assist interactive sessions but the site never depends on
  an interactive-only source.

## §7 Codex MCP/CLI in the build loop
Every phase: (a) idea generation — Codex proposes features/UX against the
captures; (b) code review — `codex exec` reviews each commit's diff; (c)
fidelity check — Codex compares built pages vs `AUTHED_CAPTURES.md` structures
and files gaps; (d) its arena portfolio + per-ticker opinions. Disagreements
between Claude and Codex are surfaced on the card ("the two models disagree —
that IS information"), never averaged away.

## §8 Honesty spine (unchanged, now product-grade)
Verdicts = research opinions with receipts; every AI opinion logged and Brier-
scored on the scorecard; the miss ledger stays pinned; backtests carry costs +
OOS status; no fabricated numbers — "n/a" renders when unknowable; "not
financial advice" on every page. The legal line from CLAUDE.md §guardrails holds.

## §9 Codex round-1 review — adopted (2026-07-05, `codex exec`, gpt-5.5)
Codex's critique of this plan, folded in as requirements:
1. **INSUFFICIENT EVIDENCE is a first-class verdict** — below a data-confidence
   floor, no Buy/Trim label ships; the card says what's missing.
2. **Confidence budget, not one blended score**: every card shows four dials —
   expected-return lean · drawdown risk · data confidence · model confidence.
3. **The scoring contract comes BEFORE any UI**: inputs, weights per profile,
   missing-data behavior, horizon mapping, calibration target — spec'd and
   property-tested; every verdict reproducible from committed, audit-hashed JSON.
4. **Arena anti-theater rules**: each AI book gets a fixed written mandate,
   scheduled rebalance windows only, costs + cash yield modeled, no lookahead
   (picks dated before marks), immutable audit-hashed snapshots. Otherwise it's
   marketing, not evidence.
5. **Unique features neither reference has** (ours to own): a DECISION JOURNAL
   ("I followed / ignored this") scored later against outcomes; a REGRET AUDIT
   (every recommendation tracked vs SPY / HYSA / equal-weight / do-nothing); a
   MATERIALITY CHANGE FEED ("verdict changed because component X moved score by
   Y" — not just news); later, a tax/account lens (taxable vs IRA, wash-sale
   warnings, dividend drag).
6. **Free-data honesty**: intraday cron is best-effort (say so on the clock);
   connector health checks + cached fallbacks; news tone is noisy — headlines
   link out, tone is a minor component; 13F/politician data deferred (stale
   without paid APIs); AI opinions are versioned immutable artifacts with dates.
7. **Framing**: the product is the operator's personal decision-support
   platform; recommendation language stays (operator decision) with the
   disclaimer + "personal research tool, not advice to others" framing on every
   page. Verdict-on-holdings shows "why this changed today" diffs.

## §10 Codex round-2 review — adopted (2026-07-05)
1. **Worker hardening** (verified vs Cloudflare docs: 100k req/day free, 10ms
   CPU, 50 subrequests): symbol allowlist FROM the registry, uppercase
   canonicalization, per-IP token bucket, per-symbol cache keys,
   stale-while-revalidate, market-hours TTLs, negative caching for
   invalid/delisted, CORS locked to our origin only, no arbitrary batch
   queries. The real fragility is upstream (Yahoo/news) — health checks +
   cached fallbacks required.
2. **Landing restraint** (trust-sensitive product): particles/grain/serif
   theatrics on `landing.html` ONLY; the app stays calmer than the marketing.
   Cut: particles over data, vertical rails in-app, video loops. Keep: paper
   texture, decisive easing, real product screenshots, freshness badges.
   **Perf budgets: landing JS <50KB, hero asset <200KB, zero layout shift,
   reduced-motion default respected.**
3. **Build order reconfirmed**: scoring contract → portfolio evaluator
   ("what changed today" + ONE clear action per holding) → the
   materiality/regret ledger as the credibility engine.
4. **DECISION FRICTION DETECTOR** (new, ours): a verdict can be positive yet
   NOT actionable — tax drag, position size vs mandate, spread/liquidity (our
   V9 spread gate as a signal), earnings proximity, wash-sale window. The card
   then says "don't do this now" with the reason. Profitable operators need
   that as much as "buy". Ships with the portfolio phase (P6c).

## Build order (post-review scope: stocks/ETFs/portfolio first)
**P6a — the scoring contract** (no UI): `signals/verdict.py` — instrument
registry (stocks + core ETFs + HYSA benchmark), the four-dial confidence
budget, profile weighting (horizon/goal/risk), INSUFFICIENT EVIDENCE floor,
committed audit-hashed verdict JSON per instrument; property tests (monotone,
profile-sensitive, confidence-gated, reproducible bytes).
**P6b — the pages**: recommendation pages (Stock Taper statement shape + the
Rallies ratings scale), compare, home-as-platform (search, today's verdicts,
profile control re-weighting client-side), materiality change feed.
**P6c — portfolio + arena**: portfolio evaluation page (mandate, overlap,
regret audit vs SPY/HYSA); the AI arena — Claude + Codex books under written
mandates with immutable snapshots, marked daily, Rallies book layout, benchmark
rows always on, 7-day incubation before any label.
**P6d — journal + watchers + freshness**: decision journal, watcher templates
(earnings/squeeze/insider-cluster/verdict-change) into alerts, intraday
best-effort refresh + connector health panel.
**P6e — docs + fidelity**: CLAUDE.md remade around the platform (market trends,
stocks, ETFs, mutual funds, HYSA guidance); Codex fidelity review vs
AUTHED_CAPTURES; mutual-fund twins + tax lens as the follow-on.
