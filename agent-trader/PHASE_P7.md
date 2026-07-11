# PHASE P7 — THE DESK CHAT + CONGRESS/13F CONTEXT (build spec)

*Read first: `agent-trader/PLATFORM_PLAN.md` §11–§12 (the operator decisions
this phase delivers: "local desk chat (flab-ask)" and "congress/13F
best-effort with staleness labels") and §6 (free-data honesty: 13F and
politician disclosures are STALE BY DESIGN — context, never signal). P1–P6e
are live in production at `spoonxs.github.io/forecasting-lab`; CI must stay
green after every push.*

## Ground rules (unchanged)
- Honest `n/a`, no fabrication, not-financial-advice; personal data
  browser-local ONLY; pages make no external fetches; connectors degrade
  honestly and land in the health panel.
- **≥5 commits**, each with property/render tests (properties, never golden
  numbers); `python -m pytest` and `python -m ruff check src tests` green
  before each is called done; CI green on the pushed result.
- **USE CODEX per commit**: diff piped INLINE into
  `codex exec --sandbox read-only -`, real findings fixed AND pinned,
  `Codex-Review: <one line>` trailer.

## A) flab-ask — the local desk chat (the Rallies chat shape, our honesty)
A CLI (`flab-ask "what changed today"`) and an importable `desk/ask.py` that
answer DETERMINISTICALLY from the committed artifacts. Six intents:
1. **verdict** — "what's the verdict on NVDA (and why)": label + score + the
   four dials + top drivers + missing evidence + the audit hash;
2. **changes** — "what changed today": the materiality feed vs the prior
   artifact;
3. **arena** — "how's the arena going": books, equity, benchmarks, incubation
   status, last rebalance receipts;
4. **regret** — "how have the recommendations actually done": the regret
   summary vs the four baselines (honest "no resolved horizons yet");
5. **fees/twins** — "is VTSAX cheap to hold": the fund-twin card + fee
   multiple (or the ETF's own expense ratio);
6. **watchers** — "what are the watchers seeing": the latest feed's events +
   skips.
Every answer carries its receipts (as_of + audit hash, or "no record");
unknown questions get an honest "I can answer these six things" — never a
guess. Intent matching is deterministic patterns, NOT an LLM. Optional
`--llm`: when the local codex CLI exists, it may REPHRASE the deterministic
answer — the facts block is passed verbatim and pinned as the only source;
without codex the flag degrades honestly. No network in the core path.

## B) 13F holders (SEC EDGAR, free)
`sources/thirteenf.py`: for a curated manager list (Berkshire Hathaway,
Bridgewater, Renaissance Technologies, Citadel Advisors, Pershing Square…),
locate the newest 13F-HR via the existing proper-UA EDGAR client, parse the
information-table XML (top holdings by value, shares, ticker-mappable
issuers), and file a dated digest + TidyStore facts. EVERY datum carries the
filing period AND a computed staleness ("positions as of 2026-03-31, filed
46d later — up to ~135d old today"). Offline/blocked → stated skip. Tests:
parser on fixture XML, staleness math, blocked-network honesty.

## C) Congress trades (best-effort — the operator's stated tolerance)
`sources/congress.py`: the House/Senate financial-disclosure endpoints where
reachable (they are flaky; a blocked fetch is a stated skip). Dated rows
{member, chamber, ticker, amount_range, transaction_date, disclosed_date}
with the disclosure LAG computed and shown. Never a verdict input.

## D) Surfaces
A "Context — external positioning" module on `t/<SYM>.html`: 13F holders of
this name + recent congressional disclosures, EACH row carrying its staleness
label, under a standing banner: "context, not signal — this data is old by
design". Honest empty state. Both connectors registered in
`sources/registry` and the health panel. Optional: a `13f_new_position`
watcher template (deterministic, dated by the filing). **NOTHING here enters
`compute_verdict` — pinned: the contract's weights are byte-identical.**

## E) Wiring + docs
Connectors into `flab-run-all` (honest skips); `flab-ask` into pyproject
scripts; CLAUDE.md repo map updated (~150 lines max); push and confirm CI +
Pages stay green.

## Done
flab-ask answers the six intents from real artifacts with receipts; 13F +
congress data files with staleness labels and renders as clearly-marked
context on ticker pages without touching any verdict; connectors appear in
the health panel; full pytest + ruff green locally AND CI green on the pushed
result; ≥5 commits on master, each with a `Codex-Review` trailer.
