# LangAlpha vs. this lab — a code-grounded comparison

*What actually works in the LangAlpha open-source repo, feature by feature, against
the current `forecasting_lab` + `agent_trader` state. Every claim below was verified
by reading the source at `LangAlpha-main/` (not the README), 2026-07-03.*

LangAlpha's own README calls it **"a vibe investing agent harness."** That's an
honest label. It is a *superb agentic research workbench* and a *poor forecasting
system* — because it was never built to be one. This lab is the inverse. They sit on
opposite sides of the same problem and barely overlap.

---

## 1. What LangAlpha actually is

A LangGraph agent (`deepagents` / `create_agent`, **not** a hand-written StateGraph)
wrapped in a ~25-layer middleware stack, whose defining trick is **PTC — Programmatic
Tool Calling**: the LLM doesn't call data tools directly, it *writes Python* that runs
in a Daytona/Docker sandbox, imports generated MCP wrapper modules, processes the data
locally, and returns only the result. Around that: parallel background subagents
(general-purpose / research / data-prep / equity-analyst / report-builder), persistent
per-goal workspaces (1 workspace = 1 sandbox + an `agent.md` notes file that compounds
across threads), a Postgres+Redis production backend with SSE streaming, and a React 19
research workbench with live charts, subagent telemetry, plan-approval cards, and
per-turn source provenance.

Scale: 952 Python files, 615 TS/TSX, 32 skills, ~10 MCP data servers. This is a
serious, well-engineered product.

## 2. What genuinely works there — and is worth stealing

These are real, and this lab does **not** have them:

1. **PTC / code-execution data layer.** Instead of dumping 10,000 rows of OHLCV into
   the context window, the agent writes pandas that runs next to the data and returns a
   number. This is the correct token architecture for an LLM over financial data, and
   it's the single most adoptable idea. *We* currently hand the LLM (in the agent-team
   layer) pre-summarized briefs — fine for now, but PTC is how you scale to "analyze 5
   years of every S&P name" without drowning.

2. **Persistent per-goal workspaces that compound.** The "vibe investing" thesis —
   research is Bayesian and unfolds over weeks, so give the agent a filesystem that
   survives — is genuinely good and cleanly executed (`agent.md` injected into every
   model call; a store-backed long-term memory tier; a user memo store for uploaded
   PDFs). Our `forwardtest/` + `AgentLedger` accrete *marks* over runs; LangAlpha
   accretes *reasoning and artifacts*. Both are "compound over time," different axes.

3. **The agent-output UX.** SSE streaming with Redis-buffered reconnect replay, live
   subagent telemetry, plan-approval interrupts (HITL), agent-drawn annotations pinned
   onto a live TradingView chart, a per-turn sources/provenance panel. This is a
   genuine agentic workbench, well beyond a chat box — and it's exactly the "feel like
   a real agentic desk" quality the Agent Terminal was reaching for, done at production
   depth.

4. **~10 competent IB-standard analytical skills** — `dcf-model`, `comps-analysis`,
   `3-statements`, `earnings-analysis`/`-preview`, `initiating-coverage`,
   `sector-overview`, `competitive-analysis`, `idea-generation`, `thesis-tracker`.
   (Caveat: most carry *"Derived from anthropics/financial-services-plugins"* — they're
   adapted from Anthropic's public FS plugins, not original, and they're prompt
   templates, not validated models.)

5. **Middleware-as-architecture + model resilience.** Retry → fallback-model chain,
   prompt caching, auto-compaction at 120k tokens, leak detection, protected paths,
   BYOK via OAuth. Production-grade agent plumbing.

## 3. What LangAlpha does NOT have — the entire reason this lab exists

I grepped the whole repo hard (`brier`, `log.loss`, `reliability`, `walk.forward`,
`purged`, `embargo`, `deflated`, `PBO`, `sharpe`, `backtest`, `kelly`,
`promotion.gate`, `paper.trade`, `broker`, `place.order`, `survivorship`,
`point.in.time`, `look.ahead`, `leakage`, `delist`). **Every single hit is a false
positive.** Specifically:

- **No calibration scoring.** No Brier, no log-loss, no reliability diagram, no ECE, no
  Murphy decomposition. The README's *"calibrated to your book"* is marketing — the
  only `calibrate` in the codebase is `scripts/ops/calibrate_model_ratings.py`, which
  calibrates *LLM speed/intelligence star-ratings* from the Artificial Analysis API.
  Nothing scores a forecast.
- **No backtesting.** `backtest` appears only as prose in skill templates and one MCP
  docstring ("adjust prices for splits in backtesting"). There is no engine, no
  walk-forward, no purged/embargoed CV, no honest baseline.
- **No cost model.** No fee/slippage/turnover accounting anywhere.
- **No promotion / go-live gate.** No deflated Sharpe, no PBO/CSCV, no
  multiple-testing correction. "Kill-switch" in config is a Redis event-spill toggle.
