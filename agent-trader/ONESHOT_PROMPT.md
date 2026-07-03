# Agent Investing Team — the one-shot prompt

Build the agentic trading team from `agent-trader/PLAN.md` the same way we built the
lab: **one measurable `/goal` per phase**, verification hooks enforcing the floor,
the honesty guardrails baked into the goal conditions. Run the phases in order; each
has a checkable finish line. Reuse the `forecasting_lab` package as the brain/brakes.

---

## Step 1 — Hooks (once)
Same `.claude/settings.json` as the lab: a **PostToolUse** hook running `ruff +
pytest` after every `.py` edit (so a red suite blocks progress), and a
**PreToolUse** hook blocking commands that look like they carry a secret (broker
keys especially — this project touches real credentials). See the lab's
`.claude/hooks/`.

## Step 2 — Prime the session
```
Read agent-trader/PLAN.md and the forecasting_lab CLAUDE.md in full first. Reuse the
lab: predictions.Prediction (no pick without odds + evidence), promotion.evaluate_
promotion (the only path to live), eval.deflated / eval.skill, forwardtest, the edge
features, media.voices. Non-negotiable: no look-ahead/leakage, model costs, calibration
over accuracy, purged walk-forward (never random k-fold). Determinism: explicit seeds,
no wall-clock in logic. Every model/metric ships a PROPERTY test.

Hard product rules: (1) every trade decision is a logged forecast with a calibrated
probability AND its evidence; (2) hardcoded safeguards (per-trade stop-loss, daily
drawdown kill switch, exposure + fractional-Kelly caps) are agent-proof — the agents
cannot override them; (3) NEVER auto-wire a broker or place a live order — the team
decides and sizes; a human, paper-first, behind the promotion gate, executes. Bill the
Agent SDK to the Max subscription; do the heavy data lifting in cached Python, call Opus
only at the judgment step.
```

## Step 3 — Phases (one `/goal` each)

### P0 — Data brief (MCP data servers + PTC, cheap)
```
Build the data layer LangAlpha-style: expose prices/volume, fundamentals, fresh news,
options, and the lab's signals as MCP data servers with circuit-breaker fault tolerance,
and aggregate them into ONE structured, cached daily brief per candidate. Use Programmatic
Tool Calling (agent-written Python in a sandbox returns only results, not raw data) to keep
token cost near zero. Each source degrades honestly when blocked.

/goal a `daily_brief(ticker)` returns a structured, cached brief (prices, fundamentals,
news, options, lab signals) exposed via MCP tools, with a round-trip cache test and
honest-degradation tests, keeps raw data out of the model context (PTC: only results
returned), and pytest + ruff are green.
```

### P1 — The agent team (Agent SDK)
```
Implement the team on the Claude Agent SDK: Scout (news/catalysts), Analyst (thesis +
calibrated probability + evidence as a predictions.Prediction), Risk officer (veto:
sizing/stops/caps/kill-switch), Red team (adversarial bear case), Portfolio manager
(final allocation within hard limits). Deterministic orchestration on the pre-aggregated
brief; small/fast model for Scout, Opus for the debate.

The agents NEVER place a trade or decide live: the PM proposes a diff to a versioned,
deterministic strategy config (weights/signals/thresholds) for human review, and the
strategy CODE — not the model — makes the calls. Jobs talk through files/DB, not chat context.

/goal one orchestration cycle turns a brief into a PM *proposal* (a diff to the versioned
deterministic strategy) carrying a calibrated probability + evidence + the risk officer's
verdict + the red team's counter, logged as a scored forecast; a test proves the agents have
no code path that executes a trade (only the deterministic strategy does); agent judgment is
mockable so a deterministic test drives a full cycle without network; pytest + ruff are green.
```

### P2 — Execution layer + paper broker (guardrails as refusing tools + reconciliation)
```
Implement the execution layer (the chokepoint that talks to Alpaca paper) with the
safeguards as TOOLS THAT REFUSE, not prompt text: per-trade stop-loss, daily drawdown
kill switch (> X% -> halt), per-name/sector/gross caps, fractional-Kelly (<= 1/4), cash-only.
Real-money plumbing: client_order_id idempotency, reconcile-from-broker on startup (survive
a crash between submit and DB-write), handle rejected-with-fill / partial fills / qty float
dust, adjust for splits/dividends before reading returns, pin the SIP feed, hard timeouts.

/goal property tests prove: the kill switch halts trading past the drawdown limit, an
over-sized/over-exposed order is rejected by the execution layer (no agent can override it),
a retried run does NOT double-submit (idempotent), startup reconciles positions from the
broker, and a stock split does not fire day-change exit logic; paper fills apply modeled
costs; pytest + ruff are green.
```

