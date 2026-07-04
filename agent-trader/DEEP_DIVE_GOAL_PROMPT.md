# Deep-dive research goal prompt — Rallies UI + forums + repos (leave nothing out)

*Purpose: a next-session `/goal` that exhaustively deep-dives the specific sources — the
full Rallies product UI (every page, every button, every data point, and an honest
"is the data good?" verdict), every forum thread (post + all comments), and every GitHub
repo (line-level where it matters). Section A is the full brief (the anti-omission
checklist). Section B is the ready-to-fire string (≤4000 chars) — paste it after `/goal `.*

---

## Section A — full research brief (so nothing is missed)

### Tooling reminders
- **Firecrawl CLI** is installed globally. Source the key file (never print it):
  `source "<scratchpad>/fc.env"; export PATH="/c/Users/obara/AppData/Roaming/npm:$PATH"`.
- **Reddit is blocked directly** → scrape via Firecrawl pointed at a Redlib mirror
  (`redlib.nadeko.net`, fallbacks `redlib.r4fo.com`, `redlib.catsarch.com`,
  `redlib.privacyredirect.com`); retry another mirror on an Anubis "not a bot" page.
- **Playwright MCP** for live UIs: map routes first, screenshot every page desktop
  (1440×900) AND mobile (390×844) full-page, then exercise interactive elements.
- **Auth**: for login-gated areas, use the email **magic-link** flow and read the link from
  the connected **Gmail** MCP (search `from:noreply@…`), open it in the Playwright browser
  — never handle a password. Revert any account changes you make.
- Save screenshots under `design-reference/<site>/…`; raw scrapes + per-repo notes under the
  scratchpad; write final docs into `agent-trader/`.

### 1. Rallies — FULL product deep dive (rallies.ai) — the priority
Enumerate every route (Firecrawl `map` + the footer/nav), then for EACH:
- **Public pages:** `/`, `/pricing`, `/blog` + every post, `/about`, `/api-docs`,
  `/rallies-mcp`, `/discord`, and every `/features/*` (agents, chat, discover, arena,
  portfolio, ai-funds, screener, community, news, research). Screenshot desktop+mobile;
  list every CTA/link/tab.
- **Authed product (log in via magic-link + Gmail):** `/home`, `/home/portfolio`,
  `/profile`, the live **Arena** leaderboard, the **AI-Funds** builder, **Chat**,
  **Screener**, **Discover**, **News**, **Community**, agent config/monitoring, and the
  **SnapTrade broker-connect** flow (walk it up to the point of linking real accounts, do
  NOT connect a real broker). Screenshot every screen + every drawer/modal/state.
- **Every button/interaction:** click each control, capture the result — screener filters,
  chart timeframes, agent creation, chat prompts (ask it 3–4 real questions), fund-from-a-
  thesis flow, portfolio digest, alerts. Note keyboard shortcuts and empty/loading states.
- **"Is the data good?" — verify, don't assume.** Identify exactly which data Rallies
  serves (quotes, fundamentals, filings, analyst, insider, news) and its providers. Then
  **spot-check ≥10 concrete values against ground truth** (e.g. AAPL/NVDA/JPM last price,
  market cap, latest EPS, a recent insider/congress trade, an analyst PT) versus a
  reference (the live company IR page, SEC EDGAR, another terminal). Record: is it
  real-time or delayed (how much)? accurate? complete (coverage gaps, missing tickers/
  ETFs)? timestamped/fresh? Does the **Arena** show real or paper money, which models,
  real performance vs SPY, and is the methodology honest (survivorship, costs, denominator)?
  Assess the **Rallies MCP** tools + the **openfactor R2 snapshots** for currency/quality.
  End with an explicit **data-quality grade (A–D) with evidence.**
- Also capture the Autopilot copy-trade (`link.rallies.ai/claude`) and note what it mirrors.

### 2. Forums — every thread, post + ALL comments
For each URL the user listed (r/ClaudeAI, r/ClaudeCode, r/vibecoding, r/VibeCodersNest,
r/ai_trading, r/ralliesai): scrape the **full post body and the complete comment tree**
(top comments, skeptic critiques, the OP's replies, follow-up edits, and any linked repos/
sites/videos). For each, extract: what was built, method, results claimed + whether
verified, the sharpest critique, and any genuinely new idea. Explicitly separate **good
vs hype**. Cover the ones already summarized too, but this time capture the *comment-level*
detail that was skipped. Include the two YouTube-backed ones by actually reviewing the
video transcripts (use the `watch` skill on the YouTube URLs) — 20-step pipeline
(`ALzhOld-G68`), CEO deception (`sM1JAP5PZqc`), satellite (`tr-k9jMS_Vc`).