- **No execution — paper or live.** Every finance tool is strictly **read-only data**.
  There is no order tool, no broker, no paper book, no position sizing. `max_position_pct:
  0.15` is a *user-declared preference in a JSON profile the agent reads*, not an
  enforced risk limit.
- **No data discipline.** Zero point-in-time / as-of feature construction, zero
  survivorship-bias handling (live yfinance/FMP endpoints → delisted names simply
  gone), zero lag/leakage guard. The only "as-of" is a cosmetic *"As of HH:MM ET"*
  timestamp on a display widget.
- **No outcome-scored track record.** `thesis-tracker` is a *self-graded qualitative
  conviction scorecard* — the agent grades its own thesis; nothing checks it against
  what actually happened.

In one line: **LangAlpha shows you what the agent *thinks*. It never shows you whether
the agent has been *right*.**

## 4. Feature-by-feature

| Capability | LangAlpha | This lab (`forecasting_lab` + `agent_trader`) |
|---|---|---|
| Agent harness / sandbox PTC | ✅ production-grade | ⚠️ lighter — injected briefs, no code-exec sandbox |
| Parallel subagents / swarm | ✅ background orchestrator | ⚠️ `agent_trader/team.py` roles, injected judge (no live swarm) |
| Persistent workspaces / memory | ✅ sandbox + `agent.md` + memory store | ⚠️ ledger + forward marks (data, not reasoning) |
| Streaming agentic UI | ✅ SSE, telemetry, provenance | ⚠️ static single-file dashboard + dark Agent Terminal |
| Breadth of live data | ✅ ~5 providers via code-exec | ✅ 724 tracked sources, honest degradation |
| **Calibration (Brier/ECE/reliability)** | ❌ none | ✅ `eval/` — the credibility core |
| **Leakage-controlled backtest (purged WF CV)** | ❌ none | ✅ `ml.PurgedWalkForwardCV`, `backtest/` |
| **Cost model (Kalshi/Polymarket fees)** | ❌ none | ✅ `backtest.costs` |
| **Overfitting honesty (deflated Sharpe, PBO)** | ❌ none | ✅ `eval/deflated`, fleet multiple-testing |
| **Point-in-time / survivorship discipline** | ❌ none | ✅ as-of features, `lag_features`, guardrails |
| **Outcome-scored track record** | ❌ self-graded only | ✅ `calibration_log/` (beat-the-close), `media/voices` |
| **Paper execution + risk gate** | ❌ read-only data only | ✅ `agent_trader/execution.py`, idempotent PaperBroker |
| **Promotion gate (paper→live decision)** | ❌ none | ✅ `promotion.py` / `agent_trader/gate.py`, 6 OOS gates |
| Prediction-evidence contract | ❌ free-text reports | ✅ `predictions.py` — can't construct without prob + driver |

## 5. The synthesis

**They are complementary, not competitive.** LangAlpha is the *analyst's hands* — it
fetches anything, writes code over it, and produces a beautiful report. This lab is the
*scorekeeper and the risk gate* — it measures whether a forecast was calibrated, whether
an edge survives costs and multiple-testing, and whether a strategy has earned the right
to touch real capital. LangAlpha would let a plausible-but-wrong thesis sail straight
through; that's the exact failure the CLAUDE.md Elo-loser-bug story is about.

**What to adopt (ranked):**
1. **PTC code-execution data layer** — the highest-leverage borrow. Let the agent write
   sandboxed Python over the 724 sources instead of only receiving briefs. Keep the
   cardinal rule intact: *LLM proposes code, deterministic layer decides trades.*
2. **Persistent reasoning workspace (`agent.md`)** — pair it with our marks ledger so
   the agent compounds *both* its reasoning and its scored record.
3. **Streaming UX depth** — subagent telemetry + plan-approval cards + provenance panel
   are what would make the Agent Terminal feel truly live rather than a rendered
   snapshot.

**What you uniquely have (and should lead with):** every row LangAlpha has an ❌ in.
The calibration core, the leakage-controlled backtest, the cost model, the deflated-
Sharpe/PBO overfitting honesty, the point-in-time discipline, the outcome-scored track
record, the paper-execution risk layer, and the promotion gate. That stack *is* the
moat CLAUDE.md claims — "the methodology is the moat, not the data volume." LangAlpha,
with 20× the code and a hosted data backend, has none of it.

**Bottom line:** borrow LangAlpha's *hands* (PTC, workspaces, streaming UX); keep this
lab's *conscience* (scoring, gate, discipline). The winning system is LangAlpha's
research harness feeding proposals *into* this lab's evaluation-and-gate pipeline —
never the other way around.

*Not financial advice. A research and skill-building comparison.*
