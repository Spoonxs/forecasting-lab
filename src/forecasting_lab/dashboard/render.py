"""Render the lab state into one interactive HTML page — an editorial briefing.

Design: a research *newspaper*, not a SaaS dashboard. Warm off-white paper, a
serif body/headline (Charter/Georgia — system fonts, always render), sans for
labels/nav, mono for figures/dates/tickers. A masthead with a spelled-out
dateline + issue number; kickers over every section; hairline rules instead of
shadows; tabular figures and real U+2212 minus signs. Still a *tool* underneath:
sticky section nav, a "what's moving now" board with price sparklines, live
prediction-market odds side by side, sortable tables, an "updated N ago" clock.
Self-contained (inline CSS/SVG + a little vanilla JS); content never JS-gated.
"""

from __future__ import annotations

import html as _html
from datetime import datetime

from ..eval.recalibration import default_fair_value
from ..predictions import market_prediction, mover_prediction

# ---------------------------------------------------------------- palette
PAPER = "#FAF9F6"
CARD = "#FFFFFF"
INK = "#1E1C19"
MUTED = "#6B6864"
FAINT = "#9A958C"
RULE = "#E5E1D8"
LINE = RULE  # alias
ACCENT = "#0F766E"
ACCENT_SOFT = "#EAF1EF"
UP = "#0B6B3A"
DOWN = "#B0281A"
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


def _section(anchor: str, kicker: str, title: str, explainer: str, body: str, source: str = "") -> str:
    src = f'<span class="src">{_esc(source)}</span>' if source else ""
    return (f'<section id="{anchor}" class="card reveal">'
            f'<div class="sec-head"><div><div class="kicker">{_esc(kicker)}</div>'
            f'<h2>{_esc(title)}</h2></div>{src}</div>'
            f'<p class="explain">{_esc(explainer)}</p>{body}</section>')


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


def _why(pred) -> str:
    """The odds + an expandable rationale — the design.md §7 contract, one element."""
    items = "".join(
        f'<li><span>{_esc(d.feature)}</span><b>{_dfmt(d.feature, d.value)}</b></li>'
        for d in pred.drivers[:5]
    )
    edge = pred.edge_vs_market
    if edge is not None and abs(edge) > 0.001:
        items += f'<li class="edge"><span>edge vs market</span><b>{_pct(edge,1,signed=True)}</b></li>'
    unit = "yes" if pred.kind == "market" else "lean"
    return (f'<details class="why"><summary><b>{pred.pct()}</b> {unit} · why</summary>'
            f'<ul class="drivers">{items}</ul>'
            f'<p class="cav">{_esc(pred.caveat)}</p></details>')


# ---------------------------------------------------------------- movers board
def _mover_card(c: dict) -> str:
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
        f'<b>{_signed(score)}</b></div>{_why(pred)}{news}</article>'
    )


def _movers_board(movers: dict) -> str:
    if movers.get("empty") or not movers.get("movers"):
        return _empty("The stock scan runs on the next update — it needs the live market feed. "
                      "Locally: flab-trending.")
    mom = movers.get("movers", [])[:8]
    fast = movers.get("fast", [])[:8]
    tabs = (
        '<div class="tabs" data-tab-group="movers">'
        '<button data-tab="mom" class="on">Steady climbers</button>'
        '<button data-tab="fast">Fast money</button></div>'
    )
    mom_html = '<div class="movers" data-tab-panel="mom">' + "".join(_mover_card(c) for c in mom) + "</div>"
    fast_html = '<div class="movers hidden" data-tab-panel="fast">' + "".join(_mover_card(c) for c in fast) + "</div>"
    note = "" if movers.get("reddit_ok") else '<p class="fine">Social-velocity (Reddit) is unavailable here; it feeds the fast-money score in the cloud.</p>'
    return tabs + mom_html + fast_html + note


