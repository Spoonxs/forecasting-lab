# Agent Investing Team — plan

A small team of Claude agents that research, debate, and paper-trade a portfolio —
with a **read-only advisor → paper → gated-live** ladder, hard safeguards, and an
honest scoreboard. Built on the **Claude Agent SDK** (Python), billed to a Max
subscription, cheap by design.

The differentiator, stated plainly: every "agentic trader" demo has a slick UI and
a story about beating the market. Almost none can answer *"positions or ban — is
this a real edge, or one good day?"* This one can, because it reuses the
[forecasting lab]'s honesty layer — calibration, Brier-vs-market, deflated Sharpe /
PBO, the forward study, and **the paper→live promotion gate** — as the trader's
brain and its brakes. **Not financial advice; a research and skill-building system.**

## The honest thesis (read first)
- **No one has cleanly cracked LLM alpha.** Treat this as a research instrument and
  a portfolio piece, not a money printer. Most of any "edge" is the operator's
  judgment; the system's job is to make that judgment *disciplined and scored*.
- **Slick ≠ profitable.** The deliverable that impresses is a **public, honest,
  self-scoring track record vs. SPY**, including the days it loses.
- **Live money is the operator's decision, gated and paper-first.** The team
  *decides and sizes*; it never auto-wires a broker. Real capital only after the
  promotion gate clears and a human signs off.

## The cardinal rule: the LLM proposes, deterministic code decides
The single most expensive mistake (confirmed by operators running this with real
money, and by the 2026 KDD study on LLM trading agents — they *time it backwards*,
cautious in rallies and aggressive in drawdowns): **do not let the model make the
live buy/sell call.** An LLM deciding each week gives you non-reproducible, un-
backtestable decisions and a bad market-timer.

Instead: the agents **research and propose a change to a versioned, deterministic
strategy function**; a human reviews the diff; the weekly routine then **executes
that code**, not a fresh model opinion. Claude is the researcher / orchestrator /
analyst — never the finger on the trigger. Every dollar operators keep is made by
boring code with the LLM as support crew.

## Autonomy model — genuinely hands-off, still disciplined
"Autonomous" here means **the whole loop runs unattended and executes its own trades** —
no human clicking buy each cycle. It does *not* mean the LLM free-styles orders. Think of
it as a self-driving car with a governor, not a teenager with the keys. Four autonomy
levels (a dial you turn up only as evidence accrues):

| Level | The system may… | Human still owns… |
|---|---|---|
| **L0 Advisor** | watch + log what it *would* do | every trade |
| **L1 Auto-execute** | place the **approved strategy's** trades on its own, inside hard limits | approving a new strategy *version* |
| **L2 Auto-tune** | nudge parameters within pre-registered bounds (e.g. thresholds ±10%), logged + reversible | the bounds, and any out-of-bounds change |
| **L3 (never)** | rewrite its own strategy live / lift its own limits | — this rung doesn't exist |

Day to day it runs at **L1/L2: fully autonomous execution of a versioned, backtested,
gate-cleared strategy.** The agents autonomously re-research every cycle and *propose*
the next version; a human only signs the version bump and the capital step-ups. Between
versions, nobody touches it — it trades, manages, and reports on its own.

