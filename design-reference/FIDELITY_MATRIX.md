# Feature fidelity matrix — Codex round 4 (2026-07-05)

*Codex's exhaustive cross-check of PLATFORM_PLAN.md against every reference
feature inventory (Stock Taper, Rallies authed, Intel Desk, Engo, Sakura).
IMPORTANT correction: Codex audited the PLAN TEXT only — several PARTIAL/
MISSING rows are ALREADY BUILT in code (P4/P5): confidence dots, catch-me-up,
fail-closed pill, heartbeat, receipt chips, peer strip, mascots, question
chips. The platform pages inherit them. Resolutions in PLATFORM_PLAN §12.*

(A) REFERENCE FEATURE | SOURCE | PLAN STATUS (COVERED@section / PARTIAL / MISSING / CUT-justified?) | NOTE

| REFERENCE FEATURE | SOURCE | PLAN STATUS | NOTE |
|---|---|---|---|
| Recommendation / ratings scale | Rallies | COVERED@§1/P6b | Strong Buy→Avoid mapped to deterministic score. |
| Analyst consensus, avg PT, distribution | Rallies/Auth captures | PARTIAL | Plan has expert leaderboard, not full analyst distribution UI. |
| Price header + day change | Stock Taper/Rallies | COVERED@P6b | Implied recommendation pages. |
| Chart with timeframe pills | Stock Taper/Rallies | PARTIAL | Mentioned via references, not explicit in build order. |
| Line/candle toggle, indicators, compare chart | Rallies | MISSING | Compare page exists, chart controls not specified. |
| Splits/dividend overlays | Stock Taper | PARTIAL | Corporate actions covered in contract, UI overlay missing. |
| Quarterly/annual financial toggle | Stock Taper/Rallies | PARTIAL | Financial frame planned; toggle not explicit. |
| Financial statement tables | Stock Taper/Rallies | PARTIAL (P6b fidelity pass) | The component-evidence table (graded score+confidence per driver) is built; full income/balance/cash-flow statements need a fundamentals data feed — deferred, rendered honestly as n/a until wired, never faked. |
| Per-cell ▲/▼ financial arrows | Stock Taper/Auth captures | COVERED@§1 | Explicit. |
| Going-well / concerning AI pairs | Stock Taper | COVERED@§1/P6b | Core borrowed structure. |
| “What this implies” plain-English debt/metric explainers | Stock Taper/Auth captures | PARTIAL | Plain-English explanation planned, specific explainer affordance not. |
| View Breakdown modal | Stock Taper/Site blueprint | PARTIAL | Component noted in blueprint, not P6 build order. |
| AI-analysis tabs / accordions | Stock Taper | PARTIAL | Research pages use sections, not tabbed free-tier IA. |
| Earnings call summary archive | Stock Taper | CUT-justified? | Not investment-platform launch core. |
| Earnings calendar | Stock Taper | PARTIAL | Earnings proximity watcher planned, not calendar surface. |
| Revenue by product/geography | Stock Taper | MISSING | Not in plan. |
| CEO compensation | Stock Taper/Auth captures | MISSING | Not in plan. |
| Split record | Stock Taper/Auth captures | PARTIAL | Corporate actions in contract, no page module. |
| ETFs holding this stock | Stock Taper | PARTIAL | ETF overlap planned for portfolio, not stock page. |
| Institutional sentiment w/ named sources | Stock Taper/Auth captures | COVERED@§1 | Named news/expert sources. |
| 13F hedge-fund holders | Rallies/Stock Taper | PARTIAL | Deferred/stale data noted; Discover/funds not launch-core. |
| Politician trades per ticker | Rallies/Stock Taper | CUT-justified? | Explicitly deferred in §9 free-data honesty. |
| Insider trades per ticker | Rallies/Stock Taper | PARTIAL | Insider-cluster watcher planned; full tab missing. |
| Analyst detail pages | Stock Taper | MISSING | No directory/detail page plan. |
| Institution detail pages | Stock Taper | MISSING | No directory/detail page plan. |
| ETF detail: holdings, sectors, region allocation | Stock Taper | PARTIAL | ETF overlap/expense/drawdown planned; region donuts missing. |
| Mutual fund → ETF twin mapping | Plan/ref-adjacent | COVERED@§3/P6e | Plan feature, not a major reference feature. |
| HYSA/cash benchmark and rate context | Plan/ref-adjacent | COVERED@§3 | Unique extension. |
| Search autocomplete / all-symbol search | Stock Taper/Rallies | COVERED@§2b/P6b | All ~11k searchable. |
| A-Z directories | Stock Taper | CUT-justified? | SEO surface, low platform value. |
| Compare tool, two tickers | Stock Taper/Rallies | COVERED@P6b | Explicit. |
| Compare per-dimension verdicts | Stock Taper | COVERED@P6b | Explicit. |
| Watchlist | Stock Taper/Rallies | COVERED@§2b/P6b | Watchlisting promotes to full tier. |
| Add-to-watchlist button | Stock Taper/Rallies | PARTIAL | Behavior exists; button placement not explicit. |
| Watchlist activity filters | Stock Taper | PARTIAL | Site feed planned, filter chips not explicit. |
| Congress follow / alert toggle | Stock Taper | CUT-justified? | Congress data deferred. |
| Opportunity Radar thesis card | Stock Taper | COVERED@§1/P6b | Evidence-backed recommendation cards. |
| Ticker chips in thesis cards | Stock Taper | PARTIAL | Not explicitly specified. |
| Evidence citations per claim | Stock Taper/Intel Desk | COVERED@§1/§8 | Receipts/audit hash/sources. |
| Watch-for / red-flags blocks | Stock Taper | PARTIAL | Drivers+caveats planned; exact blocks not stated. |
| Confidence dots | Stock Taper | PARTIAL | Replaced by four dials. |
| Sector Pulse accordion | Stock Taper | PARTIAL | Macro regime and baskets planned; sector accordion missing. |
| Market snapshot tables | Stock Taper | PARTIAL | Today verdicts/home planned, exact table absent. |
| Article→stock autolinking | Stock Taper | PARTIAL | P6e docs/research writeups mention later only via blueprint. |
| Related articles/cards | Stock Taper | MISSING | No editorial surface plan. |
| Embedded widgets in articles | Stock Taper | MISSING | No article product loop. |
| Pricing/free trial/auth/billing | Stock Taper/Rallies | CUT-justified? | Personal public-code/private-data platform, not SaaS. |
| Magic-link auth | Stock Taper | CUT-justified? | Local-only private data decision. |
| Manage account/logout | Stock Taper/Rallies | CUT-justified? | No hosted account model. |
| Promo video modal | Stock Taper | MISSING | Landing could use product screenshots, not video. |
| Feature carousel dots | Stock Taper | MISSING | Marketing detail. |
| App-store/mobile app CTA | Rallies/Stock Taper | CUT-justified? | Web app only. |
| Global nav / feature-per-surface IA | Rallies | COVERED@P6b/P6c/P6d | Home, portfolio, arena, watchers, scorecard. |
| Today feed layout | Rallies/Auth captures | COVERED@P6b/P6d | Materiality/feed/freshness. |
| Portfolio home/net worth hub | Rallies | PARTIAL | Portfolio evaluation exists; net-worth/account aggregation cut. |
| Connected accounts strip | Rallies | CUT-justified? | Privacy/local-only, no broker linking. |
| Hide values toggle | Rallies | MISSING | Useful for portfolio page. |
| Portfolio/Markets/Watchlist tabs | Rallies | PARTIAL | Equivalent surfaces planned, tab IA not explicit. |
| Allocation donut | Rallies/Auth captures | PARTIAL | Allocation planned, visual not explicit. |
| Add physical asset | Rallies | CUT-justified? | Outside stocks/ETFs/HYSA launch scope. |
| Add crypto wallet | Rallies | CUT-justified? | Outside launch scope. |
| AI Digest | Rallies | PARTIAL | AI opinions and materiality feed, not digest module. |
| Market rails: indices/trending/gainers/losers/popular | Rallies | PARTIAL | Trending/full tier exists, exact rails missing. |
| Suggested AI question chips | Rallies | PARTIAL | Chat chips referenced in plan refs, not build order. |
| Chat surface | Rallies | PARTIAL | AI opinions planned; interactive chat not launch-core. |
| Ask/Dashboards chat modes | Rallies | MISSING | No chat app mode plan. |
| Visible multi-step agent plan | Rallies/LangAlpha | PARTIAL | Watcher workflow deterministic, no chat plan UI. |
| Cited chat answers | Rallies | PARTIAL | Receipts cover pages, not chat. |
| Follow-up suggestions | Rallies | MISSING | No chat follow-up UX. |
| Voice input | Rallies | CUT-justified? | Not needed. |
| Intelligence selector | Rallies | CUT-justified? | Two AI opinions, no runtime model selector. |
| Custom instructions | Rallies | PARTIAL | Profile goals/risk/horizon cover core personalization. |
| Searchable chat history | Rallies | MISSING | No chat history surface. |
| Agent builder | Rallies | COVERED@§5/P6d | “Describe what to watch” templates. |
| Agent template gallery | Rallies/Auth captures | COVERED@§5/P6d | Earnings/squeeze/insider/verdict templates. |
| 24/7 watcher alerts | Rallies | COVERED@§5/P6d | Telegram/Discord/site feed. |
| Feed / notifications stream | Rallies | COVERED@§5/P6d | Alerts channel + site feed. |
| Arena model portfolios | Rallies/Auth captures | COVERED@§4/P6c | Claude + Codex books. |
| Arena position-level book table | Rallies | COVERED@§4/P6c | Exact columns specified. |
| Total P&L + available cash | Rallies/Auth captures | COVERED@§4/P6c | Explicit. |
| Multiple model competitors GPT/Grok/Gemini/Claude | Rallies | PARTIAL | Plan uses Claude + Codex only. |
| Paper/demo transparency | Rallies/Engo | COVERED@§4/§9 | Incubating/paper/audit rules. |
| SPY benchmark line/row | Engo/Site blueprint | COVERED@§4/P6c | SPY and HYSA always on board. |
| Arena gate stats / 7-day publish gate | Engo | COVERED@§4/§9 | Explicit. |
| Discover funds catalog | Rallies | CUT-justified? | 13F deferred. |
| Discover politicians catalog | Rallies | CUT-justified? | Politician data deferred. |
| Discover theme baskets | Rallies | PARTIAL | Theme/signal baskets mentioned, not launch-core. |
| Research sub-tabs Chart/Financials/Funds/Politicians/Insiders/Analyst | Rallies | PARTIAL | Plan borrows IA but launch compresses/defers some tabs. |
| Peer strip | Rallies/Stock Taper | PARTIAL | Referenced, not build-order requirement. |
| Key metrics table | Rallies/Stock Taper | COVERED@§1/P6b | Component grades/stats. |
| AI Q&A on ticker page | Rallies | PARTIAL | Claude/Codex theses, not Q&A. |
| Invest button | Rallies | CUT-justified? | No brokerage/execution. |
| Trust badge/readout | Intel Desk/Site blueprint | COVERED@§1/§8 | Sources + freshness. |
| Claim-tape receipts drawer | Intel Desk | PARTIAL | Receipts/audit hash planned; drawer UI not explicit. |
| Source reliability tiers A/B/C/D | Intel Desk | PARTIAL | Expert Brier weighting present; connector tiers not explicit except health. |
| Public Brier scorecard | Intel Desk | COVERED@§8/P6d | AI opinions scored publicly. |
| Miss ledger | Intel Desk | COVERED@§8 | Pinned. |
| Calibration gate/open horizons | Intel Desk | COVERED@§8/§9 | Brier/calibration target. |
| ACT/VERIFY/PRICE/FADE buckets | Intel Desk | MISSING | Not in P6 plan. |
| Catch-me-up digest | Intel Desk | PARTIAL | Materiality feed covers “what changed,” not return modal. |
| Onboarding lane picker | Intel Desk | CUT-justified? | Personal investment tool, not multi-desk launch. |
| Armable alert packs | Intel Desk | COVERED@§5/P6d | Watcher templates. |
| Density/focus modes | Intel Desk | MISSING | Low priority terminal nicety. |
| Market tape + risk read chip | Intel Desk | PARTIAL | Freshness/macro planned; terminal tape not explicit. |
| Escalation/recession ladder gauge | Intel Desk | PARTIAL | Macro regime planned; ladder UI not explicit. |
| Streaming agent telemetry/provenance panel | LangAlpha | PARTIAL | Codex automation logged; live telemetry not explicit. |
| Editable desk notes / mandate card | Intel Desk | PARTIAL | Arena mandates exist; editable UI missing. |
| Phased heartbeat / next beat | openprophet | PARTIAL | Updated-ago clock planned; next-run status not explicit. |
| Fail-closed status pill | openprophet | PARTIAL | Gates planned; explicit pill missing. |
| Stock Taper cream skin / IBM Plex Mono / cards / eyebrow tags | Stock Taper/Site blueprint | COVERED@P6b | Adopted as skin. |
| Mascots per panel | Stock Taper/Site blueprint | PARTIAL | In blueprint, not PLATFORM_PLAN build order. |
| Ops-console skin for terminal/scorecard | Intel Desk | PARTIAL | Terminal/scorecard not front-and-center in P6 plan. |
| Landing canvas particles | Sakura | CUT-justified? | §10 says landing only; app restrained. |
| Film grain overlay | Sakura | PARTIAL | Allowed lightly on app/landing; not build-critical. |
| Editorial serif landing hero | Sakura | COVERED@§10 | Landing only. |
| Extreme tracked eyebrows | Sakura | COVERED@§10 | Landing-only styling. |
| Vertical text accents | Sakura | CUT-justified? | §10 cuts vertical rails in-app; landing only optional. |
| Backdrop-blur nav / printed imagery | Sakura | PARTIAL | Landing quality note, not product plan. |
| Reduced-motion support | Sakura/Site blueprint | COVERED@§10 | Explicit. |
| Landing perf budgets | Sakura/§10 | COVERED@§10 | JS/asset/CLS budgets explicit. |