# ---------------------------------------------------------------- odds board
def _odds_card(event, k, p, similarity, footer) -> str:
    pred = market_prediction(event, p, "Polymarket", gap=abs(float(k) - float(p)),
                             similarity=similarity, fair_value=default_fair_value(p))
    return (
        f'<div class="odds">'
        f'<div class="odds-q">{_esc(event)}<span class="sim">match {_pct(similarity,0)}</span></div>'
        f'<div class="odds-bars">'
        f'<div class="ob"><label>Kalshi</label>{_bar(k, "#2F6690")}<span>{_pct(k,0)}</span></div>'
        f'<div class="ob"><label>Polymarket</label>{_bar(p, ACCENT)}<span>{_pct(p,0)}</span></div></div>'
        f'<div class="odds-edge">{footer}</div>{_why(pred)}</div>'
    )


def _odds_row(event, yes, venue, color) -> str:
    pred = market_prediction(event, yes, venue, fair_value=default_fair_value(yes))
    return (f'<div class="odds1"><div class="o1-q">{_esc(event)}</div>'
            f'<div class="ob">{_bar(yes, color)}<span>{_pct(yes,0)} yes</span></div>'
            f'<div class="o1-v">{_esc(venue)}</div>{_why(pred)}</div>')


def _odds_board(edges: dict) -> str:
    flagged = edges.get("edges") or []
    matched = edges.get("matched") or []
    live = edges.get("live") or {}

    cross = ""
    if flagged:
        cards = []
        for e in sorted(flagged, key=lambda e: abs(e.get("net_edge", 0)), reverse=True)[:8]:
            buy = "Kalshi" if "kalshi" in str(e.get("direction", "")).lower() else "Polymarket"
            footer = f'<b>{_pct(e.get("net_edge",0),1,signed=True)}</b> gap after fees · cheaper on {_esc(buy)}'
            cards.append(_odds_card(e["event"], e.get("kalshi", 0), e.get("poly", 0), e.get("similarity", 0), footer))
        cross = ('<h3>Cross-venue gaps</h3>'
                 '<p class="fine">The same question priced differently on each venue — candidates to investigate.</p>'
                 '<div class="oddswrap">' + "".join(cards) + "</div>")
    elif matched:
        cards = [_odds_card(m["event"], m.get("kalshi", 0), m.get("poly", 0), m.get("similarity", 0),
                            f'{_pct(m.get("gap",0),1)} apart · within fees')
                 for m in sorted(matched, key=lambda m: m.get("gap", 0), reverse=True)[:6]]
        cross = ('<h3>Same question, both venues</h3>'
                 '<div class="oddswrap">' + "".join(cards) + "</div>")

    live_html = ""
    poly, kalshi = live.get("poly") or [], live.get("kalshi") or []
    if poly or kalshi:
        cols = []
        if poly:
            rows = "".join(_odds_row(m["event"], m["yes"], "Polymarket", ACCENT) for m in poly[:8])
            cols.append(f'<div class="ocol"><h3>Polymarket · most traded</h3>{rows}</div>')
        if kalshi:
            rows = "".join(_odds_row(m["event"], m["yes"], "Kalshi", "#2F6690") for m in kalshi[:8])
            cols.append(f'<div class="ocol"><h3>Kalshi · most active</h3>{rows}</div>')
        live_html = '<div class="ocols">' + "".join(cols) + "</div>"

    if not cross and not live_html:
        scanned = ""
        if edges.get("n_kalshi") is not None:
            scanned = f" Scanned {edges.get('n_kalshi',0)} Kalshi + {edges.get('n_poly',0)} Polymarket markets."
        return _empty("The market feed returned no priced markets right now." + scanned)
    return cross + live_html


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

    if ar.get("empty"):
        arena_body = _empty("The strategy race hasn't run yet. Locally: flab-sim run --bars 250.")
    else:
        cols = [("strategy", "strategy", "name"), ("total_return", "return", "signed"),
                ("sharpe", "risk-adj.", "signed"), ("deflated_sharpe", "confidence real", "num"),
                ("max_drawdown", "worst drop", "signed")]
        max_ret = max((abs(r["total_return"]) for r in ar["leaderboard"]), default=1.0) or 1.0
        table = _sortable(ar["leaderboard"], cols, bar_col="total_return", bar_max=max_ret, highlight="ml_ranker")
        pbo = ar.get("pbo", 0.0)
        ml_line = ""
        if ml_rank:
            ml_line = (f'<div class="mlcard"><span class="dot" style="background:{STRATEGY_COLORS["ml_ranker"]}"></span>'
                       f'<div><b>The ML model ranks #{ml_rank} of {len(ar["leaderboard"])}.</b> It is a gradient-boosted '
                       f'model that self-tunes with leak-free walk-forward validation, then longs the names it predicts '
                       f'will lead. On this near-random synthetic market it does not beat simple momentum — which is the '
                       f'honest result, and exactly what the test is for.</div></div>')
        arena_body = (
            '<div class="chart wide">' + equity_svg(ar["curves"]) + "</div>" + table + ml_line
            + f'<div class="note"><strong>How to read it.</strong> Click any column to sort. This is <em>paper trading</em> '
            f'on historical prices with fees — not real money. “Confidence real” (0–1) discounts each result for the fact '
            f'that seven strategies were tried; there is a <strong>{pbo:.0%}</strong> chance the leader is just luck. '
            f'The dashed lines are the two controls a real strategy must beat.</div>'
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

    media = state.digests.get("media-watch", {"empty": True})
    media_body = ""
    if not media.get("empty"):
        for heading, content in media["sections"].items():
            if content["table"]:
                media_body += f"<h3>{_esc(heading)}</h3>" + _md_table(content["table"])

    nav = "".join(
        f'<a href="#{a}">{lbl}</a>' for a, lbl in [
            ("now", "Now"), ("markets", "Markets"), ("strategies", "Strategies"),
            ("edges", "Edges"), ("trust", "Sports"), ("economy", "Economy"), ("record", "Track record"),
        ]
    )

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
  --serif:Charter,"Bitstream Charter","Sitka Text",Cambria,Georgia,serif;
  --display:"Iowan Old Style","Palatino Linotype",Palatino,P052,Georgia,serif;
  --sans:Inter,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SFMono-Regular","Cascadia Code",Menlo,Consolas,monospace;
}}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--paper); color:var(--ink); font:400 17px/1.6 var(--serif);
  -webkit-font-smoothing:antialiased; font-variant-numeric:oldstyle-nums; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 22px 80px; }}
