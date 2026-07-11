# PHASE P6e — MUTUAL-FUND TWINS + TAX LENS + FINAL FIDELITY (build spec)

*Read first: `agent-trader/PLATFORM_PLAN.md` §3 (instruments beyond stocks),
§10 item 4 (the friction detector incl. tax drag), §12 (the fidelity matrix).
P6a–P6d are live. This is the last planned phase: mutual funds become real
(scored via their ETF twins with the fee delta called out), the portfolio gets
the taxable-vs-IRA lens, and the platform takes its closing fidelity review.
After this phase the operator's first `git push` turns everything on.*

## Ground rules (unchanged — keep every existing test green)
- Single-file no-build pages, Stock Taper skin; server-rendered; **no external
  fetches**; honest `n/a` / INSUFFICIENT degradation; not-financial-advice
  everywhere; personal data browser-local ONLY.
- **≥5 commits**, each with property/render tests (properties, never golden
  numbers); `python -m pytest` and `python -m ruff check src tests` green
  before each is called done.
- **USE CODEX per commit**: diff piped INLINE into
  `codex exec --sandbox read-only -`, real findings fixed AND pinned,
  `Codex-Review: <one line>` trailer.

## A) Mutual-fund twins (§3)
`sources/instruments`: a bundled `MUTUAL_FUND_TWINS` mapping of the common
index mutual funds (VTSAX, VFIAX, FXAIX, SWPPX, SWTSX, FSKAX, VTIAX, VBTLX…)
to their ETF twins (VTI, VOO, VOO, VOO, VTI, VTI, VXUS, BND) with BOTH
expense ratios as published. Funds register as kind `mutual_fund`, searchable
like everything else; the twin ETFs (VXUS, BND join the core list) carry
their own metadata. `t/<FUND>.html` renders the TWIN's verdict clearly
labeled — "a mutual fund, scored via its ETF twin VTI (same exposure); fees
0.04% vs 0.03%" — with the fee multiple called out when material ("~3x the
fee"). Honest INSUFFICIENT when the twin isn't rated. The mapping is exported
in the scoring contract so no client ever re-hardcodes it. Tests: mapping
bidirectional lookups, fee-delta math (None when either ratio is unknown),
unrated-twin honesty, search finds funds, fund pages render labeled.

## B) The tax/account lens (§12 item 5 — "later" is now)
An account-type control on the portfolio page (taxable / IRA / 401k,
localStorage, default taxable) feeding BOTH the Python engine and the JS
mirror through the SAME contract: `signals/portfolio` grows `account_type`;
in **taxable** accounts the wash-sale friction stays and high-dividend
holdings get a stated dividend-drag advice line (ONLY when a yield datum
exists — never fabricated); in **IRA/401k** those two are suppressed WITH the
reason on screen ("wash-sale rules don't apply in an IRA").
`portfolio_contract()` carries the account behaviors (which frictions apply
where, the dividend-drag threshold). Tests: taxable-vs-IRA divergence pinned
on the same book; no-yield-datum silence; the contract round-trips the
behaviors; the JS mirror reads them (never re-hardcoded).

## C) The final fidelity pass (§12)
Pipe the BUILT pages (home, a t/SYM page, portfolio, arena, journal, compare,
the landing head) + the AUTHED_CAPTURES summaries + the FIDELITY_MATRIX
deltas into Codex; fix every REAL confirmed gap (missing reference elements,
dishonest rendering) and pin the fixes in render tests. Note what was closed
in `design-reference/FIDELITY_MATRIX.md`.

## D) Docs
CLAUDE.md: the header still says "mutual-fund→ETF-twin mapping is planned
(P6e)" — mutual funds are now real; add the tax lens + twins to the repo map
(~150 lines max). Refresh the PLATFORM_PLAN/MASTER_PLAN phase-status lines
(P6a–P6e built).

## E) Ship check
`flab-run-all` completes locally (jobs may skip honestly); `flab-dashboard`
builds every page offline; `agent-trader/OPERATOR_RUNBOOK.md` = the
first-push checklist (git push → enable Pages → enable Actions → optional
Telegram token → optional CF worker) with what turns on at each step.

## Done
Mutual-fund pages render via labeled twins; the tax lens diverges
taxable-vs-IRA in both engine and mirror from one contract; the fidelity pass
is run and real gaps closed; docs current; the runbook exists; full pytest +
ruff green; ≥5 commits on master, each with a `Codex-Review` trailer.
