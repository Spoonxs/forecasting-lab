"""Render the lab state into one clean, self-explaining HTML page.

Design goal: a non-expert can glance and understand *what this system forecasts
and whether it's any good*. Every section leads with a plain-English question and
a one-sentence answer; jargon is translated, not displayed. Light "research
briefing" look — white cards on cool grey, one teal accent, green/red only for
gains and losses. Hand-rolled SVG, no frameworks, system fonts (always renders).
"""

from __future__ import annotations

import html as _html
import re as _re

# ---------------------------------------------------------------- palette
PAPER = "#F4F5F7"
CARD = "#FFFFFF"
INK = "#161A21"
MUTED = "#5A626E"
FAINT = "#8A909B"
LINE = "#E5E8ED"
ACCENT = "#0E7C6B"      # deep teal — the one accent
ACCENT_SOFT = "#E6F1EF"
UP = "#12855A"
DOWN = "#C24436"

STRATEGY_COLORS = {
    "momentum_60d": ACCENT,
    "breakout_120d": "#3E7CB1",
    "meanrev_5d": "#C98A3B",
    "voltarget_20d": "#7A6BB0",
    "buy_hold": "#8A909B",
    "random": "#B9BEC7",
}
BASELINES = {"buy_hold", "random"}


def _esc(s) -> str:
    return _html.escape(str(s))


def _fmt(v, digits=3):
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return _esc(v)


def _pct(v, digits=0):
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return _esc(v)