a {{ color:var(--accent); text-decoration:none; }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}

/* ---- masthead ---- */
.masthead {{ text-align:center; padding:30px 0 0; }}
.wordmark {{ font:700 clamp(30px,5vw,48px)/1 var(--display); letter-spacing:.01em; }}
.subword {{ font:400 14px/1.4 var(--serif); color:var(--muted); font-style:italic; margin-top:8px; }}
.dateline {{ font:600 11px/1 var(--mono); letter-spacing:.07em; color:var(--muted);
  font-variant-caps:all-small-caps; text-transform:lowercase;
  border-top:1px solid var(--rule); border-bottom:3px solid var(--ink);
  margin-top:16px; padding:9px 0; display:flex; flex-wrap:wrap; gap:6px 18px; justify-content:center; }}
.dateline .live::before {{ content:""; display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--up); margin-right:5px; vertical-align:middle; }}

/* ---- lead ---- */
.lead {{ padding:34px 0 8px; }}
.kicker {{ font:600 12px/1 var(--sans); letter-spacing:.11em; text-transform:uppercase; color:var(--accent); margin-bottom:9px; }}
.lead h1 {{ font:700 clamp(30px,5.2vw,52px)/1.04 var(--display); letter-spacing:-.015em; text-wrap:balance; }}
.lead .deck {{ font:400 19px/1.5 var(--serif); color:var(--muted); max-width:44ch; margin-top:12px; }}

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
.card h2 {{ font:700 26px/1.15 var(--display); letter-spacing:-.015em; text-wrap:balance; }}
.card h3 {{ font:600 12px/1.3 var(--sans); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); margin:24px 0 11px; }}
.src {{ font:600 10.5px/1.4 var(--mono); color:var(--faint); white-space:nowrap; text-transform:uppercase; letter-spacing:.05em; text-align:right; }}
.explain {{ color:var(--muted); font:400 16px/1.55 var(--serif); margin:9px 0 20px; max-width:68ch; }}

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

