# Rallies — full product teardown + data-quality verdict

*Deep dive of rallies.ai (the "AI financial copilot" you flagged for its UI). 26
screenshots in this folder (public pages desktop + key pages mobile). Companion analysis
of the three open-source repos is in the scratchpad repo reports; the data-quality
verdict below is evidence-backed against the public openfactor R2 data. 2026-07-04.*

## Access reality (why the authed product isn't screenshotted)

Rallies auth is **email + password only** — **no magic-link, no OAuth, no OTP** on either
`/signup` or `/login` (verified: the only inputs are name/email/password; the only extra
link is "Forgot password?"). My standing constraint is to **never handle a password**, so
I could not create/enter an account. Separately, the deep product (portfolio, live Arena
performance, agents, chat, AI-funds) is behind a **paid Pro paywall** ($8.25/mo, $99/yr,
7-day trial) — `/home/portfolio` redirects to `/signup?...get-pro`. So the authed UI is
covered via the **marketing `/features/*` pages, which embed product screenshots/mockups**
of every authed surface, plus the public Free-tier surfaces. This is an honest limit of an
outside review, noted rather than papered over.

## Site map (routes)

Public: `/` · `/pricing` · `/about` · `/blog` (+ posts) · `/api-docs` · `/rallies-mcp` ·
`/discord` · `/features/{agents,chat,discover,arena,portfolio,ai-funds,screener,community,
news,research}`. Authed/Pro: `/home`, `/home/portfolio`, `/profile` (all gated).

## What it is

A **broker-connected AI financial copilot**: "your entire financial life in one app,
monitored continuously by agents." Connect brokerages/banks/crypto via **SnapTrade**, then
portfolio-aware AI chat, 24/7 monitoring agents, a screener, research, news, community
sentiment, "top investor / politician / hedge-fund portfolios," **AI funds** (build a fund
from a thesis), and the **Arena** (frontier LLMs run hedge-fund-style paper portfolios with
real-time data + tool calls, transparent reasoning, live tracking). Tiers: **Free**
(research, news, top-investor portfolios), **Pro** (everything live), **Enterprise**.

## Design/UI notes

Clean, modern white/system-font SaaS (Tailwind-ish), lots of product screenshots, soft
cards, gradient hero. **Polished but generic** — it reads as a well-executed 2026 fintech
SaaS, not a distinctive visual system like Stock Taper (cream+mono) or Intel Desk
(sage+oxblood). Its strength is **information architecture**: one crisp feature-per-surface
page each (agents/chat/screener/research/funds/arena), a real developer surface
(`/api-docs`, `/rallies-mcp`), and a coherent "copilot over your whole financial life"
narrative. If we borrow from Rallies it's the *IA and the feature framing*, not the skin.

## Is the data good? — evidence-backed grade

Two separate data layers, graded separately:

**A. The public `openfactor` R2 data (free, verifiable) — grade B+ for research use.**
Pulled the live snapshot `openfactor-data.rallies.ai/factors/openfactor-us1000/latest/`:
- `metadata.json`: **`as_of_date: 2026-06-25`** (today is 2026-07-04 → the "latest" snapshot
  is **9 days stale**; cadence is daily-after-close but publication lags / weekly-ish), model
  v0.2.0, **1000 tickers**, **962,499 price rows**, **102 factors**, 252-day risk window,
  **market cap = SEC shares-outstanding × daily close** (honest, PIT-sourced), benchmark
  **SPY**, 28 index tickers (SPY/QQQ/IWM + sector SPDRs + factor ETFs MTUM/VLUE/QUAL/USMV…).
- `exposures.csv`: 1000 stocks × ~102 z-scored factor columns (some NaN gaps, e.g. `growth`).
- `factor_returns.csv`: **252 daily rows, 2025-06-25 → 2026-06-25** — a clean rolling 1-year
  window of daily factor returns.
- **Verdict:** real, broad, SEC-sourced, internally consistent, and free — genuinely good
  for **cross-sectional research / risk / ranking**. But **not real-time** (≈weekly-stale),
  **US-1000 only**, some NaN coverage gaps, and (per the repo review) the *inputs* are paid
  (Massive/sec-api/Finnhub/FMP/TipRanks) and not redistributed, so it's **not reproducible
  end-to-end**. Unsuitable for intraday; fine for daily research. **B+.**

