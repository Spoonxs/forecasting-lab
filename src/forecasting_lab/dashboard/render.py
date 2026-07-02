"""Render the lab state into one self-contained HTML file.

Aesthetic: amber-phosphor terminal (the quant desk's native artifact) on deep
ink-navy. The signature element is the hero reliability diagram whose 45-degree
diagonal is labeled THE HONESTY LINE — calibration is the lab's entire thesis,
so the page opens on it. Section eyebrows are the actual CLI commands that
produced each panel's data. Hand-rolled SVG, no frameworks, degrades to system
fonts offline.
"""

from __future__ import annotations

import html as _html
import re as _re

# ---------------------------------------------------------------- palette
BG = "#0A0E14"
PANEL = "#10161F"
GRID = "#1C2433"
AMBER = "#FFAE33"
AMBER_DIM = "#8A6420"
TEXT = "#E9E4D8"
MUTED = "#7E8798"
UP = "#3DD68C"
DOWN = "#F0524D"

STRATEGY_COLORS = {
    "momentum_60d": AMBER,
    "breakout_120d": "#45C4A8",
    "meanrev_5d": "#D4707F",
    "voltarget_20d": "#5B9BD9",
    "buy_hold": "#B9C0CE",
    "random": MUTED,
}
BASELINES = {"buy_hold", "random"}


def _esc(s) -> str:
    return _html.escape(str(s))


def _fmt(v, digits=4):
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return _esc(v)