# ---------------------------------------------------------------- SVG: reliability
def reliability_svg(records: list[dict], width=640, height=430) -> str:
    """Calibration chart: predicted probability (x) vs what actually happened (y).
    Dots on the diagonal = the model's confidence matches reality."""
    ml, mr, mt, mb = 60, 20, 20, 92
    pw, ph = width - ml - mr, height - mt - mb
    hist_h = 40

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
        parts.append(f'<line x1="{sx(p):.1f}" y1="{sy(0):.1f}" x2="{sx(p):.1f}" y2="{sy(1):.1f}" stroke="{LINE}"/>')
        parts.append(f'<line x1="{sx(0):.1f}" y1="{sy(p):.1f}" x2="{sx(1):.1f}" y2="{sy(p):.1f}" stroke="{LINE}"/>')
        parts.append(f'<text x="{sx(p):.1f}" y="{sy(0)+18:.1f}" class="ax" text-anchor="middle">{p:.0%}</text>')
        parts.append(f'<text x="{ml-10:.1f}" y="{sy(p)+4:.1f}" class="ax" text-anchor="end">{p:.0%}</text>')

    parts.append(
        f'<line x1="{sx(0):.1f}" y1="{sy(0):.1f}" x2="{sx(1):.1f}" y2="{sy(1):.1f}" '
        f'stroke="{FAINT}" stroke-width="1.5" stroke-dasharray="5 5" class="draw" pathLength="1"/>'
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
                f'stroke="{CARD}" stroke-width="1.5" class="dot"><title>said ~{r["mean_pred"]:.0%}, '
                f'happened {r["frac_pos"]:.0%} ({r["count"]} times)</title></circle>'
            )
        # distribution strip
        bar_w = pw / len(records) - 3
        hy = height - hist_h - 22
        for r in records:
            bh = (r["count"] / maxc) * hist_h if r["count"] else 0
            parts.append(
                f'<rect x="{sx(r["bin_low"])+1.5:.1f}" y="{hy+hist_h-bh:.1f}" width="{bar_w:.1f}" '
                f'height="{bh:.1f}" rx="1" fill="{ACCENT}" fill-opacity="0.22"/>'
            )
        parts.append(f'<text x="{ml}" y="{hy+hist_h+16}" class="ax">how many predictions fell in each range</text>')

    parts.append(f'<text x="{ml}" y="{sy(1)-6:.0f}" class="axt">what actually happened &#8593;</text>')
    parts.append(f'<text x="{sx(1):.0f}" y="{sy(0)+38:.0f}" class="axt" text-anchor="end">the model\'s prediction &#8594;</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- SVG: equity
def equity_svg(curves: dict[str, list[float]], width=780, height=300) -> str:
    """Growth-of-$1 chart on a log scale (money compounds, so the axis should)."""
    import math

    ml, mr, mt, mb = 54, 172, 14, 28
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
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="{LINE}" stroke-width="{1.6 if t==1 else 1}"/>')
        parts.append(f'<text x="{ml-8}" y="{y+4:.1f}" class="ax" text-anchor="end">{t:g}&#215;</text>')
    order = sorted(curves, key=lambda k: curves[k][-1], reverse=True)
    for idx, name in enumerate(order):
        vals = curves[name]
        color = STRATEGY_COLORS.get(name, INK)
        dash = ' stroke-dasharray="5 4"' if name in BASELINES else ""
        path = "M " + " L ".join(f"{sx(i):.1f} {sy(v):.1f}" for i, v in enumerate(vals))
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"{dash} class="draw" pathLength="1"/>')
        ly = mt + 12 + idx * 20
        parts.append(f'<line x1="{width-mr+8}" y1="{ly-4}" x2="{width-mr+26}" y2="{ly-4}" stroke="{color}" stroke-width="2.5"{dash}/>')
        label = _plain_strategy_name(name)
        parts.append(f'<text x="{width-mr+32}" y="{ly}" class="leg">{_esc(label)} <tspan fill="{MUTED}">{vals[-1]:.1f}&#215;</tspan></text>')
    parts.append("</svg>")
    return "".join(parts)


def _plain_strategy_name(name: str) -> str:
    return {
        "momentum_60d": "Momentum",
        "breakout_120d": "Breakout",
        "meanrev_5d": "Mean-reversion",
        "voltarget_20d": "Risk-balanced",
        "buy_hold": "Buy & hold",
        "random": "Random (control)",
    }.get(name, name)


# ---------------------------------------------------------------- HTML bits
def _kpi(label: str, value: str, sub: str = "", tone: str = "") -> str:
    tcls = f" kpi-{tone}" if tone else ""
    subhtml = f'<div class="kpi-sub">{_esc(sub)}</div>' if sub else ""
    return (f'<div class="kpi{tcls}"><div class="kpi-label">{_esc(label)}</div>'
            f'<div class="kpi-val">{value}</div>{subhtml}</div>')


def _section(title: str, explainer: str, body: str, source: str = "") -> str:
    src = f'<span class="src">{_esc(source)}</span>' if source else ""
    return (f'<section class="card reveal"><div class="sec-head"><h2>{_esc(title)}</h2>{src}</div>'
            f'<p class="explain">{_esc(explainer)}</p>{body}</section>')


def _stat(label: str, value: str, sub: str = "", big: bool = False) -> str:
    cls = "stat big" if big else "stat"
    subhtml = f'<span class="stat-sub">{_esc(sub)}</span>' if sub else ""
    return f'<div class="{cls}"><span class="stat-label">{_esc(label)}</span><span class="stat-val">{value}</span>{subhtml}</div>'


def _table(rows: list[dict], cols: list[tuple], num=(), signed=(), int_cols=()) -> str:
    head = "".join(f"<th>{_esc(lbl)}</th>" for _, lbl in cols)
    body = []
    for row in rows:
        tds = []
        for key, _ in cols:
            v = row.get(key, "")
            if key in signed:
                cls = "up" if float(v) >= 0 else "down"
                tds.append(f'<td class="num {cls}">{float(v):+.2f}</td>')
            elif key in int_cols:
                tds.append(f'<td class="num">{int(float(v)):,}</td>')
            elif key in num:
                tds.append(f'<td class="num">{_fmt(v, 2)}</td>')
            else:
                tds.append(f"<td>{_esc(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="twrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _md_table(rows: list[list[str]], limit: int = 6) -> str:
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


# ---------------------------------------------------------------- assembly
def render_dashboard(state) -> str:
    t = state.tennis["summary"]
    sources_total = state.sources.get("total", 0)

    # --- at a glance verdicts -------------------------------------------
    calib = "Well-calibrated" if t["ece"] < 0.04 else "Roughly calibrated"
    ar = state.arena
    leader = "—"
    if not ar.get("empty") and ar.get("leaderboard"):
        leader = _plain_strategy_name(ar["leaderboard"][0]["strategy"])
    mc = state.macro
    recession = _pct(mc["recession_prob_12m"]) if not mc.get("empty") and mc.get("recession_prob_12m") is not None else "—"

    glance = "".join([
        _kpi("Forecast quality", calib, "predictions match reality", "good"),
        _kpi("Top strategy (simulated)", leader, "in a paper-trading test"),
        _kpi("Recession odds, 12 mo", recession, "from the yield curve"),
        _kpi("Sources tracked", f"{sources_total:,}", "refreshed every run"),
    ])

    # --- calibration hero ------------------------------------------------
    base_brier = t["base_rate"] * (1 - t["base_rate"])
    calib_read = "".join([
        _stat("How close to reality", "Very close", f"error {t['ece']:.1%} (0% = perfect)", big=True),
        _stat("Beats a coin flip by", f"{t['brier_skill_score']:+.0%}", "vs. always guessing the base rate"),
        _stat("Tested on", f"{t['n']:,} matches", state.tennis["label"]),
    ])
    calib_body = (
        '<div class="split"><div class="chart">' + reliability_svg(state.tennis["reliability"]) + "</div>"
        '<div class="readout">' + calib_read
        + '<p class="fine">Read it like this: group every prediction by how confident the model was, '
        "then check how often those things actually happened. If it says ‘30%’ and they happen "
        "about 30% of the time, the dots land on the line. These do.</p></div></div>"
    )

    # --- sports ----------------------------------------------------------
    nba, sc = state.nba["summary"], state.soccer["eval"]
    sports_body = '<div class="grid3">' + "".join([
        _mini("Tennis", f"{t['brier']:.3f}", f"vs {base_brier:.3f} baseline", f"beats a coin flip by {t['brier_skill_score']:+.0%}"),
        _mini("Basketball (NBA)", f"{nba['brier']:.3f}", f"vs {nba['base_rate']*(1-nba['base_rate']):.3f} baseline", f"home team wins {nba['base_rate']:.0%} of the time"),
        _mini("Soccer", f"{sc['rps']:.3f}", f"vs {sc['rps_baseline']:.3f} baseline", f"home {sc['base_rates']['home']:.0%} / draw {sc['base_rates']['draw']:.0%} / away {sc['base_rates']['away']:.0%}"),
    ]) + "</div>"

    # --- arena (simulated) ----------------------------------------------
    if ar.get("empty"):
        arena_body = _empty("The strategy test hasn't run yet.")
    else:
        board = [{**r, "name": _plain_strategy_name(r["strategy"])} for r in ar["leaderboard"]]
        cols = [("name", "strategy"), ("total_return", "return"), ("sharpe", "risk-adj. return"),
                ("deflated_sharpe", "confidence it's real"), ("max_drawdown", "worst drop")]
        pbo = ar.get("pbo", 0.0)
        arena_body = (
            '<div class="chart wide">' + equity_svg(ar["curves"]) + "</div>"
            + _table(board, cols, num=("deflated_sharpe",), signed=("total_return", "sharpe", "max_drawdown"))
            + f'<div class="note"><strong>Reality check.</strong> This is <em>paper trading</em> on '
            f'historical prices with trading fees — not real money. “Confidence it’s real” '
            f'(0–1) discounts for the fact that six strategies were tried; and there’s a '
            f'<strong>{pbo:.0%}</strong> chance the leader just got lucky. The dashed lines are the two '
            f'controls (buy-everything and random) that a real strategy has to beat.</div>'
        )

    # --- forward study ---------------------------------------------------
    fw = state.forward
    if fw.get("empty"):
        forward_body = _empty("The live study hasn’t started collecting real results yet.")
    else:
        fboard = [{**r, "name": _plain_strategy_name(r["strategy"])} for r in fw["leaderboard"]]
        fcols = [("name", "strategy"), ("equity", "grew to"), ("live_return", "live return"), ("live_marks", "live checks")]
        live = fw.get("live_started")
        forward_body = (
            '<div class="chart wide">' + equity_svg(fw["curves"]) + "</div>"
            + _table(fboard, fcols, num=("equity",), signed=("live_return",), int_cols=("live_marks",))
            + '<p class="fine">' + (f"Real, out-of-sample results have been accruing since {_esc(live)} — everything before that is historical context."
               if live else "So far this is historical context; genuine day-by-day results start on the next scheduled run.")
            + "</p>"
        )

    # --- how strategies work --------------------------------------------
    stat_by = {r["strategy"]: r for r in ar["leaderboard"]} if not ar.get("empty") else {}
    cards = []
    for c in state.strategies:
        s = stat_by.get(c["name"], {})
        ret = f"{s['total_return']:+.0%}" if s else "—"
        cls = "up" if (s and s["total_return"] >= 0) else ("down" if s else "")
        cards.append(
            f'<div class="scard"><div class="scard-top"><span class="swatch" style="background:{STRATEGY_COLORS.get(c["name"], INK)}"></span>'
            f'<span class="sname">{_esc(_plain_strategy_name(c["name"]))}</span>'
            f'<span class="sret {cls}">{ret}</span></div>'
            f'<p>{_esc(c["description"])}</p></div>'
        )
    strategies_body = '<div class="scards">' + "".join(cards) + "</div>"

    # --- digests ---------------------------------------------------------
    def digest_section(slug, title, explainer, headline_first=False):
        d = state.digests.get(slug, {"empty": True})
        if d.get("empty"):
            return _section(title, explainer, _empty("No fresh data filed yet — it appears after the next run."))
        chunks = []
        for heading, content in d["sections"].items():
            if content["table"]:
                chunks.append(f"<h3>{_esc(heading)}</h3>" + _md_table(content["table"]))
            elif content["bullets"]:
                items = "".join("<li>" + _re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', _esc(b)) + "</li>"
                                for b in content["bullets"][:6])
                chunks.append(f"<h3>{_esc(heading)}</h3><ul>{items}</ul>")
        return _section(title, explainer, "".join(chunks) or _empty("Quiet right now."), source=d["name"])

    # --- macro -----------------------------------------------------------
    if mc.get("empty"):
        macro_body = _empty("The economy check needs the live data feed.")
    else:
        prob = mc["recession_prob_12m"]
        ts = mc["term_spread"]
        rows = [_stat("Recession odds (next 12 months)", _pct(prob) if prob is not None else "—",
                      "from the shape of the yield curve", big=True)]
        for label, v in list(mc["levels"].items())[:4]:
            if v["value"] is not None:
                rows.append(_stat(label, _fmt(v["value"], 2)))
        macro_body = "".join(rows) + f'<p class="fine">A recession probability, not a forecast of certainty. Yield-curve model, live data as of {_esc(ts["date"])}.</p>'

    # --- track record ----------------------------------------------------
    fl = state.forecast_log
    if fl.get("empty"):
        track_body = _empty("No forecasts have been logged and resolved yet. Once real predictions are recorded and their markets settle, this fills with a live accuracy score.")
    else:
        s = fl["score"]
        rows = [_stat("Forecasts scored", str(s["n"]), f"of {fl['n_total']} logged", big=True),
                _stat("Accuracy (Brier, lower is better)", _fmt(s["brier"])),
                _stat("Beats the base rate by", f"{s['brier_skill_score']:+.0%}")]
        beat = fl.get("beat") or {}
        if beat.get("n"):
            rows.append(_stat("Beats the market by", f"{beat['brier_skill_vs_market']:+.0%}", f"right more often than the price {beat['beat_rate']:.0%} of the time"))
        track_body = "".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forecasting Lab</title>
<script>document.documentElement.className="js";</script>
<style>
:root {{
  --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --muted:{MUTED}; --faint:{FAINT};
  --line:{LINE}; --accent:{ACCENT}; --accent-soft:{ACCENT_SOFT}; --up:{UP}; --down:{DOWN};
  --sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SFMono-Regular","Cascadia Code",Consolas,monospace;
}}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--paper); color:var(--ink); font:16px/1.6 var(--sans);
  -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums;
  padding:0 20px 64px; }}
