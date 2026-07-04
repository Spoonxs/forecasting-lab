# Master context prompt — everything researched so far (session handoff)

*Written 2026-07-04 at the end of a long Opus 4.8 research session, so any fresh session
(now on Fable 5) can pick up with full context without re-deriving anything. Section A is
the paste-ready prompt; Section B is the full artifact index behind it.*

---

## Section A — paste-ready prompt (copy everything in the block)

You are continuing work on bundle-forecasting-lab (github.com/Spoonxs/forecasting-lab, branch master) — a calibration-first quant forecasting platform plus a companion honest agent-trader. Read CLAUDE.md first: the six non-negotiable guardrails (purged walk-forward CV only, no look-ahead/leakage, model costs, calibration-over-accuracy with Brier + reliability, survivorship-bias-free data, the legal line) and the cardinal rule "LLM proposes, deterministic code decides; paper until the promotion gate clears + human confirms" govern everything. The agent-trader (src/forecasting_lab/agent_trader/, phases P0-P6 built and tested) has a live paper Agent Desk + dark Agent Terminal on the dashboard.

A large research program is already DONE and written into the repo — do not redo it, read it:

RESEARCH DOCS (agent-trader/): CONSOLIDATED_RESEARCH_PLAN.md = 16 Reddit builder threads distilled (9 recurring anti-patterns confirming our guardrails + 16 honest primitives mapped to modules + 5-phase plan A-E, Phase A1 = the Sarithis ~30-bug leakage/cost test taxonomy). LANGALPHA_ANALYSIS.md = teardown of the LangAlpha "vibe investing agent harness" (952 py files — superb agentic research workbench, PTC code-execution data layer, persistent workspaces, but ZERO calibration/backtest/gate; borrow the hands, keep our conscience). SOURCES_ROUND2_ASSESSMENT.md + DEEP_DIVE_FINDINGS.md + DEEP_DIVE_REPOS.md + DEEP_DIVE_FORUMS.md = round-2 deep dive: 9 repos line-level, 10 forum threads comment-level, Rallies product walked logged-in. ROUND2_GOAL_PROMPT.md and DEEP_DIVE_GOAL_PROMPT.md = ready-to-fire /goal strings for the next build/research phases. PLAN.md + ONESHOT_PROMPT.md = the original agent-trader plan.

KEY VERDICTS (already evidence-backed, trust them): (1) Engo Arena (engo.capital) is the north star — it productizes our exact stack (deflated Sharpe, 1-PBO, family-FDR ≤5% across candidates, forward-paper, "0 survive → hold 100% SPY", paper→live Blended-book ladder); we still lack fleet-level FDR and the hold-benchmark default. (2) ralliesai/openfactor is the one genuinely rigorous open asset: correct Barra √cap-WLS with zero-sum KKT constraints, MAD winsorization, structural as-of no-look-ahead, Apache-2.0, free weekly R2 snapshots (1000 US names, 102 factors) — BUT its semantic factor-accept gate is in-sample (after_var<before_var on the same 63d fit window = curve-fit trap) and it ships zero tests; adopt the estimation + as-of patterns, re-gate any factor with our PurgedWalkForwardCV. (3) Kingler16/Velora is the most honest repo: machine-checked mandate.py validator (pass/warn/block on every recommendation), refuses to compute fake alpha, surfaces survivorship — adopt both patterns into agent_trader/execution.py and eval/predictions. (4) btopn/OpenInsider-MCP: 16 free EDGAR/FINRA/RegSHO tools with literature-cited, freshness-caveated descriptions — feed sources/finra+sec and signals/squeeze. (5) jakenesler/openprophet: great harness plumbing (fail-closed ORDER_TOOLS gate, Go bracket/trailing exits, phased heartbeat) but LLM-as-sole-decider with risk caps that exist only as prompt text and backtesting removed by design — borrow plumbing, avoid epistemics; CC BY-NC. (6) Larcker-Zakolyukina 2012 earnings-call deception detection (restatement-labeled, OOS, 6-16% real edge) is the one genuinely new signal worth building (signals/deception). (7) The single unrefuted objection across every LLM-trading experiment is training-data look-ahead — you cannot backtest an LLM on memorized dates; forwardtest/ genuine-OOS is the only honest path. (8) Rallies live data verified logged-in: grade A- (NVDA $194.83/$4.72T and AAPL $4.53T cross-match Stock Taper exactly; one P/E inconsistency 29.70 vs 81.2x between research page and chat); its Arena is transparent paper money but shows no SPY benchmark and no gate.

