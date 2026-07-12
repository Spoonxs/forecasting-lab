# PHASE P9 — THE GLOW-UP (build spec)

*Read first: `agent-trader/AUDIT_P8.md` §P9 and
`design-reference/other-uis/SAKURA_TEARDOWN.md` (the quality bar and its
eight verified techniques). P8 is live — the platform rates, the gate is ok
on the public site. This phase buys the landing the Sakura depth the operator
asked for (GSAP + three.js, vendored) and gives the app pages a restrained
motion layer. Data surfaces stay hand-rolled SVG; content is never JS-gated;
every number shown comes from the committed artifacts.*

## Ground rules
- **Vendored, never CDN'd**: gsap.min.js + ScrollTrigger.min.js (GSAP is free
  since the Webflow acquisition — license text committed) and
  three.module.min.js (MIT, license committed) live in
  `src/forecasting_lab/dashboard/assets/vendor/` as package data; the build
  copies them to `site/vendor/`; pages reference ONLY relative paths. The
  no-external-fetch pins are updated deliberately: local `./vendor/` and
  `./motion.js` srcs allowed; `http(s)` script srcs stay forbidden everywhere.
- **One kill-switch**: `prefers-reduced-motion` OR a user toggle persisted in
  localStorage disables EVERYTHING (canvas, scrub, reveals, counters).
- **Budgets, pinned in tests**: landing JS total (vendored incl.) < 250KB
  gzipped; landing HTML < 60KB; hero readable with NO JS (static poster
  fallback — procedural CSS/SVG now, a 4070 Ti-generated poster may replace it
  later); reduced-motion = the static experience.
- ≥4 commits, property/budget tests (never golden pixels), pytest + ruff green
  per commit, Codex review per commit with trailer, CI green on push.

## The landing storyboard (S0–S5, GSAP ScrollTrigger pinned scenes)
- **S0 HERO (pinned)** — three.js: a drifting field of thin verdict-card
  planes (cream quads, green/brick edge accents) above a faint price-surface
  wireframe; film-grain overlay; display-serif headline **"Every verdict
  carries its receipts."**; tracked-out eyebrow (.5em) "THE VERDICT DESK ·
  PAPER FIRST"; vertical rail "EST. 2026 · NOT FINANCIAL ADVICE"; scrollcue.
  Easing everywhere: `cubic-bezier(.7,0,.2,1)`.
- **S1 THE CARD ASSEMBLES (scrub)** — a Stock Taper verdict card builds
  component-by-component with the TOP RATED name's real rows from the
  committed artifact (label stamps in, then trend/backtest/residual/macro
  slide in with their real scores).
- **S2 THE DIALS FILL (scrub)** — the four confidence gauges sweep to that
  name's real dial values.
- **S3 THE ARENA DRAWS (scrub)** — equity lines draw from the arena ledger's
  real curve points (Claude's book vs the SPY benchmark), incubation chip.
- **S4 THE RECEIPTS STAMP (scrub)** — the regret ledger's real counts stamp
  down ("N recommendations tracked vs SPY · HYSA · equal-weight ·
  do-nothing") with audit-hash chips.
- **S5 THE HONEST CLOSE** — "Most models can't beat the market. This one
  shows its work either way." + not-financial-advice + CTA → index.html.
No-JS/reduced-motion: the same sections render statically stacked, poster
hero, everything readable — the current static landing's honesty preserved.

## Commits
1. **P9-1 vendoring + motion.js**: the three vendored files + licenses as
   package data; build copies to `site/vendor/`; `motion.js` (kill-switch,
   reveal helpers, eased counters); test-pin updates for local srcs; budget
   tests armed.
2. **P9-2 the landing**: `dashboard/landing.py` full rebuild to the
   storyboard; real artifact numbers server-rendered; poster fallback; budget
   + honesty tests (no invented numbers; content present without JS).
3. **P9-3 app polish**: home hero counters, dial sweeps, row reveals, tab
   underline — ≤300ms, motion.js only, dead under the kill-switch; pins.
4. **P9-4 fidelity + perf**: Codex fidelity pass vs the teardown (fix real
   gaps); byte budgets recorded; full rebuild; push; CI green; LIVE landing
   verified (vendor 200s, poster present); AUDIT_P8 §P9 stamped.

## Done
The landing tells the receipted-verdicts story with a real WebGL hero +
scroll choreography inside the budgets, honest no-JS/reduced-motion
fallbacks; app pages carry the restrained layer behind one kill-switch;
vendored libs + licenses committed; fidelity pass run; suite + CI green;
≥4 commits with Codex-Review trailers.