## Architecture — cheap Python data, Opus only for judgment
Mirrors the pattern that keeps costs on a Max plan (not per-API-call):
1. **Data layer (Python + MCP, minimal LLM):** expose prices, volume, fundamentals,
   news, options, and the lab's signals (edge features, calibration, voice
   leaderboard) as **MCP data servers** with circuit-breaker fault tolerance
   (LangAlpha's shape). Reduce cost with **Programmatic Tool Calling** — the agent
   writes Python that runs in a sandbox and returns only the *result*, never the raw
   data, to the model. Aggregate into one cached **daily brief** per candidate. This
   is 95% of the work and near-0% of the token cost.
2. **Agent team (Opus via Agent SDK, invoked only when judgment is needed):**
   - **Scout** — reads the brief + fresh news, surfaces catalysts per candidate.
   - **Analyst** — forms a thesis and a **calibrated probability + evidence**
     (reuse `predictions.Prediction`: no pick without odds *and* a why).
   - **Risk officer** — veto power: position sizing (fractional Kelly ≤ ¼),
     per-name & sector caps, stop-loss placement, correlation, the drawdown kill
     switch. Can kill any trade.
   - **Red team** — adversarial: argues the bear case and why the thesis is wrong
     (the "tribunal + red-team" the smart traders in the thread asked for).
   - **Portfolio manager** — does **not** place trades. It proposes a diff to the
     versioned strategy config (weights, which signals, thresholds), with the
     debate attached, for human review. The deterministic strategy code then runs.
     Every proposal is logged as a scored forecast.
3. **Orchestration:** a deterministic Python loop / SDK workflow. Agents run once
   per cycle, on the pre-aggregated brief, so token spend is small and bounded.
   Jobs communicate through **files/DB, never conversation context** — treat each
   run like a CI job that reads fresh state, not a chat.

## Borrow the engine (LangAlpha), add the honesty it lacks
[LangAlpha](https://github.com/ginlix-ai/LangAlpha) is the best open reference for the
*research* half — steal its patterns, don't reinvent them. What it does brilliantly,
and what it conspicuously **lacks** (and we add):

| Borrow from LangAlpha (the engine) | Add from the lab (the honesty) |
|---|---|
| **Programmatic Tool Calling (PTC):** the agent writes Python run in a sandbox; only the *result* returns to the model — the real fix for token cost, better than "Python pre-aggregates" | **Leak-free backtest** (purged walk-forward) for the quant signals — LangAlpha has none |
| **MCP data servers** (prices/fundamentals/macro/options/X-sentiment) with circuit-breaker fault tolerance | **Calibration + Brier-vs-market** on every decision — "right vs the closing line," not vibes |
| **Skills library** (DCF, comps, earnings preview, catalyst calendar, morning note) — a menu of analysis workflows | **Deflated Sharpe + PBO** — overfitting honesty across all the prompts you tried |
| **Interactive workbench** (TradingView, live widgets, provenance panel per turn) | **Forward paper study** — genuine out-of-sample marks that accrue |
| **Human-in-the-loop plan mode** (approval interrupt before execution) → our gate to live | **The promotion gate** — the only path to real money; LangAlpha never trades |
| **Credential-leak detection + sandboxed exec + per-workspace vault** for API/broker keys | **Agent-proof safeguards** (stop-loss, drawdown kill switch, Kelly/exposure caps) |

Net: LangAlpha answers *"what should I look at?"* beautifully. It cannot answer
*"does this actually have an edge, and has it earned real money?"* — which is the whole
point here, and the exact question the thread kept asking ("positions or ban").

## Safeguards live in the execution layer, not the prompt
A prompt instruction is *not* a guardrail; **a tool that refuses is.** All limits are
enforced at the chokepoint — the execution/MCP layer that talks to the broker — so no
agent (or human) can talk past them:
- **Per-trade stop-loss** on every entry.
- **Daily drawdown kill switch:** account down > X% intraday → halt all trading,
  flag for human review (reuse the promotion gate's kill-switch logic).
- **Exposure caps:** max per-name weight, max gross exposure (no leverage),
  sector concentration cap.
- **Fractional-Kelly sizing** (≤ ¼), never full-Kelly.
- **Circuit breaker on the agent itself:** if its calibration or Brier-vs-market
  degrades over a rolling window, auto-demote it from live back to paper.

## The paper → live ladder (never skip a rung)
1. **Read-only advisor** — tracks the real portfolio, logs what it *would* do,
   scored against outcomes. (Months, not days.)
2. **Paper trader** — its own simulated account with real fills-modeling + costs +
   the safeguards. This is where the forward study accrues genuine out-of-sample
   marks.
3. **Gated live** — only after `promotion.evaluate_promotion` clears all six gates
   (deflated Sharpe > 1, PBO < 0.2, ≥ N real forward marks, Brier-skill-vs-market
   > 0, survives costs, risk gate) **and a human approves**. Live execution is a
   separate, operator-owned, paper-first module — the team never places an order on
   its own.

## Parallel paper fleet — but score it for multiple testing
"Run as many fake-money agents in parallel as possible" is the right instinct and the
hidden trap. Run **K strategy variants** (different signal combos, thresholds, prompts)
in parallel paper accounts, yes — but if you then crown the best of K, **you've just
multiple-tested yourself into a false positive.** The luckiest of 50 random strategies
looks brilliant.

This is exactly what the lab's honesty core is for: score the fleet with
**deflated Sharpe** (which discounts a strategy's Sharpe for *having tried K of them*)
and **PBO / CSCV** (probability the in-sample winner is overfit). The promotion gate
then only advances a variant whose edge survives the multiple-testing penalty on real
forward marks. So the fleet becomes an honest tournament, not a lucky-winner generator —
the single biggest thing separating this from every "I ran a bunch of agents and one
crushed it" post.

Also: **one job per agent.** The decision agent analyzes only — it does not fetch data
or manage positions (a separate manager handles fills/stops). Agents that "do a bunch of
stuff" is the other common failure operators report.

## Real-money operations — the scar list (from operators who've done it)
The bugs that cost real money aren't in the strategy, they're in the plumbing:
- **Idempotency:** a retried run double-submits. Every order carries a
  `client_order_id` dedup key.
- **Partial states:** the process *will* die between broker-submit and DB-write. Use
  atomic claims and **reconcile-from-broker on every startup** — the order exists even
  if your system forgot it.
- **Broker weirdness (Alpaca):** a terminal "rejected" can carry a full fill; partial
  fills happen; selling `qty` a hair above `qty_available` (float dust) rejects the
  whole exit. Handle each explicitly.
- **Corporate actions:** a 4:1 split reads as −75% on the day. Any exit logic on
  day-change fires falsely — adjust for splits/dividends before reading returns.
- **Data-feed traps:** Alpaca's default IEX feed is stale after hours (frozen prices,
  `ask=0`). Pin **SIP** explicitly.
- **LLM-specific:** `claude -p` *hangs* (doesn't error) on quota exhaustion — hard
  timeouts on everything; and never feed signals through conversation context.
- **The kill switch is a tool, not a note:** the execution layer enforces max position
  size, max daily notional, cash-only, and a hard halt — a refusing tool, per above.

## Edge-finding & honest scoring (the part everyone skips)
- **Every agent decision is a logged forecast** with a probability, scored
  **Brier-vs-market** (beat the closing line), not just "% right".
- **Returns vs SPY/VOO**, all-time and rolling, shown honestly including drawdowns.
- **Deflated Sharpe + PBO** on the paper account — discounts for the many
  strategies/prompts tried, so a lucky streak doesn't read as skill.
- **The agent gets its own track record** (like the lab's voice leaderboard):
  is *this agent* early and right, or just confident?
- **The backtesting-with-news answer** (the thread's best critique): you *can't*
  perfectly replay news-context decisions, so split it — (a) leak-free
  **purged-walk-forward backtest** for the quantitative signals, and (b) a
  **live forward paper study** for the agent's news judgment, which is genuinely
  out-of-sample and accrues over weeks. Never claim a clean backtest you can't run.
- **Test alt-data legs point-in-time and kill the dead ones.** Replay each signal
  over your own history **including delisted names** (survivorship-free), vs. random
  stocks **control-matched for volatility/liquidity on the same date**. Assume
  published alpha is ~half-decayed after publication. Known traps in this exact
  universe: **congress trades** show no risk-adjusted alpha in the *implementable*
  (45-day-lagged) version; **insider buying**'s edge concentrates in *opportunistic*
  (irregular) buyers, not routine ones. Kill a leg before it trades, not after.
- **Legal/optics:** trading your own commercial data while selling it and posting
  live updates — talk to counsel first. Boring, and much cheaper before than after.

## Cost model
Agent SDK billed to Max 20x. Python aggregates and caches everything; Opus is
called only at the judgment step, once per cycle, on a compact brief. Batch
candidates. Use a small/fast model for the Scout summary, Opus only for the
Analyst/Risk/Red-team/PM debate. Expect low, bounded usage.

## What "good" looks like (and the ceiling)
Good = a system that, after weeks of paper trading, can **honestly tell you whether
it has an edge** — and mostly it will say "not yet, stay on paper," which is the
correct, valuable answer. The win condition is the *methodology and the public
track record*, not a P&L screenshot. If it ever does clear the gate on real
out-of-sample marks, that's a genuinely rare, defensible result.

## The autonomous run loop (unattended)
One idempotent job, scheduled (cron / systemd timer / a Claude routine on a schedule),
that runs the full cycle with no human present and is safe to kill/restart at any point:

```
wake → reconcile positions FROM the broker (source of truth, not the DB)
     → refresh data via MCP (PTC: results only)
     → agents research → propose next strategy version (queued for human sign-off; NOT auto-applied)
     → run the CURRENTLY-APPROVED deterministic strategy → target weights
     → risk/execution layer vets every order (refusing tool) → size, stop-loss, caps, kill switch
     → submit to Alpaca with client_order_id (idempotent) → poll fills → reconcile
     → mark to market → append to the append-only ledger → publish live snapshot → alert
     → sleep
```

Runs on **paper first at full autonomy** (real cadence, real fills-modeling, zero blast
radius), so you watch a genuinely autonomous system trade for weeks before a cent is real.
Self-healing: a crash mid-cycle is recovered by the reconcile-from-broker step on the next
wake. Timeouts on every external call (incl. the model — `claude -p` hangs on quota). Cash
buffer enforced; if the daily-drawdown kill switch trips, it halts and pages you.

## Live results — the real account, in real time
The dashboard reads the **actual Alpaca account**, not a simulation of one, so the numbers
are the real numbers:
- **Live equity curve + today's P&L**, streamed (Alpaca trading-account websocket +
  market-data websocket, SIP feed pinned), with a polling fallback.
- **Positions heatmap** and a **fills / activity feed** ("Firm Chat" style) — every order,
  fill, stop, and kill-switch event as it happens, each carrying its odds + evidence.
- **Return vs QQQ/SPY** intraday + all-time, **drawdown**, hit rate, Brier-vs-market — the
  honest scoreboard, live.
- **Which strategy version is live**, when it was promoted, and the signed promotion record.
- **A blunt banner:** paper vs. real, dollar amount at risk, and "edge proven? not yet" until
  the gate says otherwise. Real results shown live — including the red days.

Public/shareable read-only view (the "learn in public" part) — but it shows the *scored*
track record vs the benchmark, never just a green screenshot.

## Phases
- **P0 — Data brief:** MCP data servers + Programmatic Tool Calling → one cached daily
  brief per candidate. No raw data in the model context.
- **P1 — The team (propose, don't decide):** Scout / Analyst / Risk / Red-team / PM;
  the PM proposes a diff to the versioned deterministic strategy, logged as a `Prediction`
  (odds + evidence). Agents have no trade-execution code path.
- **P2 — Execution layer + paper broker:** guardrails as refusing tools (stop-loss,
  drawdown kill switch, caps, cash-only) + real-money plumbing (idempotency,
  reconcile-from-broker, splits, SIP feed).
- **P3 — Parallel fleet + honest scoreboard:** K variants scored with deflated
  Sharpe + PBO applied to K (no luckiest-of-K promotion), returns vs SPY, Brier-vs-market.
- **P4 — Promotion gate:** the only path from paper to a live version; signed dated record.
- **P5 — Autonomous run loop:** one idempotent scheduled job that runs the whole cycle
  unattended on Alpaca **paper** at full autonomy — reconcile → data → propose → execute
  approved strategy → mark → publish → alert; self-healing; timeouts; kill switch pages you.
- **P6 — Live results dashboard + go-live ladder:** real-time dashboard reading the actual
  account (equity, positions, fills feed, vs-benchmark, drawdown), a shareable scored view,
  and the human-gated capital ladder (paper → $100 → $1k → $100k), each step behind the gate.

[forecasting lab]: the existing `forecasting_lab` package — reuse `predictions`,
`promotion`, `eval.deflated`, `eval.skill`, `forwardtest`, the edge features, and
`media.voices` as the brain and the brakes.
