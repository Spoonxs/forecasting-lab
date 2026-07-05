# Round-2 source review — what's good, what's hype, what to steal

*Deep pass over the second batch of sources (repos cloned + read, live UIs captured, the
academic paper + Reddit/Medium threads scraped via Firecrawl). Goal: separate genuine
signal from hype and extract concrete improvements for the lab. 2026-07-04. Companion to
`CONSOLIDATED_RESEARCH_PLAN.md` and the `LANGALPHA_ANALYSIS.md`.*

The headline: **two sources are genuinely excellent and change the roadmap** — `openfactor`
(a real leakage-aware factor model) and **Engo Arena** (the honest-methodology arena the
lab has been describing, shipped as a product). Most of the rest are polished harnesses or
demos with no out-of-sample validation — useful plumbing, not evidence of edge.

---

## 1. Verdict table (good vs hype)

| Source | What it is | Verdict |
|---|---|---|
| **Engo Arena** (engo.capital) | Public AI-strategy arena vs SPY | ⭐⭐ **Best in class.** Uses the lab's *exact* rigor: Deflated Sharpe, **1−PBO**, **family-FDR ≤5%**, forward-paper, survivor-universe, "0 survive → 100% SPY", paper→live "Blended book". Productized `eval/deflated`+`promotion.py`. |
| **openfactor** (ralliesai) | Barra-style US factor risk model | ⭐⭐ **Genuinely good.** Cross-sectional WLS w/ zero-sum constraints, ~25 winsorized style factors, structural no-look-ahead (`as_of_price_matrix`), **semantic residual discovery gated on OOS variance reduction**. Free runtime via public R2. No calibration/backtest/gate (complements us). |
| **Larcker–Zakolyukina 2012** (paper) | Earnings-call deception detection | ⭐⭐ **The rigorous anchor.** Restatement-labeled ground truth, OOS-only, modest **6–16% above-chance classification accuracy** (not a return edge), specific linguistic markers. A legit new `signals/` feature template. |
| **Satellite parking-lot** (r/ClaudeCode) | Free-Sentinel replication of a $100k/yr fund signal | ⭐ **Genuinely honest.** SAR 3/3 at 30 stores → **5/10 (coin flip) at 100** — author calls it noise; "the moat is data resolution, not the algorithm." A clean external echo of our core guardrail. |
| **Velora** (Kingler16) | AI wealth advisor (claudefolio successor) | ⭐ **Best-engineered honest one.** Tracked expectancy, **refuses to compute fake alpha**, surfaces survivorship bias, machine-checkable **"Mandate"** guardrail validator. No Brier/CV. |
| **Scanner "lying by omission"** (temple-stuart) | 20-step options pipeline + cautionary tale | ◐ **Insight > product.** The coding agent silently added caches/fallbacks that broke as-of freshness → a **data-freshness audit layer**. Pipeline itself unvalidated (n=3 trades). |
| **Buffett 48 letters** (r/ClaudeAI) | Extract Buffett rubric, pick blind | ◐ **Neat demo, mostly hype.** Training-data contamination + look-ahead; **subagent isolation (extract vs score)** is the keeper; honest "position sizing > selection". |
| **openprophet / Claude_Prophet** (Jake Nesler) | Claude-Code options trader, $100k paper | ◐ **Great harness, no epistemics.** Phased heartbeat, SSE webui, **fail-closed permission gate**, bracket exits, vector setup memory. But LLM-as-sole-decider, guardrails-as-prompt-text, **backtesting removed by design**, −22.4% drawdown, agent can edit own risk caps. |
| **get-rich-slow** (brentrager) | Kalshi sports live-lag scalper | ◐ **Solid plumbing, thin edge.** Real-time WS + settlement handling; **"what-if" shadow parallel-strategy** tracking is a nice lightweight forward-study analog. No cost/calibration. |
| **Sonnet vs Opus deception** (r/ClaudeAI) | LLM replication of the paper | ◐ **Intriguing, unproven.** "Smaller model wins" is testable but n≈6/group, no stats, leakage likely. |
| **Rallies** (rallies.ai) | AI financial copilot + arena | ◐ **Polished product, high-quality UI.** `openfactor` is the real substance; `rallies-cli`/`tenk` are LLM scaffolding. Broker-connected via SnapTrade. |
| **Claude Prophet Medium** | The $100k writeup | ◐ **Self-aware hype.** +7.6% in one leveraged options month = noise; author says so repeatedly. |
| **Stock Taper premium** (r/vibecoding, mislabeled "freetradejournal") | Retail research product | ◐ Already our design reference; readability layer, no edge. |
| **20-step pipeline demo** (VibeCodersNest) | Same repo, promo | ✗ Low-signal duplicate of the scanner post. |
| **margincall.io / freetradejournal / Autopilot** | Game sim / trade journal / copy-trade | ✗ Product/UX references only, no forecasting rigor. |

---

## 2. New ideas & improvements to adopt (ranked by leverage)