(B) TOP 5 MISSING/PARTIAL worth adding

| FEATURE | EFFORT | WHY |
|---|---:|---|
| Explicit ticker page chart controls: timeframe, line/candle, splits/dividend overlays | M | High user expectation; references both do it. |
| Source reliability tiers + receipts drawer UI | M | Makes “receipts” tangible, not just a promise. |
| Hide values toggle + portfolio privacy affordance | S | Fits private local portfolio; easy trust win. |
| Analyst consensus distribution + avg PT module | M | Central Rallies feature; complements recommendation card. |
| Return-visit “catch me up / what changed” digest | M | Strongly aligned with materiality feed and daily operator workflow. |

(C) TOP 3 plan features with NO reference precedent

| UNIQUE BET | WORTH RISK? | NOTE |
|---|---|---|
| Regret audit vs SPY/HYSA/equal-weight/do-nothing | Yes | Best differentiator; turns recommendations into accountable outcomes. |
| Decision journal scored later | Yes | Strong operator loop; keep private/local. |
| Decision friction detector | Yes | Practical and rare: separates “good asset” from “good action now.” |

(D) max 5 improvement suggestions not yet in the plan

1. Add a privacy toggle: `Hide values` for portfolio and arena-notional views.
2. Make receipts clickable: trust badge opens source/timeline/contradiction drawer.
3. Add analyst consensus distribution beside the deterministic verdict, clearly labeled as external opinion.
4. Add a compact “Changed since last visit” digest fed by the materiality ledger.
5. Specify ticker chart controls in P6b, including split/dividend markers from the corporate-actions contract.

