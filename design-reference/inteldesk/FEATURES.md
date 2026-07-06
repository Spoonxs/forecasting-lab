# Intel Desk — complete feature & mechanism teardown

*Every surface, panel, and honest-verification mechanism on inteldesk.app, mapped from
the live product (no login — the whole desk is public). Design language is in
`DESIGNS.md`. 2026-07-03.*

Intel Desk is a **free geopolitical/OSINT risk terminal**: `/pricing` and `/signup` both
redirect to `/dashboard` — there is no paywall or account. It positions as a *"free
Bloomberg alternative"* and monetizes via an iPhone app. What makes it worth a full pass
is its **verification machinery**, which is our forecasting-lab thesis applied to
geopolitics.

---

## 1. Site map (35 URLs)

- **Terminal:** `/dashboard` (the desk; panels via `?panel=` / `?filter=` / `?preset=`).
- **Live:** `/live` (Live Wire feed), `/corridor/hormuz` (geographic dossier).
- **Proof suite:** `/methodology`, `/sources`, `/scorecard`, `/replay`,
  `/proof/how-we-verify`, `/proof/speed`, `/proof/contradictions`, `/proof/corroboration`,
  `/proof/lead-time`, `/proof/signal-quality`, `/case-file/{slug}`, `/status`.
- **Marketing:** `/`, `/bloomberg-alternative`, `/for/{energy-traders|osint-analysts|macro-traders}`, `/updates/*`, `/faq`, `/open-first`, `/launch`, `/go/osint`.
- **Legal:** `/privacy`, `/terms`, `/support`.

---

## 2. The terminal (`/dashboard`) — every panel

Opens with an **onboarding "pick your lane"** overlay (`03`): Oil / LNG / Macro / Rates /
Defence / Chips → each loads a preset desk (e.g. *LNG DESK: 6 symbols, watchlist
NG=F/LNG/SHEL/BZ=F, region Gulf + shipping corridors, alerts Qatar LNG/Hormuz/Terminals,
morning brief 07:30*). Then **Open First**.

