"""Render the lab state into one interactive HTML page — the almanac desk view.

Design (MASTER_PLAN §2): **Stock Taper skin × Rallies layout**. Warm cream paper,
white cards with hairlines, IBM Plex Mono throughout (ui-monospace fallback — no
external font fetch), muted green/brick for up/down, uppercase eyebrow tags +
heavy uppercase headings, one tiny hand-drawn inline-SVG mascot per section.
Rallies supplies the structure: sticky feature-per-surface nav with scroll-spy,
a peer strip over the movers, suggested-question chips, book tables, a filtered
activity feed. Still a *tool* underneath: sparklines, live odds side by side,
sortable tables, an "updated N ago" clock. Self-contained (inline CSS/SVG + a
little vanilla JS); content never JS-gated; "going well / concerning" pairs and
plain-English framing on every surface. Not financial advice, everywhere.
"""

from __future__ import annotations

import html as _html
from datetime import datetime

from ..eval.honest_stats import format_metric
from ..eval.recalibration import default_fair_value
from ..predictions import market_prediction, mover_prediction

# ---------------------------------------------------------------- palette
PAPER = "#FBF7EB"
CARD = "#FFFFFF"
INK = "#1E1C19"
MUTED = "#6B6864"
FAINT = "#9A958C"
RULE = "#E5E5E5"
LINE = RULE  # alias
ACCENT = "#1D5C2E"
ACCENT_SOFT = "#EAF2E4"
UP = "#2F7D31"
DOWN = "#C6392C"
MINUS = "−"

STRATEGY_COLORS = {
    "ml_ranker": "#A6511C",
    "momentum_60d": ACCENT,
    "breakout_120d": "#2F6690",
    "meanrev_5d": "#B0791F",
    "voltarget_20d": "#6A5A94",
    "buy_hold": "#8A857C",
    "random": "#B8B2A6",
}
BASELINES = {"buy_hold", "random"}

PLAIN_NAME = {
    "ml_ranker": "ML model",
    "momentum_60d": "Momentum",
    "breakout_120d": "Breakout",
    "meanrev_5d": "Mean-reversion",
    "voltarget_20d": "Risk-balanced",
    "buy_hold": "Buy & hold",
    "random": "Random (control)",
}


def _esc(s) -> str:
    return _html.escape(str(s))


def _json_html(obj) -> str:
    """JSON safe to embed inside a <script> tag (neutralize </script> + U+2028/9)."""
    import json as _json

    out = _json.dumps(obj)
    for ch, esc in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                    (" ", "\\u2028"), (" ", "\\u2029")):
        out = out.replace(ch, esc)
    return out


def _fmt(v, digits=3):
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return _esc(v)


def _pct(v, digits=0, signed=False):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(v)
    body = f"{abs(f) * 100:.{digits}f}%"
    if f < 0:
        return MINUS + body
    return ("+" if signed else "") + body


def _signed(f: float, digits=2) -> str:
    return (MINUS if f < 0 else "+") + f"{abs(f):.{digits}f}"


def _plain(name: str) -> str:
    return PLAIN_NAME.get(name, name)


# ---------------------------------------------------------------- SVG: sparkline
def sparkline_svg(series: list[float], width=150, height=40) -> str:
    """A tiny price line, colored green/red by net move over the window."""
    pts = [float(v) for v in series if v is not None]
    if len(pts) < 2:
        return f'<svg viewBox="0 0 {width} {height}" class="spark" aria-hidden="true"></svg>'
    lo, hi = min(pts), max(pts)
    rng = hi - lo or 1.0
    pad = 3
    n = len(pts)
    color = UP if pts[-1] >= pts[0] else DOWN
    coords = [
        (pad + i / (n - 1) * (width - 2 * pad), height - pad - (v - lo) / rng * (height - 2 * pad))
        for i, v in enumerate(pts)
    ]
    line = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
    area = line + f" L {coords[-1][0]:.1f} {height} L {coords[0][0]:.1f} {height} Z"
    return (
        f'<svg viewBox="0 0 {width} {height}" class="spark" preserveAspectRatio="none" '
        f'role="img" aria-label="price trend">'
        f'<path d="{area}" fill="{color}" fill-opacity="0.07"/>'
        f'<path d="{line}" fill="none" stroke="{color}" stroke-width="1.6"/>'
        f'<circle cx="{coords[-1][0]:.1f}" cy="{coords[-1][1]:.1f}" r="2.2" fill="{color}"/></svg>'
    )


