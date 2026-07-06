# Stock Taper — design reference & build guide

*The visual model for this project's site. Captured in full from
[stocktaper.com](https://www.stocktaper.com/) on 2026-07-03 — every public page
screenshotted, every brand asset downloaded, the promo video pulled, and the exact
design tokens read off the live DOM. This file is the single source of truth for **how
the site should look**; pair it with the honest-content plan in `agent-trader/`.*

> **The one-line read:** Stock Taper is a *warm, monospace, illustrated almanac* for
> stock research — cream paper background, IBM Plex Mono everywhere, heavy black
> headings, muted green/red, and a cast of hand-rendered animal/object mascots. It feels
> like a friendly financial zine, not a Bloomberg terminal. That warmth + the mascot
> system is what makes it distinctive and worth modeling.

---

## 0. Everything captured (file index)

**Full-page screenshots** (in this folder):

| File | Page | What to study |
|---|---|---|
| `01-home-full.png` | Home | The whole system: hero, feature carousel, mascot feature cards, blog grid, market-snapshot tables, footer |
| `02-stock-detail-nvda.png` | `/stock/NVDA` (free) | **The core product.** Price header + 15 stacked data sections, charts, tables |
| `03-pricing.png` | `/pricing` | Monthly/annual toggle, 5 mascot feature cards |
| `04-congress-list.png` | `/congress` | Politician index grid with avatars |
| `05-congress-detail-pelosi.png` | `/congress/nancypelosi` | Individual member trade history |
| `06-stocks-directory.png` | `/stocks/A` | A–Z ticker directory, alphabet pager |
| `07-institutions.png` | `/institutions/A` | Institutional-investor directory |
| `08-analysts.png` | `/analysts/A` | Analyst directory |
| `09-earnings-calendar.png` | `/earnings-calendar` | Weekly earnings grid |
| `10-etfs.png` | `/etfs/A` | ETF directory |
| `11-blog-list.png` | `/blog` | Article card grid |
| `12-blog-article.png` | `/blog/{slug}` | Long-form article layout |
| `13-about.png` | `/about` | Mission + product screenshots + founder story |
| `14-signup.png` | `/auth/signup` | Auth form styling |
| `15-stock-premium-aapl.png` | `/stockPremium/AAPL` | **The flagship premium deep-dive** — the richest view |
| `16-home-mobile.png` | Home @ 390px | Responsive behavior |

**Brand assets** (`./assets/`): `logo.avif`, `astro-hero.png`, `astro-pointing.avif`,
5 mascots (`mascot-falcon/pigeon/capitol/scale/radar.png`), 7 product shots
(`product-*.png`), app-store badges, `promo-video.mp4` (65s, compressed), 5
`video-frames/frame-*.png`, `promo-video-poster.webp`.

**Page copy** (raw markdown of every page) lives in the scratchpad
`st_pages/*.md` — reference for exact wording/voice.

**Deep design gallery** — 26 extra shots focused on the *look* (sector variety,
signature-component close-ups, blog templates, detail pages, mobile) live in
**`./gallery/`** with an index in `gallery/README.md`. This is the richest set for
studying the visual system.

**Feature teardown** — the complete authenticated feature/button/interaction inventory
(dashboard, Opportunity Radar, Sector Pulse, premium AI Q&A, compare tool, watchlist,
and the article cross-linking model) is in **`FEATURES.md`**, with reference images in
**`./features/`** (`00-login-gate` … `08-earnings-call-summary`). Read that for *what the
product does*; this file is for *how it looks*.

---

## 1. Design tokens (read off the live site — use these verbatim)

### Color

| Token | Value | Use |
|---|---|---|
| **Paper** (page bg) | `#FBF7EB` (rgb 251,247,235) | The whole background — warm cream, *not* white |
| **Card** | `#FFFFFF` | Panels, tables, cards sit on the cream |
| **Ink** | `#141414` (rgb 20,20,20) | Body text |
| **Heading ink** | `#393939` (rgb 57,57,57) | H1/H2 |
| **Price ink** | `#2B2B2B` (rgb 43,43,43) | Big numbers |
| **Up / positive** | `#2F7D31` (rgb 47,125,49) | Gains, "Purchase", positive % — a *muted forest green*, not neon |
| **Down / negative** | `#C6392C` (rgb 198,57,44) | Losses, "Sale", negative % — a *brick red*, not pure red |
| **Muted** | `#9E9E9E` (rgb 158,158,158) | Secondary text, labels |
| **Mid gray** | `~#8A8A8A` (oklch 0.556) | Meta text, timestamps |
| **Hairline** | `~#E5E5E5` (oklch 0.922) | Borders, separators |

The palette is deliberately **desaturated and warm** — the green and red are earthy, so
the page reads calm and editorial even when it's dense with numbers. This is the
opposite of the neon-on-black fintech cliché, and it's the single biggest reason the
site feels approachable.

### Type — the signature move

**One typeface, everywhere: `"IBM Plex Mono", monospace`.** Headings, body, tables,
buttons, prices — all monospace. That's what gives it the "typewriter almanac / honest
receipt" character.

| Element | Size | Weight | Notes |
|---|---|---|---|
| H1 | 36px | 700 | e.g. *"Look up a stock. Actually get it."* |
| H2 | 30px | 700 | Section titles |
| H3 | 20px | **900** | Feature titles — very heavy, often UPPERCASE |
| Body | 14px | 400 | |
| Button / nav | 14px | 600 | |
| Eyebrow tag | ~11–12px | 600–700 | UPPERCASE mini-label above H3 (`DECODED`, `ALERTS`, `CONGRESS`, `1 v 1`, `RADAR`) |

Monospace tabular figures are a *functional* win too: numbers line up in columns
without extra effort — perfect for financial tables.

### Reproduction starter (drop-in CSS variables)

```css
:root{
  --paper:#FBF7EB; --card:#FFFFFF; --ink:#141414; --head:#393939;
  --up:#2F7D31; --down:#C6392C; --muted:#9E9E9E; --hair:#E5E5E5;
  --mono:"IBM Plex Mono", ui-monospace, "SFMono-Regular", Consolas, monospace;
}
body{ background:var(--paper); color:var(--ink); font:14px/1.55 var(--mono); }
h1{ font:700 36px/1.1 var(--mono); color:var(--head); }
h2{ font:700 30px/1.15 var(--mono); color:var(--head); }
h3{ font:900 20px/1.2 var(--mono); text-transform:uppercase; }
.eyebrow{ font:700 11px/1 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.up{color:var(--up)} .down{color:var(--down)}
.card{ background:var(--card); border:1px solid var(--hair); border-radius:12px; }
```
Load IBM Plex Mono self-hosted or from Google Fonts (weights 400/600/700 + a 900 fallback; IBM Plex Mono tops out at 700, so the "900" H3 look is achieved with 700 + uppercase + tight tracking).

---

## 2. The mascot / illustration system — *the thing to copy*

Stock Taper's identity is a cast of **rendered characters, one per feature**. They're
warm, slightly retro, 3D-ish illustrations that turn abstract finance features into
friendly icons. This is what to emulate for the lab (see §6).

| Asset | Character | Represents | On page |
|---|---|---|---|
| `assets/astro-hero.png` / `astro-pointing.avif` | **Astronaut** | The brand mascot / "explore" | Hero + pricing |
| `assets/mascot-falcon.png` | **Falcon** | Deep-dive fundamentals (`DECODED`) — sharp-eyed | Home + pricing feature card |
| `assets/mascot-pigeon.png` | **Carrier pigeon** | Watchlist & alerts (`ALERTS`) — delivers messages | Feature card |
| `assets/mascot-capitol.png` | **Capitol building** | Congress trade alerts (`CONGRESS`) | Feature card |
| `assets/mascot-scale.png` | **Balance scale** | Head-to-head comparisons (`1 v 1`) | Feature card |
| `assets/mascot-radar.png` | **Radar dish** | Spot opportunities (`RADAR`) | Feature card |

Each **Premium Feature card** = eyebrow tag → heavy uppercase H3 → 2–3 bullet list →
the mascot illustration bottom-right. Simple, repeatable, and the illustrations do the
charm. (See `01-home-full.png` mid-page and `03-pricing.png`.)

The **logo** (`assets/logo.avif`) is a simple mark paired with "Stock Taper" set in the
same mono face.

---

## 3. Layout & component patterns

**Global shell**
- **Top nav** (sticky): logo left; `Pricing · Sign Up · Log In` right. Minimal.
- **Centered max-width container** (~1100–1200px), generous vertical rhythm.
- **Footer**: 4 columns — *Company* (About, Blog, Press, Contact, Support), *Legal*
  (Privacy, Terms), *Resources* (Stocks, ETFs, Institutions, Congress, Analysts,
  Earnings Calendar), *Get the app* (store badges) + `© 2026 Stock Taper`.

**Home page anatomy** (`01-home-full.png`, top→bottom)
1. **Hero** — two columns: left = H1 + sub + **stock search box** + "▶ Watch Me" video
   trigger + trial CTA + app badges; right = astronaut illustration.
2. **Feature carousel** — "See the full picture on any stock" + a 7-slide product-shot
   carousel with dot pagination (uses `product-*.png`).
3. **Premium Features** — 5 mascot cards (see §2).
4. **Latest Articles** — blog card grid (image + title + dek + "N min read · date").
5. **Market Snapshot** — three side-by-side tables: *Largest Market Cap* (logo · ticker
   · name · $mktcap), *Recent Senate Trades*, *Recent House Trades* (avatar · member ·
   Buy/Sell · logo · ticker · date). Buy=green, Sell=red.

**Stock detail** (`02-stock-detail-nvda.png` free, `15-stock-premium-aapl.png` premium)
— the product core. A **price header** (big mono price + brick-red/green change) then a
long stack of white card sections: *Income / Balance / Cash-Flow statements · Revenue by
Products · Revenue by Geography · Earnings Call Summary · 5-Year Trend Analysis · About ·
Compensation Summary · Split Record · ETFs Holding This Stock · Ratings Snapshot ·
Analyst Grades · Price Target · Institutional Ownership.* Heavy on charts (≈10 canvas +
28 SVG + 12 tables per page). The premium page is the same skeleton, richer.

**Directory pages** (`06`,`07`,`08`,`10`) — a shared template: title "X starting with A",
an **A–Z alphabet pager**, and a clean table/grid of entities with logos/avatars.

**Congress** (`04`,`05`) — index of members with circular avatars; detail page = a
member's trade history table.

**Earnings calendar** (`09`) — weekly grid, before/after-market grouping, EPS est vs
actual.

**Blog** (`11` list, `12` article) — editorial card grid → clean long-form article with
a hero image, generous measure, mono body.

**Pricing** (`03`) — "Choose Your Plan", **Monthly $7.99 / Annual $63 ($5.25/mo, SAVE
34%)** toggle, "EARLY ADOPTER PRICING", 7-day free-trial CTA, "View AAPL Demo" link,
then the 5 mascot feature cards. Reassurance line: *"Cancel before Day 8 and you won't
be charged."*

---

## 4. Voice & copy (part of the design)

Plain-English, anti-jargon, a little playful. Set headings in the mono face and keep the
sentences human:
- *"Look up a stock. Actually get it."*
- *"…arranged so the story is easy to read, even if you don't have a fancy finance degree."*
- *"No more tab-hopping between different sites."*
- Feature titles are punchy and imperative: *DEEP-DIVE THE FUNDAMENTALS*, *SPOT THE OPPORTUNITIES*.

This matches the lab's own CLAUDE.md dashboard rule ("every section leads with a
plain-English question; jargon is translated, not shown") — Stock Taper is proof the
approach reads as premium, not dumbed-down.

---

## 5. The promo video (`assets/promo-video.mp4`)

65s brand video (Wistia `ymbd7p9r5j`, downloaded + compressed to ~3.4 MB; original was
133 MB). Keyframes in `assets/video-frames/`. It's a motion showcase of the same
system — astronaut, product pans, mono type, cream palette. Use it to see how the
illustrations animate and how the product screens are framed. Poster:
`assets/promo-video-poster.webp`.

---

## 6. How to apply this to our dashboard (concrete mapping)

Today `dashboard/render.py` ships a *light theme, one teal accent, system fonts*. To
model it on Stock Taper without losing the honest-content thesis, change the **skin**,
keep the **substance**:

| Change | From (current) | To (Stock Taper) |
|---|---|---|
| Background | white | **`#FBF7EB` cream** |
| Font | system sans | **IBM Plex Mono** everywhere |
| Accent | single teal | **muted green `#2F7D31` / brick red `#C6392C`** for up/down; keep one calm accent for links |
| Headings | regular sans | **heavy mono, uppercase H3 + eyebrow tags** |
| Sections | plain panels | **white cards on cream, hairline borders, 12px radius** |
| Personality | none | **a small mascot set** — one illustration per panel |

**Section-by-section translation** (our dashboard → their pattern):
- "What's moving now" board → **Market Snapshot tables** (logo · ticker · sparkline · %),
  green/red per direction.
- Agent desk / positions → **stock-detail card stack** (price header + stacked data
  cards); the dark Agent Terminal can keep dark, but the *research* dashboard adopts the
  cream almanac skin.
- Edge research / strategy panels → **mascot feature cards** (eyebrow tag → heavy H3 →
  bullets → illustration). e.g. a *radar* for the edge scanner, a *scale* for
  head-to-head strategy comparisons, a *falcon* for the deep-dive.
- Calibration / reliability → their **chart-heavy section** styling (white card, mono
  axis labels, muted palette).
- Blog/《research log》 → their **article grid + long-form** layout.

**Our own mascot cast** (proposed, matching our modules): 🛰️ astronaut = the agent;
🦅 falcon = the edge scanner (`signals/trending`); ⚖️ scale = strategy arena (`sim/`);
🎯 radar = divergence monitor (`markets/monitor`); 📡 pigeon = alerts (`alerts/`);
🏛️ capitol = congress/insider data. Commission or generate a consistent illustration
set in the same warm, slightly-retro rendered style.

**Do keep** our non-negotiables visible — calibration, "not financial advice", the
prediction-evidence "why" expanders. Stock Taper shows the *skin* to aim for; the lab's
methodology stays the substance underneath.

---

*Reference only. Assets © Stock Taper — captured for private design study, not
redistribution. Not financial advice.*