1. **Adopt `openfactor` as a leakage-aware factor/residual layer for `ml/`.** Its
   cross-sectional exposure construction (winsorize→z-score around cap-weighted median),
   `as_of_price_matrix` prior-close slicing, and factor covariance/idiosyncratic risk give
   us a proper risk model *and* clean residual returns to rank on — exactly what our GBM
   ranker should train on. Runtime is free (public R2 CSVs). **Its semantic-residual gate
   (accept a new factor only if it reduces OOS idiosyncratic variance) is a model for how
   we should admit any new edge feature.** Apache-ish open; verify licence before vendoring.

2. **Make Engo Arena the north-star for our arena + gate, and close two gaps we don't have
   yet:** (a) **family-wise FDR / false-discovery-rate control across the strategy fleet**
   (we have PBO/deflated-Sharpe per strategy; add multiple-testing correction *across* the
   fleet so "26 candidates, 0 survive" is possible); (b) the **honest default: when nothing
   survives the gate, hold the benchmark (100% SPY)** rather than force a pick. Both drop
   into `fleet.py` + `promotion.py`. Also mirror their **paper→live "Blended book" ladder**
   (only survivors earn real capital) — we already have the ladder in `agent_trader/ladder.py`.

3. **Add a `signals/deception` earnings-call feature (the genuinely novel edge).** Follow
   Larcker–Zakolyukina *exactly*: label calls from **subsequent restatements** (objective,
   as-of-knowable), extract linguistic markers (extreme vs non-extreme positive emotion,
   anxiety words, references-to-shareholder-value, general-knowledge hedges), score **OOS
   under purged CV**, beat the financial-variable baseline, report Brier. The paper shows
   6–16% above-chance OOS classification accuracy with academic grounding (a return edge
   must still be proven) — the first genuinely new signal in the whole review.
   Use the Reddit "Sonnet vs Opus" result only as a hypothesis to test, never as evidence.

4. **Add a data-freshness audit layer to `pipeline/` (defends against agent-introduced
   leakage).** Every datum carries a fetch timestamp + age; every pipeline step can surface
   raw output before use; a check fails loudly if data is staler than its as-of budget.
   This guards against the exact failure the scanner post hit — an LLM coding agent silently
   inserting caches/fallbacks that break point-in-time correctness. Pairs with our leakage
   guardrail #2.

5. **Adopt Velora's two disciplines:** (a) a **machine-checkable "Mandate" validator** —
   structured hard rules (max-position%, min-cash%, sector caps, forbidden tickers) that
   validate *every* agent proposal before it reaches the execution layer (guardrail-as-tool,
   fits `agent_trader/execution.py`); (b) **"refuse to compute a metric you can't compute
   point-in-time"** — e.g. don't report alpha if the entry-date benchmark level wasn't
   stored. Bake into `predictions.py` / `eval`.

6. **Use the subagent-isolation anti-leakage pattern for any LLM scoring** (`media/voices`,
   `research_log`): score anonymized inputs in an isolated context so the model can't map
   financials→identity. Cheap, and it blunts training-data contamination.

7. **Borrow harness plumbing from openprophet** (not its epistemics): the phased-heartbeat
   loop, SSE live desk, **fail-closed permission gate**, deterministic bracket exits, and
   vector "setup memory" — for `agent_trader`'s execution/monitoring layer, always with our
   deterministic decider between proposal and order.

8. **Add `get-rich-slow`'s "what-if shadow strategies"** to `forwardtest/`: track N
   parameter variants against the *same* real forward marks — a cheap live sensitivity
   check that complements the purged backtest.

---

## 3. UI / design notes (captured under `design-reference/`)

- **Rallies** (`design-reference/rallies/`, 13 shots) — the high-quality UI you flagged.
  Clean white/system-font SaaS: feature pages (Arena, Agents, Portfolio, AI-Funds,
  Research, Screener, Chat, Discover), a real **MCP + API-docs** surface, SnapTrade broker
  linking. Design is polished-generic-modern (not distinctive like Stock Taper), but the
  **information architecture** — "your whole financial life, monitored by agents" with a
  feature-per-surface layout — is a strong model for how to present our agent surfaces.
- **Engo Arena** (`design-reference/other-uis/engo-*`, 4 shots) — the substance-rich one.
  Live leaderboard vs SPY, per-strategy equity curves, a Studio "build-a-bot-by-clicking",
  and methodology stated in the open (Deflated Sharpe / 1−PBO / family-FDR / forward-paper).
  This is the closest existing product to *our* thesis — study its board + research pages.
- **margincall.io / freetradejournal / Autopilot** (`design-reference/other-uis/`) — a
  game-sim, a trade journal (login-gated), and a copy-trade landing. Reference only.

---

## 4. Bottom line

The review sharpens the moat rather than threatening it. **openfactor** gives us a free,
rigorous factor/residual layer to plug in; **Engo Arena** proves the exact
deflated-Sharpe/PBO/FDR/forward-paper stack we're building is a credible product and shows
the two additions we're missing (fleet-level FDR + "hold benchmark when nothing survives");
the **deception paper** hands us the first genuinely new, academically-grounded signal; and
the honest failure stories (satellite, scanner, Prophet's drawdown) are field confirmations
of guardrails we already hold. Everything else is plumbing to borrow or hype to note.

*Not financial advice. A research and skill-building synthesis.*