.wrap {{ max-width:1080px; margin:0 auto; }}
a {{ color:var(--accent); }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; border-radius:3px; }}

header {{ padding:44px 0 26px; border-bottom:1px solid var(--line); }}
.eyebrow {{ font:600 12px/1 var(--sans); letter-spacing:.14em; text-transform:uppercase; color:var(--accent); }}
header h1 {{ font:700 clamp(30px,5vw,46px)/1.05 var(--sans); letter-spacing:-.02em; margin:10px 0 8px; }}
header p {{ font-size:17px; color:var(--muted); max-width:60ch; }}
.meta {{ display:flex; flex-wrap:wrap; gap:8px 10px; margin-top:16px; }}
.tag {{ font:500 12.5px/1 var(--sans); color:var(--muted); background:var(--card);
  border:1px solid var(--line); padding:7px 11px; border-radius:999px; }}
.tag.warn {{ color:#8a5a12; background:#fbf3e3; border-color:#f0dfbf; }}

.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:24px 0; }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 18px 16px; }}
.kpi-label {{ font:600 12px/1.2 var(--sans); letter-spacing:.04em; text-transform:uppercase; color:var(--muted); }}
.kpi-val {{ font:700 26px/1.15 var(--sans); letter-spacing:-.01em; margin:8px 0 3px; }}
.kpi.kpi-good .kpi-val {{ color:var(--accent); }}
.kpi-sub {{ font-size:13px; color:var(--faint); }}

