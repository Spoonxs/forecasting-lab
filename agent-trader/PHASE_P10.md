# PHASE P10 — PARITY DEPTH (build spec)

*Read first: `agent-trader/AUDIT_P8.md` §P10. P8 (the platform rates) and P9
(the Sakura landing + motion layer) are live. This phase closes the remaining
reference-parity gaps: the in-site chat, real fundamentals, the watcher
builder, exact-year personalization, and live quotes via the operator's
worker deploy.*

## Ground rules
Honest n/a, no fabrication, not-financial-advice; personal data
browser-local; pages fetch SAME-ORIGIN only; connectors degrade with stated
skips; fundamentals are dated by FILING ACCEPTANCE date and never touch a
verdict. ≥5 commits, property/render tests each, pytest + ruff green per
commit, Codex review per commit with a `Codex-Review:` trailer, CI green on
every push.

## 1. In-site chat — `desk.html` (the Rallies chat shape, our honesty)
A client-side DETERMINISTIC mirror of `flab-ask`'s six intents
(verdict / changes / arena / regret / fees / watchers) over same-origin
artifact JSON (embedded at build or lazy-fetched like `universe.json`).
Rallies suggested-question chips; the same receipts (as_of + audit hash or
"no record"); the honest capability list for anything else; NO LLM in the
browser. The JS and `desk/ask.py` share ONE exported `desk_contract()`
(intent patterns + answer skeletons) so the two sides cannot drift. The nav
gains **Desk**. Tests: each intent answers from fixture artifacts, receipts
present, XSS-safe, zero external fetches.

## 2. Fundamentals — SEC XBRL `companyfacts` (free, proper UA)
`sources/fundamentals.py` for the RATED tier, cached like the price panel
(`data/fundamentals/`, gitignored, CI-cached, incremental, circuit breaker):
annual + quarterly revenue / net income / EPS, every datum carrying its
FILING ACCEPTANCE date + fiscal period. A **Financials** section on
`t/<SYM>.html` renders sparktables dated honestly ("FY2025, filed
2026-02-14"), honest empty state when unfetched. NEVER a verdict input
(pinned: contract weights byte-identical). Wired into `flab-run-all`
(honest skip) and the health panel.

## 3. Watcher builder (the Rallies agent-builder shape)
A builder on `agent.html` editing `data/watchers.json` semantics
client-side: the five templates as a gallery with plain-language
descriptions, threshold controls bounded to each template's stated valid
range, a live JSON preview, and copy-to-clipboard "commit this config" (the
config stays a COMMITTED file — no server writes, stated on screen).
Validates against a `watchers_contract()` exported from
`pipeline/watchers.py` (kinds, bounds, defaults — never re-hardcoded).
Tests: contract round-trips, generated JSON round-trips through
`load_config`, bounds enforced, XSS-safe.

## 4. Profile depth
Exact-year horizon: a 0–30y slider INTERPOLATING between the existing
bucket-multiplier anchors, exported in the scoring contract so the client
relabeling stays contract-driven. Optional dollar goal + monthly
contribution on the portfolio page → the honest compounding line ("at the
HYSA's current yield your contributions reach $X by year N — the book must
beat that"), clearly labeled ARITHMETIC, not a prediction; n/a without a
yield datum. Engine + JS mirror from one contract. Pins: interpolation
monotonicity between anchors; no-datum silence.

## 5. Live quotes (operator decision recorded: the worker WILL deploy)
Hand the operator the exact steps (`wrangler login` / `wrangler deploy` with
`ALLOWED_ORIGIN=https://spoonxs.github.io`) and WAIT for confirmation; then
wire TIER LIVE fully (the worker URL into the build; the on-demand preview
path), push, and verify LIVE: an unbuilt symbol renders its stated
one-component preview + the add-to-watchlist honesty. If deferred:
everything ships worker-ready behind the existing stated degradation, noted
in the runbook.

## 6. Docs + ship
CLAUDE.md repo map (~150 lines); AUDIT_P8 §P10 stamped; full rebuild; push;
CI green; live spot-checks (desk.html answers, Financials on AAPL, the
builder round-trip).

## Done
desk.html answers the six intents client-side with receipts from the shared
contract; fundamentals render on rated pages dated by filing acceptance with
the connector in run-all + health; the builder round-trips a valid config
from the exported contract; exact-year horizons + the dollar-goal arithmetic
work in engine and mirror from one contract; live quotes verified live (or
worker-ready degradation stated); pytest + ruff green AND CI green on the
pushed result; ≥5 commits with Codex-Review trailers.
