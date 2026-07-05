# Site blueprint — every feature & UI pattern extracted from the references

> **DESIGN PRIORITY UPDATE (2026-07-05, operator decision):** the two favorite UIs are
> **Rallies and Stock Taper — use their UI the most.** Concretely: **Stock Taper = the
> skin** (cream `#FBF7EB`, IBM Plex Mono, white cards, eyebrow tags, mascots,
> "going well / concerning" pairs) and **Rallies = the layout & IA** (feature-per-surface
> nav, peer strips, position-level book tables, research sub-tabs, suggested-question
> chips, filtered feed, visible multi-step agent plans, theme baskets). **Intel Desk is
> demoted to a mechanics-only source** — its trust badges, claim-tape drawer, Brier
> scorecard structure and ACT/VERIFY/PRICE/FADE buckets are adopted but **restyled in
> the Stock Taper/Rallies language** (no sage/oxblood skin on the research surfaces; the
> dark terminal may keep its own look). Engo contributes arena honesty only (benchmark
> line, gate stats, 7-day publish gate). The build order + rigor track live in
> **`agent-trader/MASTER_PLAN.md`** — that doc supersedes Part 4 below.

*The consolidated extraction. Each reference was captured in full (screenshots + teardowns
in this folder); this doc pulls out **every component and feature worth having**, says
exactly which reference it comes from, what data powers it, and where it lands on our
site. No code here — this is the spec the visual/build pass executes against.
Sources: `stocktaper/` (60 shots), `inteldesk/` (35), `rallies/` (40 + video),
`other-uis/` (Engo etc.), plus the LangAlpha repo teardown. 2026-07-04.*

---

## Part 1 — The design system (two skins, one family)

Our site has two surfaces with different jobs → two skins that share a type system:

### Skin A — "Almanac" (research dashboard `index.html`) ← Stock Taper
| Token | Value | Notes |
|---|---|---|
| Paper bg | `#FBF7EB` | warm cream, never white page bg |
| Card | `#FFFFFF` | white cards on cream, 1px `#E5E5E5` hairline, ~12px radius |
| Ink / heading | `#141414` / `#393939` | |
| Up / down | `#2F7D31` / `#C6392C` | muted forest & brick — never neon |
| Muted | `#9E9E9E` | labels, meta |
| Type | **IBM Plex Mono everywhere** | H1 36/700 · H2 30/700 · H3 20/heavy UPPERCASE · body 14 |
| Signature | **eyebrow tag** (11px, uppercase, letterspaced, muted) above every H3 | `DECODED`, `RADAR`, `1 v 1` style |
| Personality | **one mascot illustration per panel** | warm, slightly-retro rendered set |

### Skin B — "Ops console" (Agent Terminal `agent.html` + scorecard) ← Intel Desk
| Token | Value | Notes |
|---|---|---|
| Field bg | `#E2E6E1` (light) — our terminal may keep dark `#0d0f13` | sage-grey console |
| Alert accent | `#7A1020` oxblood | critical/risk — the one loud color |
| Confirm | `#3D6B2E` olive | verified/positive |
| Type | IBM Plex Mono headings/data + Plex Sans prose | terse UPPERCASE labels: `THREAT HIGH`, `REL D`, `VERIFY BEFORE SIZING` |

Voice (both skins): plain-English, anti-jargon, honest. Every section leads with a
question ("What's moving now?"), jargon translated, limitations stated (`what the desk
does not do yet`). Stock Taper proves warm; Intel Desk proves blunt; we need both.

---

## Part 2 — Component library (extracted, with source + data + destination)

### A. Cards & evidence (the crown jewels)

1. **Evidence-thesis card** — *Stock Taper Opportunity Radar* (`stocktaper/features/03`).
   Structure: ticker chips → **WHY NOW** → **EVIDENCE** (each claim + cited source) →
   **WATCH FOR ↑** → **RED FLAGS ↓** → **picks each with Confidence ●●●●○ dots**.
   Data: `predictions.py` contract (probability + drivers + caveat) already matches 1:1.
   → Our **forecast cards** (market picks, edge research, macro nowcast).