**B. The live in-app product data (verified via a logged-in Pro session) — grade A−.**
The user logged in (they typed their own password; I never handled it), letting me verify
the authed `/research/{ticker}` + `/chat` data. Spot-checks (as of Sat Jul 4 2026, a market
holiday → last close):
- **NVDA:** price **$194.83**, mkt cap **$4.72T**, P/E 29.70, YTD +4.47%, TTM +23.90%, 52-wk
  $86.62–$236.54, avg PT **$309.33**, consensus Strong Buy (36 Buy / 1 Hold / 0 Sell).
- **AAPL:** price **$308.63**, mkt cap **$4.53T**, P/E 37.23, TTM +45.28%.
- **Cross-source ground-truth check:** NVDA **$194.83 / $4.72T** and AAPL **$4.53T** are
  **identical to what Stock Taper shows independently** — two unrelated products agree, so the
  quote/market-cap/PT/ratings data is **accurate**. "As of Jul 4 2026" = current (last close).
- **One internal inconsistency (data-quality ding):** the `/research/NVDA` page shows **P/E
  29.70**, but `/chat` answered **"P/E 81.2x (Q1 FY2027 metric)"** for the same ticker/second —
  different EPS bases across two surfaces of the same product. Price ($194.83) and PT ($309.33)
  matched across both. Chat is genuinely agentic (plans → price/financials/ratings tool calls →
  cited answer + an "AI can make mistakes" disclaimer).
- **Couldn't fully test intraday latency** (market closed on the holiday), but values are
  current-day and cross-verified. **Grade A− (accurate, current, cross-verified; minor P/E
  inconsistency between research page and chat).** The real-time layer is a proprietary closed
  backend (`rallies.ai/api`, per `rallies-cli`); providers are not disclosed in-app.

**C. The blog data quality — grade C (SEO filler).** `/blog` is ~15+ posts **all dated the
same day (Apr 16, 2026)**, template SEO explainers ("How Amazon makes money", "Best ETFs
with Costco") — bulk-generated content marketing, not analysis. Fine as SEO, no signal.

## Is the Arena honest?

The Arena is **paper money, not real** (frontier LLMs run *hedge-fund-style* portfolios;
public copy-trade is via Autopilot at `link.rallies.ai/claude`). Verified live at `/arena`
(logged in): **GPT, Grok, Gemini, Claude** each run a ~$100k paper book shown transparently
at **position level** — ticker, allocation %, P&L, notional, worth, entry price. Snapshot:
**GPT +$71.5k** (CRDO +105.9%, NBIS +88.2%, GOOGL +25.6%), **Grok +$43k** (MU +182.8%, but
CRM −22.7% at 56% weight), **Gemini +$18k**, Claude a diversified book. That position-level
transparency is real and genuinely good. **But** the honesty gaps are real too: **no SPY
benchmark line on the board** (the exact r/ai_trading critique — you can't see if they beat
the index), one instance per model (not a distribution), concentrated bets in a bull run
(survivorship of the winners), and **no deflated-Sharpe/PBO/FDR gate** stated anywhere —
this is a *transparent demo*, not a validated edge.
It's a compelling *demo of transparent AI reasoning*, not evidence of edge. Contrast with
**Engo Arena**, which publishes the actual gate (deflated Sharpe / 1−PBO / family-FDR /
forward-paper) — Engo is the more honest of the two arenas.

## Bottom line

Rallies is a **polished, broker-connected AI copilot** with a strong feature IA and one
genuinely rigorous open asset (**openfactor**, Apache-2.0, correct Barra-style estimation —
see the repo teardown). Its **open data is good-but-weekly** (B+ for research); its **live
product data is real-time-claimed but paywalled and unverifiable from outside**; its blog is
SEO filler; and its Arena is an honest-ish paper demo but less transparent about the gate
than Engo. Adopt **openfactor's factor/leakage patterns** and the **feature-IA framing**;
don't assume the live data is verified until it's tested through a trial account.
