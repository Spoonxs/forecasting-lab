# Intel Desk — design reference & build guide

*Full-pass capture of [inteldesk.app](https://www.inteldesk.app/) — a free, no-auth
**geopolitical / OSINT risk terminal** for energy, macro & OSINT traders. Every page and
dashboard panel screenshotted, design tokens read off the live DOM, verification
framework transcribed. 2026-07-03. Feature teardown is in `FEATURES.md`.*

> **Why this one matters to us:** Intel Desk is the closest thing on the web to *our own
> thesis* rendered as a product. Its spine is honest calibration — a public **Brier-scored
> thesis scorecard**, **source reliability tiers (A/B/C/D)**, **contradictions kept on
> screen**, **"shows receipts or stays quiet"**, and **paper-only prediction markets**.
> Steal the *situation-room look* here; steal the *proof mechanics* into the lab.

---

## 0. File index

**Screenshots** (this folder): `01-home-full` · `02-dashboard-desk` · `03-onboarding-overlay`
· `04-desk-clean` · `05-trust-readout-drawer` · `06/08-panel-polymarket` (odds) ·
`07-claim-tape-receipts` · `09-panel-map` · `10-panel-osint` · `11-panel-tools` ·
`12-methodology` · `13-sources` · `14-proof-how-we-verify` · `15-scorecard` ⭐ ·
`16-replay` · `17-case-file` · `18-for-energy-traders` · `19-corridor-hormuz` ·
`20-live-wire` · `21-bloomberg-alternative` · `22-faq` · `23-updates` ·
`24-proof-lead-time` · `25-proof-contradictions`.

**Assets** (`./assets/`): `og-image.png`, `favicon-32.png`, `apple-touch-icon.png`.
There is **no image logo** — the brand is a pure typographic wordmark **`INTEL DESK`**.

**Page copy** (raw markdown of all 22 pages) in scratchpad `inteldesk/*.md`.

---

## 1. Design tokens (read off the live site)

### Color — "situation room"

| Token | Value | Use |
|---|---|---|
| **Field** (page bg) | `#E2E6E1` (rgb 226,230,225) | Cool sage-grey — the whole background |
| Field-2 / panel | `#D3D9D4` / `#EDF0EB` | Slightly lighter/darker panels |
| **Ink** | `#101214` (rgb 16,18,20) | Near-black text |
| Ink-2 / muted | `#4F595B` · `#2B3133` · `#3D4648` | Secondary/label greys |
| Sage-muted | `#8F9B95` · `#B8C2BC` | Dividers, faint labels |
| **Alert / accent** ⭐ | `#7A1020` (rgb 122,16,32) → `#8B1424` | Deep **oxblood crimson** — critical, threat, the signature |
| **Confirm** | `#3D6B2E` (rgb 61,107,46) | Muted olive green — verified / up |
| (down/red on tape) | crimson family | Negative % on the market tape |

The palette is **desaturated, cool, and military**: sage-grey field, near-black ink, one
oxblood-crimson alert accent, olive green for "confirmed". It reads like a classified
dossier / ops console — calm until something goes red. No neon, no gradients.

### Type

Two IBM Plex faces:
- **IBM Plex Mono** — all headings, labels, tickers, data, badges. (`h1` 57.6px/800,
  `h2` 19.4px/**900**, `h3` 15.3px/800.) Heavy weights, frequently **UPPERCASE**.
- **IBM Plex Sans** — body / longform prose.

Tabular mono figures everywhere → the dense data tables and market tape align for free.
Labels are terse, uppercase, telegraphic: `THREAT HIGH`, `STAGE KINETIC`, `REL D`,
`SINGLE SOURCE`, `VERIFY BEFORE SIZING`.

### Reproduction starter

```css
:root{
  --field:#E2E6E1; --panel:#EDF0EB; --ink:#101214; --muted:#4F595B;
  --line:#B8C2BC; --alert:#7A1020; --confirm:#3D6B2E;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
  --sans:"IBM Plex Sans",-apple-system,"Helvetica Neue",Arial,sans-serif;
}
body{ background:var(--field); color:var(--ink); font:15px/1.55 var(--sans); }
h1,h2,h3,.label,.ticker,.badge{ font-family:var(--mono); font-weight:800; }
.badge--alert{ color:#fff; background:var(--alert); text-transform:uppercase; letter-spacing:.04em; }
.badge--verify{ color:var(--confirm); border:1px solid var(--confirm); }
.tape .up{color:var(--confirm)} .tape .down{color:var(--alert)}
```

---

## 2. Layout & signature patterns

**Marketing pages** (`01`,`12`–`25`): tight max-width, mono H1s, telegraphic section
heds that *are the thesis* — *"Specific beats smooth. The desk shows receipts or it stays
quiet." · "Two-source threshold before confidence." · "Contradictions stay on screen." ·
"What the desk does not do yet."* Content is dense text + small data cards + inline
badges; almost no imagery. Footer columns: **THE DESK / REFERENCE / HOUSE RULES**.

**The terminal** (`02`–`11`) — a full-screen, dense, keyboard-driven **desk**:
- **Status strip**: `LIVE 726MS · ITEMS 39 · ALERTS 18 · CRITICAL 0`, `THREAT: HIGH`,
  `STAGE: KINETIC`, a live **market tape** (NG=F, LNG, SHEL, BRENT, GOLD, VIX… with
  green/crimson %), TTS/audit/settings.
- **Panel nav**: `DASHBOARD · OSINT · MAP · TOOLS · ODDS(polymarket)`.
- **Feed** of claim cards, each a **trust readout** badge (tier + receipts + timing).
- **Right rail**: editable **Thesis Question / Three Tape-Changers / Execution Rules**,
  the **MY BOOK** P&L, thesis probabilities, and the signal buckets.
- **Density modes** (Comfortable/Standard/Dense), Focus mode, Critical mode, PWA install,
  keyboard shortcuts. Built to be left open all session.

**Signature components to copy:**
- **Trust badge** on every item: `SINGLE SOURCE · Verify before sizing` /
  `UNVERIFIED · Watch until another source confirms` / `VERIFIED · 20 src · 2 buckets`,
  with a **receipts count** and **lead-time stamp** (`FIRST +4m / CHECK +12m`).
- **Reliability letter** `REL A/B/C/D` inline on each source.
- **Signal→action buckets**: `ACT · VERIFY · PRICE · FADE` with counts.
- **Thesis card**: a falsifiable claim + horizon + % confidence + linked signals
  (`7D · 42% · CLOSES JUL 10 · BZ=F/CL=F/GC=F/^VIX`).

---

## 3. Voice & copy (inseparable from the design)

Terse, declarative, trader-blunt, and relentlessly *honest*:
- *"The desk shows receipts or it stays quiet."*
- *"Size against label, not headline heat."*
- *"We do not hide the misses."*
- *"The rating system is deterministic rules, not editorial judgment… The reader makes
  the final call."*
- A whole section titled *"What the desk does not do yet."*

This is exactly the register CLAUDE.md asks for — plain, no hand-waving, limitations
stated up front.

---

## 4. How to apply to our dashboard

Two of our sites are worth blending: **Stock Taper** = warm/approachable retail; **Intel
Desk** = dense/honest pro terminal. For the *research/agent* surfaces, Intel Desk is the
better model. Mapping:

| Our surface | Intel Desk pattern |
|---|---|
| `calibration_log/` public log | **`/scorecard`** — Brier score, hit/miss/inconclusive, miss ledger, "denominator opens only after horizons settle" (no look-ahead). Near-verbatim to our ethos. |
| `predictions.py` cards | **Thesis card** — falsifiable claim + horizon + % + linked signals + trust badge. |
| Prediction-evidence "why" | **Claim Tape drawer** — receipts, source tiers, contradiction status, market reaction, freshness, timeline. |
| Edge/signal panels | **Signal buckets ACT/VERIFY/PRICE/FADE**; reliability letters A/B/C/D. |
| `sim/` paper arena | **ODDS / Intel Markets** — *"Paper calls only. No real-money trading,"* 10,000 IC balance, leaderboard. Our cardinal rule, shipped. |
| `markets/monitor` divergence | **Contradictions stay on screen** — `A-contested` badges, never deleted. |
| Voice/track record | **Lead-time proof** — "what hit before price," first-seen vs first-published. |
| Skin | Sage-grey field + IBM Plex Mono + oxblood alert + olive confirm; dense mono tables; uppercase telegraphic labels. |

**Concrete steal for the agent terminal:** re-skin the dark Agent Terminal toward this
sage-grey ops console, and give every agent pick a **trust badge** (source count +
confidence tier) and a **claim-tape drawer** (the evidence + contradictions), with a
**Brier scorecard** page as the public ledger. That single move makes the desk *feel*
verified instead of asserted.

---

*Reference only. © Intel Desk — captured for private design study, not redistribution.
Not financial advice.*