# ---------------------------------------------------------------- SVG: reliability
def reliability_svg(records: list[dict], width=620, height=420) -> str:
    ml, mr, mt, mb = 58, 18, 18, 88
    pw, ph = width - ml - mr, height - mt - mb
    hist_h = 38

    def sx(p):
        return ml + p * pw

    def sy(p):
        return mt + (1 - p) * ph

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Calibration: predicted probability vs how often it actually happened">'
    ]
    for i in range(6):
        p = i / 5
        parts.append(f'<line x1="{sx(p):.1f}" y1="{sy(0):.1f}" x2="{sx(p):.1f}" y2="{sy(1):.1f}" stroke="{RULE}"/>')
        parts.append(f'<line x1="{sx(0):.1f}" y1="{sy(p):.1f}" x2="{sx(1):.1f}" y2="{sy(p):.1f}" stroke="{RULE}"/>')
        parts.append(f'<text x="{sx(p):.1f}" y="{sy(0)+18:.1f}" class="ax" text-anchor="middle">{p:.0%}</text>')
        parts.append(f'<text x="{ml-10:.1f}" y="{sy(p)+4:.1f}" class="ax" text-anchor="end">{p:.0%}</text>')

    parts.append(
        f'<line x1="{sx(0):.1f}" y1="{sy(0):.1f}" x2="{sx(1):.1f}" y2="{sy(1):.1f}" '
        f'stroke="{FAINT}" stroke-width="1.5" stroke-dasharray="5 5"/>'
    )
    cx, cy = sx(0.72), sy(0.72)
    parts.append(
        f'<text x="{cx:.0f}" y="{cy-10:.0f}" class="diag" transform="rotate(-38 {cx:.0f} {cy:.0f})" '
        f'text-anchor="middle">a perfect model sits on this line</text>'
    )

    used = [r for r in records if r.get("count")]
    if used:
        maxc = max(r["count"] for r in used)
        pts = [(sx(r["mean_pred"]), sy(r["frac_pos"])) for r in used]
        path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        parts.append(f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2.5" class="draw" pathLength="1"/>')
        for r, (x, y) in zip(used, pts, strict=True):
            rad = 3 + 7 * (r["count"] / maxc) ** 0.5
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{ACCENT}" fill-opacity="0.9" '
                f'stroke="{CARD}" stroke-width="1.5"><title>said ~{r["mean_pred"]:.0%}, '
                f'happened {r["frac_pos"]:.0%} ({r["count"]} times)</title></circle>'
            )
        bar_w = pw / len(records) - 3
        hy = height - hist_h - 20
        for r in records:
            bh = (r["count"] / maxc) * hist_h if r["count"] else 0
            parts.append(
                f'<rect x="{sx(r["bin_low"])+1.5:.1f}" y="{hy+hist_h-bh:.1f}" width="{bar_w:.1f}" '
                f'height="{bh:.1f}" rx="1" fill="{ACCENT}" fill-opacity="0.22"/>'
            )
        parts.append(f'<text x="{ml}" y="{hy+hist_h+15}" class="ax">how many predictions fell in each range</text>')

    parts.append(f'<text x="{ml}" y="{sy(1)-5:.0f}" class="axt">what actually happened &#8593;</text>')
    parts.append(f'<text x="{sx(1):.0f}" y="{sy(0)+36:.0f}" class="axt" text-anchor="end">the model\'s prediction &#8594;</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- SVG: equity
def equity_svg(curves: dict[str, list[float]], width=780, height=300) -> str:
    import math

    ml, mr, mt, mb = 52, 188, 14, 26
    pw, ph = width - ml - mr, height - mt - mb
    if not curves:
        return ""
    n = max(len(v) for v in curves.values())
    floor = 1e-3
    lo = max(min(min(v) for v in curves.values()), floor)
    hi = max(max(v) for v in curves.values())
    llo, lhi = math.log(lo) - 0.05, math.log(hi) + 0.05

    def sx(i):
        return ml + (i / max(n - 1, 1)) * pw

    def sy(v):
        return mt + (1 - (math.log(max(v, floor)) - llo) / (lhi - llo)) * ph

    ticks = [t for t in (0.25, 0.5, 1, 2, 5, 10, 20, 50) if lo * 0.95 <= t <= hi * 1.05] or [1]
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Growth of $1 by strategy (log scale)">']
    for t in ticks:
        y = sy(t)
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="{RULE}" stroke-width="{1.6 if t==1 else 1}"/>')
        parts.append(f'<text x="{ml-8}" y="{y+4:.1f}" class="ax" text-anchor="end">{t:g}&#215;</text>')
    order = sorted(curves, key=lambda k: curves[k][-1], reverse=True)
    for idx, name in enumerate(order):
        vals = curves[name]
        color = STRATEGY_COLORS.get(name, INK)
        # dashed baselines stay static; solid strategy lines draw on (dasharray would clash)
        legdash = ' stroke-dasharray="5 4"' if name in BASELINES else ""
        extra = legdash if name in BASELINES else ' class="draw" pathLength="1"'
        wdt = 2.6 if name == "ml_ranker" else 2
        path = "M " + " L ".join(f"{sx(i):.1f} {sy(v):.1f}" for i, v in enumerate(vals))
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{wdt}"{extra}/>')
        ly = mt + 12 + idx * 20
        parts.append(f'<line x1="{width-mr+8}" y1="{ly-4}" x2="{width-mr+26}" y2="{ly-4}" stroke="{color}" stroke-width="2.5"{legdash}/>')
        parts.append(f'<text x="{width-mr+32}" y="{ly}" class="leg">{_esc(_plain(name))} <tspan fill="{MUTED}">{vals[-1]:.1f}&#215;</tspan></text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- HTML helpers
def _bar(frac: float, color: str) -> str:
    w = max(0.0, min(1.0, frac)) * 100
    return f'<span class="ibar"><i style="width:{w:.0f}%;background:{color}"></i></span>'


def _chip(label: str, value: float) -> str:
    cls = "up" if value >= 0 else "down"
    return f'<span class="chip {cls}">{_pct(value, 1, signed=True)} <em>{_esc(label)}</em></span>'


def _kpi(label: str, value: str, sub: str, tone: str = "", anchor: str = "") -> str:
    tcls = f" kpi-{tone}" if tone else ""
    tag = "a" if anchor else "div"
    href = f' href="#{anchor}"' if anchor else ""
    return (f'<{tag} class="kpi{tcls}"{href}><div class="kpi-label">{_esc(label)}</div>'
            f'<div class="kpi-val">{value}</div><div class="kpi-sub">{_esc(sub)}</div></{tag}>')


# tiny hand-drawn inline-SVG mascots, one per surface (our own doodles — never
# copied art). Simple stroke figures in the section's corner, aria-hidden.
def _doodle(body: str) -> str:
    return (f'<svg class="mascot" viewBox="0 0 44 44" aria-hidden="true" fill="none" '
            f'stroke="{INK}" stroke-width="1.6" stroke-linecap="round">{body}</svg>')


MASCOTS = {
    "desk": _doodle('<rect x="8" y="14" width="28" height="18" rx="2"/><path d="M14 32v4h16v-4"/>'
                    '<path d="M14 20h10M14 24h16"/><circle cx="31" cy="20" r="1.5" fill="#2F7D31" stroke="none"/>'),
    "movers": _doodle('<path d="M7 32 L16 22 L23 27 L37 12"/><path d="M30 12h7v7"/>'),
    "odds": _doodle('<path d="M22 8v28M12 14h20"/><path d="M12 14l-5 9h10zM32 14l-5 9h10z"/>'
                    '<path d="M7 23a5 5 0 0 0 10 0M27 23a5 5 0 0 0 10 0"/>'),
    "edges": _doodle('<circle cx="22" cy="22" r="13"/><circle cx="22" cy="22" r="7"/>'
                     '<circle cx="22" cy="22" r="1.6" fill="#C6392C" stroke="none"/><path d="M22 4v6M22 34v6M4 22h6M34 22h6"/>'),
    "arena": _doodle('<path d="M10 36V22M22 36V10M34 36V16"/><path d="M6 36h32"/>'
                     '<circle cx="22" cy="7" r="2" fill="#2F7D31" stroke="none"/>'),
    "scorecard": _doodle('<rect x="9" y="7" width="26" height="30" rx="2"/><path d="M14 14h10M14 20h16M14 26h13"/>'
                         '<path d="M15 31l3 3 6-6"/>'),
    "macro": _doodle('<rect x="7" y="16" width="30" height="20" rx="1"/><path d="M7 16 L22 7 L37 16"/>'
                     '<path d="M13 22v8M22 22v8M31 22v8"/>'),
    "watch": _doodle('<circle cx="18" cy="20" r="9"/><path d="M25 27 L36 38"/><path d="M14 20a4 4 0 0 1 4-4"/>'),
    "sports": _doodle('<circle cx="22" cy="22" r="14"/><path d="M8 22h28M22 8a20 20 0 0 1 0 28M22 8a20 20 0 0 0 0 28"/>'),
    "feed": _doodle('<path d="M9 12h26M9 20h26M9 28h18"/><circle cx="33" cy="30" r="4"/>'),
}


def _section(anchor: str, kicker: str, title: str, explainer: str, body: str,
             source: str = "", mascot: str = "") -> str:
    src = f'<span class="src">{_esc(source)}</span>' if source else ""
    art = MASCOTS.get(mascot, "")
    return (f'<section id="{anchor}" class="card reveal">'
            f'<div class="sec-head"><div><div class="kicker">{_esc(kicker)}</div>'
            f'<h2>{_esc(title)}</h2></div>{src}{art}</div>'
            f'<p class="explain">{_esc(explainer)}</p>{body}</section>')


def _well_concerning(preds) -> str:
    """The Stock Taper 'What's going well? / What's concerning?' pair, derived
    strictly from the picks' drivers (positive vs negative contributions) and
    their caveats — plain English over the same evidence, never new claims."""
    good: list[str] = []
    bad: list[str] = []
    for pred in preds:
        name = _esc(pred.label.split()[0]) if pred.label else "pick"
        for d in pred.drivers:
            if abs(d.contribution) < 1e-9:
                continue
            line = f"<b>{name}</b> · {_esc(d.feature)} {_dfmt(d.feature, d.value)}"
            (good if d.contribution > 0 else bad).append(line)
    if not good and not bad:
        return ""
    good_html = "".join(f"<li>{g}</li>" for g in good[:5]) or "<li>nothing stands out today</li>"
    bad_html = "".join(f"<li>{b}</li>" for b in bad[:5]) or "<li>no red flags in the drivers — the caveats still apply</li>"
    return ('<div class="wellcon">'
            f'<div class="wc-good"><h4>What&#8217;s going well?</h4><ul>{good_html}</ul></div>'
            f'<div class="wc-bad"><h4>What&#8217;s concerning?</h4><ul>{bad_html}</ul></div></div>')


def _stat(label: str, value: str, sub: str = "", big: bool = False) -> str:
    cls = "stat big" if big else "stat"
    subhtml = f'<span class="stat-sub">{_esc(sub)}</span>' if sub else ""
    return f'<div class="{cls}"><span class="stat-label">{_esc(label)}</span><span class="stat-val">{value}</span>{subhtml}</div>'


def _mini(title: str, value: str, base: str, note: str) -> str:
    return (f'<div class="mini"><h4>{_esc(title)}</h4><div class="m-val">{_esc(value)}</div>'
            f'<div class="m-base">{_esc(base)}</div><div class="m-note">{_esc(note)}</div></div>')


def _md_table(rows, limit=6) -> str:
    if not rows:
        return '<p class="empty">Nothing to show yet.</p>'
    head = "".join(f"<th>{_esc(c)}</th>" for c in rows[0])
    body = []
    for r in rows[1:limit + 1]:
        tds = []
        for c in r:
            try:
                float(c)
                tds.append(f'<td class="num">{_esc(c)}</td>')
            except ValueError:
                tds.append(f"<td>{_esc(c)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="twrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _empty(note: str) -> str:
    return f'<p class="empty">{_esc(note)}</p>'


# ---------------------------------------------------------------- evidence ("why")
def _dfmt(feature: str, value: float) -> str:
    """Format a driver value by what the feature is (× for volume, % for the rest)."""
    if "volume" in feature:
        return f"{value:,.0f}×" if abs(value) >= 100 else f"{value:.2f}×"
    if "composite" in feature:
        return f"{value:+.2f}"
    return _pct(value, 1, signed=True)


def _dots(prob: float) -> str:
    """Confidence dots: the probability bucketed 1-5, never a fake precision."""
    filled = max(1, min(5, round(float(prob) * 5)))
    return ('<span class="dots" title="confidence (probability bucketed 1-5)">'
            + "●" * filled + "○" * (5 - filled) + "</span>")


def _trust_badge(sources: str, fetched_at: str | None) -> str:
    """The Intel Desk trust mechanic, restyled: what fed this pick and how fresh.
    An unstamped feed says so — silence about freshness is the bug."""
    fresh = (f"fetched {_esc(str(fetched_at)[:16])}" if fetched_at
             else "freshness unstamped — treated as run-time data")
    return (f'<span class="trust" title="sources behind this pick + data freshness">'
            f'&#10003; {_esc(sources)} · {fresh}</span>')


def _why(pred, trust: str = "") -> str:
    """The evidence-thesis card (design.md §7 + the Intel Desk teardown), one
    element: WHY NOW → EVIDENCE (value + signed push) → WATCH FOR / RED FLAGS →
    confidence dots + trust badge → the caveat. All server-rendered."""
    ev_items = "".join(
        f'<li><span>{_esc(d.feature)}</span>'
        f'<b>{_dfmt(d.feature, d.value)} <i class="push {"up" if d.contribution >= 0 else "down"}">'
        f'{"&#9650;" if d.contribution >= 0 else "&#9660;"}</i></b></li>'
        for d in pred.drivers[:5]
    )
    edge = pred.edge_vs_market
    if edge is not None and abs(edge) > 0.001:
        ev_items += f'<li class="edge"><span>edge vs market</span><b>{_pct(edge,1,signed=True)}</b></li>'
    watch = [d for d in pred.drivers if d.contribution > 0][:3]
    flags = [d for d in pred.drivers if d.contribution < 0][:3]
    watch_html = "".join(f"<li>{_esc(d.feature)} {_dfmt(d.feature, d.value)}</li>" for d in watch) \
        or "<li>momentum holding its drivers</li>"
    flags_html = "".join(f"<li>{_esc(d.feature)} {_dfmt(d.feature, d.value)}</li>" for d in flags) \
        or "<li>none in the drivers — the caveat still applies</li>"
    why_now = _esc(", ".join(d.feature for d in pred.drivers[:2]) or "the drivers below")
    unit = "yes" if pred.kind == "market" else "lean"
    return (
        f'<details class="why"><summary><b>{pred.pct()}</b> {unit} {_dots(pred.probability)} · why</summary>'
        f'<div class="ev"><h5>Why now</h5><p class="whynow">{why_now}</p>'
        f'<h5>Evidence</h5><ul class="drivers">{ev_items}</ul>'
        f'<div class="wf"><div><h5 class="wfg">Watch for</h5><ul>{watch_html}</ul></div>'
        f'<div><h5 class="wfb">Red flags</h5><ul>{flags_html}</ul></div></div>'
        f'{trust}<p class="cav">{_esc(pred.caveat)}</p></div></details>'
    )


# ---------------------------------------------------------------- movers board
def _mover_card(c: dict, trust: str = "") -> str:
    last = c.get("last")
    price = f"${last:,.2f}" if isinstance(last, (int, float)) else ""
    score = c.get("momentum", 0.0)
    heads = _esc(c.get("headline", "")) if c.get("headline") else ""
    news = f'<p class="mv-news">{heads}</p>' if heads else ""
    frac = max(0.0, min(1.0, (score + 2) / 4))
    pred = mover_prediction(c)
    return (
        f'<article class="mover">'
        f'<div class="mv-top"><span class="tk">{_esc(c["ticker"])}</span><span class="px">{price}</span></div>'
        f'{sparkline_svg(c.get("spark", []))}'
        f'<div class="chips">{_chip("5d", c.get("ret_5d",0))}{_chip("60d", c.get("ret_60d",0))}'
        f'<span class="chip flat">{_pct(c.get("pct_from_high",0),0,signed=True)} <em>vs high</em></span></div>'
        f'<div class="mv-score"><span>signal</span>{_bar(frac, STRATEGY_COLORS["momentum_60d"])}'
        f'<b>{_signed(score)}</b></div>{_why(pred, trust)}{news}</article>'
    )


def _peer_strip(cards: list[dict]) -> str:
    """Rallies-style peer strip: every scanned name as a scrolling chip with its move."""
    chips = []
    for c in cards[:16]:
        ret = float(c.get("ret_5d", 0) or 0)
        cls = "up" if ret >= 0 else "down"
        chips.append(f'<a href="#now">{_esc(c["ticker"])} <b class="{cls}">{_pct(ret,1,signed=True)}</b></a>')
    return f'<div class="peers">{"".join(chips)}</div>' if chips else ""


def _movers_board(movers: dict) -> str:
    if movers.get("empty") or not movers.get("movers"):
        return _empty("The stock scan runs on the next update — it needs the live market feed. "
                      "Locally: flab-trending.")
    mom = movers.get("movers", [])[:8]
    fast = movers.get("fast", [])[:8]
    trust = _trust_badge("Yahoo charts + Google News",
                         (movers.get("freshness") or {}).get("fetched_at"))
    peers = _peer_strip(mom + [c for c in fast if c["ticker"] not in {m["ticker"] for m in mom}])
    tabs = (
        '<div class="tabs" data-tab-group="movers">'
        '<button data-tab="mom" class="on">Steady climbers</button>'
        '<button data-tab="fast">Fast money</button></div>'
    )
    mom_html = '<div class="movers" data-tab-panel="mom">' + "".join(_mover_card(c, trust) for c in mom) + "</div>"
    fast_html = '<div class="movers hidden" data-tab-panel="fast">' + "".join(_mover_card(c, trust) for c in fast) + "</div>"
    note = "" if movers.get("reddit_ok") else '<p class="fine">Social-velocity (Reddit) is unavailable here; it feeds the fast-money score in the cloud.</p>'
    pair = _well_concerning([mover_prediction(c) for c in mom])
    return peers + tabs + mom_html + fast_html + pair + note


# ---------------------------------------------------------------- odds board
def _odds_card(event, k, p, similarity, footer, trust: str = "") -> str:
    pred = market_prediction(event, p, "Polymarket", gap=abs(float(k) - float(p)),
                             similarity=similarity, fair_value=default_fair_value(p))
    return (
        f'<div class="odds">'
        f'<div class="odds-q">{_esc(event)}<span class="sim">match {_pct(similarity,0)}</span></div>'
        f'<div class="odds-bars">'
        f'<div class="ob"><label>Kalshi</label>{_bar(k, "#2F6690")}<span>{_pct(k,0)}</span></div>'
        f'<div class="ob"><label>Polymarket</label>{_bar(p, ACCENT)}<span>{_pct(p,0)}</span></div></div>'
        f'<div class="odds-edge">{footer}</div>{_why(pred, trust)}</div>'
    )


def _odds_row(event, yes, venue, color, trust: str = "") -> str:
    pred = market_prediction(event, yes, venue, fair_value=default_fair_value(yes))
    return (f'<div class="odds1"><div class="o1-q">{_esc(event)}</div>'
            f'<div class="ob">{_bar(yes, color)}<span>{_pct(yes,0)} yes</span></div>'
            f'<div class="o1-v">{_esc(venue)}</div>{_why(pred, trust)}</div>')


def _odds_board(edges: dict) -> str:
    flagged = edges.get("edges") or []
    matched = edges.get("matched") or []
    live = edges.get("live") or {}
    trust = _trust_badge("Kalshi + Polymarket live books",
                         (edges.get("freshness") or {}).get("fetched_at"))

    cross = ""
    if flagged:
        cards = []
        for e in sorted(flagged, key=lambda e: abs(e.get("net_edge", 0)), reverse=True)[:8]:
            buy = "Kalshi" if "kalshi" in str(e.get("direction", "")).lower() else "Polymarket"
            footer = f'<b>{_pct(e.get("net_edge",0),1,signed=True)}</b> gap after fees · cheaper on {_esc(buy)}'
            cards.append(_odds_card(e["event"], e.get("kalshi", 0), e.get("poly", 0), e.get("similarity", 0), footer, trust))
        cross = ('<h3>Cross-venue gaps</h3>'
                 '<p class="fine">The same question priced differently on each venue — candidates to investigate.</p>'
                 '<div class="oddswrap">' + "".join(cards) + "</div>")
    elif matched:
        cards = [_odds_card(m["event"], m.get("kalshi", 0), m.get("poly", 0), m.get("similarity", 0),
                            f'{_pct(m.get("gap",0),1)} apart · within fees', trust)
                 for m in sorted(matched, key=lambda m: m.get("gap", 0), reverse=True)[:6]]
        cross = ('<h3>Same question, both venues</h3>'
                 '<div class="oddswrap">' + "".join(cards) + "</div>")

    live_html = ""
    poly, kalshi = live.get("poly") or [], live.get("kalshi") or []
    if poly or kalshi:
        cols = []
        if poly:
            rows = "".join(_odds_row(m["event"], m["yes"], "Polymarket", ACCENT, trust) for m in poly[:8])
            cols.append(f'<div class="ocol"><h3>Polymarket · most traded</h3>{rows}</div>')
        if kalshi:
            rows = "".join(_odds_row(m["event"], m["yes"], "Kalshi", "#2F6690", trust) for m in kalshi[:8])
            cols.append(f'<div class="ocol"><h3>Kalshi · most active</h3>{rows}</div>')
        live_html = '<div class="ocols">' + "".join(cols) + "</div>"

    if not cross and not live_html:
        scanned = ""
        if edges.get("n_kalshi") is not None:
            scanned = f" Scanned {edges.get('n_kalshi',0)} Kalshi + {edges.get('n_poly',0)} Polymarket markets."
        return _empty("The market feed returned no priced markets right now." + scanned)

    # the going-well/concerning pair over the same evidence the cards show
    preds = [market_prediction(e["event"], e.get("poly", 0), "Polymarket",
                               gap=abs(float(e.get("kalshi", 0)) - float(e.get("poly", 0))),
                               fair_value=default_fair_value(e.get("poly", 0)))
             for e in (flagged or matched)[:6]]
    preds += [market_prediction(m["event"], m["yes"], "Polymarket",
                                fair_value=default_fair_value(m["yes"])) for m in poly[:4]]
    return cross + live_html + _well_concerning(preds)


# ---------------------------------------------------------------- sortable table
def _sortable(rows: list[dict], cols: list[tuple], *, bar_col=None, bar_max=1.0, highlight=None) -> str:
    head = "".join(
        f'<th data-sort="{i}" class="{"num" if typ not in ("name", "text") else ""}">{_esc(lbl)}<i></i></th>'
        for i, (key, lbl, typ) in enumerate(cols)
    )
    body = []
    for row in rows:
        cls = ' class="hl"' if highlight and row.get("strategy") == highlight else ""
        tds = []
        for key, _lbl, typ in cols:
            v = row.get(key, "")
            if typ == "name":
                color = STRATEGY_COLORS.get(row.get("strategy", ""), INK)
                tds.append(f'<td data-v="{_esc(v)}"><span class="swatch" style="background:{color}"></span>{_esc(_plain(v))}</td>')
            elif typ == "signed":
                fv = float(v)
                c = "up" if fv >= 0 else "down"
                barhtml = _bar(abs(fv) / bar_max, UP if fv >= 0 else DOWN) if key == bar_col else ""
                tds.append(f'<td class="num {c}" data-v="{fv}">{barhtml}<span>{_signed(fv)}</span></td>')
            elif typ == "pct":
                fv = float(v)
                tds.append(f'<td class="num" data-v="{fv}">{_pct(fv,0)}</td>')
            elif typ == "int":
                tds.append(f'<td class="num" data-v="{v}">{int(float(v)):,}</td>')
            elif typ == "num":
                tds.append(f'<td class="num" data-v="{v}">{_fmt(v,2)}</td>')
            else:
                tds.append(f'<td data-v="{_esc(v)}">{_esc(v)}</td>')
        body.append(f"<tr{cls}>" + "".join(tds) + "</tr>")
    return f'<div class="twrap"><table class="sortable"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


# ---------------------------------------------------------------- assembly
VERDICT_TONE = {"STRONG BUY": UP, "BUY": UP, "HOLD": MUTED, "TRIM": DOWN,
                "AVOID": DOWN, "INSUFFICIENT EVIDENCE": FAINT}


def _verdict_chip(row: dict) -> str:
    sym, label = row["symbol"], row["label"]
    tone = VERDICT_TONE.get(label, FAINT)
    dim = " insuf" if label == "INSUFFICIENT EVIDENCE" else ""
    short = "INSUF." if label == "INSUFFICIENT EVIDENCE" else label
    return (f'<a class="vchip{dim}" href="t/{_esc(sym)}.html" data-m="{_esc(_json_html(row.get("matrix", {})))}">'
            f'<span class="vc-sym">{_esc(sym)}</span>'
            f'<span class="vc-lab" style="color:{tone}">{_esc(short)}</span></a>')


def _platform_home(state) -> str:
    """The platform top: hero + universe search + today's verdicts grid + the
    profile control + the ETF core row. Replaces the old newspaper masthead."""
    v = getattr(state, "verdicts", {}) or {}
    rows = v.get("rows") or []
    symbols = v.get("symbols") or []

    if not rows:
        grid = ('<p class="empty">No recommendation verdicts built yet — run '
                '<code>flab-verdicts</code> (nightly in the cloud). Search still works '
                'over the full universe once an artifact exists.</p>')
        etf_row = ""
    else:
        shown = rows[:48]
        grid = '<div class="vgrid">' + "".join(_verdict_chip(r) for r in shown) + "</div>"
        etfs = [r for r in rows if r.get("is_etf")]
        etf_row = ('<div class="etfrow"><span class="etfrow-lab">Core ETFs</span>'
                   + "".join(_verdict_chip(r) for r in etfs) + "</div>") if etfs else ""

    profile = (
        '<div class="profctl" id="profctl">'
        '<span class="pc-lab">For my</span>'
        '<select id="pcH"><option value="0-1y">0–1y horizon</option>'
        '<option value="1-5y" selected>1–5y horizon</option>'
        '<option value="5y+">5y+ horizon</option></select>'
        '<select id="pcG"><option value="grow" selected>growth</option>'
        '<option value="income">income</option><option value="preserve">preserve</option></select>'
        '<select id="pcR"><option value="low">low risk</option>'
        '<option value="med" selected>med risk</option><option value="high">high risk</option></select>'
        '<span class="pc-note">re-scores every verdict for your goals — reading the contract, not recomputing</span>'
        '</div>'
    )
    as_of = _esc(v.get("as_of", "")) if rows else ""
    change_feed = ""
    if rows:
        from .compare import materiality_feed_html

        change_feed = (
            '<section class="card"><div class="sec-head"><div>'
            '<div class="kicker">What changed</div>'
            '<h2>What moved since the last build?</h2></div></div>'
            '<p class="explain">Every verdict change, attributed to the component that '
            'drove it — never a vague "sentiment shift". Compare any two names on the '
            '<a href="compare.html">compare page</a>.</p>'
            + materiality_feed_html(v.get("changes") or [], v.get("has_prior", False))
            + "</section>"
        )
    return (
        '<header class="phero">'
        '<div class="pbrand">THE&nbsp;VERDICT&nbsp;DESK</div>'
        '<div class="ptag">Investment recommendations with receipts — every verdict carries its '
        'evidence, its confidence, and its scored track record. A personal research tool, '
        '<b>not financial advice</b>.</div>'
        '<div class="search"><input id="q" type="search" autocomplete="off" '
        'placeholder="Search any stock or ETF — VOO, QQQ, NVDA, SCHD…" '
        'aria-label="search the full universe"><div id="qres" class="qres"></div></div>'
        f'{profile}</header>'
        f'{_since_last_visit_html(v.get("as_of", ""), v.get("changes") or [])}'
        f'<section class="card" id="today"><div class="sec-head"><div>'
        f'<div class="kicker">Today&#8217;s verdicts{" · " + as_of if as_of else ""}</div>'
        f'<h2>What&#8217;s attractive right now?</h2></div>{MASCOTS.get("edges", "")}</div>'
        '<p class="explain">Ranked most-attractive first for the default profile; change the '
        'profile above and every card re-scores. Dimmed = INSUFFICIENT EVIDENCE (honest: not '
        f'enough data to rate yet, never a guess).</p>{etf_row}{grid}</section>'
        f'{change_feed}'
        f'{_watchers_feed_html()}'
        f'<script id="built" type="application/json">{_json_html(symbols)}</script>'
    )


def _since_last_visit_html(as_of: str, changes: list[dict]) -> str:
    """The changed-since-last-visit banner (P6d §12.5): pure client-side FILTER
    of the server-rendered change feed — it never recomputes a score. Silent on
    the first visit (it just stamps); dismissing stamps the build as seen."""
    data = {"as_of": as_of,
            "changes": [{"symbol": c.get("symbol"), "was": c.get("was"),
                         "now": c.get("now"), "dir": c.get("dir")} for c in changes[:12]]}
    return (
        f'<script id="sincelast" type="application/json">{_json_html(data)}</script>'
        '<div class="visitbar" id="visitbar" hidden>'
        '<span id="visitmsg"></span>'
        '<a href="#" id="visitfeed">see what changed</a>'
        '<button id="visitdismiss" aria-label="dismiss">&#10005;</button></div>'
        """<script>
(function(){
  var el=document.getElementById('sincelast'), d;
  try{d=JSON.parse(el.textContent||'{}');}catch(e){return;}
  if(!d.as_of)return;
  var seen=localStorage.getItem('flab_seen_asof');
  if(!seen){localStorage.setItem('flab_seen_asof',d.as_of);return;} // first visit: silent
  if(d.as_of<=seen||!(d.changes||[]).length)return;                 // nothing new for you
  var bar=document.getElementById('visitbar'),msg=document.getElementById('visitmsg');
  var names=d.changes.map(function(c){return c.symbol+(c.dir==='up'?' ▲':c.dir==='down'?' ▼':'');});
  msg.textContent=d.changes.length+' verdict'+(d.changes.length===1?'':'s')
    +' moved since you were here: '+names.slice(0,6).join(', ')
    +(names.length>6?' +'+(names.length-6)+' more':'');
  document.getElementById('visitfeed').addEventListener('click',function(ev){
    ev.preventDefault();
    var t=document.querySelector('.mf-list')||document.getElementById('today');
    if(t)t.scrollIntoView({behavior:'smooth'});});
  document.getElementById('visitdismiss').addEventListener('click',function(){
    localStorage.setItem('flab_seen_asof',d.as_of); bar.hidden=true;});
  bar.hidden=false;
})();
</script>"""
    )


def _watchers_feed_html() -> str:
    """The watcher-events feed (P6d): dated template firings with their audit
    hashes; silent when no feed exists yet (honest — nothing to show)."""
    try:
        from ..pipeline.digest import read_latest_data

        feed = read_latest_data("watchers") or {}
    except Exception:  # noqa: BLE001 - the home page renders without the feed
        feed = {}
    events, skips = feed.get("events", []), feed.get("skips", [])
    if not events and not skips:
        return ""
    rows = "".join(
        f'<li><span class="wk">{_esc(e.get("kind", ""))}</span> {_esc(e.get("reason", ""))}'
        f'<span class="wmeta">{_esc(e.get("date", ""))} · audit {_esc(str(e.get("sha256", ""))[:12])}</span></li>'
        for e in events[:8]
    )
    quiet = "" if events else '<p class="explain">No watcher fired — quiet by the stated thresholds.</p>'
    skipped = ("".join(f'<li class="wskip">{_esc(s.get("kind", ""))}: {_esc(s.get("reason", ""))}</li>'
                       for s in skips) if skips else "")
    return (
        '<section class="card" id="watchers"><div class="sec-head"><div>'
        '<div class="kicker">Watchers</div>'
        '<h2>What the templates are watching</h2></div></div>'
        '<p class="explain">Deterministic triggers over public data — earnings windows, squeeze '
        'fuel, insider clusters, verdict changes, the macro line. Every firing carries its '
        'stated reason and an audit hash; missing sources say so.</p>'
        f'<ul class="wlist">{rows}{skipped}</ul>{quiet}</section>'
    )


def render_dashboard(state) -> str:
    t = state.tennis["summary"]
    sources_total = state.sources.get("total", 0)
    calib = "Well-calibrated" if t["ece"] < 0.04 else "Roughly calibrated"
    ar = state.arena
    mc = state.macro

    # dateline + issue number from the run timestamp (data, not wall-clock)
    try:
        dt = datetime.strptime(str(state.generated)[:16], "%Y-%m-%d %H:%M")
        dateline = f"{dt.strftime('%A')}, {dt.strftime('%B')} {dt.day}, {dt.year}"
        issue = dt.timetuple().tm_yday
    except (ValueError, TypeError):
        dateline, issue = _esc(state.generated), 1

    leader = "—"
    ml_rank = None
    if not ar.get("empty") and ar.get("leaderboard"):
        board = ar["leaderboard"]
        leader = _plain(board[0]["strategy"])
        for i, r in enumerate(board, 1):
            if r["strategy"] == "ml_ranker":
                ml_rank = i
    recession = _pct(mc["recession_prob_12m"]) if not mc.get("empty") and mc.get("recession_prob_12m") is not None else "—"
    n_movers = len(state.movers.get("movers", [])) if not state.movers.get("empty") else 0

    glance = "".join([
        _kpi("Moving now", f"{n_movers}" if n_movers else "—", "stocks scanned today", "", "now"),
        _kpi("Top strategy", leader, "in the paper-trading race", "good", "strategies"),
        _kpi("Forecast quality", calib, "predictions match reality", "", "trust"),
        _kpi("Recession odds", recession, "next 12 months", "", "economy"),
    ])

    now_body = _movers_board(state.movers)
    odds_body = _odds_board(state.market_edges)

    # ---- agent desk (paper book on real data) ----
    ag = state.agent
    if not ag or not ag.get("picks"):
        agent_body = _empty("The agent hasn't opened any paper positions yet — it acts on the next data scan "
                            "(needs the live movers + odds feed).")
    else:
        ret = ag.get("return", 0.0)
        head = (
            '<div class="deskstat">'
            f'<div><span>Paper equity</span><b>${ag["equity"]:,.0f}</b></div>'
            f'<div><span>Stock book return</span><b class="{"up" if ret >= 0 else "down"}">{_pct(ret,2,signed=True)}</b></div>'
            f'<div><span>Open</span><b>{ag["n_stocks"]} stocks · {ag["n_markets"]} market bets</b></div>'
            '</div>'
        )
        blot = "".join(f"<li>{_esc(b)}</li>" for b in ag.get("blotter", []))
        blotter = f'<h3>Trade blotter</h3><ul class="blotter">{blot}</ul>' if blot else ""
        prows = []
        for p in ag["picks"]:
            stock = p["kind"] == "stock"
            entry = f'${p["entry"]:,.2f}' if stock else _pct(p["entry"], 0)
            now = f'${p["mark"]:,.2f}' if stock else _pct(p["mark"], 0)
            cls = "up" if p["pnl"] >= 0 else "down"
            # alloc% only when the ledger stored it — never reconstructed after the fact
            alloc = format_metric(p.get("alloc"), "{:.0%}")
            prows.append(
                f'<tr><td>{_esc(p["name"])}</td><td>{_esc(p["side"])}</td>'
                f'<td class="num">{_esc(alloc)}</td>'
                f'<td class="num">{entry}</td><td class="num">{now}</td>'
                f'<td class="num {cls}">{_pct(p["pnl"],1,signed=True)}</td><td>{_esc(p["thesis"])}</td></tr>'
            )
        table = ('<div class="twrap"><table><thead><tr><th>position</th><th>side</th>'
                 '<th class="num">alloc</th>'
                 '<th class="num">entry</th><th class="num">now</th><th class="num">P&amp;L</th><th>why</th>'
                 f'</tr></thead><tbody>{"".join(prows)}</tbody></table></div>')
        agent_body = head + blotter + table

    if ar.get("empty"):
        arena_body = _empty("The strategy race hasn't run yet. Locally: flab-sim run --bars 250.")
    else:
        cols = [("strategy", "strategy", "name"), ("total_return", "return", "signed"),
                ("sharpe", "risk-adj.", "signed"), ("deflated_sharpe", "confidence real", "num"),
                ("max_drawdown", "worst drop", "signed")]
        max_ret = max((abs(r["total_return"]) for r in ar["leaderboard"]), default=1.0) or 1.0
        table = _sortable(ar["leaderboard"], cols, bar_col="total_return", bar_max=max_ret, highlight="ml_ranker")
        pbo = ar.get("pbo", 0.0)

        # the gate stated in the open (Engo honesty): candidates -> survivors -> default
        gate = ar.get("gate") or {}
        gate_html = ""
        if gate:
            if gate.get("hold"):
                verdict = (f'<b class="hold">0 survive &#8594; the stated allocation is 100% '
                           f'{_esc(gate.get("benchmark", "benchmark"))}</b>')
            else:
                names = ", ".join(_plain(s) for s in gate.get("survivors", []))
                verdict = f"<b>{len(gate.get('survivors', []))} survive: {_esc(names)}</b>"
            crowd = ar.get("crowding") or {}
            crowd_html = ""
            if crowd:
                flag = ('<b class="warn">crowded — the fleet is mostly one bet</b>' if crowd.get("crowded")
                        else "not crowded")
                crowd_html = (f'<span class="crowd">Crowding gauge: mean pairwise correlation '
                              f'{crowd.get("mean_pairwise_corr", 0):+.2f} &#183; {flag}</span>')
            gate_html = (
                f'<div class="gateline">THE GATE: {gate.get("k", 0)} candidates &#183; '
                f'deflated-Sharpe / PBO / fleet-FDR &#183; {verdict}{crowd_html}</div>'
            )
        ml_line = ""
        if ml_rank:
            ml_line = (f'<div class="mlcard"><span class="dot" style="background:{STRATEGY_COLORS["ml_ranker"]}"></span>'
                       f'<div><b>The ML model ranks #{ml_rank} of {len(ar["leaderboard"])}.</b> It is a gradient-boosted '
                       f'model that self-tunes with leak-free walk-forward validation, then longs the names it predicts '
                       f'will lead. On this near-random synthetic market it does not beat simple momentum — which is the '
                       f'honest result, and exactly what the test is for.</div></div>')
        arena_body = (
            gate_html
            + '<div class="chart wide">' + equity_svg(ar["curves"]) + "</div>" + table + ml_line
            + f'<div class="note"><strong>How to read it.</strong> Click any column to sort. This is <em>paper trading</em> '
            f'on historical prices with fees — not real money. The benchmark rows (buy &amp; hold, random) are always '
            f'on the board — a strategy that can\'t beat them isn\'t one. “Confidence real” (0–1) is the deflated Sharpe: '
            f'how sure we are the result beats the best-of-K-tries luck. PBO is the chance the in-sample winner is '
            f'overfit — here <strong>{pbo:.0%}</strong>. The dashed lines are the two controls.</div>'
        )

    fw = state.forward
    if fw.get("empty"):
        forward_body = _empty("The live study hasn’t started collecting real results yet.")
    else:
        fcols = [("strategy", "strategy", "name"), ("equity", "grew to", "num"),
                 ("live_return", "live return", "signed"), ("live_marks", "live checks", "int")]
        forward_body = ('<div class="chart wide">' + equity_svg(fw["curves"]) + "</div>"
                        + _sortable(fw["leaderboard"], fcols, bar_col="live_return", bar_max=0.5, highlight="ml_ranker"))
        live = fw.get("live_started")
        forward_body += ('<p class="fine">' + (f"Real, out-of-sample results accruing since {_esc(live)}."
                         if live else "Genuine day-by-day results start on the next scheduled run.") + "</p>")

    stat_by = {r["strategy"]: r for r in ar["leaderboard"]} if not ar.get("empty") else {}
    cards = []
    for c in state.strategies:
        s = stat_by.get(c["name"], {})
        ret = _pct(s["total_return"], 0, signed=True) if s else "—"
        cls = "up" if (s and s["total_return"] >= 0) else ("down" if s else "")
        cards.append(
            f'<div class="scard"><div class="scard-top"><span class="swatch" style="background:{STRATEGY_COLORS.get(c["name"], INK)}"></span>'
            f'<span class="sname">{_esc(_plain(c["name"]))}</span><span class="sret {cls}">{ret}</span></div>'
            f'<p>{_esc(c["description"])}</p></div>'
        )
    strategies_extra = '<h3>How each one works</h3><div class="scards">' + "".join(cards) + "</div>"

    nba, sc = state.nba["summary"], state.soccer["eval"]
    base_brier = t["base_rate"] * (1 - t["base_rate"])
    sports_body = (
        '<div class="split"><div class="chart">' + reliability_svg(state.tennis["reliability"]) + "</div>"
        '<div class="readout">'
        + _stat("How close to reality", "Very close", f"error {t['ece']:.1%} (0% = perfect)", big=True)
        + _stat("Beats a coin flip by", f"{t['brier_skill_score']:+.0%}", "vs. guessing the base rate")
        + _stat("Tested on", f"{t['n']:,} matches", state.tennis["label"])
        + '<p class="fine">Group predictions by confidence, then check how often those things happened. '
        "On the line = trustworthy.</p></div></div>"
        '<div class="grid3">' + "".join([
            _mini("Tennis", f"{t['brier']:.3f}", f"vs {base_brier:.3f} baseline", f"beats a coin flip by {t['brier_skill_score']:+.0%}"),
            _mini("Basketball (NBA)", f"{nba['brier']:.3f}", f"vs {nba['base_rate']*(1-nba['base_rate']):.3f} baseline", f"home team wins {nba['base_rate']:.0%} of the time"),
            _mini("Soccer", f"{sc['rps']:.3f}", f"vs {sc['rps_baseline']:.3f} baseline", f"home {sc['base_rates']['home']:.0%} / draw {sc['base_rates']['draw']:.0%} / away {sc['base_rates']['away']:.0%}"),
        ]) + "</div>"
    )

    if mc.get("empty"):
        macro_body = _empty("The economy check needs the live FRED feed.")
    else:
        prob = mc["recession_prob_12m"]
        ts = mc["term_spread"]
        gauge = ""
        if prob is not None:
            gauge = (f'<div class="gauge"><div class="gbar"><i style="width:{prob*100:.0f}%"></i></div>'
                     f'<div class="glabels"><span>0%</span><span>recession odds, 12 mo</span><span>100%</span></div></div>')
        rows = [_stat("Recession odds (next 12 months)", _pct(prob) if prob is not None else "—",
                      "from the shape of the yield curve", big=True)]
        for label, v in list(mc["levels"].items())[:4]:
            if v["value"] is not None:
                rows.append(_stat(label, _fmt(v["value"], 2)))
        macro_body = gauge + "".join(rows) + f'<p class="fine">A probability, not a certainty. Yield-curve model, live data as of {_esc(ts["date"])}.</p>'

    fl = state.forecast_log
    if fl.get("empty"):
        track_body = _empty("No forecasts have been logged and resolved yet. Once real predictions are recorded and "
                            "their markets settle, this fills with a live accuracy score — including whether it beats the market price.")
    else:
        s = fl["score"]
        rows = [_stat("Forecasts scored", str(s["n"]), f"of {fl['n_total']} logged", big=True),
                _stat("Accuracy (Brier, lower better)", _fmt(s["brier"])),
                _stat("Beats the base rate by", f"{s['brier_skill_score']:+.0%}")]
        beat = fl.get("beat") or {}
        if beat.get("n"):
            rows.append(_stat("Beats the market by", f"{beat['brier_skill_vs_market']:+.0%}",
                              f"right more often than the price {beat['beat_rate']:.0%} of the time"))
        track_body = "".join(rows)

    # ---- edge research ----
    ef = state.edge_features
    if ef.get("empty") or not ef.get("rows"):
        edges_body = _empty("Edge-feature scoring is unavailable right now.")
    else:
        erows = "".join(
            f'<tr><td>{_esc(r["name"])}</td>'
            f'<td class="num {"up" if r["skill"] >= 0 else "down"}">{_pct(r["skill"],1,signed=True)}</td>'
            f'<td>{_esc(r["what"])}</td><td class="estatus">{_esc(r["status"])}</td></tr>'
            for r in ef["rows"]
        )
        edges_body = (
            '<div class="twrap"><table><thead><tr>'
            '<th>feature</th><th class="num">OOS skill</th><th>what it measures</th><th>status</th>'
            f'</tr></thead><tbody>{erows}</tbody></table></div>'
            '<p class="fine">"OOS skill" is the out-of-sample Brier-skill versus each feature\'s baseline on a '
            'deterministic, leak-free synthetic benchmark — evidence the signal is real, not overfit. Every feature '
            'is property-tested so pure noise scores ~0. Real-world skill accrues live and is expected to be far '
            'smaller; this is the honest scaffold, not a promise of profit.</p>'
        )

    # ---- ahead of the curve (voices) ----
    vlb = state.voices
    vrows = vlb.get("rows") or []
    if not vrows:
        voices_body = _empty("Voice track records haven't accrued yet.")
    else:
        trs = "".join(
            f'<tr><td>{_esc(r["voice"])}</td>'
            f'<td class="num {"up" if r["brier_skill"] >= 0 else "down"}">{_pct(r["brier_skill"],1,signed=True)}</td>'
            f'<td class="num">{"—" if not r["lead"] else str(r["lead"]) + "d early"}</td>'
            f'<td class="num">{int(r["n_calls"])}</td>'
            f'<td class="num">{_bar(min(1.0, r["weight"] / 0.3), STRATEGY_COLORS["momentum_60d"])}'
            f'<span>{r["weight"]:.2f}</span></td></tr>'
            for r in vrows
        )
        asof = _esc(vlb.get("as_of", ""))
        voices_body = (
            '<div class="twrap"><table class="sortable"><thead><tr>'
            '<th data-sort="0">voice<i></i></th><th data-sort="1" class="num">right (Brier-skill)<i></i></th>'
            '<th data-sort="2" class="num">early (lead)<i></i></th><th data-sort="3" class="num">calls<i></i></th>'
            '<th data-sort="4" class="num">weight<i></i></th>'
            f'</tr></thead><tbody>{trs}</tbody></table></div>'
            f'<p class="fine">Ranked by <em>record</em>, never followers — "right" is Brier-skill vs the base rate, '
            f'"early" is the lead at which the voice\'s calls best predict the move, and a stale record decays. '
            f'As of {asof}. This is a deterministic synthetic demonstration that the scoring is leak-free '
            f'(random calls score ~0); real names and ranks fill in as logged calls accrue live.</p>'
        )

    media = state.digests.get("media-watch", {"empty": True})
    media_body = ""
    if not media.get("empty"):
        for heading, content in media["sections"].items():
            if content["table"]:
                media_body += f"<h3>{_esc(heading)}</h3>" + _md_table(content["table"])

    # Rallies IA: one crisp surface per job in the sticky nav
    platform_top = _platform_home(state)

    nav = "".join(
        f'<a href="{href}">{lbl}</a>' for href, lbl in [
            ("#today", "Verdicts"), ("portfolio.html", "Portfolio"),
            ("journal.html", "Journal"), ("compare.html", "Compare"), ("#now", "Movers"),
            ("#markets", "Odds"), ("#edges", "Edges"), ("arena.html", "Arena"),
            ("scorecard.html", "Scorecard"), ("#agent", "Desk"), ("#economy", "Macro"),
            ("#voices", "Watch"),
        ]
    )

    qchips = (
        '<div class="qchips">'
        '<a href="#edges">Is anything squeezing?</a>'
        '<a href="#agent">What is the desk holding?</a>'
        '<a href="#markets">Where is the money betting?</a>'
        '<a href="#trust">Can I trust these numbers?</a>'
        '<a href="scorecard.html">How right have we been?</a>'
        "</div>"
    )

    # ---- the tape: a filtered activity feed from the ledger + forecast log ----
    feed_items = list(getattr(state, "feed", None) or [])
    if feed_items:
        rows = "".join(
            f'<li data-feed-kind="{_esc(i.get("kind","note"))}">'
            f'<span class="fk">{_esc(i.get("kind","note"))}</span> {_esc(i.get("text",""))}</li>'
            for i in feed_items[:30]
        )
        feed_body = (
            '<div class="tabs" data-feed-filter>'
            '<button data-kind="all" class="on">All</button>'
            '<button data-kind="pick">Picks</button>'
            '<button data-kind="resolve">Resolves</button>'
            '<button data-kind="alert">Alerts</button></div>'
            f'<ul class="feed">{rows}</ul>'
        )
        feed_section = _section("feed", "The tape", "What just happened",
                                "Every pick, resolution and alert as it lands — the desk's paper trail, newest first.",
                                feed_body, mascot="feed")
    else:
        feed_section = ""

    media_section = _section("media", "Media watch", "What the news and voices are saying",
                             "About 100 outlets and commentators, scanned for which companies and themes they're naming today.",
                             media_body) if media_body else ""

    return f"""<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="1800">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='4' fill='%230F766E'/%3E%3Cpath d='M6 22 L13 15 L18 19 L26 9' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<title>The Forecasting Briefing</title>
<script>document.documentElement.className="js";</script>
<style>
:root {{
  --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --muted:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --accent-soft:{ACCENT_SOFT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular","Cascadia Code",Menlo,Consolas,monospace;
  --serif:var(--mono); --display:var(--mono); --sans:var(--mono);
}}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--paper); color:var(--ink); font:400 14.5px/1.65 var(--mono);
  -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums lining-nums; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 22px 80px; }}
a {{ color:var(--accent); text-decoration:none; }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}

/* ---- masthead ---- */
.masthead {{ text-align:center; padding:30px 0 0; }}
.wordmark {{ font:700 clamp(24px,4vw,38px)/1.05 var(--display); letter-spacing:.06em; text-transform:uppercase; }}
.subword {{ font:400 13px/1.4 var(--serif); color:var(--muted); margin-top:8px; }}
.dateline {{ font:600 11px/1 var(--mono); letter-spacing:.07em; color:var(--muted);
  font-variant-caps:all-small-caps; text-transform:lowercase;
  border-top:1px solid var(--rule); border-bottom:3px solid var(--ink);
  margin-top:16px; padding:9px 0; display:flex; flex-wrap:wrap; gap:6px 18px; justify-content:center; }}
.dateline .live::before {{ content:""; display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--up); margin-right:5px; vertical-align:middle; }}

/* ---- lead ---- */
.lead {{ padding:34px 0 8px; }}
.kicker {{ font:600 12px/1 var(--sans); letter-spacing:.11em; text-transform:uppercase; color:var(--accent); margin-bottom:9px; }}
.lead h1 {{ font:700 clamp(24px,4.4vw,40px)/1.1 var(--display); letter-spacing:.03em; text-transform:uppercase; text-wrap:balance; }}
.lead .deck {{ font:400 15px/1.6 var(--serif); color:var(--muted); max-width:52ch; margin-top:12px; }}
.qchips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
.qchips a {{ font:600 12px/1 var(--mono); color:var(--ink); background:var(--card); border:1px solid var(--rule);
  border-radius:999px; padding:8px 13px; }}
.qchips a:hover {{ border-color:var(--accent); color:var(--accent); }}

/* ---- P6b platform home ---- */
.phero {{ padding:34px 0 20px; text-align:center; }}
.pbrand {{ font:800 clamp(24px,4vw,40px)/1 var(--mono); letter-spacing:.14em; }}
.ptag {{ font:400 14px/1.6 var(--mono); color:var(--muted); max-width:60ch; margin:12px auto 0; }}
.ptag b {{ color:var(--ink); }}
.search {{ position:relative; max-width:560px; margin:22px auto 0; }}
.search input {{ width:100%; font:500 15px/1.4 var(--mono); color:var(--ink); background:var(--card);
  border:1px solid var(--rule); border-radius:8px; padding:13px 16px; }}
.search input:focus {{ outline:2px solid var(--accent); outline-offset:1px; }}
.qres {{ position:absolute; left:0; right:0; top:calc(100% + 4px); z-index:30; background:var(--card);
  border:1px solid var(--rule); border-radius:8px; overflow:hidden; text-align:left; display:none; }}
.qres.on {{ display:block; }}
.qres a, .qres div {{ display:flex; justify-content:space-between; gap:10px; padding:10px 14px;
  font:500 13px/1 var(--mono); border-bottom:1px solid var(--rule); color:var(--ink); }}
.qres a:last-child, .qres div:last-child {{ border-bottom:0; }}
.qres a:hover {{ background:var(--paper); }}
.qres .muted {{ color:var(--faint); }}
.profctl {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:center; margin:18px 0 0; }}
.profctl .pc-lab {{ font:600 12px/1 var(--mono); color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
.profctl select {{ font:600 12px/1 var(--mono); color:var(--ink); background:var(--card);
  border:1px solid var(--rule); border-radius:6px; padding:8px 10px; }}
.profctl .pc-note {{ flex-basis:100%; text-align:center; font:400 11.5px/1.4 var(--mono); color:var(--faint); margin-top:4px; }}
.etfrow {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; padding:12px 0; border-bottom:1px solid var(--rule); margin-bottom:14px; }}
.etfrow-lab {{ font:700 10.5px/1 var(--mono); text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin-right:6px; }}
.vgrid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(112px,1fr)); gap:8px; }}
.vchip {{ display:flex; flex-direction:column; gap:4px; padding:11px 12px; border:1px solid var(--rule);
  border-radius:6px; background:var(--card); }}
.vchip:hover {{ border-color:var(--accent); }}
.vchip.insuf {{ opacity:.5; }}
.vc-sym {{ font:800 15px/1 var(--mono); }}
.vc-lab {{ font:700 11px/1 var(--mono); letter-spacing:.03em; }}
.mfeed {{ list-style:none; }}
.mfeed li {{ display:flex; flex-wrap:wrap; gap:6px 10px; align-items:baseline; padding:8px 0; border-bottom:1px solid var(--rule); font-size:13px; }}
.mfeed li:last-child {{ border-bottom:0; }}
.mf-move {{ font-weight:700; font-size:12px; }}
.mf-why {{ color:var(--muted); font-size:12px; }}
.mf-none {{ color:var(--faint); font-size:13px; }}
.enginebar {{ margin-top:26px; }}
.engineroom-head {{ margin:8px 0 4px; }}
.engineroom-head h2 {{ font:700 15px/1.2 var(--mono); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }}

nav {{ position:sticky; top:0; z-index:20; background:rgba(250,249,246,.9);
  backdrop-filter:blur(6px); border-bottom:1px solid var(--rule); margin:22px -22px 20px;
  padding:0 22px; display:flex; gap:2px; overflow-x:auto; }}
nav a {{ padding:12px 13px; font:600 12px/1 var(--sans); letter-spacing:.04em; text-transform:uppercase;
  color:var(--muted); white-space:nowrap; border-bottom:2px solid transparent; }}
nav a:hover {{ color:var(--ink); }}
nav a.active {{ color:var(--accent); border-bottom-color:var(--accent); }}

.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); margin:0 0 6px; border:1px solid var(--rule); border-radius:3px; overflow:hidden; }}
.kpi {{ padding:16px 18px; border-right:1px solid var(--rule); display:block; color:inherit; background:var(--card); }}
.kpi:last-child {{ border-right:0; }}
a.kpi:hover {{ background:#fdfcf9; }}
.kpi-label {{ font:600 11px/1.2 var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }}
.kpi-val {{ font:700 27px/1.12 var(--display); letter-spacing:-.01em; margin:8px 0 2px; }}
.kpi.kpi-good .kpi-val {{ color:var(--accent); }}
.kpi-sub {{ font:400 12.5px/1.3 var(--serif); color:var(--faint); }}

.card {{ background:var(--card); border:1px solid var(--rule); border-radius:3px; padding:26px 28px; margin:14px 0; scroll-margin-top:56px; }}
.sec-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }}
.card h2 {{ font:700 19px/1.25 var(--display); letter-spacing:.04em; text-transform:uppercase; text-wrap:balance; }}
.mascot {{ flex:none; width:44px; height:44px; opacity:.9; }}
.peers {{ display:flex; gap:8px; overflow-x:auto; padding-bottom:10px; margin-bottom:14px; border-bottom:1px solid var(--rule); }}
.peers a {{ flex:none; font:600 12px/1 var(--mono); color:var(--ink); background:var(--paper);
  border:1px solid var(--rule); border-radius:999px; padding:7px 12px; white-space:nowrap; }}
.peers a b.up {{ color:var(--up); }} .peers a b.down {{ color:var(--down); }}
.wellcon {{ display:grid; grid-template-columns:1fr 1fr; gap:0; border:1px solid var(--rule); border-radius:3px; margin-top:18px; overflow:hidden; }}
.wellcon > div {{ padding:14px 16px; background:var(--card); }}
.wellcon > div:first-child {{ border-right:1px solid var(--rule); }}
.wellcon h4 {{ font:700 11.5px/1 var(--mono); letter-spacing:.06em; text-transform:uppercase; margin-bottom:9px; }}
.wellcon .wc-good h4 {{ color:var(--up); }} .wellcon .wc-bad h4 {{ color:var(--down); }}
.wellcon ul {{ list-style:none; }}
.wellcon li {{ font:400 12.5px/1.5 var(--mono); color:var(--muted); padding:3px 0; }}
.wellcon li b {{ color:var(--ink); }}
@media (max-width:900px) {{ .wellcon {{ grid-template-columns:1fr; }} .wellcon > div:first-child {{ border-right:0; border-bottom:1px solid var(--rule); }} }}
.card h3 {{ font:600 12px/1.3 var(--sans); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); margin:24px 0 11px; }}
.src {{ font:600 10.5px/1.4 var(--mono); color:var(--faint); white-space:nowrap; text-transform:uppercase; letter-spacing:.05em; text-align:right; }}
.explain {{ color:var(--muted); font:400 16px/1.55 var(--serif); margin:9px 0 20px; max-width:68ch; }}
.wlist {{ list-style:none; padding:0; margin:0; }}
.wlist li {{ padding:9px 0; border-bottom:1px solid var(--rule); font:400 13.5px/1.5 var(--mono); }}
.wlist li:last-child {{ border-bottom:0; }}
.wk {{ font:700 10.5px/1 var(--mono); text-transform:uppercase; letter-spacing:.05em;
  background:var(--ink); color:var(--paper); border-radius:3px; padding:3px 7px; margin-right:8px; }}
.wmeta {{ display:block; color:var(--faint); font-size:11px; margin-top:2px; }}
.wskip {{ color:var(--faint); font-size:12px; }}
.visitbar {{ display:flex; gap:12px; align-items:center; background:var(--ink); color:var(--paper);
  border-radius:4px; padding:11px 16px; margin:14px 0; font:600 13px/1.4 var(--mono); }}
.visitbar a {{ color:var(--paper); text-decoration:underline; white-space:nowrap; }}
.visitbar button {{ margin-left:auto; background:none; border:0; color:var(--paper);
  font-size:14px; cursor:pointer; }}

.tabs {{ display:inline-flex; gap:2px; border:1px solid var(--rule); border-radius:3px; padding:3px; margin-bottom:18px; }}
.tabs button {{ font:600 12px/1 var(--sans); letter-spacing:.03em; text-transform:uppercase; color:var(--muted); background:none; border:0; padding:8px 14px; border-radius:2px; cursor:pointer; }}
.tabs button.on {{ background:var(--ink); color:var(--paper); }}
.hidden {{ display:none !important; }}

.movers {{ display:grid; grid-template-columns:repeat(4,1fr); gap:0; border-top:1px solid var(--rule); }}
.mover {{ padding:15px 15px 15px 0; border-right:1px solid var(--rule); border-bottom:1px solid var(--rule); }}
.mover:nth-child(4n) {{ border-right:0; }}
.movers .mover {{ padding-left:15px; }}
.movers .mover:nth-child(4n+1) {{ padding-left:0; }}
.mv-top {{ display:flex; justify-content:space-between; align-items:baseline; }}
.tk {{ font:700 16px/1 var(--sans); letter-spacing:-.01em; }}
.px {{ font:600 12.5px/1 var(--mono); color:var(--muted); }}
.spark {{ width:100%; height:38px; margin:9px 0; display:block; }}
.chips {{ display:flex; flex-wrap:wrap; gap:5px; }}
.chip {{ font:600 11px/1 var(--mono); padding:4px 6px; border-radius:2px; background:var(--paper); }}
.chip em {{ font-style:normal; color:var(--faint); font-weight:500; }}
.chip.up {{ color:var(--up); }} .chip.down {{ color:var(--down); }} .chip.flat {{ color:var(--muted); }}
.mv-score {{ display:flex; align-items:center; gap:8px; margin-top:11px; font:600 11px/1 var(--sans); text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
.mv-score b {{ margin-left:auto; font-family:var(--mono); color:var(--ink); }}
.mv-news {{ font:400 13px/1.4 var(--serif); color:var(--muted); margin-top:10px;
  display:-webkit-box; -webkit-line-clamp:3; line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}

.ibar {{ display:inline-block; width:52px; height:6px; background:var(--rule); border-radius:2px; overflow:hidden; vertical-align:middle; }}
.ibar i {{ display:block; height:100%; }}

.oddswrap {{ display:grid; grid-template-columns:repeat(2,1fr); gap:0; border-top:1px solid var(--rule); }}
.odds {{ padding:15px 20px 15px 0; border-bottom:1px solid var(--rule); }}
.odds:nth-child(odd) {{ border-right:1px solid var(--rule); padding-right:20px; }}
.odds:nth-child(even) {{ padding-left:20px; }}
.odds-q {{ font:600 15px/1.35 var(--serif); margin-bottom:10px; }}
.odds-q .sim {{ float:right; font:600 10px/1 var(--mono); color:var(--faint); text-transform:uppercase; }}
.ob {{ display:flex; align-items:center; gap:10px; margin:5px 0; font:400 13px/1 var(--mono); }}
.ob label {{ width:82px; color:var(--muted); font-family:var(--sans); }}
.ob .ibar {{ flex:1; width:auto; height:9px; }}
.ob span {{ width:56px; text-align:right; font-weight:600; }}
.odds-edge {{ margin-top:8px; font:400 12.5px/1.4 var(--serif); color:var(--muted); }}
.odds-edge b {{ color:var(--accent); font-family:var(--mono); }}
.ocols {{ display:grid; grid-template-columns:1fr 1fr; gap:14px 30px; }}
.ocol h3 {{ margin-top:6px; }}
.odds1 {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px 12px; padding:9px 0; border-bottom:1px solid var(--rule); }}
.odds1:last-child {{ border-bottom:0; }}
.o1-q {{ flex:1 1 auto; font:400 14px/1.35 var(--serif); }}
.odds1 .ob {{ flex:0 0 128px; }}
.odds1 .ob .ibar {{ height:8px; }}
.o1-v {{ display:none; }}
.odds1 .why {{ flex-basis:100%; }}

/* evidence expander: odds in the summary, drivers + caveat on open */
.why {{ margin-top:9px; }}
.why > summary {{ list-style:none; cursor:pointer; font:600 12px/1 var(--sans); color:var(--muted);
  text-transform:uppercase; letter-spacing:.04em; padding:5px 0; }}
.why > summary::-webkit-details-marker {{ display:none; }}
.why > summary::after {{ content:" ▾"; color:var(--faint); }}
.why[open] > summary::after {{ content:" ▴"; }}
.why > summary b {{ font-family:var(--mono); color:var(--accent); font-size:13px; }}
.drivers {{ list-style:none; margin:6px 0 0; border-top:1px solid var(--rule); }}
.drivers li {{ display:flex; justify-content:space-between; gap:10px; padding:5px 0;
  border-bottom:1px solid var(--rule); font:400 12.5px/1.3 var(--serif); }}
.drivers li span {{ color:var(--muted); }}
.drivers li b {{ font-family:var(--mono); font-weight:600; }}
.drivers li.edge b {{ color:var(--accent); }}
.why .cav {{ font:italic 11.5px/1.4 var(--serif); color:var(--faint); margin-top:8px; }}
.dots {{ font-size:10px; letter-spacing:2px; color:var(--accent); margin-left:6px; }}
.trust {{ display:inline-block; font:600 10.5px/1.5 var(--mono); color:var(--muted); background:var(--paper);
  border:1px solid var(--rule); border-radius:2px; padding:4px 8px; margin-top:10px; }}
.ev h5 {{ font:700 10.5px/1 var(--mono); letter-spacing:.07em; text-transform:uppercase; color:var(--muted); margin:10px 0 4px; }}
.ev .whynow {{ font:400 12.5px/1.5 var(--mono); color:var(--ink); }}
.ev .push {{ font-style:normal; font-size:9px; }}
.wf {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:4px; }}
.wf ul {{ list-style:none; }}
.wf li {{ font:400 11.5px/1.5 var(--mono); color:var(--muted); padding:2px 0; }}
.wf .wfg {{ color:var(--up); }} .wf .wfb {{ color:var(--down); }}
.gateline {{ font:600 13px/1.6 var(--mono); background:var(--card); border:1px solid var(--rule);
  border-left:4px solid var(--accent); border-radius:3px; padding:12px 16px; margin-bottom:16px; }}
.gateline b.hold {{ color:var(--accent); }}
.gateline .crowd {{ display:block; font-weight:400; font-size:12px; color:var(--muted); margin-top:4px; }}
.gateline .crowd b.warn {{ color:var(--down); }}

.chart svg, .chart.wide svg {{ width:100%; height:auto; display:block; }}
.split {{ display:grid; grid-template-columns:1.25fr 1fr; gap:26px; align-items:center; }}
.ax {{ font:500 11px var(--sans); fill:var(--faint); }}
.axt {{ font:600 12px var(--sans); fill:var(--muted); }}
.diag {{ font:italic 11px var(--serif); fill:var(--faint); }}
.leg {{ font:500 13px var(--sans); fill:var(--ink); }}
.readout {{ display:flex; flex-direction:column; }}

.stat {{ display:flex; align-items:baseline; gap:12px; padding:11px 0; border-bottom:1px solid var(--rule); flex-wrap:wrap; }}
.stat:last-child {{ border-bottom:0; }}
.stat-label {{ font:400 14px/1.4 var(--serif); color:var(--muted); flex:1 1 auto; }}
.stat-val {{ font:600 19px/1 var(--mono); }}
.stat.big .stat-val {{ font:700 30px/1 var(--display); color:var(--accent); }}
.stat-sub {{ font:400 12px/1.3 var(--serif); color:var(--faint); flex-basis:100%; text-align:right; margin-top:-3px; }}

.grid3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:0; margin-top:20px; border-top:1px solid var(--rule); }}
.mini {{ padding:16px 18px 16px 0; border-right:1px solid var(--rule); }}
.mini:last-child {{ border-right:0; }}
.grid3 .mini {{ padding-left:18px; }} .grid3 .mini:first-child {{ padding-left:0; }}
.mini h4 {{ font:700 15px/1 var(--display); margin-bottom:9px; }}
.mini .m-val {{ font:700 24px/1 var(--mono); }}
.mini .m-base {{ font:400 12.5px/1.3 var(--serif); color:var(--faint); margin-top:4px; }}
.mini .m-note {{ font:400 13px/1.4 var(--serif); color:var(--muted); margin-top:9px; }}

table {{ width:100%; border-collapse:collapse; font:400 14px/1.5 var(--mono); font-variant-numeric:tabular-nums lining-nums; }}
.twrap {{ overflow-x:auto; }}
th {{ text-align:left; font:600 11px/1 var(--sans); letter-spacing:.05em; font-variant-caps:all-small-caps; text-transform:lowercase;
  color:var(--muted); padding:0 12px 9px 0; border-bottom:2px solid var(--ink); }}
table.sortable th {{ cursor:pointer; user-select:none; white-space:nowrap; }}
table.sortable th i {{ display:inline-block; width:0; height:0; margin-left:4px; opacity:.35;
  border-left:4px solid transparent; border-right:4px solid transparent; border-top:5px solid currentColor; }}
table.sortable th.asc i {{ border-top:0; border-bottom:5px solid currentColor; opacity:1; }}
table.sortable th.desc i {{ opacity:1; }}
th.num {{ text-align:right; }}
td {{ padding:10px 12px 10px 0; border-bottom:1px solid var(--rule); }}
tr:last-child td {{ border-bottom:0; }}
td:first-child {{ font-family:var(--serif); }}
td.num {{ text-align:right; }}
td.num span {{ display:inline-block; min-width:56px; }}
td .swatch, .scard .swatch {{ width:9px; height:9px; border-radius:2px; display:inline-block; margin-right:8px; }}
tr.hl td {{ background:#faf4ee; }}
.up {{ color:var(--up); }} .down {{ color:var(--down); }}

.mlcard {{ display:flex; gap:12px; align-items:flex-start; background:#faf4ee; border:1px solid #ecd9c8;
  border-radius:3px; padding:15px 17px; margin-top:16px; font:400 14px/1.5 var(--serif); color:#5a3a25; }}
.mlcard .dot {{ width:11px; height:11px; border-radius:50%; margin-top:5px; flex:none; }}
.mlcard b {{ color:#3f2717; }}

.note {{ background:var(--accent-soft); border:1px solid #cfe2de; border-radius:3px; padding:14px 16px; font:400 14px/1.55 var(--serif); color:#1d3b37; margin-top:18px; }}
.fine {{ font:400 13px/1.5 var(--serif); color:var(--muted); margin-top:13px; max-width:72ch; }}
.empty {{ color:var(--muted); font:400 15px/1.5 var(--serif); background:#fbfaf7; border:1px dashed var(--rule); border-radius:3px; padding:16px; }}

.deskstat {{ display:flex; gap:30px; flex-wrap:wrap; margin-bottom:16px; }}
.deskstat span {{ display:block; font:600 11px/1 var(--sans); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); margin-bottom:5px; }}
.deskstat b {{ font:700 27px/1.05 var(--display); }}
.blotter {{ list-style:none; font:400 13px/1.6 var(--mono); border-top:1px solid var(--rule); margin:6px 0 18px; }}
.blotter li {{ padding:7px 0; border-bottom:1px solid var(--rule); }}
.blotter li:last-child {{ border-bottom:0; }}
.gauge {{ margin:2px 0 18px; }}
.gbar {{ height:14px; border-radius:2px; background:linear-gradient(90deg,#e8f1ef,#f3ead6,#f2dad2); position:relative; overflow:hidden; }}
.gbar i {{ position:absolute; top:0; bottom:0; left:0; border-right:3px solid var(--ink); }}
.glabels {{ display:flex; justify-content:space-between; font:600 11px/1 var(--mono); color:var(--faint); margin-top:6px; text-transform:uppercase; }}

.scards {{ display:grid; grid-template-columns:repeat(2,1fr); gap:0; border-top:1px solid var(--rule); }}
.scard {{ padding:13px 20px 13px 0; border-bottom:1px solid var(--rule); }}
.scard:nth-child(odd) {{ border-right:1px solid var(--rule); }}
.scard:nth-child(even) {{ padding-left:20px; }}
.scard-top {{ display:flex; align-items:center; gap:2px; }}
.sname {{ font:700 15px/1 var(--display); }}
.sret {{ margin-left:auto; font:600 14px/1 var(--mono); }}
.scard p {{ font:400 13.5px/1.45 var(--serif); color:var(--muted); margin-top:6px; }}

.faq p {{ font:400 16px/1.6 var(--serif); margin-bottom:13px; max-width:70ch; }}
.rules {{ list-style:none; }}
.rules li {{ display:flex; gap:14px; font:400 15.5px/1.5 var(--serif); padding:5px 0; align-items:baseline; }}
.rules .rn {{ color:var(--accent); font:700 18px/1 var(--display); flex:none; width:20px; }}

.feed {{ list-style:none; border-top:1px solid var(--rule); }}
.feed li {{ display:flex; gap:12px; align-items:baseline; font:400 13px/1.55 var(--mono); padding:8px 0; border-bottom:1px solid var(--rule); }}
.feed li:last-child {{ border-bottom:0; }}
.feed .fk {{ flex:none; font:700 10px/1 var(--mono); letter-spacing:.06em; text-transform:uppercase;
  color:var(--muted); background:var(--paper); border:1px solid var(--rule); border-radius:2px; padding:3px 6px; }}
.feed li[data-feed-kind="resolve"] .fk {{ color:var(--up); }}
.feed li[data-feed-kind="alert"] .fk {{ color:var(--down); }}

footer {{ margin-top:32px; padding-top:18px; border-top:1px solid var(--rule); font:400 12.5px/1.6 var(--sans); color:var(--faint); text-align:center; }}

.reveal {{ animation:up .5s cubic-bezier(.2,.6,.2,1) both; }}
@keyframes up {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}
.draw {{ stroke-dasharray:1; stroke-dashoffset:1; animation:draw .9s ease-out .15s forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
a,button,.kpi {{ transition:color .15s ease, border-color .15s ease, background .15s ease; }}
@media (prefers-reduced-motion:reduce) {{
  .reveal {{ animation:none; }}
  .draw {{ animation:none; stroke-dasharray:none; stroke-dashoffset:0; }}
}}
@media (max-width:900px) {{
  .kpis {{ grid-template-columns:repeat(2,1fr); }}
  .kpi:nth-child(2) {{ border-right:0; }}
  .movers {{ grid-template-columns:repeat(2,1fr); }}
  .mover:nth-child(2n) {{ border-right:0; }} .movers .mover:nth-child(2n+1) {{ padding-left:0; }} .movers .mover {{ padding-left:15px; }}
  .oddswrap, .split, .grid3, .scards, .ocols {{ grid-template-columns:1fr; }}
  .odds:nth-child(odd) {{ border-right:0; padding-right:0; }} .odds:nth-child(even) {{ padding-left:0; }}
  .mini {{ border-right:0; }} .grid3 .mini {{ padding-left:0; }}
  .scard:nth-child(odd) {{ border-right:0; }} .scard:nth-child(even) {{ padding-left:0; }}
}}
@media (max-width:520px) {{ .movers {{ grid-template-columns:1fr; }} .mover {{ border-right:0; }} }}
</style>
</head>
<body>
<div class="wrap">

{platform_top}

<div class="dateline enginebar">
  <span>{_esc(dateline)}</span>
  <span>{sources_total:,} sources tracked</span>
  <span><a href="agent.html" style="color:var(--accent);font-weight:700">&#9656; Live Agent Terminal</a></span>
  <span class="live" id="clock" data-gen="{_esc(state.generated)}">updated {_esc(state.generated)}</span>
</div>

<div class="engineroom-head"><h2>The engine room</h2>
  <p class="explain">Everything under the verdicts — the signals, the arena, the calibration
  and the honest track record they&#8217;re built from. {qchips}</p></div>

<nav>{nav}</nav>

<div class="kpis">{glance}</div>

{_section("agent", "Live · Paper", "The agent desk", "What the agent is actually doing right now: a paper book on live data. It buys the top trending stocks and takes YES/NO positions on the most-traded Kalshi/Polymarket markets by its recalibrated fair value, marks them to the current data, and logs every trade. Real data and real (paper) marks that accrue over runs — not real money.", agent_body, "paper account", mascot="desk")}

{_section("now", "Markets · Movers", "What's moving now", "Today's trending stocks, scored two ways: steady climbers (NVIDIA-shape trends) and fast money (GameStop-shape squeezes). Each card shows the recent price line, how far it's moved, and a signal score. Attention, not advice.", now_body, "Yahoo + Google News", mascot="movers")}

{_section("markets", "Prediction markets", "Where the money is betting", "Live YES odds on the most-traded markets at each venue — the current, high-value questions people are betting on. When the same question is priced on both Kalshi and Polymarket, the gap is flagged as a candidate to investigate (verify both resolve identically before believing any 'arb').", odds_body, "Kalshi + Polymarket", mascot="odds")}

{_section("strategies", "Strategy arena", "Strategy leaderboard", "Seven strategies — including one machine-learning model — race on historical prices with fees charged. A paper-trading experiment answering 'which style would have worked', not a live account.", arena_body + strategies_extra, mascot="arena")}

{_section("forward", "Out-of-sample", "Live study — watching it play out", "The stricter test: each run records what every strategy would buy today on a real basket, then marks it on the next run. Nothing is scored until real time passes, so it can't cheat.", forward_body)}

{_section("edges", "Edge research", "Does any of it actually beat the market?", "Leading-signal features — cross-venue lead-lag, attention acceleration, squeeze setup, price recalibration, residual momentum, deception language — each scored out-of-sample under purged walk-forward validation. Positive skill beats the baseline; pure noise scores ~0 by construction.", edges_body, mascot="edges")}

{feed_section}

{_section("voices", "Ahead of the curve", "Who's early and right?", "The people worth following aren't the loudest — they're the ones whose calls are right and land before the move. Each tracked voice is scored by Brier-skill (right) and timing lead (early), ranked by record and never by follower count. A voice making random calls scores ~0.", voices_body, mascot="watch")}

{_section("trust", "Calibration · Sports", "Are the predictions trustworthy?", "When the model says 30%, does it happen about 30% of the time? The closer the dots to the line, the more you can trust the numbers. Each sport is scored (Brier, lower is better) against simply guessing the base rate.", sports_body, "sports Elo", mascot="sports")}

{_section("economy", "Macro", "Economy check", "A read on recession risk from the bond market. When short-term rates rise above long-term ones (an 'inverted' yield curve), recessions have historically followed.", macro_body, "FRED", mascot="macro")}

{_section("record", "Track record", "The scored forecasts", "The credibility piece: real predictions, logged with a probability and scored once the outcome is known — including whether they beat the market's own price. The full ledger lives on the scorecard page.", track_body + '<p class="fine"><a href="scorecard.html">&#9656; Open the full scorecard — every forecast, hits and misses</a></p>', mascot="scorecard")}

{media_section}

<section class="card faq reveal">
  <div class="sec-head"><div><div class="kicker">The honest bit</div><h2>Is it actually making money?</h2></div></div>
  <p><strong>Honestly, no — and it's not pretending to.</strong> Everything here is simulated or paper-traded.
  The models are well-calibrated (their probabilities are trustworthy), but calibrated isn't the same as having
  an edge the market hasn't already priced in.</p>
  <p>In the simulation, momentum leads and the ML model doesn't beat it — on near-random synthetic data, that's the
  honest result. The overfitting check exists precisely so a lucky result doesn't get mistaken for skill, and the
  live study only just started collecting genuine results.</p>
  <p>If the goal is growing money, a boring index fund still beats everything here. The point is the
  <strong>skill and the honest track record</strong> — what a quant desk or grad program actually looks for.</p>
</section>

<section class="card reveal">
  <div class="sec-head"><div><div class="kicker">Method</div><h2>The ground rules</h2></div></div>
  <p class="explain">The habits that separate real research from a lucky-looking backtest — baked into every number above.</p>
  <ul class="rules">
    <li><span class="rn">1</span><span>Only test on the past, predict the future — never let tomorrow's data leak into today.</span></li>
    <li><span class="rn">2</span><span>Always charge trading fees; a cost-free backtest is a fantasy.</span></li>
    <li><span class="rn">3</span><span>Judge probabilities, not '% right' — and always beat the simple baseline.</span></li>
    <li><span class="rn">4</span><span>Discount for luck: trying many strategies means one wins by chance.</span></li>
    <li><span class="rn">5</span><span>An honest 'no edge' is a stronger result than a suspiciously perfect one.</span></li>
  </ul>
</section>

<footer>
  Set in IBM Plex Mono (system fallback) · No. {issue} · auto-refreshes every 30&nbsp;min · Not financial advice.<br>
  Data from public sources (Kalshi, Polymarket, Yahoo, FRED, arXiv, football-data.co.uk and others), each under its own terms.
</footer>
</div>

<script>
(function(){{
  document.querySelectorAll('[data-tab-group]').forEach(function(g){{
    g.querySelectorAll('button').forEach(function(b){{
      b.addEventListener('click', function(){{
        g.querySelectorAll('button').forEach(function(x){{x.classList.remove('on');}});
        b.classList.add('on');
        var scope=g.parentElement, key=b.getAttribute('data-tab');
        scope.querySelectorAll('[data-tab-panel]').forEach(function(p){{
          p.classList.toggle('hidden', p.getAttribute('data-tab-panel')!==key);
        }});
      }});
    }});
  }});
  document.querySelectorAll('table.sortable').forEach(function(tbl){{
    tbl.querySelectorAll('th[data-sort]').forEach(function(th){{
      th.addEventListener('click', function(){{
        var idx=+th.getAttribute('data-sort'), body=tbl.tBodies[0];
        var rows=[].slice.call(body.rows);
        var asc=!th.classList.contains('asc');
        tbl.querySelectorAll('th').forEach(function(x){{x.classList.remove('asc','desc');}});
        th.classList.add(asc?'asc':'desc');
        rows.sort(function(a,b){{
          var av=a.cells[idx].getAttribute('data-v'), bv=b.cells[idx].getAttribute('data-v');
          var an=parseFloat(av), bn=parseFloat(bv);
          if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;
          return asc? String(av).localeCompare(bv) : String(bv).localeCompare(av);
        }});
        rows.forEach(function(r){{body.appendChild(r);}});
      }});
    }});
  }});
  document.querySelectorAll('[data-feed-filter]').forEach(function(g){{
    g.querySelectorAll('button').forEach(function(b){{
      b.addEventListener('click', function(){{
        g.querySelectorAll('button').forEach(function(x){{x.classList.remove('on');}});
        b.classList.add('on');
        var kind=b.getAttribute('data-kind');
        g.parentElement.querySelectorAll('.feed li').forEach(function(li){{
          li.classList.toggle('hidden', kind!=='all' && li.getAttribute('data-feed-kind')!==kind);
        }});
      }});
    }});
  }});
  var links={{}}; document.querySelectorAll('nav a[href^="#"]').forEach(function(a){{links[a.getAttribute('href').slice(1)]=a;}});
  if('IntersectionObserver' in window){{
    var obs=new IntersectionObserver(function(es){{
      es.forEach(function(e){{ if(e.isIntersecting){{
        Object.keys(links).forEach(function(k){{links[k].classList.remove('active');}});
        if(links[e.target.id]) links[e.target.id].classList.add('active');
      }}}});
    }},{{rootMargin:'-45% 0px -50% 0px'}});
    document.querySelectorAll('section[id]').forEach(function(s){{obs.observe(s);}});
  }}
  var c=document.getElementById('clock');
  if(c){{ var gen=new Date((c.getAttribute('data-gen')||'').replace(' ','T'));
    if(!isNaN(gen)){{ var m=Math.max(0,Math.round((Date.now()-gen)/60000));
      var ago=m<1?'just now':m<60?m+' min ago':Math.round(m/60)+'h ago';
      c.textContent='updated '+ago; }} }}
  // gentle count-up on the numeric hero KPIs (reduced-motion respected)
  if(window.matchMedia && !matchMedia('(prefers-reduced-motion: reduce)').matches){{
    document.querySelectorAll('.kpi-val').forEach(function(el){{
      var mm=el.textContent.trim().match(/^(\\d[\\d,]*)(%?)$/); if(!mm) return;
      var target=parseInt(mm[1].replace(/,/g,''),10), suf=mm[2], t0=performance.now();
      function tick(t){{ var p=Math.min(1,(t-t0)/600);
        el.textContent=Math.round(p*target).toLocaleString()+suf;
        if(p<1) requestAnimationFrame(tick); }}
      requestAnimationFrame(tick);
    }});
  }}

  // ---- P6b: full-universe search — built symbols nav; unbuilt -> honest path ----
  function esc(x){{ return String(x).replace(/[&<>"']/g,function(c){{
    return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]; }}); }}
  var built={{}}, blist=[];
  try{{ blist=JSON.parse(document.getElementById('built').textContent||'[]'); }}catch(e){{}}
  blist.forEach(function(s){{ built[s]=true; }});  // every artifact symbol has a page (Codex: complete map)
  var uni=null;  // full listed universe, lazy-fetched (same-origin) on first use
  function loadUni(){{ if(uni!==null) return Promise.resolve();
    return fetch('universe.json').then(function(r){{return r.json();}})
      .then(function(a){{ uni={{}}; a.forEach(function(s){{uni[s]=true;}}); }})
      .catch(function(){{ uni={{}}; }}); }}  // offline: uni stays empty, degrade honestly
  var q=document.getElementById('q'), qres=document.getElementById('qres');
  function safeSym(s){{ return /^[A-Z][A-Z0-9.\\-]{{0,9}}$/.test(s); }}
  function render(s){{
    var rows=[], seen={{}};
    blist.forEach(function(x){{ if(x.indexOf(s)===0 && !seen[x]){{ seen[x]=1;
      rows.push('<a href="t/'+esc(x)+'.html"><b>'+esc(x)+'</b><span class="muted">full verdict &#8594;</span></a>'); }} }});
    if(uni){{ Object.keys(uni).forEach(function(x){{ if(rows.length<8 && x.indexOf(s)===0 && !seen[x]){{ seen[x]=1;
      rows.push('<div><b>'+esc(x)+'</b><span class="muted">listed — add to watchlist for tomorrow&#8217;s full verdict</span></div>'); }} }}); }}
    if(!rows.length){{
      if(built[s]) rows.push('<a href="t/'+esc(s)+'.html"><b>'+esc(s)+'</b><span class="muted">full verdict &#8594;</span></a>');
      else if(uni && uni[s]) rows.push('<div><b>'+esc(s)+'</b><span class="muted">listed — add to watchlist</span></div>');
      else if(uni && safeSym(s)) rows.push('<div><b>'+esc(s)+'</b><span class="muted">not a listed US stock/ETF</span></div>');
      else if(safeSym(s)) rows.push('<div><b>'+esc(s)+'</b><span class="muted">add to watchlist — listing check needs the online build</span></div>');
      else rows.push('<div><span class="muted">enter a ticker symbol</span></div>');
    }}
    qres.innerHTML=rows.slice(0,8).join(''); qres.className='qres on';
  }}
  function route(){{ var s=(q.value||'').trim().toUpperCase();
    if(!s){{qres.className='qres';qres.innerHTML='';return;}}
    // render immediately from the built list (sync), then refine once the universe
    // loads — but only if the query hasn't changed (Codex: no stale async results)
    render(s);
    loadUni().then(function(){{ if((q.value||'').trim().toUpperCase()===s) render(s); }}); }}
  if(q){{ q.addEventListener('input',route);
    q.addEventListener('keydown',function(e){{ if(e.key==='Enter'){{ var a=qres.querySelector('a'); if(a) location.href=a.href; }} }});
    document.addEventListener('click',function(e){{ if(!e.target.closest('.search')) qres.className='qres'; }}); }}

  // ---- P6b: profile control re-scores every verdict chip from its matrix ----
  var VT={{'STRONG BUY':'{UP}','BUY':'{UP}','HOLD':'{MUTED}','TRIM':'{DOWN}','AVOID':'{DOWN}','INSUFFICIENT EVIDENCE':'{FAINT}'}};
  var pH=document.getElementById('pcH'),pG=document.getElementById('pcG'),pR=document.getElementById('pcR');
  function loadProf(){{ try{{return JSON.parse(localStorage.getItem('flab_profile'))||{{}};}}catch(e){{return {{}};}} }}
  function saveProf(){{ localStorage.setItem('flab_profile',JSON.stringify({{horizon:pH.value,goal:pG.value,risk:pR.value}})); }}
  function applyProf(){{
    if(!pH) return; var key=pH.value+'|'+pG.value+'|'+pR.value;
    document.querySelectorAll('.vchip').forEach(function(a){{
      var m; try{{m=JSON.parse(a.getAttribute('data-m')||'{{}}');}}catch(e){{return;}}
      var lab=m[key]; if(!lab) return; var el=a.querySelector('.vc-lab');
      el.textContent=(lab==='INSUFFICIENT EVIDENCE')?'INSUF.':lab;
      el.style.color=VT[lab]||'{FAINT}'; a.classList.toggle('insuf',lab==='INSUFFICIENT EVIDENCE');
    }});
  }}
  if(pH){{ var p=loadProf(); if(p.horizon)pH.value=p.horizon; if(p.goal)pG.value=p.goal; if(p.risk)pR.value=p.risk;
    [pH,pG,pR].forEach(function(s){{s.addEventListener('change',function(){{saveProf();applyProf();}});}}); applyProf(); }}
}})();
</script>
</body>
</html>"""
