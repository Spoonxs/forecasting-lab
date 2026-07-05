# Engo Arena — authed teardown (the north-star, inside)

*Signed up (email-verification flow, account `alexsb`, landed on free Pro — "no billing
wired yet, upgrade is a self-serve unlock"), walked the developer console + the
verified-tier board. Screenshots `engo-05`…`engo-12` in this folder. 2026-07-05.*

## What the login unlocked

**Developer console** (`/dashboard`): Dashboard · **Prompt your own** (NEW) · **Options
lab** · Usage · API Keys · Plans · Settings.

- **"Prompt your own"** — the standout distribution idea: **ready-made template prompts
  to paste into Claude Code / Codex** that build an autonomous bot against their REST API
  (e.g. *Momentum long-only: rank S&P 100 by 3-month return, top-10 equal weight, POST
  /api/v1/models once, PUT .../positions each morning, goal: beat SPY*; also a
  market-neutral long/short factor template). Plus tutorials and a point-and-click stock
  builder that needs no API key. They explicitly note *"sandboxed agents can't POST — run
  it where the network is open (your machine / a cron VM)."*
- **Your models table** — every user bot ranked by weekly return with full algo detail
  per row (weights · methodology · reasoning · curve · stats); **"publishing unlocks
  after 7 days of track record"** — a mini forward-test gate before a bot may appear on
  the public board. "Shared" (strategy visible/pullable via API) and "Public" (P&L on the
  leaderboard) are independent flags.
- **Options lab** — chains with Black-Scholes greeks anchored to delayed ATM IV;
  click-a-contract leg builder; Pro gets **live Schwab option marks** (incl. 0DTE +
  spreads) with a BS-theoretical fallback for same-day listings "so legs are never stuck
  flat."
- **Usage** — per-key REST call log (status · endpoint · latency); console clicks not
  logged.
- **Plans** — Pro: 200 models, real-time Schwab marks, **2× leverage**, options
  real-time. Billing not wired; Pro is currently a free self-serve unlock.

**Verified-tier board**: the full leaderboard opens up — house **"Fine-tuned quant live
agent" runs REAL money** (`● LIVE TRADING MODEL — REAL MONEY`, +3.05%, +2.07% vs SPY, 27
days) with **holdings sealed but P&L public**, and the fine print: *"time-weighted
(deposit-adjusted) — external funding is never counted as performance."* Below it: a
**Top-3 blended** book of the best public models, wildcards (insider cluster-buy, biotech
event overlay — the top-2 sealed as promised), community bots (`engo_autopilot`,
forked user bots), PAPER-SHADOW-tagged models marked at $100k flat, and even an
**"analog bench · Claude-4.8"** baseline model.

## Why this matters for the lab (new honesty mechanics to note)

1. **7-day track-record gate before publishing** — even community bots must forward-test
   before the leaderboard sees them. Cheap, elegant, matches our promotion-gate ethos at
   the social layer.
2. **Deposit-adjusted time-weighted returns** on the live book — funding ≠ performance.
   A subtle honesty trap most trackers fail.
3. **Sealed-holdings/public-P&L split** — verifiable results without giving away the
   book. (And "Shared vs Public" as independent flags.)
4. **Claude-Code-prompt-as-onboarding** — they distribute strategy *templates as agent
   prompts*, making the agent ecosystem their user acquisition. If our lab ever exposes
   an API, this is the pattern.
5. Confirmed end-to-end: paper-first, blended-book real capital "earned through a gate,
   never assumed" — the product proves the whole thesis is shippable.

*Reference only. Account is the user's; nothing was published or traded. Not financial
advice.*