### 3. GitHub repos — full line-level analysis
Clone (shallow) and fully analyze EACH: `ralliesai/openfactor`, `ralliesai/rallies-cli`,
`ralliesai/tenk`, `ralliesai` (org — list all repos), `brentrager/get-rich-slow`,
`jakenesler/openprophet`, `JakeNesler/Claude_Prophet`, `Kingler16/Velora`,
`btopn/OpenInsider-MCP`, `quixio/klaus-kode-agentic-integrator`. For each: read the README
+ every significant module; map the architecture; list data sources (free vs paid, and
**are they good/real-time?**); **grep hard for rigor** (`brier|backtest|walk.forward|sharpe|
calibrat|kelly|purge|embargo|deflated|PBO|as.of|survivor|cost`) and report present-vs-
absent; check the licence; and note precisely what is reusable for the lab vs scaffolding
vs red flag. For **openfactor** go deepest: the factor math, the WLS/constraints, the
as-of leakage handling, the semantic-residual gate, the R2 data pipeline, the tests, and
whether the published factors actually validate. Temple-Stuart's repo is private/gone —
reconstruct it from its two Reddit posts.

### Deliverables
- Per-source deep-dive docs (Rallies UI teardown incl. data-quality grade; a forums
  comment-level digest; a per-repo teardown table).
- One consolidated `DEEP_DIVE_FINDINGS.md` in `agent-trader/`: good-vs-hype, data-quality
  grades, and any new ideas/improvements for the lab, each mapped to a lab module + guardrail.
- Keep the honest lens (CLAUDE.md guardrails); flag every leakage/survivorship/no-OOS/
  data-staleness issue you find.

---

## Section B — ready-to-fire /goal string (≤4000 chars; paste after `/goal `)

Deep-dive, in depth and without skipping anything, the specific sources in agent-trader/SOURCES_ROUND2_ASSESSMENT.md and the user's list, and write the findings into agent-trader/. Tooling: Firecrawl CLI (source the scratchpad fc.env for the key, never print it; scrape Reddit via a Redlib mirror redlib.nadeko.net with fallbacks r4fo/catsarch/privacyredirect, retry on Anubis pages); Playwright MCP for live UIs (map routes first, then full-page screenshot every page at 1440x900 AND 390x844, then click every interactive element and capture each result/modal/state); for login-gated areas use the email magic-link flow and read the link from the connected Gmail MCP, open it in the Playwright browser, never handle a password, and revert any account change; the `watch` skill for the YouTube URLs. (1) RALLIES full product deep dive (priority): enumerate every route; capture every public page (/, /pricing, /blog + posts, /about, /api-docs, /rallies-mcp, all /features/*) and, logged in via magic-link, every authed screen (/home, /home/portfolio, /profile, Arena leaderboard, AI-Funds builder, Chat, Screener, Discover, News, Community, agent config, the SnapTrade connect flow up to but not linking a real broker); click every button/filter/chart-control and ask Chat 3-4 real questions. Then answer "is the data good?" by spot-checking >=10 concrete values (prices, market cap, EPS, an insider/congress trade, an analyst PT for AAPL/NVDA/JPM) against ground truth (company IR, SEC EDGAR, another source), determining real-time-vs-delayed, accuracy, coverage gaps, and freshness/timestamps; assess whether the Arena is real or paper money, which models, honest vs SPY (survivorship/costs/denominator), and the openfactor R2 snapshot currency; end with an explicit data-quality grade A-D with evidence. (2) FORUMS: scrape every listed Reddit/YouTube thread's full post AND complete comment tree (skeptic critiques, OP replies, edits, linked repos), separating good vs hype, capturing the comment-level detail skipped before. (3) REPOS: shallow-clone and fully analyze ralliesai/openfactor (deepest: factor math, WLS/constraints, as-of leakage handling, semantic-residual gate, R2 pipeline, tests, do the factors validate), ralliesai/rallies-cli, ralliesai/tenk, the whole ralliesai org, brentrager/get-rich-slow, jakenesler/openprophet, JakeNesler/Claude_Prophet, Kingler16/Velora, btopn/OpenInsider-MCP, quixio/klaus-kode; for each map architecture, list data sources (free/paid, real-time?), grep hard for rigor (brier|backtest|walk.forward|sharpe|calibrat|kelly|purge|embargo|deflated|PBO|as.of|survivor|cost) reporting present-vs-absent, check licence, and note reusable-vs-scaffolding-vs-red-flag. Deliverables: a Rallies UI teardown with data-quality grade, a forums comment-level digest, a per-repo teardown table, and one consolidated agent-trader/DEEP_DIVE_FINDINGS.md (good-vs-hype, data grades, new ideas mapped to lab module + guardrail). Apply CLAUDE.md guardrails and flag every leakage/survivorship/no-OOS/data-staleness issue. Done when every listed page is screenshotted desktop+mobile with every interactive element exercised, >=10 Rallies data points verified against ground truth with a written A-D grade, every forum thread has post+comments captured, every listed repo has a written teardown, and DEEP_DIVE_FINDINGS.md plus the per-source docs are committed.