DESIGN REFERENCES (design-reference/, screenshots/videos local-only and gitignored; the .md docs are committed): stocktaper/ = the design to model the research dashboard on (60 shots + assets + promo video; DESIGNS.md = warm cream #FBF7EB paper, IBM Plex Mono everywhere, muted green #2F7D31 / brick red #C6392C, heavy uppercase headings + eyebrow tags, white cards, per-feature mascot set; FEATURES.md + gallery/). inteldesk/ = the proof-mechanics reference (35 shots; sage-grey #E2E6E1 ops console, oxblood #7A1020 alert, olive #3D6B2E confirm; public Brier-scored thesis scorecard with honest denominator, A/B/C/D source tiers, claim-tape receipts drawer with contradictions kept on screen, ACT/VERIFY/PRICE/FADE buckets, paper-only markets). rallies/ = 26 public + 14 authed shots + 42s walkthrough video + RALLIES_TEARDOWN.md + AUTHED_FEATURE_MAP.md (polished SaaS IA: Today/Agents/Chat/Arena/Discover/Research-with-6-subtabs). other-uis/ = Engo Arena board, margincall, freetradejournal. CLAUDE.md's dashboard section already encodes this direction: Stock Taper skin for the research dashboard, Intel Desk proof mechanics for the agent/forecast surfaces.

THE AGREED NEXT BUILDS (in priority order, each as its own PR with a property test, pytest + ruff before done): (1) fire agent-trader/ROUND2_GOAL_PROMPT.md — signals/deception (restatement-labeled, purged-CV, Brier), fleet-level FDR + hold-benchmark-when-nothing-survives in fleet.py/promotion.py, openfactor as a leakage-aware factor/residual feature layer re-gated by our CV, pipeline data-freshness audit layer, Velora-style Mandate validator + refuse-uncomputable-metrics, subagent-isolation for LLM scoring. (2) The dashboard visual pass: reskin the research dashboard to the Stock Taper system (cream + Plex Mono + mascots + "what's going well/concerning" cards) and give agent picks Intel-Desk-style trust badges + a claim-tape receipts drawer + a public Brier scorecard page — keep every honest-substance element (calibration, why-expanders, not-financial-advice). Tooling notes: Firecrawl CLI is installed (key in scratchpad fc.env — never print it); Reddit is blocked directly, scrape via Redlib mirrors (redlib.nadeko.net / r4fo / catsarch), retry on Anubis pages; cloned reference repos live in the scratchpad repos/ dir; the user prefers full-scope autonomous execution with verification (memory: working-style-autonomous-builds).

---

## Section B — full artifact index

### Committed docs
| File | What it holds |
|---|---|
| `agent-trader/PLAN.md`, `ONESHOT_PROMPT.md` | Original agent-trader plan + one-shot /goal (P0-P6, all built) |
| `agent-trader/CONSOLIDATED_RESEARCH_PLAN.md` | 16-thread Reddit synthesis → anti-patterns, primitives, phases A-E |
| `agent-trader/LANGALPHA_ANALYSIS.md` | LangAlpha teardown + feature table + what to adopt |
| `agent-trader/SOURCES_ROUND2_ASSESSMENT.md` | Round-2 good-vs-hype table + ranked adoptions |
| `agent-trader/ROUND2_GOAL_PROMPT.md` | Fire-ready /goal for the 6 build adoptions |
| `agent-trader/DEEP_DIVE_GOAL_PROMPT.md` | Fire-ready /goal for further research (already executed) |
| `agent-trader/DEEP_DIVE_FINDINGS.md` | Consolidated verdicts + data grades + ideas→module map |
| `agent-trader/DEEP_DIVE_REPOS.md` | 9-repo line-level teardown table |
| `agent-trader/DEEP_DIVE_FORUMS.md` | 10-thread comment-level digest |
| `design-reference/rallies/RALLIES_TEARDOWN.md` | Rallies product + data-quality grade A− |
| `design-reference/rallies/AUTHED_FEATURE_MAP.md` | Every authed page/button |
| `design-reference/stocktaper/DESIGNS.md`, `FEATURES.md`, `gallery/README.md` | The visual system to copy |
| `design-reference/inteldesk/DESIGNS.md`, `FEATURES.md` | The proof mechanics to copy |
| `CLAUDE.md` | Updated with both design references + visual direction |

### Local-only (gitignored — third-party copyrighted)
- `design-reference/stocktaper/` — 60 screenshots, 23 assets (logo, 5 mascots, product shots), promo video + keyframes
- `design-reference/inteldesk/` — 35 screenshots + icons/OG
- `design-reference/rallies/` — 40 screenshots + `authed/rallies-walkthrough.mp4`
- `design-reference/other-uis/` — Engo/margincall/freetradejournal/Autopilot shots
- Scratchpad: cloned repos (`repos/`), raw forum scrapes (`deepforums/`, `newsrc/`), page scrapes

### Session facts a fresh model should know
- Firecrawl API key lives in scratchpad `fc.env` (source it; never print). Reddit → Redlib mirrors.
- Rallies login was done by the user typing their own password (never handle passwords; magic-link + Gmail MCP is the preferred flow — used successfully for Stock Taper).
- The dashboard deploys via `.github/workflows/deploy.yml` on push to master; daily.yml persists `data/agent/ledger.json`.
- Everything committed through `3e0c44d docs(research): round-2 deep dive`.
