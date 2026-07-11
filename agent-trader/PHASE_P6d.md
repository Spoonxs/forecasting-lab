# PHASE P6d — JOURNAL + WATCHERS + FRESHNESS (build spec)

*Read first: `agent-trader/PLATFORM_PLAN.md` §5 (the agent workflow), §6
(automation & freshness), §11–§12 (operator decisions + the adopted fidelity
matrix). P6a–P6c are live: the verdict engine + artifacts, the ticker/compare/
home pages, the portfolio page, the regret ledger, and the AI arena. This phase
adds the three surfaces that make the platform *usable over years*: the
decision journal (did following it pay?), the watcher templates (the Rallies
"describe what to watch" shape, deterministically), and the freshness/health
layer (does the operator know when the data went stale?).*

## Ground rules (unchanged — keep every existing test green)
- Single-file no-build pages, Stock Taper skin; server-rendered content;
  small vanilla JS; **no external fetches**; honest `n/a` degradation;
  not-financial-advice everywhere. Reduced-motion respected.
- **PRIVACY (§11): the decision journal is browser-local ONLY** — localStorage
  + the existing passphrase-encrypted export/import pattern; NEVER committed,
  never uploaded; no fetch/upload path may exist for journal data (pinned).
  Server-side watchers run on **PUBLIC data only** (watchlist, verdicts,
  sidecars, the V10 store) — never on holdings.
- **≥5 commits**, each with property/render tests (properties, never golden
  numbers); `python -m pytest` and `python -m ruff check src tests` green
  before each is called done.
- **USE CODEX per commit**: pipe the diff INLINE into
  `codex exec --sandbox read-only -` via stdin (its sandbox can't read files),
  terse review, fix real findings AND pin each in a test, add a
  `Codex-Review: <one line>` commit trailer.

## A) The decision journal (§11 — a unique bet)
"I followed this / I ignored this" buttons on `t/<SYM>.html` + the portfolio
page, logging `{date, symbol, label, score, action, note?}` to localStorage.
A journal surface (own page or portfolio section) lists entries and joins them
CLIENT-SIDE against the **public regret artifact**: an aged entry shows
"following beat/lagged SPY / HYSA by X" once its horizon resolves; honest
"not yet resolved" before; honest "not tracked" when the regret ledger never
opened that name. Encrypted export/import covers the journal. Server-rendered
empty state so the surface is never blank. Tests: entries join correctly
against a fixture regret artifact; unresolved/untracked states honest; NO
fetch/upload path in the page (pinned); XSS-safe notes.

## B) Watcher templates (§5 — Rallies agents shape, our honesty)
`pipeline/watchers.py`, deterministic TEMPLATES only (no free-text LLM
promises; the LLM may later PROPOSE configs, deterministic code runs them):
- **earnings-proximity** on watchlist names (when the datum exists);
- **squeeze-trigger** — the squeeze composite crossing a stated threshold;
- **insider-cluster-buy** — the V10 store's distinct-insider cluster events;
- **verdict-change/downgrade** — today's artifact vs the prior one (reuse the
  materiality logic; a label change or a score move ≥ a stated threshold);
- **macro-regime-flip** — the recession nowcast crossing its stated line.
Config = committed `data/watchers.json`. Each firing is a **dated event with
the stated reason + audit-hashed inputs**, landing in BOTH the alerts digest
(`flab-alert` → Telegram/Discord/`inputs/alerts.log`, already wired) and a
site feed JSON the home page renders. Tests: each template fires on injected
data, stays silent otherwise; a missing source is an honest stated skip —
never a fabricated trigger; events carry hashes and replayable inputs.

## C) Changed-since-last-visit (§12 item 5)
Client-side digest on the home page from the existing materiality feed:
localStorage last-visit stamp → "N verdicts moved since you were here" with
the movers named, dismissible, silent on first visit, and it NEVER recomputes
scores (it only filters the server-rendered feed by date).

## D) Connector health panel (§6)
An engine-room surface listing every registered source's last-fetch stamp and
an ok/degraded/stale label driven by `pipeline.freshness`, server-rendered,
with honest "never fetched" states. Rate-limited jobs skip cleanly with a
stated reason — **no infinite retries anywhere** (pinned).

## E) Wiring + docs
The watchers job into `flab-run-all` (and `flab-intraday` where cheap);
CLAUDE.md repo map updated for journal/watchers/health (~150 lines max).

## Done
Journal + watchers + health panel + since-last-visit all exist and render
offline with honest degradation; the full pytest suite + ruff are green;
≥5 commits on master, each carrying a `Codex-Review` trailer.
