# Stock Taper — complete feature & interaction teardown

*Every feature, button, and cross-link on stocktaper.com, mapped from the inside. I
signed into the live free-trial account (magic-link auth) and walked the full
authenticated surface. Reference images in `./features/`; the design language itself is
in `DESIGNS.md`. 2026-07-03.*

---

## 0. Access model (free vs. trial vs. premium)

| Tier | Reaches |
|---|---|
| **Public / logged-out** | Home, `/stock/{T}` (free deep-dive), directories (`/stocks`,`/etfs`,`/institutions`,`/analysts`,`/congress`), `/earnings-calendar`, `/earningsCallSummary/{T}`, `/blog`, `/stockPremium/{T}` (viewable!), `/about`,`/pricing`. |
| **Gated → `/pricing`** | `/compare` (head-to-head), `/dashboard` (redirects to `/auth/login?next=/dashboard`). |
| **Logged-in (trial)** | `/dashboard`, `/compare`, watchlist, alerts, Opportunity Radar, Sector Pulse; **`/stock/{T}` auto-redirects to `/stockPremium/{T}`** so premium users always get the richer page. |

Auth is **Supabase**: Google OAuth · **email magic-link (PKCE)** · password. The magic-link
email is itself on-brand (cream `#FBF7EB`, IBM Plex Mono, a 6-digit code + "SIGN IN ON
THE WEB" button). `ref: features/00-login-gate.png`.

---

## 1. The dashboard (`features/02-dashboard.png`) — the logged-in home

A single scroll with these panels:

- **Watchlist** — up to 20 stocks; `+ Add a Stock` opens an inline ticker search
  (`features/06-watchlist-add-modal.png`).
- **Watchlist Activity** — a unified event feed with filter tabs: **All · Congress ·
  Ratings · Earnings · Insider**. (Aggregates the alert types the watchlist watches.)
- **Opportunity Radar** — the flagship "RADAR" feature; a carousel of evidence-backed
  investment *themes* (see §2).
- **Sector Pulse** — 12 sectors (Technology, Energy, Financial Services, Real Estate,
  Healthcare, Basic Materials, …) each with a 2026 outlook that expands (§3).
- **Comparison History** + **Most Popular Comparisons** — deep-links into `/compare?a=X&b=Y`.
- **Most Popular Stocks** — deep-links into `/stockPremium/{T}`.
- **Congress Tracker** — followed politicians' latest trades.
- Account controls: `Manage Account` (Stripe billing portal), `Log Out`.

## 2. Opportunity Radar — the standout (`features/03-opportunity-radar-theme.png`)

Each theme (e.g. *"Nuclear Renaissance & SMR Commercialization"*, *"Agentic AI & The
Software ROI Shift"*, *"Defense Tech & The Security Supercycle"*) expands **in place** to
a fully-structured thesis:

- **Ticker chips** (CCJ · GEV · SMR · OKLO)
- **WHY NOW** — the catalyst rationale
- **EVIDENCE** — each claim followed by a **cited source** ("U.S. Congressional records,
  2025"; "Uranium spot market data, Q4 2025")
- **WATCH FOR ↑** — bullish confirmations to monitor
- **RED FLAGS ↓** — what would break the thesis
- **STOCKS LIKELY TO BENEFIT** — each ticker + one-line thesis + a **Confidence: ●●●●○**
  (filled-dot) rating

> This is the single most lab-relevant thing on the site. It's *exactly* the shape of our
> `predictions.py` prediction-evidence contract — probability/confidence + driver list +
> caveat — but presented beautifully, with **red flags and cited evidence baked in**.
> Copy this structure for our Edge-research and forecast cards.

## 3. Sector Pulse (`features/07-sector-pulse-expanded.png`)

Same accordion pattern, one row per sector: a plain-English **2026 structural outlook**
("Technology… transitioning from an AI hardware boom to a structural infrastructure
phase… infrastructure and memory suppliers best positioned, mega-cap consumer tech faces
regulatory and valuation headwinds"), expanding to positioning + stocks to watch.

## 4. Stock deep-dive — free vs. premium

**Free `/stock/{T}`** (`../02-stock-detail-nvda.png`): price header (big mono price +
brick-red/green change), then stacked sections: Income/Balance/Cash-Flow statements ·
Revenue by Products/Geography · Earnings Call Summary · 5-Year Trend Analysis · About ·
Compensation · Split Record · ETFs Holding This Stock · Ratings Snapshot · Analyst Grades
· Price Target · Institutional Ownership. Buttons: `View Stats →`, AI-analysis tabs
(*Executive Summary · Income Statement Trends · Balance Sheet Health · Cash Flow Analysis
· Competitive Position · Innovation & R&D*), `What Does This Mean?` metric explainers,
`Add To Watchlist`, plus per-section `View All …`.

**Premium `/stockPremium/{T}`** (`../15-stock-premium-aapl.png`, `features/05-premium-nvda-full.png`)
adds the **DECODED** layer — every financial statement carries an AI-written
plain-English pair:

- **What's going well?** — the positives, in one sentence
- **What's concerning?** — and honestly caveated (real quote: *"A big chunk of this
  quarter's profit came from investment gains, which may not repeat…"* — it flags
  non-recurring items).

Interactive chart controls: timeframe **1D · 1W · 1M · 3M · 6M · YTD · 1YR · 5YR · 10YR ·
All**, **Toggle splits overlay**, **Toggle dividends overlay**, **Quarterly / Annually**
toggle. Financial tables show a **▲/▼ trend arrow per cell**. Peer strip auto-links to
other `/stockPremium/{T}` pages and to `/compare?a=THIS&b=PEER`.

## 5. Head-to-head Compare (`features/04-compare-tool.png`)

`/compare?a=AAPL&b=NVDA` (premium). Sections: **Financials & Popularity · Key Metrics ·
Fundamentals Analysis**, with an AI-generated verdict. Two ticker pickers + `Compare
Stocks`. This is the "1 v 1" scale-mascot feature.

## 6. Directories & the SEO surface

`/stocks/{A-Z}`, `/etfs/{A-Z}`, `/institutions/{A-Z}`, `/analysts/{A-Z}`, `/congress`
(+ member pages), `/earnings-calendar`, and **`/earningsCallSummary/{T}`** — a per-stock,
per-quarter archive of AI earnings-call summaries (`features/08-earnings-call-summary.png`;
~1,000 such pages in the sitemap). Every directory uses the same alphabet-pager template.

## 7. Search (`features/01-search-autocomplete.png`)

The hero/nav search fires a **live autocomplete** on keystroke — dropdown of logo +
ticker + company name, routing to the stock page. Present on every page.

---

## 8. The article cross-linking model (the growth loop you asked about)

Direction matters — it's **one-way and deliberate**:

1. **Article → stock pages (heavy).** In `/blog/{slug}` bodies, *every* company mention is
   an inline hyperlink to its `/stock/{TICKER}` deep-dive. The NVDA article alone carries
   **78 stock links** ("Nvidia (NVDA)", "Microsoft", "Intel", "AMD" → their pages). This
   is the SEO/engagement engine: long ticker-rich essays that funnel readers into the
   product's core pages.
2. **Article → article.** Each article ends with a **"Related Articles"** block of cards,
   tagged by category chip (NEWS · TECHNOLOGY). Articles follow a fixed template: *Bull
   Case → Bear Case → How It Compares to Peers → Key Takeaways (Buy/Hold/Avoid).*
3. **Article → global widgets.** The **Market Snapshot** tables (Largest Market Cap,
   Recent Senate/House Trades) render at the bottom of articles too — cross-selling the
   data product from editorial pages.
4. **Stock page → article? No.** Stock/premium pages **do not** link back to the blog.
   The funnel runs article → stock → compare/watchlist, never the reverse.
5. **Home → articles.** The homepage "Latest Articles" grid is the other entry point.

**Takeaway for us:** if we ever publish research write-ups, auto-link every ticker in the
prose to its dashboard entity, end with related-research cards, and embed the live
"what's moving" widget — a clean, honest version of the same loop (and it doubles as
internal navigation).

---

## 8b. Detail-page templates & deeper interactions (second pass)

Captured on a follow-up sweep to close gaps:

- **Institution detail** (`/institutionDetail/{cik}`, `features/09-institution-detail.png`)
  — institution name + a single **"Holdings (Top positions)"** table. ~19 in the map.
- **Analyst detail** (`/analystDetail/{slug}`, `features/10-analyst-detail.png`) —
  **"Stock Ratings by {analyst}"** + a **STOCKS RATED** list. ~7 in the map.
- **ETF detail** (`/etf/{TICKER}`, `features/11-etf-detail.png`) — About + **Holdings
  (Top 20)** + **Sector Holdings** + **Asset Allocation by Region** (2 donut charts).
- **"View Breakdown" modal** (`features/12-view-breakdown.png`) — on each premium
  financial statement. Opens **"{Statement} Analysis — AI-generated"** with a **verdict
  header** (*Overall: Excellent · Trend: Improving · Bottom Line: Strong*), a **Last Year
  / Last Quarter** toggle, and plain-English Q&A: *"What's the profit per dollar of
  revenue? 27 cents for every dollar of sales" · "Is share dilution affecting
  shareholders? Minimal – share count down ~2%…"*. This is the deepest expression of the
  DECODED feature.
- **Congress follow** (`features/13-congress-follow-loggedin.png`,
  `14-congress-alert-set.png`) — a member page (logged-in) has **"Alert Me On Future
  Trades"**; clicking flips it to **"Tracking"** and adds them to the dashboard Congress
  Tracker (toggles back off on a second click). Trade history is paginated (1–7).
- **Compare — run state + AI verdict** (`features/15-compare-run-verdict.png`) — after
  `Compare Stocks`, it renders **per-dimension winners with rationale**: *Risk Comparison
  → "AAPL Lower Risk"*, *Valuation Perspective → "AAPL Better Value"* (P/E 36.6, P/B 27.9),
  each a balanced paragraph naming **both** sides' risks. Carries an explicit **"not
  financial advice"** disclaimer. 17 charts.

**Now captured (second pass):**
- **Free `/stock/{T}` AI-analysis tabs** (`features/16-free-ai-analysis-tabs.png`) — the
  free tier's **"5-Year Trend Analysis"**: an accordion of *Executive Summary · Income
  Statement Trends · Balance Sheet Health · Cash Flow Analysis · Competitive Position ·
  Innovation & R&D*. The Executive Summary is a **Strengths / Risks / Outlook** narrative,
  honestly balanced (e.g. flags concentration, cyclicality, and *"current margins may be
  above long-term sustainable levels"*). This is the free-tier counterpart to the premium
  per-statement "What's going well / concerning" Q&A. (Requires logged-out; logged-in
  accounts auto-redirect `/stock` → `/stockPremium`.)
- **"▶ Watch Me" video modal** (`features/17-video-modal.png`) — homepage hero trigger
  opens a centered **Wistia player** overlay (the 65s brand film; the video file itself is
  also saved at `../assets/promo-video.mp4` + poster + 5 keyframes).

**Left untouched:** `Manage Account` → a Stripe billing portal.

## 9. Full interaction/button inventory (for parity)

- **Global:** logo→home, `Pricing`, `Sign Up`, `Log In` / (auth) `Menu` drawer,
  `Manage Account`, `Log Out`, `Contact`; live search autocomplete; footer 4-col.
- **Home:** search, "▶ Watch Me" video modal (Wistia, `../assets/promo-video.mp4`),
  feature carousel dots (7), `Start 7-Day Free Trial`, app-store badges.
- **Pricing:** Monthly `$7.99` / Annual `$63 ($5.25/mo, SAVE 34%)` toggle, `Start 7-Day
  Free Trial`, `View AAPL Demo`.
- **Stock/premium:** chart timeframes (10), splits/dividends overlays, Quarterly/Annually,
  `View Breakdown`, `Add To Watchlist`, AI-analysis tabs (6), `What Does This Mean?`,
  `View All Recent Insider Trades / Holders / Grades / Splits / ETFs`, `← Prev / Next →`
  (earnings-call pager), peer→compare links.
- **Dashboard:** `+ Add a Stock`, Watchlist-Activity filters (All/Congress/Ratings/
  Earnings/Insider), Radar carousel `← →` + expand, Sector-Pulse expanders,
  popular-comparison / popular-stock deep links.
- **Compare:** two ticker pickers, `Compare Stocks`, section `Prev/Next`.
- **Directories:** A–Z alphabet pager.

---

*Reference only. Content & assets © Stock Taper — captured for private design/feature
study, not redistribution. Not financial advice.*
