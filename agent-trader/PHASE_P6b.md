# PHASE P6b — THE PAGES (build spec)

*The platform becomes visible. Read first: `agent-trader/PLATFORM_PLAN.md`
(§1 recommendation engine, §12 adopted improvements, §10 landing restraint),
`design-reference/AUTHED_CAPTURES.md`, `design-reference/other-uis/SAKURA_TEARDOWN.md`,
`design-reference/FIDELITY_MATRIX.md`. P6a's engine is live: verdicts read
`data/verdicts/<date>.json` + `contract.json` (the `labels_by_profile` matrix is
precomputed per symbol) and `dashboard/tier_live.py`.*

## Ground rules (unchanged, keep every existing test green)
- Single-file no-build HTML per page; content **server-rendered** (never JS-gated);
  hand-rolled SVG; small vanilla JS; **no external fetches** (no CDN fonts/scripts).
- Reduced-motion respected; renders with every artifact/sidecar missing; honest
  degradation (`n/a`, INSUFFICIENT EVIDENCE) — **never fabricate a number**.
- Not-financial-advice on every page; verdicts are the operator's research opinions.
- **MOBILE READ-FIRST**: phone-first verdict cards + portfolio reading; editing
  surfaces (holdings, journal — later phases) desktop-optimized.
- **≥5 commits**, each with render tests; `python -m pytest` and
  `python -m ruff check src tests` green before each step is called done.
- **USE CODEX per commit**: pipe the diff (`git show`/`git diff --cached`) INLINE
  into `codex exec --sandbox read-only -` (its Windows sandbox can't read files),
  terse review, fix real findings, add a commit trailer `Codex-Review: <one line>`.

## A) Ticker recommendation pages — `site/t/<SYM>.html`
Built by `flab-dashboard` for the watchlist + core ETFs + trending set (nightly
builds extend the set). Stock Taper statement shape × Rallies ratings scale:
- Price header with day change (from sidecars; `n/a` offline).
- Hand-rolled SVG chart with range pills (1M/3M/6M/1Y) + split/dividend markers
  from the corporate-actions data when present.
- **RECOMMENDATION HEADER**: the big label (STRONG BUY..AVOID / INSUFFICIENT
  EVIDENCE) + score + the **FOUR DIALS as gauges** (expected-return, drawdown
  risk, data confidence, model confidence) + a **"for YOUR profile"** line that
  swaps the label client-side from the embedded `labels_by_profile` matrix.
- Component breakdown table — each graded row with its score + confidence
  (Stock Taper breakdown-modal style).
- "What's going well? / What's concerning?" pairs derived from the components.
- **EVIDENCE CARD with a CLICKABLE RECEIPTS DRAWER**: audit hash, sources,
  freshness stamps, contradictions kept on screen (the Intel Desk claim-tape).
- **ANALYST CONSENSUS module**: best-effort free source, labeled **EXTERNAL
  OPINION** with staleness; `n/a` offline.
- Clickable dated news headlines (real link-outs).
- Peer strip linking sibling pages.
- Add-to-watchlist CTA explaining the tier contract.
- The `tier_live` stub embedded for on-demand symbols.

## B) Home as the platform — `index.html` rebuilt
- Platform hero replaces the newspaper masthead.
- **SEARCH** over the full universe: a compact client index — built pages
  navigate directly; unbuilt symbols get the tier-live / degradation path
  ("add to watchlist — full verdict on tomorrow's build").
- **TODAY'S VERDICTS** grid: verdict chips per built name, attractive-first;
  INSUFFICIENT chips honest + dimmed.
- **PROFILE CONTROL** (horizon / goal / risk, localStorage): re-renders every
  label client-side from the embedded matrices + `contract.json` — **no
  recomputation drift** (the JS reads the contract, never re-hardcodes numbers).
- ETF core row.
- The old briefing sections stay BELOW the fold as "the engine room".

## C) Compare + materiality change feed
- `site/compare.html` (`?a=X&b=Y`): two built tickers side-by-side, per-component
  verdicts + the winner per row (Stock Taper compare shape).
- **MATERIALITY CHANGE FEED** on home: diff the two latest verdict artifacts →
  "NVDA BUY → HOLD because trend fell −0.31", component-attributed, never vague.
  Honest with only one artifact ("first build — no changes yet").

## D) Landing — `site/landing.html` (Sakura treatment within §10 restraint)
Canvas particle layer (our own motifs — paper motes / tiny candlesticks, not
copied art), film grain, display-serif hero, tracked eyebrows, decisive easing,
scroll reveals. **PERF BUDGETS ENFORCED BY TEST**: inline JS < 50KB, total page
< 300KB, no unsized elements (zero layout shift), reduced-motion kills all
motion. Real product screenshots/links into the app. The **app pages stay
calmer** — no particles over data tables.

## E) Fidelity + docs
- Codex fidelity pass: compare the built pages' rendered HTML structure vs
  `AUTHED_CAPTURES.md` + the `FIDELITY_MATRIX.md` rows marked COVERED@P6b — fix
  real gaps it finds.
- Update CLAUDE.md's dashboard line (keep the file ~150 lines max).

## Tests (throughout)
Pages render offline fully degraded (`n/a` price, INSUFFICIENT verdicts, no
analyst data) and never fabricate; the ratings header + four dials + profile
matrix are present server-side; the receipts-drawer content is present without
JS; the search index is present; compare + the change feed build from fixture
artifacts; landing budget checks (inline-JS byte count, reduced-motion rule, no
external font/script fetches anywhere).

## Done
`flab-dashboard` builds `landing.html` + `index.html` + `compare.html` + ≥6
ticker pages offline; the full pytest suite + ruff are green; a `Codex-Review`
trailer on each commit; ≥5 commits landed on master.