<header class="masthead">
  <div class="wordmark">The Forecasting Briefing</div>
  <div class="subword">A research bulletin on markets, sports &amp; the economy — every forecast scored on how right it actually is.</div>
  <div class="dateline">
    <span>{_esc(dateline)}</span>
    <span>Research briefing</span>
    <span>No. {issue}</span>
    <span>{sources_total:,} sources tracked</span>
    <span class="live" id="clock" data-gen="{_esc(state.generated)}">updated {_esc(state.generated)}</span>
  </div>
</header>

<div class="lead">
  <div class="kicker">Today's briefing</div>
  <h1>Predictions, kept honest.</h1>
  <p class="deck">Sports, prediction markets, stocks and the economy — forecast, then marked against reality. Click the tabs to explore; every table sorts on any column.</p>
</div>

<div class="kpis">{glance}</div>

<nav>{nav}</nav>

{_section("now", "Markets · Movers", "What's moving now", "Today's trending stocks, scored two ways: steady climbers (NVIDIA-shape trends) and fast money (GameStop-shape squeezes). Each card shows the recent price line, how far it's moved, and a signal score. Attention, not advice.", now_body, "Yahoo + Google News")}

{_section("markets", "Prediction markets", "Where the money is betting", "Live YES odds on the most-traded markets at each venue — the current, high-value questions people are betting on. When the same question is priced on both Kalshi and Polymarket, the gap is flagged as a candidate to investigate (verify both resolve identically before believing any 'arb').", odds_body, "Kalshi + Polymarket")}

{_section("strategies", "Strategy arena", "Strategy leaderboard", "Seven strategies — including one machine-learning model — race on historical prices with fees charged. A paper-trading experiment answering 'which style would have worked', not a live account.", arena_body + strategies_extra)}

{_section("forward", "Out-of-sample", "Live study — watching it play out", "The stricter test: each run records what every strategy would buy today on a real basket, then marks it on the next run. Nothing is scored until real time passes, so it can't cheat.", forward_body)}

{_section("edges", "Edge research", "Does any of it actually beat the market?", "Four leading-signal features — cross-venue lead-lag, attention acceleration, squeeze setup, and price recalibration — each scored out-of-sample under purged walk-forward validation. Positive skill beats the baseline; pure noise scores ~0 by construction.", edges_body)}

{_section("trust", "Calibration · Sports", "Are the predictions trustworthy?", "When the model says 30%, does it happen about 30% of the time? The closer the dots to the line, the more you can trust the numbers. Each sport is scored (Brier, lower is better) against simply guessing the base rate.", sports_body, "sports Elo")}

{_section("economy", "Macro", "Economy check", "A read on recession risk from the bond market. When short-term rates rise above long-term ones (an 'inverted' yield curve), recessions have historically followed.", macro_body, "FRED")}

{_section("record", "Track record", "The scored forecasts", "The credibility piece: real predictions, logged with a probability and scored once the outcome is known — including whether they beat the market's own price.", track_body)}

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
  Set in Charter &amp; Iowan Old Style · No. {issue} · auto-refreshes every 30&nbsp;min · Not financial advice.<br>
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
  var links={{}}; document.querySelectorAll('nav a').forEach(function(a){{links[a.getAttribute('href').slice(1)]=a;}});
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
}})();
</script>
</body>
</html>"""