.card {{ background:var(--card); border:1px solid var(--line); border-radius:16px;
  padding:24px 26px; margin:16px 0; }}
.sec-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; }}
.card h2 {{ font:650 22px/1.25 var(--sans); letter-spacing:-.01em; }}
h2 {{ font-weight:700; }}
.src {{ font:500 12px/1 var(--mono); color:var(--faint); white-space:nowrap; }}
.explain {{ color:var(--muted); font-size:15.5px; margin:6px 0 18px; max-width:70ch; }}
.card h3 {{ font:600 13px/1.3 var(--sans); letter-spacing:.02em; text-transform:uppercase;
  color:var(--muted); margin:20px 0 8px; }}

.split {{ display:grid; grid-template-columns:1.35fr 1fr; gap:26px; align-items:center; }}
.chart svg, .chart.wide svg {{ width:100%; height:auto; display:block; }}
.readout {{ display:flex; flex-direction:column; gap:2px; }}
.ax {{ font:500 11px var(--sans); fill:var(--faint); }}
.axt {{ font:600 12px var(--sans); fill:var(--muted); }}
.diag {{ font:500 11px var(--sans); fill:var(--faint); }}
.leg {{ font:500 13px var(--sans); fill:var(--ink); }}

.stat {{ display:flex; align-items:baseline; gap:12px; padding:11px 0; border-bottom:1px solid var(--line); }}
.stat:last-child {{ border-bottom:0; }}
.stat-label {{ font-size:14px; color:var(--muted); flex:1 1 auto; }}
.stat-val {{ font:650 19px/1 var(--sans); }}
.stat.big .stat-val {{ font-size:30px; color:var(--accent); }}
.stat-sub {{ font-size:12.5px; color:var(--faint); flex-basis:100%; text-align:right; margin-top:-4px; }}

