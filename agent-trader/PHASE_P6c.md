# PHASE P6c — PORTFOLIO + THE AI ARENA (build spec)

*Read first: `agent-trader/PLATFORM_PLAN.md` §4 (the portfolio + arena), §9–§12
(the adopted Codex reviews + operator decisions). The P6a engine (verdicts,
`data/verdicts/<date>.json`, `signals/verdict`, the four-dial confidence budget)
and P6b pages are live. This phase makes the platform evaluate YOUR holdings and
race two AI-built books — with the regret ledger, the credibility engine, built
BEFORE the arena (the operator's sequencing fix).*

## Ground rules (unchanged — keep every existing test green)
- Single-file no-build pages; content server-rendered; hand-rolled SVG; small
  vanilla JS; **no external fetches**. Reduced-motion respected; honest `n/a` /
  INSUFFICIENT degradation; never fabricate. Not-financial-advice everywhere.
- **PRIVACY (operator decision §11): personal holdings/journal are browser-local
  ONLY** — localStorage + a one-click encrypted export/import; NEVER committed,
  never uploaded. Broker CSV import is parsed **client-side** and stays local.
  The AI arena books + the regret ledger ARE public (paper).
- **MOBILE READ-FIRST**: the portfolio + arena read well on a phone; holdings
  entry / CSV import is desktop-optimized.
- **≥5 commits**, each with property/render tests; `python -m pytest` and
  `python -m ruff check src tests` green before each is called done.
- **USE CODEX per commit**: pipe the diff INLINE into
  `codex exec --sandbox read-only -` (its sandbox can't read files), terse
  review, fix real findings, add a `Codex-Review: <one line>` commit trailer.

## A) Portfolio evaluation engine (Python core, property-tested)
`signals/portfolio.py` (or extend `agent_trader`): given holdings
`[{symbol, weight or dollars}]` + a `Profile` + the verdict artifact, compute:
- allocation + **concentration vs the V4 mandate** (reuse `agent_trader.mandate`
  thresholds — max_position_pct, min_cash_pct, max_sector_pct; concentration on
  **invested** capital; sells always pass);
- **ETF overlap** (QQQ⊂VOO⊂SPY, etc.) from bundled constituent lists — flag
  double-counted exposure ("holding QQQ + VOO = ~X% overlap in the top names");
- **per-holding verdict** joined from the artifact (INSUFFICIENT where unknown);
- **book-level crowding** (reuse `fleet_correlation` shape — is the whole book
  one bet?); **vs-SPY and vs-HYSA** comparison over the profile horizon;
- **the DECISION FRICTION DETECTOR (§10)**: a positive verdict that is NOT
  actionable — position already over the mandate cap, spread/liquidity (the V9
  spread gate as a signal), earnings proximity, wash-sale window — renders
  "don't do this now: <reason>". Profitable operators need that as much as "buy".
- deterministic **advice lines with the reason stated** ("38% in one name
  exceeds the 25% cap"; "QQQ+VOO overlap ~40% — you're doubling the megacaps").
Export the mandate thresholds + overlap constituent data as JSON so the client
mirror uses the SAME numbers (never re-hardcoded). Property tests: over-cap
flagged, overlap flagged, crowding flagged, friction fires on the right inputs,
missing data → n/a never imputed, math matches the client contract.

## B) Portfolio page (`portfolio.html`)
Holdings via a small form + **broker CSV import** (Robinhood/Fidelity/Schwab
column shapes, parsed in-browser, never uploaded) + localStorage, with a
one-click **encrypted export/import**. Evaluated client-side against the
build-time JSON (per-ticker metrics + thresholds + overlap): the mandate
verdict, ETF-overlap warnings, per-holding verdict chips, crowding gauge,
vs-SPY/vs-HYSA, the friction flags, and the advice lines. A **hide-values
toggle (§12)** blurs dollar amounts. A server-rendered demo portfolio so the
page is never blank; honest n/a for anything unpriced. Not advice; it's the
operator's own tool.

## C) The regret ledger (the credibility engine — BEFORE the arena)
`calibration_log/regret.py` (or extend forwardtest): every recommendation the
platform surfaces is tracked forward vs **SPY / HYSA / equal-weight /
do-nothing** at the operator's horizon — the honest definition of "profitable"
(operator decision §11). Dated, audit-hashed, replayable; renders on a
`regret` surface (its own page or a home section) with honest zeros before
results accrue. Property tests: the four baselines computed correctly; a
recommendation that beat/lagged each baseline is scored right; empty ledger
states "no resolved horizons yet".

## D) The AI arena (Rallies shape, Engo honesty)
`agent_trader/arena_books.py`: **Claude's book** (generated deterministically
from the verdicts — top attractive names, mandate-legal weights, a stated
thesis) and **Codex's book** (via `codex exec` when available, else the last
committed artifact renders WITH its date), each an immutable **audit-hashed
JSON** with a **written mandate** (fixed caps, scheduled rebalance windows only,
costs + cash yield modeled, no lookahead — picks dated before marks). Marked
daily by the forward study. The book table is the **Rallies layout** (stock ·
alloc% · P&L · P&L% · notional · worth · entry, TOTAL P&L + AVAILABLE CASH).
**Benchmark rows (SPY, HYSA) are always on the board.** The fleet gate + a
**7-day track-record rule** before a book is labeled anything but "incubating".
Rebalances are dated events with receipts. Render **open "bring-your-own-model"
slots** (§12) so Gemini/Grok drop in later with a key — no fake competitors.
Operator portfolios can join. Arena page or home section.

## E) Docs + fidelity
Codex fidelity pass comparing the built portfolio + arena vs
`AUTHED_CAPTURES.md` (Rallies arena book table, agent surfaces) — fix real gaps.
Update CLAUDE.md (keep it ~150 lines) + the `flab-*` CLI wiring (portfolio/arena
build into `flab-dashboard`; any new job into `flab-run-all`).

## Tests (throughout)
Portfolio math property-tested + the client contract round-trips it; the page
renders offline with the demo book + honest n/a and never fabricates; CSV parse
is client-side (no upload); hide-values present; regret ledger scores the four
baselines + honest empty state; arena books are audit-hashed + incubating < 7
days + benchmarks always on the board + open slots rendered; no external
fetches; not-financial-advice on every page.

## Done
`flab-dashboard` builds `portfolio.html` + the arena + the regret surface
offline (with the demo/committed data); the full pytest suite + ruff are green;
a `Codex-Review` trailer on each commit; ≥5 commits landed on master.