2. **Trust badge / readout** — *Intel Desk* (`inteldesk/05`). Inline chip on every feed
   item: status (`SINGLE SOURCE · Verify before sizing` / `VERIFIED · 20 src`), receipts
   count, lead-time stamp (`FIRST +4m / CHECK +12m`). Data: per-pick source count +
   `calibration_log` first-seen times. → Every agent pick + mover card.
3. **Claim-tape receipts drawer** — *Intel Desk* (`inteldesk/07`). Click a trust badge →
   drawer: STATUS · RECEIPTS (source list w/ reliability letter + pub/seen times) ·
   Claim Timeline (desk-first-seen vs published = lead time) · **CONTRADICTION (kept on
   screen, `-contested`, never deleted)** · MARKET REACTION (`PARTLY IN · BZ=F +0.46%`) ·
   FRESHNESS (`repeated 14×`). → The "why" expander on agent picks, upgraded to receipts.
4. **"What's going well? / What's concerning?" AI pair** — *Stock Taper premium*
   (`stocktaper/gallery/06`). Two short honest paragraphs under every data table,
   caveats included ("profit came from investment gains, may not repeat"). → Under each
   strategy/edge/mover panel; text from our drivers + caveat fields.
5. **Verdict-header breakdown modal** — *Stock Taper "View Breakdown"*
   (`stocktaper/features/12`). Modal: `Overall: Excellent · Trend: Improving · Bottom
   Line: Strong` header + plain-English Q&A rows ("profit per dollar of revenue? 27¢").
   → Per-strategy deep-dive (equity curve stats as Q&A).
6. **A/B/C/D source-reliability tiers** — *Intel Desk methodology* (`inteldesk/14`).
   NATO-admiralty letters assigned at ingestion, visible for life, `-contested` suffix;
   deterministic composite confidence (HIGH needs ≥3 sources incl. ≥2 A/B, no unresolved
   contradictions). → `sources/registry` gets a tier per connector; badges ride picks.

### B. Scoreboard & honesty surfaces

7. **Public Brier scorecard page** — *Intel Desk `/scorecard`* (`inteldesk/15`) ⭐.
   "Every thesis is a falsifiable claim with a horizon… hit/miss/inconclusive… **we do
   not hide the misses.**" Blocks: HIT RATE · **BRIER** ("0 perfect, 0.25 coin flip") ·
   **calibration gate** (only closed horizons count — denominator opens only after
   settlement) · **MISS LEDGER** (highest-confidence misses pinned) · open horizons under
   audit (`7D · 42% · CLOSES JUL 10 · linked signals`). Data: `calibration_log/` +
   `forwardtest/` — we already compute all of it. → New page `scorecard.html`.
8. **Arena board vs benchmark + gate stats** — *Engo* (`other-uis/engo-02`). Equity
   curves indexed to 100, **SPY line always on the board**, and the gate stated in the
   open: `26 candidates · 0 survive family-FDR ≤5% · ensemble: 100% SPY` + "everything
   starts as paper; the best earn real capital." (Rallies' arena shows position-level
   books — GPT/Grok/Gemini/Claude, alloc/P&L/entry — but **no SPY line**: copy Rallies'
   position transparency, Engo's benchmark honesty.) → `sim/` arena panel upgrade.
9. **ACT / VERIFY / PRICE / FADE buckets** — *Intel Desk*. Four action-shaped bins with
   counts; every signal is triaged into one. → The edge-research panel: each edge lands
   in a bucket based on OOS skill + freshness.
10. **Position-level paper book** — *Rallies arena* (`rallies/28`). Table per strategy:
    ticker · alloc% · P&L · P&L% · notional · worth · entry. → Agent desk blotter detail.

### C. Data-display components

11. **Market-snapshot tables** — *Stock Taper home* (`stocktaper/gallery/24`): logo ·
    ticker · name · value; Buy=green/Sell=red chips (Senate/House trades tables). →
    "What's moving" + insider/congress tape (data: `sources/finra`+`sec`, OpenInsider
    endpoints).