# ---------------------------------------------------------------- SVG: hero
def reliability_svg(records: list[dict], width=620, height=584) -> str:
    """The honesty line: reliability diagram + count histogram strip."""
    ml, mr, mt, mb = 52, 18, 18, 120
    pw, ph = width - ml - mr, height - mt - mb
    hist_h = 54  # histogram strip inside the bottom margin, below the tick labels

    def sx(p):  # prob -> x
        return ml + p * pw

    def sy(p):  # prob -> y (flipped)
        return mt + (1 - p) * ph

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Reliability diagram: predicted probability vs observed frequency">'
    ]
    # grid
    for i in range(6):
        p = i / 5
        parts.append(
            f'<line x1="{sx(p):.1f}" y1="{sy(0):.1f}" x2="{sx(p):.1f}" y2="{sy(1):.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<line x1="{sx(0):.1f}" y1="{sy(p):.1f}" x2="{sx(1):.1f}" y2="{sy(p):.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{sx(p):.1f}" y="{sy(0) + 20:.1f}" class="tick" text-anchor="middle">{p:.1f}</text>'
        )
        parts.append(
            f'<text x="{ml - 10:.1f}" y="{sy(p) + 4:.1f}" class="tick" text-anchor="end">{p:.1f}</text>'
        )

    # the honesty line (drawn on load)
    parts.append(
        f'<line x1="{sx(0):.1f}" y1="{sy(0):.1f}" x2="{sx(1):.1f}" y2="{sy(1):.1f}" '
        f'stroke="{AMBER_DIM}" stroke-width="1.5" stroke-dasharray="6 5" class="honesty" '
        f'pathLength="1"/>'
    )
    # label set along the diagonal
    cx, cy = sx(0.56), sy(0.56)
    angle = -42  # visually matches the diagonal at this aspect ratio
    parts.append(
        f'<text x="{cx:.0f}" y="{cy - 12:.0f}" class="honesty-label" '
        f'transform="rotate({angle} {cx:.0f} {cy:.0f})" text-anchor="middle">'
        f"THE HONESTY LINE&#8201;&#8212;&#8201;FORECAST = FREQUENCY</text>"
    )

    used = [r for r in records if r.get("count")]
    if used:
        max_count = max(r["count"] for r in used)
        # model path + dots
        pts = [(sx(r["mean_pred"]), sy(r["frac_pos"])) for r in used]
        path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        parts.append(
            f'<path d="{path}" fill="none" stroke="{AMBER}" stroke-width="2" '
            f'class="drawline" pathLength="1"/>'
        )
        for r, (x, y) in zip(used, pts, strict=True):
            radius = 3 + 8 * (r["count"] / max_count) ** 0.5
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{AMBER}" '
                f'fill-opacity="0.85" stroke="{BG}" stroke-width="1.5" class="dot">'
                f"<title>bin {r['bin_low']:.1f}-{r['bin_high']:.1f}: predicted "
                f"{r['mean_pred']:.3f}, observed {r['frac_pos']:.3f} (n={r['count']})</title>"
                f"</circle>"
            )
        # histogram strip: where the forecasts actually live (below the tick row)
        bar_w = pw / len(records) - 3
        hist_y = height - hist_h - 22
        for r in records:
            bh = (r["count"] / max_count) * hist_h if r["count"] else 0
            x = sx(r["bin_low"]) + 1.5
            parts.append(
                f'<rect x="{x:.1f}" y="{hist_y + hist_h - bh:.1f}" width="{bar_w:.1f}" '
                f'height="{bh:.1f}" fill="{AMBER}" fill-opacity="0.28"/>'
            )
        parts.append(
            f'<text x="{ml}" y="{hist_y + hist_h + 16}" class="tick">forecast distribution</text>'
        )

    parts.append(
        f'<text x="{ml}" y="{sy(1) - 4:.0f}" class="axis">observed frequency</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- SVG: arena
def equity_svg(curves: dict[str, list[float]], width=760, height=300) -> str:
    """Log-scale multiples chart — equity compounds, so the axis should too."""
    import math

    ml, mr, mt, mb = 52, 168, 12, 26
    pw, ph = width - ml - mr, height - mt - mb
    if not curves:
        return ""
    n = max(len(v) for v in curves.values())
    floor = 1e-3  # equity can approach zero but the log axis cannot
    lo = max(min(min(v) for v in curves.values()), floor)
    hi = max(max(v) for v in curves.values())
    llo, lhi = math.log(lo) - 0.05, math.log(hi) + 0.05

    def sx(i):
        return ml + (i / max(n - 1, 1)) * pw

    def sy(v):
        return mt + (1 - (math.log(max(v, floor)) - llo) / (lhi - llo)) * ph

    # tick candidates that read naturally as multiples
    candidates = [0.25, 0.5, 1, 2, 5, 10, 20, 50, 100]
    ticks = [t for t in candidates if lo * 0.95 <= t <= hi * 1.05] or [1]

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Strategy equity curves (log scale)">'
    ]
    for t in ticks:
        y = sy(t)
        emphasis = f'stroke="{GRID}" stroke-width="{2 if t == 1 else 1}"'
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml + pw}" y2="{y:.1f}" {emphasis}/>')
        label = f"{t:g}x"
        parts.append(
            f'<text x="{ml - 8}" y="{y + 4:.1f}" class="tick" text-anchor="end">{label}</text>'
        )
    # order legend by final equity
    order = sorted(curves, key=lambda k: curves[k][-1], reverse=True)
    for idx, name in enumerate(order):
        vals = curves[name]
        color = STRATEGY_COLORS.get(name, TEXT)
        dash = ' stroke-dasharray="5 4"' if name in BASELINES else ""
        path = "M " + " L ".join(f"{sx(i):.1f} {sy(v):.1f}" for i, v in enumerate(vals))
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.8"{dash} '
            f'class="drawline" pathLength="1"/>'
        )
        ly = mt + 14 + idx * 20
        parts.append(
            f'<line x1="{width - mr + 8}" y1="{ly - 4}" x2="{width - mr + 26}" y2="{ly - 4}" '
            f'stroke="{color}" stroke-width="2"{dash}/>'
        )
        parts.append(
            f'<text x="{width - mr + 32}" y="{ly}" class="legend">{_esc(name)} '
            f'<tspan fill="{MUTED}">{vals[-1]:.1f}x</tspan></text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- HTML bits
def _table(rows: list[dict], cols: list[tuple[str, str]], number_cols=(), signed=(), int_cols=()) -> str:
    head = "".join(f"<th>{_esc(label)}</th>" for _, label in cols)
    body = []
    for row in rows:
        tds = []
        for key, _ in cols:
            v = row.get(key, "")
            if key in signed:
                cls = "up" if float(v) >= 0 else "down"
                tds.append(f'<td class="num {cls}">{float(v):+.3f}</td>')
            elif key in int_cols:
                tds.append(f'<td class="num">{int(float(v)):,}</td>')
            elif key in number_cols:
                tds.append(f'<td class="num">{_fmt(v, 3)}</td>')
            else:
                tds.append(f"<td>{_esc(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _md_table(rows: list[list[str]]) -> str:
    if not rows:
        return '<p class="empty">no rows</p>'
    head = "".join(f"<th>{_esc(c)}</th>" for c in rows[0])
    body = []
    for r in rows[1:]:
        tds = []
        for c in r:
            try:
                float(c)
                tds.append(f'<td class="num">{_esc(c)}</td>')
            except ValueError:
                tds.append(f"<td>{_esc(c)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _panel(command: str, title: str, body: str, wide: bool = False) -> str:
    cls = "panel reveal wide" if wide else "panel reveal"
    return (
        f'<section class="{cls}"><p class="cmd" aria-hidden="true">&gt; {_esc(command)}</p>'
        f"<h2>{_esc(title)}</h2>{body}</section>"
    )


def _empty(command: str, note: str) -> str:
    return (
        f'<div class="empty-state"><p>{_esc(note)}</p>'
        f'<code>&gt; {_esc(command)}</code></div>'
    )


def _stat(label: str, value: str, note: str = "", accent: bool = False) -> str:
    cls = "stat accent" if accent else "stat"
    note_html = f'<span class="note">{_esc(note)}</span>' if note else ""
    return (
        f'<div class="{cls}"><span class="label">{_esc(label)}</span>'
        f'<span class="value">{value}</span>{note_html}</div>'
    )


# ---------------------------------------------------------------- assembly
def render_dashboard(state) -> str:
    tennis_summary = state.tennis["summary"]
    hero_svg = reliability_svg(state.tennis["reliability"])

    base = tennis_summary["base_rate"]
    base_brier = base * (1 - base)
    scorecard = "".join(
        [
            _stat("brier score", _fmt(tennis_summary["brier"]), f"base rate {base_brier:.4f}", accent=True),
            _stat("brier skill", f"+{tennis_summary['brier_skill_score']:.4f}", "> 0 beats climatology"),
            _stat("ece", _fmt(tennis_summary["ece"]), "gap to the honesty line"),
            _stat("log loss", _fmt(tennis_summary["log_loss"])),
            _stat("matches scored", f"{tennis_summary['n']:,}", state.tennis["label"]),
        ]
    )

    # forecast log card
    fl = state.forecast_log
    if fl.get("empty"):
        pending = fl.get("pending")
        note = (
            f"{pending} forecasts logged, none resolved yet."
            if pending
            else "No forecasts logged yet. The public track record starts with one line:"
        )
        forecast_body = _empty(fl["command"], note)
    else:
        s = fl["score"]
        cards = [
            _stat("resolved forecasts", str(s["n"]), f"of {fl['n_total']} logged"),
            _stat("brier", _fmt(s["brier"]), accent=True),
            _stat("skill vs base rate", f"{s['brier_skill_score']:+.3f}"),
            _stat("ece", _fmt(s["ece"])),
        ]
        beat = fl.get("beat") or {}
        if beat.get("n"):
            cards.append(_stat("skill vs market", f"{beat['brier_skill_vs_market']:+.3f}",
                               f"beat the price {beat['beat_rate']:.0%} of {beat['n']}"))
            cards.append('<p class="footnote">"skill vs market" is the beat-the-closing-line test '
                         "— &gt;0 means your probabilities beat the market's, not just the base rate.</p>")
        forecast_body = "".join(cards)

    # arena
    ar = state.arena
    if ar.get("empty"):
        arena_body = _empty(ar["command"], "The arena has no saved state yet. Start it running:")
    else:
        board_cols = [
            ("strategy", "strategy"),
            ("sharpe", "sharpe"),
            ("deflated_sharpe", "deflated (P)"),
            ("total_return", "total return"),
            ("max_drawdown", "max drawdown"),
            ("bars", "bars"),
        ]
        pbo = ar.get("pbo", 0.0)
        arena_body = (
            equity_svg(ar["curves"])
            + _table(ar["leaderboard"], board_cols, int_cols=("bars",), number_cols=("deflated_sharpe",),
                     signed=("sharpe", "total_return", "max_drawdown"))
            + f'<p class="footnote">bar {ar["bar"]:,} of {ar["total_bars"]:,} · costs 10bps/turnover · '
            f"dashed lines are the baselines a real strategy must beat<br>"
            f"<strong>deflated (P)</strong> = confidence the Sharpe survives the multiple-testing penalty "
            f"(6 strategies raced); <strong>PBO {pbo:.0%}</strong> = probability the in-sample winner is "
            f"overfit (CSCV). High PBO means don't trust the leader.</p>"
        )

    # sports tables
    tennis_table = _table(
        state.tennis["leaderboard"], [("player", "player"), ("rating", "elo")], number_cols=("rating",)
    )
    nba = state.nba["summary"]
    nba_table = _table(
        state.nba["leaderboard"], [("team", "team"), ("rating", "elo")], number_cols=("rating",)
    ) + (
        f'<p class="footnote">brier {nba["brier"]:.4f} vs home base rate {nba["base_rate"]:.3f} · '
        f'ece {nba["ece"]:.4f} · {state.nba["label"]}</p>'
    )

    # soccer (3-outcome, RPS)
    sc = state.soccer["eval"]
    br = sc["base_rates"]
    soccer_body = "".join(
        [
            _stat("ranked prob score", _fmt(sc["rps"]), f"baseline {sc['rps_baseline']:.3f}", accent=True),
            _stat("RPS skill", f"{sc['rps_skill']:+.3f}", "> 0 beats climatology"),
            _stat("outcome mix", f"{br['home']:.0%}/{br['draw']:.0%}/{br['away']:.0%}", "home / draw / away"),
        ]
    ) + '<p class="footnote">Davidson draw model, 3 outcomes · ' + _esc(state.soccer["label"]) + "</p>"

    # strategy cards: plain-language rule + how each is doing right now
    stat_by_name = {}
    if not ar.get("empty"):
        stat_by_name = {r["strategy"]: r for r in ar["leaderboard"]}
    strat_rows = []
    for card in state.strategies:
        s = stat_by_name.get(card["name"], {})
        sharpe = f"{s['sharpe']:+.2f}" if s else "—"
        cls = "up" if (s and s["sharpe"] >= 0) else ("down" if s else "")
        strat_rows.append(
            f'<div class="strat"><div class="strat-head">'
            f'<span class="dot-sw" style="background:{STRATEGY_COLORS.get(card["name"], TEXT)}"></span>'
            f'<span class="strat-name">{_esc(card["name"])}</span>'
            f'<span class="kind">{_esc(card["kind"])}</span>'
            f'<span class="strat-sharpe num {cls}">{sharpe}</span></div>'
            f'<p class="strat-desc">{_esc(card["description"])}</p></div>'
        )
    strategies_body = (
        '<div class="strat-grid">' + "".join(strat_rows) + "</div>"
        + '<p class="footnote">sharpe is each rule\'s live standing in the arena above · '
        "trend rules lead in trending regimes; the baselines are the honest bar</p>"
    )

    # forward study (real basket, marked to market over calendar time)
    fw = state.forward
    if fw.get("empty"):
        forward_body = _empty(fw["command"], "The forward study hasn't started. Seed it once:")
    else:
        live = fw.get("live_started")
        fcols = [
            ("strategy", "strategy"),
            ("equity", "equity (x)"),
            ("live_return", "live return"),
            ("live_marks", "live marks"),
            ("as_of", "as of"),
        ]
        forward_body = (
            equity_svg(fw["curves"])
            + _table(fw["leaderboard"], fcols, number_cols=("equity",),
                     signed=("live_return",), int_cols=("live_marks",))
            + '<p class="footnote">real basket, marked to market · '
            + (f"live out-of-sample marks since {_esc(live)} — everything prior is backfill context"
               if live else "all backfill so far; the live study begins on the next scheduled run")
            + "</p>"
        )

    # macro
    mc = state.macro
    if mc.get("empty"):
        macro_body = _empty(mc["command"], "No macro read yet (needs FRED).")
    else:
        prob = mc["recession_prob_12m"]
        ts = mc["term_spread"]
        cards = [
            _stat("recession prob (12m)", f"{prob:.0%}" if prob is not None else "n/a",
                  "from the yield curve", accent=True),
            _stat("10Y-3M spread", f'{ts["value"]:+.2f} pts' if ts["value"] is not None else "n/a",
                  "inverted (<0) = warning"),
        ]
        for label, v in list(mc["levels"].items())[:4]:
            if v["value"] is not None:
                cards.append(_stat(label.lower(), _fmt(v["value"], 2)))
        macro_body = "".join(cards) + f'<p class="footnote">Estrella-Mishkin probit · live FRED · as of {_esc(ts["date"])}</p>'

    # digests
    def digest_body(slug: str, command: str) -> str:
        d = state.digests.get(slug, {"empty": True})
        if d.get("empty"):
            return _empty(command, "No digest filed yet. Run the scan:")
        chunks = [f'<p class="footnote">from {_esc(d["name"])}</p>']
        for heading, content in d["sections"].items():
            if content["table"]:
                chunks.append(f"<h3>{_esc(heading)}</h3>" + _md_table(content["table"]))
            elif content["bullets"]:
                items = "".join(
                    "<li>"
                    + _re.sub(r"\*\*(.+?)\*\*", r'<strong class="tkr">\1</strong>', _esc(b))
                    + "</li>"
                    for b in content["bullets"][:8]
                )
                chunks.append(f"<h3>{_esc(heading)}</h3><ul>{items}</ul>")
            elif content["text"]:
                chunks.append(
                    f'<h3>{_esc(heading)}</h3><p class="footnote">{_esc(" ".join(content["text"]))}</p>'
                )
        return "".join(chunks)

    trending_body = digest_body("trending-stocks", "flab-trending")
    divergence_body = digest_body("market-divergence", "flab-divergence --live")
    research_body = digest_body("research-digest", "flab-research")
    media_body = digest_body("media-watch", "flab-watch")

    field_guide = """
    <ul class="rules">
      <li><span class="rule-n">1</span>Paying off expensive debt beats every strategy in this repo.</li>
      <li><span class="rule-n">2</span>Costs and taxes compound; minimize both before optimizing anything.</li>
      <li><span class="rule-n">3</span>Never trade money you cannot lose; size positions assuming you're wrong.</li>
      <li><span class="rule-n">4</span>Edge is measured — calibration log, walk-forward, after costs — never felt.</li>
      <li><span class="rule-n">5</span>If the pitch involves a Discord, a course, or urgency, you are the exit liquidity.</li>
      <li><span class="rule-n">6</span>Leverage kills: markets stay irrational longer than you stay solvent.</li>
      <li><span class="rule-n">7</span>When in doubt, the answer is the boring index fund.</li>
    </ul>
    <p class="footnote">the full curriculum — foundations &rarr; index core &rarr; market mechanics &rarr;
    the quant canon &rarr; forecasting psychology — lives in <strong>learning-investing.md</strong>.
    tier 0 and 1 come before believing any backtest.</p>"""

    return f"""<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forecasting Lab — terminal</title>
<script>document.documentElement.classList.remove("no-js");document.documentElement.classList.add("js");</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:{BG}; --panel:{PANEL}; --grid:{GRID}; --amber:{AMBER};
  --text:{TEXT}; --muted:{MUTED}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
  --sans:"IBM Plex Sans",system-ui,sans-serif;
  --display:"Big Shoulders Display","Arial Narrow",var(--sans);
}}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--bg); color:var(--text); font:14px/1.55 var(--sans);
  padding:0 clamp(12px,3vw,40px) 60px; }}
a {{ color:var(--amber); }}
:focus-visible {{ outline:2px solid var(--amber); outline-offset:2px; }}

header {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:14px 22px;
  padding:26px 0 18px; border-bottom:1px solid var(--grid); }}
header h1 {{ font:700 clamp(34px,5vw,54px)/0.95 var(--display);
  letter-spacing:0.5px; text-transform:uppercase; }}
header h1 .amp {{ color:var(--amber); }}
.chips {{ display:flex; gap:10px; flex-wrap:wrap; margin-left:auto; }}
.chip {{ font:600 11px/1 var(--mono); letter-spacing:1.2px; text-transform:uppercase;
  color:var(--muted); border:1px solid var(--grid); padding:7px 10px; border-radius:2px; }}
.chip.warn {{ color:var(--amber); border-color:{AMBER_DIM}; }}
.chip.accent-chip {{ color:var(--bg); background:var(--amber); border-color:var(--amber); }}
.strat-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:12px 22px; }}
.strat {{ padding:11px 0; border-bottom:1px solid var(--grid); }}
.strat-head {{ display:flex; align-items:center; gap:9px; }}
.dot-sw {{ width:10px; height:10px; border-radius:2px; flex:0 0 auto; }}
.strat-name {{ font:600 13px var(--mono); color:var(--text); }}
.kind {{ font:10px var(--mono); letter-spacing:1px; text-transform:uppercase; color:var(--muted);
  border:1px solid var(--grid); padding:2px 6px; border-radius:2px; }}
.strat-sharpe {{ margin-left:auto; font:600 14px var(--mono); }}
.strat-desc {{ font:13px/1.5 var(--sans); color:var(--muted); margin-top:5px; }}
@media (max-width:760px) {{ .strat-grid {{ grid-template-columns:1fr; }} }}

main {{ display:grid; grid-template-columns:repeat(12,1fr); gap:14px; margin-top:16px; }}
.panel {{ background:var(--panel); border:1px solid var(--grid); border-radius:3px;
  padding:16px 18px 18px; grid-column:span 4; min-width:0; }}
.panel.wide {{ grid-column:span 12; }}
.panel.hero {{ grid-column:span 7; }}
.panel.score {{ grid-column:span 5; display:flex; flex-direction:column; }}
.cmd {{ font:11px/1 var(--mono); color:var(--muted); letter-spacing:0.6px; margin-bottom:6px; }}
h2 {{ font:600 13px/1.2 var(--mono); letter-spacing:1.6px; text-transform:uppercase;
  color:var(--text); margin-bottom:12px; }}
h3 {{ font:600 11px/1.2 var(--mono); letter-spacing:1.2px; text-transform:uppercase;
  color:var(--muted); margin:14px 0 6px; }}

svg {{ width:100%; height:auto; display:block; }}
.tick {{ font:10px var(--mono); fill:var(--muted); }}
.axis {{ font:10px var(--mono); fill:var(--muted); letter-spacing:1px; }}
.legend {{ font:11px var(--mono); fill:var(--text); }}
.honesty-label {{ font:600 11px var(--mono); fill:{AMBER_DIM}; letter-spacing:2.4px; }}

.stat {{ display:flex; align-items:baseline; gap:12px; padding:11px 2px;
  border-bottom:1px solid var(--grid); }}
.stat:last-child {{ border-bottom:0; }}
.stat .label {{ font:600 11px var(--mono); letter-spacing:1.4px; text-transform:uppercase;
  color:var(--muted); flex:0 0 44%; }}
.stat .value {{ font:600 24px/1 var(--mono); color:var(--text); }}
.stat.accent .value {{ color:var(--amber); font-size:34px; }}
.stat .note {{ font:11px var(--mono); color:var(--muted); margin-left:auto; text-align:right; }}

table {{ width:100%; border-collapse:collapse; font:12.5px var(--mono); }}
th {{ text-align:left; font-weight:600; font-size:10.5px; letter-spacing:1.2px;
  text-transform:uppercase; color:var(--muted); padding:6px 8px 6px 0;
  border-bottom:1px solid var(--grid); }}
td {{ padding:6px 8px 6px 0; border-bottom:1px solid var(--grid); overflow-wrap:anywhere; }}
tr:last-child td {{ border-bottom:0; }}
td.num {{ font-variant-numeric:tabular-nums; }}
td.up {{ color:var(--up); }} td.down {{ color:var(--down); }}
ul {{ list-style:none; }}
li {{ font:12.5px var(--mono); padding:5px 0; border-bottom:1px solid var(--grid); }}
li:last-child {{ border-bottom:0; }}

.footnote {{ font:11px var(--mono); color:var(--muted); margin-top:10px; }}
.tkr {{ color:var(--amber); font-weight:600; }}
.guardrails {{ margin-top:auto; padding-top:18px; }}
.guardrails li {{ color:var(--muted); font-size:11.5px; }}
.guardrails li::before {{ content:"+ "; color:var(--amber); }}
.panel.res {{ grid-column:span 7; }}
.panel.learn {{ grid-column:span 5; }}
.rules {{ list-style:none; }}
.rules li {{ display:flex; gap:12px; align-items:baseline; font:13px/1.5 var(--sans);
  color:var(--text); padding:9px 0; border-bottom:1px solid var(--grid); }}
.rules li:last-child {{ border-bottom:0; }}
.rule-n {{ font:600 12px var(--mono); color:var(--amber); flex:0 0 14px; }}
.empty-state {{ border:1px dashed var(--grid); border-radius:3px; padding:18px;
  color:var(--muted); font-size:13px; }}
.empty-state code {{ display:block; margin-top:10px; font:600 13px var(--mono);
  color:var(--amber); }}
footer {{ margin-top:26px; padding-top:14px; border-top:1px solid var(--grid);
  font:11px var(--mono); color:var(--muted); letter-spacing:0.4px; }}

/* Reveal-on-view is enhancement only: panels are hidden solely when JS is live,
   and always shown for no-JS, reduced-motion, and print. */
.js .reveal {{ opacity:0; transform:translateY(18px); }}
@media (prefers-reduced-motion:reduce) {{
  .reveal {{ opacity:1 !important; transform:none !important; }}
}}
@media print {{ .reveal {{ opacity:1 !important; transform:none !important; }} }}

.honesty, .drawline {{ stroke-dasharray:1; stroke-dashoffset:1;
  animation:draw 1.1s ease-out forwards; }}
.drawline {{ animation-delay:0.25s; }}
.dot {{ opacity:0; animation:appear 0.4s ease-out 1.0s forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
@keyframes appear {{ to {{ opacity:1; }} }}
@media (prefers-reduced-motion:reduce) {{
  .honesty,.drawline {{ animation:none; stroke-dasharray:none; stroke-dashoffset:0; }}
  .honesty {{ stroke-dasharray:6 5; }}
  .dot {{ animation:none; opacity:1; }}
}}
@media (max-width:1100px) {{
  .panel,.panel.hero,.panel.score,.panel.res,.panel.learn {{ grid-column:span 6; }}
}}
@media (max-width:760px) {{
  .panel,.panel.hero,.panel.score,.panel.wide,.panel.res,.panel.learn {{ grid-column:span 12; }}
}}
</style>
</head>
<body>
<header>
  <h1>Forecasting<span class="amp">&amp;</span>Markets Lab</h1>
  <div class="chips">
    <span class="chip">generated {_esc(state.generated)}</span>
    <span class="chip accent-chip">{state.sources.get("total", 0)} sources tracked</span>
    <span class="chip">calibration over accuracy</span>
    <span class="chip warn">not financial advice</span>
  </div>
</header>
<main>
  <section class="panel hero reveal">
    <p class="cmd" aria-hidden="true">&gt; flab-elo --synthetic --plot</p>
    <h2>Reliability — does 30% happen 30% of the time?</h2>
    {hero_svg}
  </section>
  <section class="panel score reveal">
    <p class="cmd" aria-hidden="true">&gt; flab-elo --synthetic</p>
    <h2>Calibration scorecard — tennis Elo</h2>
    {scorecard}
    <div class="guardrails">
      <h3>Why these numbers can be believed</h3>
      <ul>
        <li>time-forward fit — every prediction made before its match</li>
        <li>purged walk-forward CV, never random k-fold</li>
        <li>costs modeled where money would trade</li>
        <li>base-rate baseline always shown next to the score</li>
        <li>a null-signal test pins the pipeline leak-free</li>
      </ul>
    </div>
  </section>

  {_panel("flab-elo --synthetic", "Tennis Elo — top rated", tennis_table)}
  {_panel("flab-elo --sport nba --synthetic", "NBA Elo — top rated", nba_table)}
  {_panel("flab-elo --sport soccer --synthetic", "Soccer Elo — home/draw/away", soccer_body)}

  {_panel("flab-macro", "Macro nowcast — yield-curve recession odds", macro_body)}
  {_panel("flab-calibration score", "Public forecast log", forecast_body)}

  {_panel("flab-sim status", "Strategy arena — persistent paper-trading race", arena_body, wide=True)}
  {_panel("flab-forward status", "Forward study — real tickers, marked to market as time passes", forward_body, wide=True)}
  {_panel("forecasting_lab.sim.strategies", "How each strategy trades — in one line", strategies_body, wide=True)}

  {_panel("flab-watch", "Media watch — what key voices are naming today", media_body, wide=True)}
  {_panel("flab-trending", "Trending stocks — GME / NVIDIA shapes", trending_body, wide=True)}
  {_panel("flab-divergence --live", "Cross-venue divergence — Kalshi vs Polymarket", divergence_body, wide=True)}

  <section class="panel res reveal">
    <p class="cmd" aria-hidden="true">&gt; flab-research</p>
    <h2>Quant research feed — arXiv, relevance-ranked</h2>
    {research_body}
  </section>
  <section class="panel learn reveal">
    <p class="cmd" aria-hidden="true">&gt; learning-investing.md</p>
    <h2>Field guide — rules that survive real money</h2>
    {field_guide}
  </section>
</main>
<footer>
  time-respecting splits only · no look-ahead · costs modeled · calibration over accuracy ·
  survivorship-bias-free or labeled synthetic · research system, not a recommendation engine
</footer>

<!-- GSAP is progressive enhancement: offline or blocked, the page is complete
     without it (SVG draws fall back to the CSS keyframes above). -->
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js" defer></script>
<script>
window.addEventListener("load", function () {{
  var panels = document.querySelectorAll(".reveal");
  function showAll() {{
    panels.forEach(function (el) {{ el.style.opacity = 1; el.style.transform = "none"; }});
  }}
  // Fallbacks: no GSAP (blocked CDN) or reduced motion -> just show everything.
  if (!window.gsap || matchMedia("(prefers-reduced-motion: reduce)").matches) {{
    showAll();
    return;
  }}
  gsap.registerPlugin(ScrollTrigger);

  // 1) Count-up on every scorecard number (format-preserving).
  document.querySelectorAll(".stat .value").forEach(function (el) {{
    var raw = el.textContent.trim();
    var m = raw.match(/^([+-]?)([\\d,]+)(\\.\\d+)?$/);
    if (!m) return;
    var sign = m[1], decimals = m[3] ? m[3].length - 1 : 0;
    var target = parseFloat(raw.replace(/[+,]/g, ""));
    var hasComma = m[2].indexOf(",") >= 0;
    var state = {{ v: 0 }};
    gsap.to(state, {{
      v: Math.abs(target), duration: 1.4, ease: "power2.out", delay: 0.35,
      onUpdate: function () {{
        var s = state.v.toFixed(decimals);
        if (hasComma) s = Number(s).toLocaleString("en-US", {{ minimumFractionDigits: decimals }});
        el.textContent = (sign === "+" ? "+" : (target < 0 ? "-" : "")) + s;
      }},
    }});
  }});

  // 2) Header chips settle in.
  gsap.from(".chip", {{ y: -8, autoAlpha: 0, duration: 0.5, stagger: 0.08, ease: "power2.out" }});

  // 3) Panels fade+rise: on load if above the fold, on scroll otherwise. Every
  //    animation ENDS at opacity 1 / y 0, so content is never left hidden.
  var vh = window.innerHeight;
  panels.forEach(function (panel, i) {{
    if (panel.getBoundingClientRect().top < vh) {{
      gsap.to(panel, {{ opacity: 1, y: 0, duration: 0.55, delay: 0.05 * i, ease: "power2.out" }});
    }} else {{
      gsap.to(panel, {{
        opacity: 1, y: 0, duration: 0.6, ease: "power2.out",
        scrollTrigger: {{ trigger: panel, start: "top 90%", once: true }},
      }});
    }}
  }});
  // Safety net: if anything is still hidden a moment later (e.g. ScrollTrigger
  // never initialised), reveal it. Content visibility must never depend on JS.
  setTimeout(function () {{
    panels.forEach(function (el) {{
      if (getComputedStyle(el).opacity === "0") {{ el.style.opacity = 1; el.style.transform = "none"; }}
    }});
    ScrollTrigger.refresh();
  }}, 1600);
}});
</script>
</body>
</html>"""