---

## (E) Final fidelity pass — CLOSED (2026-07-11, P6e-3)

Codex re-audited the BUILT pages against the authed captures. Outcome:
- **Research sub-tab IA on ticker pages** (High) — CLOSED: a Rallies-style tab
  row (Chart / Verdict / Evidence / Analyst / News / Peers) anchor-links the
  real sections; structure without fabricated data; reduced-motion safe.
- **Analyst ratings-scale scaffold** (Medium) — CLOSED: the three slots
  (consensus / avg price target / distribution) render as honest n/a offline,
  still marked EXTERNAL OPINION; a distribution slot joins the wired branch.
- **Net-worth home shape on the portfolio page** (Medium) — CLOSED: a
  book-value hero (real dollars only — weights-only books say n/a, hide-values
  blurs it) + an allocation strip with legend, live on edit.
- **Suggested-question chips** — REFUTED: already on the home (`qchips`);
  the audit excerpt had elided them.
- **Contradictions on screen** — REFUTED: the receipts drawer renders
  disagreeing evidence whenever components actually disagree (pinned in
  tests); the sampled artifact's components genuinely agreed that day.
- All suggestions in (D) are now shipped: hide-values (P6c), clickable
  receipts (P6b), analyst module (P6b/P6e), since-last-visit (P6d), chart
  markers (P6b).