12. **Price header + sparkline/timeframe chart** — *Stock Taper stock page* + *Rallies
    research*: big mono price, brick/forest change, timeframe pills (1D…All),
    Line/Candle toggle. → Mover cards already have sparklines; add timeframe pills.
13. **Financial table with ▲/▼ per cell** — *Stock Taper premium* (`gallery/06`):
    every cell carries its own trend arrow; Quarterly/Annually toggle. → Strategy stats
    tables.
14. **Peer strip** — *Rallies research*: horizontal scroll of related tickers with live
    % chips, each clickable. → Mover card → related names.
15. **Accordion trend analysis** — *Stock Taper free* (`features/16`): Executive Summary
    (Strengths/Risks/Outlook) · per-statement trends · Competitive Position — one
    accordion per question. → "The lab explained" section.
16. **Market tape** — *Intel Desk* + our Agent Terminal already has one: thin top strip,
    mono, green/crimson %. Keep; add `RISK READ` summary chip (Intel Desk: "vol bleeding
    · credit bid").
17. **Escalation gauges** — *Intel Desk GAUGES* (`inteldesk/33`): a labeled stage ladder
    (`DIPLOMATIC → ESCALATION → KINETIC → FULL CONFLICT`). → Our macro nowcast as a
    recession-stage ladder gauge.

### D. Feeds, filters & workflow

18. **Filtered activity feed** — *Stock Taper Watchlist Activity* (tabs: All · Congress ·
    Ratings · Earnings · Insider) + *Rallies Feed*. → Agent desk event feed with the
    same filter chips (fills · bets · resolves · alerts).
19. **"Catch me up" return-visit digest** — *Intel Desk* (`inteldesk/32`): "away 3h 6m —
    27 new · 9 high priority" + active regions + market movers, `SKIP TO LIVE FEED`. →
    Dashboard modal built from the run-to-run diff of digests.
20. **Onboarding lane picker** — *Intel Desk* (`inteldesk/03`): pick Oil/LNG/Macro… →
    loads a preset desk (watchlist, alerts, brief). → "Pick your desk" presets
    (sports · markets · stocks · macro) toggling dashboard section order.
21. **Suggested-question chips** — *Rallies Today/research*: contextual questions
    ("Is my GOOGL position too large?") that deep-link into analysis. → Static
    plain-English question links that jump to the relevant dashboard section.
22. **Armable alert packs** — *Intel Desk TOOLS* (`inteldesk/11`): one-tap keyword packs
    (`Iran Escalation · Hormuz Shipping`) that arm alerts + filter feeds. → `alerts/`
    presets (squeeze watch · macro turn · line-move).
23. **Density / focus modes** — *Intel Desk*: Comfortable/Standard/Dense + Focus mode.
    → Terminal nicety, low priority.

### E. Structure & IA

24. **Research-page sub-tab IA** — *Rallies* `/research/{T}`: Chart · Financials ·
    Funds · Politicians · Insiders · Analyst, each its own route. → If we ever ship
    per-entity pages; for now maps to per-section anchors.
25. **Feature-per-surface IA** — *Rallies*: Today · Agents · Chat · Arena · Discover ·
    Feed. Our equivalent nav: **Desk (agent) · Movers · Odds · Edges · Arena · Scorecard
    · Macro · Watch**.
26. **Discover catalogs** — *Rallies*: funds (13F) · politicians · **named themes**
    ("AI Infrastructure", "Retail Revenge") with constituents + performance. → Our
    signals could publish theme baskets (squeeze basket, momentum basket) — honest,
    already-computed composites.
27. **Directory + alphabet pager** — *Stock Taper* `/stocks/A-Z`: SEO-shaped entity
    directories. Low priority (we're not an SEO site).
28. **Article→entity autolinking** — *Stock Taper blog*: every company mention links to
    its entity page; "Related articles" cards; market-snapshot widget embedded at the
    bottom of articles. → `pipeline/research` digests should autolink tickers to
    dashboard anchors.
29. **Compare tool with per-dimension verdicts** — *Stock Taper* (`features/15`):
    A-vs-B with "Risk: A lower · Valuation: A better value" reasoned paragraphs. → Our
    strategy-vs-strategy compare (arena already has the data).
30. **Earnings-call summary archive** — *Stock Taper* `/earningsCallSummary/{T}` per
    quarter. → Not ours to build; noted for completeness.

### F. Agent-surface patterns (from LangAlpha + openprophet + Rallies)

31. **Streaming agent telemetry** — *LangAlpha*: live tool-call/subagent status, plan
    approval cards, per-turn **sources/provenance panel**. → Firm Chat in the Agent
    Terminal evolves from static messages to a real event log with provenance.
32. **Visible multi-step plan in chat answers** — *Rallies Chat*: "Building a plan · 4
    checks · Checking price moves…" then the answer + follow-ups + "AI can make
    mistakes." → The research_log / analyst answer rendering.
33. **Editable desk notes** — *Intel Desk*: `Thesis Question ✎ · Three Tape-Changers ·
    Execution Rules` pinned on the desk. → Static rendering of the agent's current
    mandate + rules (from our Mandate config when built).
34. **Phased heartbeat status** — *openprophet*: pre-market/market-open/closed cadence
    shown on the desk ("next beat in 120s"). → Terminal header: last run / next run.
35. **Fail-closed status pill** — *openprophet*: order tools blocked when the decision
    service is unreachable. → Terminal risk row: "execution gate: ARMED/FAIL-CLOSED".

---

## Part 3 — Our site, page by page (composition)

**`index.html` — the research dashboard (Skin A, cream almanac).**
Masthead (mono logo + "▸ Live Agent Terminal" link + updated-ago clock) → sticky section
nav → sections, each = eyebrow tag + uppercase H3 + mascot + white cards:
1. **What's moving** — mover cards (sparkline + timeframe pills #12, peer strip #14,
   trust badge #2) + market-snapshot tables (#11).
2. **Live odds** — Kalshi/Polymarket side-by-side; each pick an **evidence-thesis card**
   (#1) with confidence dots + claim-tape drawer (#3).
3. **Edge research** — ACT/VERIFY/PRICE/FADE buckets (#9); per-edge "going well /
   concerning" pair (#4).
4. **Strategy arena** — Engo-style board (#8): equity curves + benchmark line + gate
   stats line; per-strategy verdict modal (#5); compare (#29).
5. **Agent desk teaser** — book stat + blotter tail → links to terminal.
6. **Macro** — recession nowcast as an escalation-ladder gauge (#17).
7. **Scorecard teaser** — Brier + hit/miss chips → `scorecard.html`.
8. **Media watch / voices** — leaderboard with per-voice trust badges (#2).
Mascot cast: 🛰️ agent · 🦅 edge scanner · ⚖️ arena · 🎯 odds · 📡 alerts · 🏛️ congress.

**`agent.html` — the Agent Terminal (Skin B, ops console).**
Keep dark; adopt Intel-Desk mechanics: market tape + RISK READ chip (#16), heartbeat
status (#34), fail-closed pill (#35), desk-notes card (#33), positions heatmap (existing)
with **trust badges** (#2) opening **claim-tape drawers** (#3), filtered event feed
(#18), catch-me-up modal (#19).

**`scorecard.html` — NEW (Skin B or A).**
The Intel-Desk scorecard verbatim in structure (#7): Brier · hit rate · calibration gate
· miss ledger · open horizons under audit. Powered by `calibration_log/` + `forwardtest/`.

**Everything stays:** single-file no-build HTML, content never JS-gated, reduced-motion,
plain-English question-led sections, "not financial advice" on every page.

## Part 4 — Extraction priorities (when the build pass runs)

1. Skin A reskin (tokens + eyebrow/H3 system + white-card layout) — biggest visible win.
2. Scorecard page (#7) — biggest honesty win, data already exists.
3. Evidence-thesis card (#1) + trust badge (#2) + claim-tape drawer (#3) on picks.
4. Arena board with benchmark line + gate-stats line (#8) + buckets (#9).
5. Terminal upgrades (#16-19, #33-35) + mascots + the rest.
