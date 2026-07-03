# design.md — The Forecasting Briefing

The design system for `site/index.html` (rendered by `dashboard/render.py`). One
rule above all others: **this is a research *newspaper*, not a SaaS dashboard.**
In 2025-26 editorial design, *restraint and print-craft read as expensive;
effects and motion read as cheap.* When in doubt, remove the accessory.

Hard constraint: the page is **self-contained** — inline CSS/SVG/vanilla JS only,
no external fonts/CDNs/frameworks/video, must render offline on GitHub Pages.
Every choice below respects that.

---

## 1. Voice & principles

- **Every section leads with a plain-English question** and answers it in one line. Jargon (Brier, PBO, deflated Sharpe) is *translated*, never displayed raw.
- **Every prediction states its odds AND the evidence for them.** A pick with no probability, or a probability with no "why", does not ship. See §7.
- **Honest by construction.** Empty states name the command that fills them. "No edge" is shown as a real result, not hidden.
- **Copy is sentence case, active voice, specific.** Real typographic punctuation: curly quotes, em dashes `—`, `×` not `x`, `·` middots, real minus `−` (U+2212).

## 2. Color — ink + paper + one accent

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#FAF9F6` | page background (never pure white) |
| `--card` | `#FFFFFF` | section panels |
| `--ink` | `#1E1C19` | text (warm near-black, never pure black) |
| `--muted` | `#6B6864` | secondary text, captions |
| `--faint` | `#9A958C` | metadata, axis labels |
| `--rule` | `#E5E1D8` | hairline rules & borders (the workhorse) |
| `--accent` | `#0F766E` | kickers, active nav, masthead rule, links — **one accent only** |
| `--up` / `--down` | `#0B6B3A` / `#B0281A` | gains / losses in data **only** |

No gradients (except the recession gauge's meaning-bearing heat bar). No drop
shadows — **hairline rules and whitespace do the separating.** Radius ≤ 3px.

## 3. Type — premium from system fonts

```
--display: "Iowan Old Style","Palatino Linotype",Palatino,P052,Georgia,serif;  /* headlines, masthead, big numbers */
--serif:   Charter,"Bitstream Charter","Sitka Text",Cambria,Georgia,serif;     /* body, decks, explainers */
--sans:    Inter,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;   /* kickers, nav, labels, table headers, axes */
--mono:    ui-monospace,"SFMono-Regular","Cascadia Code",Menlo,Consolas,monospace; /* figures, dates, tickers, deltas */
```

Three roles, cleanly separated: **serif reads, sans labels, mono counts.**

- Headlines: `--display`, 700, `letter-spacing:-.015em`, `text-wrap:balance`.
- Body/deck: `--serif`, 400, `line-height:1.55-1.6`, **`max-width:68ch`** (60-75 chars — the anti-template rule).
- Kickers/labels: `--sans`, 600, uppercase, `letter-spacing:.05-.11em`, ~12px, accent or muted.
- Table headers: `--sans`, `font-variant-caps:all-small-caps`, `2px solid ink` underline.
- All figures: `font-variant-numeric:tabular-nums lining-nums` in tables; `oldstyle-nums` in running prose.

Modular scale (~1.25): `0.72 · 0.85 · 1 · 1.25 · 1.55 · 1.95 · 2.4+ rem`.

## 4. Layout

- Masthead: centered wordmark (`--display`), italic standfirst, a **dateline strip** (`WEEKDAY, MONTH D, YYYY · RESEARCH BRIEFING · NO. {day-of-year} · {n} sources · updated N ago`) closed by a `3px solid ink` bottom rule. The dateline is the single biggest "news site" signal.
- Lead: kicker → display headline → serif deck → KPI strip.
- Sticky section nav (small-caps, scroll-spy active state).
- Sections: `.card` with a kicker + question headline + one-line deck, hairline border, source label right-aligned in small-caps mono.
- Grids separated by **hairline rules, not gaps** (movers, odds, strategy cards, sports minis).
- Colophon footer: "Set in Charter & Iowan Old Style · No. N · Not financial advice."

## 5. Components (contract)

`kpi` · `mover` (ticker + sparkline + delta chips + signal bar + headline) · `odds`/`odds1` (venue label + bar + %) · `sortable table` (small-caps headers, mono cells, inline bars, real −) · `reliability_svg` · `equity_svg` · `sparkline_svg` · `gauge` · `mlcard` · `note` · `stat` · `mini`. Keep these names stable — tests and `collect.py` depend on them.

## 6. Motion — the only animation you need

Allowed (self-contained, tasteful, `prefers-reduced-motion` always respected):
- **Chart draw-on**: `stroke-dasharray` line-draw on `reliability_svg` / `equity_svg` / sparklines, ~800ms ease-out, once on load.
- **Count-up** on the four hero KPI numbers (~600ms), pure JS, integer/percent aware.
- **Reveal**: the existing `translateY(8px)+fade` per section.
- **Hover micro-transitions**: 150ms on links, nav, KPI tiles, sortable headers.
- A subtle **live "updated N ago"** pulse dot.

Banned (all read AI-generated / cheap for this genre): parallax, autoplaying gradient/mesh/blob backgrounds, glassmorphism, scroll-jacking, springy/bouncy easings, embedded video heroes (incl. Seedance/AI-video — also breaks self-containment), any purely decorative motion. **A still, perfectly-set page beats a moving one here.**

> On "Seedance 2 / AI motion graphics": possible only as a pre-rendered asset, which (a) is a multi-MB external file that breaks offline render, and (b) reads as generic per the research. If a motion hero is ever wanted, do it as an **animated SVG** (a self-drawing candlestick/line ticker), not video.

## 7. The prediction contract (non-negotiable)

Anywhere the site surfaces a pick, forecast, or "edge", it MUST show:
1. **A probability / odds** (e.g. "62% · +180") — calibrated, not a vibe.
2. **The evidence**, as a short "why" with the specific drivers (e.g. "momentum 60d +41%, near 2% of high, news velocity z=2.3") — ideally an expandable detail so the top stays scannable.
3. **The honest caveat** where relevant (paper vs live, fees modeled, base rate to beat).

A number with no rationale, or a rationale with no number, is a bug. This is what separates a research tool from a tip sheet.

## 8. Quality floor (always)

Responsive to 360px · visible keyboard focus · reduced-motion honored · content never JS-gated (JS enhances a page that already works) · WCAG AA contrast · every chart `role="img"` with an `aria-label`.