### P3 — Parallel paper fleet + honest scoreboard + dashboard
```
Run K strategy variants in parallel paper accounts (different signal combos/thresholds/
prompts). Score the fleet honestly: returns vs SPY/VOO (all-time + rolling, drawdowns),
every decision Brier-vs-market, and — crucially — deflated Sharpe + PBO that DISCOUNT for
having tried K variants, so the luckiest-of-K is not mistaken for skill. Plus each variant's
"early & right" track record. Build a slick but honest read-only dashboard (reuse the lab's
editorial style + prediction-evidence expanders + a Firm-Chat-style activity feed).

/goal a K-variant paper fleet is scored with deflated Sharpe + PBO applied to K (a property
test proves K random variants -> no promotable winner), the dashboard shows returns vs SPY
with drawdowns, per-decision odds + evidence, and states plainly whether any variant's edge
survives the multiple-testing penalty (usually "not yet - stay on paper"); a browser
screenshot confirms it; pytest + ruff are green.
```

### P4 — Promotion gate (paper → a live-eligible version)
```
Wire promotion.evaluate_promotion as the ONLY path a strategy version becomes eligible for
real capital: all six gates must clear on real forward marks AND a human signs the version.
Autonomy note: the deterministic STRATEGY ENGINE executes trades on its own (that's the
autonomy); the LLM AGENTS never place an order — they only research and propose versions.

/goal the gate blocks a version from real-capital eligibility until all six criteria pass on
real marks and writes a signed dated record; a property test proves an under-proven version is
REJECTED and that no LLM/agent code path can place an order (only the deterministic strategy
engine can, inside the execution-layer limits); pytest + ruff are green.
```

### P5 — Autonomous run loop (unattended, paper first)
```
Build ONE idempotent scheduled job that runs the whole cycle with no human present, on Alpaca
PAPER at full autonomy: reconcile-from-broker -> refresh data (MCP/PTC) -> agents propose next
version (queued, not auto-applied) -> run the APPROVED deterministic strategy -> execution layer
vets/sizes every order -> submit with client_order_id -> poll fills -> reconcile -> mark ->
append to the ledger -> publish snapshot -> alert. Safe to kill/restart at any step. Timeouts on
every external call incl. the model. Runs for weeks on paper before any real capital.

/goal a single scheduled command runs a full unattended cycle end-to-end against Alpaca paper;
a property/integration test (mocked broker) proves it is idempotent (a re-run double-submits
nothing), self-heals after a mid-cycle crash by reconciling from the broker, and halts + alerts
when the drawdown kill switch trips; pytest + ruff are green.
```

### P6 — Live results dashboard + go-live ladder
```
Build a real-time dashboard that reads the ACTUAL account (not a simulation): live equity +
today's P&L (websocket, SIP pinned, polling fallback), positions heatmap, a fills/activity feed
with each decision's odds + evidence, return vs QQQ/SPY intraday + all-time, drawdown, Brier-vs-
market, which strategy version is live + its signed promotion record, and a blunt paper-vs-real /
$-at-risk / "edge proven? not yet" banner. Plus a human-gated capital ladder: paper -> $100 ->
$1k -> $100k, each step behind the promotion gate + explicit confirmation.

/goal the dashboard renders live real account state (equity, positions, fills, vs-benchmark,
drawdown) with a paper/real + $-at-risk banner and shows the live strategy version + its record;
the capital ladder cannot advance a step without a passing gate + explicit human confirmation
(property-tested); a browser screenshot confirms the live view; pytest + ruff are green.
```

---

## Why it works / anti-patterns
- **One measurable `/goal` per phase** — tests + a screenshot, not "make it trade well".
- **Safeguards are tested to be agent-proof** — the #1 way these projects blow up is an
  agent talking itself past its own risk limits. The goal conditions forbid it.
- **The honesty is in the goal conditions** — Brier-vs-market, "state plainly if there's an
  edge yet", reject-the-under-proven, no-autonomous-order — so "done" can't mean "cut a corner".
- **Never**: let the LLM make the live buy/sell call (it market-times backwards — the model
  proposes, deterministic code decides); put a guardrail in the prompt instead of a refusing
  tool; skip a rung on the paper→live ladder; skip broker reconciliation/idempotency; claim a
  clean backtest of news-context decisions; auto-place a live order; ship a P&L screenshot as
  proof instead of a scored, benchmarked track record.