**Chrome:** status strip (`LIVE 726MS · ITEMS 39 · ALERTS 18 · CRITICAL 0`, `THREAT
HIGH`, `STAGE KINETIC`, `RISK READ: MIXED`), a live **market tape**, and settings:
Sound/**TTS "voice squawk"**, density (Comfortable/Standard/Dense), Focus mode, Critical
mode, **PWA install**, push notifications, keyboard shortcuts, ⌘K.

**Panels** (`#desktopNav`): `dashboard · osint · map · tools · polymarket`. Feed filters:
`CRITICAL · ALL · WIRE · ENERGY · CHIPS · LNG · HORMUZ · OFFICIAL · CB`. Confidence
filters: `HIGH CONFIDENCE ONLY · LOW-INDEPENDENCE · DEVELOPING`.

1. **DASHBOARD / feeds** (`04`) — the claim wire. Each item is a **trust readout** button
   (see §3) + a right rail with **MY BOOK** (`+1.45%`, 5 up/0 down), editable **Thesis
   Question / Three Tape-Changers / Execution Rules**, thesis probabilities, and
   **signal→action buckets ACT/VERIFY/PRICE/FADE**.
2. **OSINT** (`10`) — raw source feed (18 items) filtered by TELEGRAM/MILITARY/ENERGY/
   IRAN/RUSSIA/SHIPPING/SANCTIONS; each tagged `1 SRC · LOW · reliability D · low
   independence · market-linked · TG: Press TV · REL D · 1m ago`.
3. **MAP** (`09`) — Map Ops: vessels, aircraft, chokepoints (AIS + ADS-B).
4. **TOOLS** (`11`) — **Sanctions Exposure Scanner** (OFAC SDN + OpenSanctions),
   **armable OSINT alert presets** (Iran Escalation / Hormuz Shipping / Russia Energy /
   Sanctions Pack), **Sortie Rate Tracker** ("military aircraft vs 24h baseline, anomaly
   detection at 2σ+").
5. **ODDS / polymarket** (`06`,`08`) — **INTEL MARKETS**: *"Live prediction-market odds on
   Iran and Russia/Ukraine. **Paper calls only. No real-money trading.**"* Balance
   **10,000 IC**, session P&L, tabs **MARKETS / MY CALLS / LEADERBOARD**.

## 3. The Claim Tape (`05`,`07`) — the verification receipts drawer ⭐

Clicking any item's **trust readout** opens a drawer with the full provenance of one
claim:
- **STATUS** — `SINGLE SOURCE · Verify before sizing` / `UNVERIFIED · Watch until another
  source or market tape confirms` / `VERIFIED`.
- **RECEIPTS** — count + reliability (`1 SOURCE / REL D / SINGLE SOURCE`).
- **Claim Timeline** — `INTEL DESK FIRST SEEN 08:28 (+30s after Press TV)`, `FIRST
  PUBLISHED`, `VERIFICATION STATUS`, `LAST MATERIAL UPDATE` → this is the **lead-time**.
- **SOURCE DISCIPLINE** (only one source logged) · **CONTRADICTION** (`NONE LOGGED` /
  live contradictory source) · **MARKET REACTION** (`PARTLY IN · BZ=F +0.46%`) ·
  **FRESHNESS** (`first seen 28m ago / repeated 14× / latest 1m ago`).
- **Source Receipts** list (each: FIRST / REL letter / PUB time / SEEN time / OPEN) +
  **Context** + actions `OPEN SOURCE · PROOF · MARKET TAPE · ROUTE · HANDLED`.

## 4. The verification framework (from `/methodology` + `/proof/how-we-verify`)

**Reliability tiers — NATO admiralty A/B/C/D**, assigned at ingestion, visible for the
life of the story, upgradable/downgradable but original preserved:
- **A — Corroborated:** ≥2 independent tiers, institutional/wire origin. Highest.
- **B — Single credible source:** established track record. *Most stories enter at B.*
- **C — OSINT, worth watching:** single open-source/social feed with credible history.
- **D — State-aligned outlet:** Press TV, TASS, IRNA, RT. Weighted down; a D denial does
  **not** auto-override an A/B confirmation.

**Composite confidence score** (deterministic, A=4/B=3/C=2/D=1):

| Level | Criteria |
|---|---|
| **HIGH** | ≥3 unique sources incl. ≥2 rated A/B; no unresolved contradictions |
| **MEDIUM** | ≥2 sources, avg reliability ≥ 2.5 |
| **LOW-MEDIUM** | ≥2 sources but avg < 2.5 (e.g. B+D or two C) |
| **LOW** | single source, no corroboration → flagged **developing** |

**Contradiction lifecycle:** `Developing → Credible → Contested → Market-Moving`.
Contradictions are **preserved in the event chain, never deleted**; a denial is filed as
a new item; the letter is appended `-contested` (e.g. `A-contested`); a `CONTESTED` badge
shows. The desk does **not** retract on a single state-media denial.

**Constants:** 199 named/tiered sources (130+ actively monitored), 6 languages, **30s**
refresh, **2-source corroboration threshold**. Explicitly: *"deterministic rules… not
editorial judgments… the reader makes the final call."* (= **LLM/pipeline proposes,
reader decides** — our cardinal rule.)

## 5. The Scorecard (`/scorecard`) — public Brier-scored calibration ⭐⭐

Nearly verbatim to `calibration_log/`:
> *"Every thesis on the dashboard is a **falsifiable claim with a horizon**. When the
> horizon elapses we grade it **hit / miss / inconclusive** and write the result here. **We
> do not hide the misses.** The whole point of the ledger is **honest calibration.**"*

- **HIT RATE** and **BRIER SCORE** (*"Lower is better. 0 = perfect, 0.25 = coin flip."*).
- **Calibration gate:** *"Closed 7d/14d/30d outcomes are the only denominator… the page
  does not manufacture a hit rate from open claims"* (no look-ahead / honest denominator).
- **Miss ledger:** *"highest-confidence misses remain attached to the proof page."*
- **Open horizons under audit:** each thesis shows `7D · 42% · CLOSES JUL 10`, linked
  signals (`BZ=F/CL=F/GC=F/^VIX`). e.g. *Hormuz transit falls >20% in 7d (42%)*, *Iran×
  Israel kinetic exchange in 14d (34%)*, *Ukraine frontline shifts >5km in 30d (50%)*.

## 6. Proof suite & other pages

- **`/proof/lead-time`** — "what hit before price" (first-seen vs first-published).
- **`/proof/contradictions`** — "When sources disagree" (the contested lifecycle).
- **`/proof/corroboration`, `/speed`, `/signal-quality`** — one proof dimension each.
- **`/replay`** — replayable tapes of past events (the Trump-Iran-Brent tape).
- **`/case-file/trump-iran-brent-2026-03-23`** — the worked example: FinancialJuice breaks
  Trump postponing Iran strikes → critical alert fires **+40s** → Tasnim denies +50m →
  **Brent −12% in 90 min**, every reliability letter and confidence transition logged.
- **`/sources`** — the tiered source map (Tier-1 squawk can trigger on one source; OSINT
  Telegram never can); notes the full list is deliberately unpublished for opsec.
- **`/for/{persona}`** — energy/osint/macro landing pages. **`/status`** — uptime.
  **`/updates`** — changelog (Intel Desk 2.0, Polymarket integration, OFAC SDN vessel
  screening, 50+ Iran sources, military-aircraft/AIS tracking).

## 6b. Remaining panels, gauges & modals (second pass)

- **HOUSE panel** (`34-panel-house.png`) — **Congressional disclosure tape**: *"Fastest
  available public filings from trades made since 1 April 2026. Not live execution data,"*
  80 trades, `FOLLOW VISIBLE TICKERS`, `REFRESH NOW`, freshness stamp
  (`house-clerk:ok · 5650ms`). Same idea as Stock Taper's congress feature.
- **GAUGES dropdown** (`33-gauges-dropdown.png`) — the `GAUGES ▾` toggle opens the
  **geopolitical escalation ladder**: `DIPLOMATIC POSTURING → ESCALATION → KINETIC →
  FULL CONFLICT`, with the current `STAGE: KINETIC` / `THREAT: HIGH` lit. This is the
  model behind the status-strip threat/stage indicators.
- **"Catch me up" modal** (`32-catch-me-up-modal.png`) — a return-visit digest:
  *"SINCE YOU WERE LAST HERE — You were away for 3h 6m — 27 NEW ITEMS · 0 CRITICAL ·
  9 HIGH,"* a high-priority item list, **ACTIVE REGIONS** (Middle East 15, Russia/Eurasia
  8, Global 2), and **MARKET MOVERS** (LITE −9.1%, MU −5.5%…), with `SKIP TO LIVE FEED`.
- **Proof suite screenshots** now captured: `/proof/speed` (`26`), `/proof/corroboration`
  (`27`), `/proof/signal-quality` (`28`) — each a single-dimension proof page in the same
  template as `how-we-verify`.
- **Persona landing pages**: `/for/osint-analysts` (`29`), `/for/macro-traders` (`30`) —
  same layout as the energy-traders page, retargeted copy.
- **`/status`** (`31`) — system-status/uptime page. **`/open-first`** (`35`) — the
  onboarding explainer landing page.
- **ODDS live odds — not captured (environmental).** The INTEL MARKETS panel shell,
  balance (10,000 IC), tabs, and "paper calls only" copy are captured (`06`,`08`), but the
  **live Polymarket odds cards never load from this environment** (the public-market-cache
  endpoint retries indefinitely — Polymarket is likely geo/network-blocked here). The
  actual live thesis probabilities are available on the **Scorecard** (§5: Hormuz 42%,
  Iran×Israel 34%, Ukraine 50%), so the substance is covered even though the odds tiles
  didn't render.

## 7. Interaction/button inventory

Nav (`≡`, DASHBOARD/OSINT/MAP/TOOLS/ODDS), feed filters (9) + confidence filters (3),
trust-readout → claim drawer, density toggle (◇◈◫), Focus/Critical modes, `+ Install
app`, `🔔` push, `🔇 Sound` / `TTS Voice Squawk`, ⌘K command, keyboard shortcuts, editable
thesis/tape-changer/rules fields, ODDS place-paper-call + leaderboard, Tools scan + arm
alert packs, onboarding lane picker, `Delete account`/`Log out` (for app users).

---

**Bottom line:** Intel Desk is a working proof that our exact guardrails — A/B/C/D source
tiering, 2-source corroboration, contradictions-on-screen, Brier-scored public scorecard
with an honest denominator, paper-only markets, "receipts or stay quiet" — make a
*credible, distinctive product*, not just internal hygiene. Adopt the **claim-tape
drawer**, the **A/B/C/D trust badge**, the **ACT/VERIFY/PRICE/FADE** buckets, and the
**Brier scorecard** into the lab's dashboard/agent surfaces.

*Reference only. © Intel Desk — captured for private study, not redistribution. Not
financial advice.*