.grid3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
.mini {{ border:1px solid var(--line); border-radius:12px; padding:16px; }}
.mini h4 {{ font:600 14px/1 var(--sans); margin-bottom:10px; }}
.mini .m-val {{ font:700 24px/1 var(--sans); }}
.mini .m-base {{ font-size:12.5px; color:var(--faint); margin-top:3px; }}
.mini .m-note {{ font-size:13px; color:var(--muted); margin-top:8px; }}

table {{ width:100%; border-collapse:collapse; font-size:14px; }}
.twrap {{ overflow-x:auto; }}
th {{ text-align:left; font:600 11.5px/1 var(--sans); letter-spacing:.03em; text-transform:uppercase;
  color:var(--faint); padding:0 12px 9px 0; border-bottom:1px solid var(--line); }}
td {{ padding:10px 12px 10px 0; border-bottom:1px solid var(--line); }}
tr:last-child td {{ border-bottom:0; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.up {{ color:var(--up); }} .down {{ color:var(--down); }}
ul {{ list-style:none; }}
li {{ font-size:14px; padding:8px 0; border-bottom:1px solid var(--line); color:var(--ink); }}
li:last-child {{ border-bottom:0; }}

.note {{ background:var(--accent-soft); border:1px solid #cfe6e1; border-radius:12px;
  padding:14px 16px; font-size:14px; color:#1c3b36; margin-top:18px; }}
.fine {{ font-size:13.5px; color:var(--muted); margin-top:14px; max-width:74ch; }}
.empty {{ color:var(--muted); font-size:14.5px; background:var(--paper); border:1px dashed var(--line);
  border-radius:12px; padding:16px; }}

.scards {{ display:grid; grid-template-columns:repeat(2,1fr); gap:12px 20px; }}
.scard {{ padding:12px 0; border-bottom:1px solid var(--line); }}
.scard-top {{ display:flex; align-items:center; gap:9px; }}
.swatch {{ width:11px; height:11px; border-radius:3px; }}
.sname {{ font:600 15px/1 var(--sans); }}
.sret {{ margin-left:auto; font:650 15px/1 var(--sans); }}
.scard p {{ font-size:13.5px; color:var(--muted); margin-top:6px; }}

.faq p {{ font-size:15px; color:var(--ink); margin-bottom:12px; max-width:74ch; }}
.faq strong {{ color:var(--ink); }}
.rules {{ list-style:none; }}
.rules li {{ display:flex; gap:12px; font-size:14.5px; }}
.rules .rn {{ color:var(--accent); font-weight:700; }}

footer {{ margin-top:28px; padding-top:16px; border-top:1px solid var(--line);
  font-size:13px; color:var(--faint); }}

.reveal {{ animation:rise .5s ease-out both; }}
@keyframes rise {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:none; }} }}
.draw {{ stroke-dasharray:1; stroke-dashoffset:1; animation:draw 1s ease-out forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
@media (prefers-reduced-motion:reduce) {{
  .reveal, .draw {{ animation:none; }}
  .draw {{ stroke-dasharray:none; stroke-dashoffset:0; }}
}}
@media (max-width:820px) {{
  .kpis {{ grid-template-columns:repeat(2,1fr); }}
  .split {{ grid-template-columns:1fr; }}
  .grid3, .scards {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Forecasting &amp; markets lab</div>
  <h1>Predictions, kept honest.</h1>
  <p>A personal research system that forecasts sports, prediction markets, stocks and the economy —
     then scores how right it actually is. It refreshes on its own every day.</p>
  <div class="meta">
    <span class="tag">Updated {_esc(state.generated)}</span>
    <span class="tag">{sources_total:,} sources tracked</span>
    <span class="tag warn">Research project · not financial advice</span>
  </div>
</header>

<div class="kpis">{glance}</div>

{_section("Are the predictions trustworthy?", "The most important question for any forecaster: when it says something is 30% likely, does it happen about 30% of the time? Here it does — the closer the dots sit to the line, the more you can trust the numbers.", calib_body, "tennis model")}

{_section("Sports rating models", "Each sport gets an Elo-style rating that turns matchups into win probabilities. The score below (Brier, lower is better) is measured against simply guessing the base rate — beating it means the model actually knows something.", sports_body)}

{_section("Strategy test (simulated)", "Six simple trading rules race each other on historical prices, with realistic fees. It answers ‘which style would have worked’ — as a paper-trading experiment, not a live account.", arena_body)}

{_section("Live study — watching it play out", "The stricter test: each run records what every strategy would buy today on a real basket of popular stocks, then checks the result on the next run. Nothing is scored until real time passes, so it can’t cheat.", forward_body)}

{_section("How each strategy works", "In one plain sentence each — so the table above isn’t a mystery. The bottom two are controls, not real strategies.", strategies_body)}

{digest_section("market-divergence", "Prediction-market price gaps", "The same real-world question is often priced differently on Kalshi and Polymarket. This flags gaps big enough to matter after fees — candidates to investigate, not sure things.")}

{digest_section("trending-stocks", "Stocks getting attention", "A daily scan of what’s moving and being talked about, split into ‘fast money’ (GameStop-style squeezes) and ‘steady climbers’ (NVIDIA-style trends). Attention, not advice.")}

{digest_section("media-watch", "What the news and voices are saying", "About 100 news outlets and commentators, scanned for which companies and themes they’re naming today — and the overall tone.")}

{_section("Economy check", "A simple read on recession risk from the bond market. When short-term rates rise above long-term ones (an ‘inverted’ yield curve), recessions have historically followed.", macro_body, "FRED")}

{_section("Track record", "The credibility piece: real predictions, logged with a probability and scored once the outcome is known — including whether they beat the market’s own price.", track_body)}

{digest_section("research-digest", "Research feed", "Recent quant-finance papers from arXiv, ranked for how relevant they are to what this lab does.")}

<section class="card faq reveal">
  <div class="sec-head"><h2>Is it actually making money?</h2></div>
  <p><strong>Honestly, no — and it’s not pretending to.</strong> Everything here is simulated or paper-traded.
  The models are well-calibrated (their probabilities are trustworthy), but being calibrated isn’t the same as
  having an edge the market hasn’t already priced in.</p>
  <p>In the simulation, the momentum strategy wins — but that’s historical, frictionless-ish, and the
  overfitting check exists precisely so a lucky result doesn’t get mistaken for skill. The live study only just
  started collecting genuine results.</p>
  <p>If the goal is growing money, a boring index fund still beats everything here. The point of this project is
  the <strong>skill and the honest track record</strong> — which is exactly what a quant desk or grad program
  looks for. The real verdict on ‘edge’ arrives once the live study has run for a few weeks.</p>
</section>

<section class="card reveal">
  <div class="sec-head"><h2>The ground rules</h2></div>
  <p class="explain">The habits that separate real research from a lucky-looking backtest — baked into every number above.</p>
  <ul class="rules">
    <li><span class="rn">1</span><span>Only test on the past, predict the future — never let tomorrow’s data leak into today.</span></li>
    <li><span class="rn">2</span><span>Always charge trading fees; a cost-free backtest is a fantasy.</span></li>
    <li><span class="rn">3</span><span>Judge probabilities, not ‘% right’ — and always beat the simple baseline.</span></li>
    <li><span class="rn">4</span><span>Discount for luck: trying many strategies means one wins by chance.</span></li>
    <li><span class="rn">5</span><span>An honest ‘no edge’ is a stronger result than a suspiciously perfect one.</span></li>
  </ul>
</section>

<footer>
  Built as a research and skill-building project. Not investment advice. Data from public sources
  (Kalshi, Polymarket, Yahoo, FRED, arXiv, football-data.co.uk and others), each under its own terms.
</footer>
</div>
</body>
</html>"""


def _mini(title: str, value: str, base: str, note: str) -> str:
    return (f'<div class="mini"><h4>{_esc(title)}</h4><div class="m-val">{_esc(value)}</div>'
            f'<div class="m-base">{_esc(base)}</div><div class="m-note">{_esc(note)}</div></div>')
