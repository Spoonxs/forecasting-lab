"""The public scorecard page — the Brier ledger with an honest denominator (P4).

The Intel Desk mechanic, in the Stock Taper skin: only RESOLVED forecasts count
toward the score (the denominator is stated up top), the MISS LEDGER is pinned
first (worst-scored forecasts lead — never hidden), open horizons are listed as
"under audit", and an empty log says so instead of claiming anything. This page
is the credibility artifact: if it ever looks too good, check the denominator.
"""

from __future__ import annotations

from .render import (
    ACCENT,
    CARD,
    DOWN,
    INK,
    MASCOTS,
    MUTED,
    PAPER,
    RULE,
    UP,
    _esc,
    _fmt,
    _pct,
    reliability_svg,
)


def _row(r: dict, worst: bool) -> str:
    said = _pct(r.get("prob", 0), 0)
    outcome = int(float(r.get("outcome", 0)))
    err = float(r.get("sq_error", 0.0))
    cls = "miss" if worst else ""
    hit = "&#10003; hit" if (outcome == 1) == (float(r.get("prob", 0)) >= 0.5) else "&#10007; miss"
    return (f'<tr class="{cls}"><td>{_esc(r.get("date", ""))}</td>'
            f'<td class="q">{_esc(r.get("question", ""))}</td>'
            f'<td class="num">{said}</td><td class="num">{outcome}</td>'
            f'<td class="num">{err:.3f}</td><td>{hit}</td></tr>')


def render_scorecard(state) -> str:
    sc = getattr(state, "scorecard", None) or {"empty": True}

    if sc.get("empty") or (not sc.get("rows") and not sc.get("open_rows")):
        body = ('<p class="empty">No resolved forecasts yet — the denominator is 0, '
                "so no score is claimed. Forecasts appear here the moment they are "
                "logged, and count the moment they resolve.</p>")
        denom = '<div class="denom"><b>0</b> resolved · <b>0</b> open — only resolved forecasts are scored</div>'
        chart = ""
    else:
        n_res, n_open = sc.get("n_resolved", 0), sc.get("n_open", 0)
        denom = (f'<div class="denom"><b>{n_res}</b> resolved · <b>{n_open}</b> open — '
                 "only resolved forecasts are scored; nothing open counts</div>")
        stats = ""
        score = sc.get("score") or {}
        if score:
            stats += (f'<div class="srow"><span>Brier (lower is better)</span><b>{_fmt(score.get("brier"), 3)}</b></div>'
                      f'<div class="srow"><span>Beats the base rate by</span>'
                      f'<b>{score.get("brier_skill_score", 0):+.0%}</b></div>')
        beat = sc.get("beat") or {}
        if beat.get("n"):
            stats += (f'<div class="srow"><span>Beats the closing line by</span>'
                      f'<b>{beat.get("brier_skill_vs_market", 0):+.0%}</b>'
                      f'<i>closer to the truth than the market {beat.get("beat_rate", 0):.0%} of the time '
                      f'(n={beat["n"]})</i></div>')
        chart = ""
        if sc.get("reliability"):
            chart = '<div class="chart">' + reliability_svg(sc["reliability"]) + "</div>"

        rows = sc.get("rows") or []
        n_worst = max(1, len(rows) // 5) if rows else 0
        table = ""
        if rows:
            trs = "".join(_row(r, i < n_worst) for i, r in enumerate(rows))
            table = (
                '<h3>The miss ledger — worst calls first, never hidden</h3>'
                '<div class="twrap"><table><thead><tr><th>date</th><th>question</th>'
                '<th class="num">said</th><th class="num">outcome</th>'
                '<th class="num">sq. error</th><th>call</th></tr></thead>'
                f"<tbody>{trs}</tbody></table></div>"
            )
        open_html = ""
        open_rows = sc.get("open_rows") or []
        if open_rows:
            lis = "".join(
                f'<li>{_esc(r.get("date",""))} — {_esc(r.get("question",""))} '
                f'<b>said {_pct(r.get("prob",0),0)}</b></li>'
                for r in open_rows[:20]
            )
            open_html = (f'<h3>Under audit — {len(open_rows)} open, not yet counted</h3>'
                         f'<ul class="open">{lis}</ul>')
        body = stats + chart + table + open_html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scorecard — The Forecasting Briefing</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --muted:{MUTED}; --rule:{RULE};
  --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--paper); color:var(--ink); font:400 14px/1.65 var(--mono);
  font-variant-numeric:tabular-nums; }}
.wrap {{ max-width:920px; margin:0 auto; padding:30px 22px 70px; }}
a {{ color:var(--accent); text-decoration:none; }}
.eyebrow {{ font:700 11px/1 var(--mono); letter-spacing:.09em; text-transform:uppercase; color:var(--accent); }}
h1 {{ font:700 26px/1.2 var(--mono); letter-spacing:.04em; text-transform:uppercase; margin:8px 0 6px; }}
h3 {{ font:700 12px/1.3 var(--mono); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:26px 0 10px; }}
.sub {{ color:var(--muted); max-width:64ch; }}
.head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }}
.mascot {{ flex:none; width:44px; height:44px; }}
.card {{ background:var(--card); border:1px solid var(--rule); border-radius:3px; padding:24px 26px; margin:16px 0; }}
.denom {{ font:600 13px/1.5 var(--mono); background:var(--card); border:1px solid var(--rule);
  border-left:4px solid var(--accent); border-radius:3px; padding:12px 16px; margin:16px 0; }}
.srow {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:10px; padding:10px 0; border-bottom:1px solid var(--rule); }}
.srow span {{ color:var(--muted); flex:1; }} .srow b {{ font-size:19px; }}
.srow i {{ flex-basis:100%; font-style:normal; font-size:12px; color:var(--muted); text-align:right; }}
.chart svg {{ width:100%; height:auto; display:block; margin-top:12px; }}
.ax {{ font:500 11px var(--mono); fill:#9A958C; }} .axt {{ font:600 12px var(--mono); fill:var(--muted); }}
.diag {{ font:italic 11px var(--mono); fill:#9A958C; }}
.twrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font:400 12.5px/1.5 var(--mono); }}
th {{ text-align:left; font:700 10.5px/1 var(--mono); letter-spacing:.05em; text-transform:uppercase;
  color:var(--muted); padding:0 10px 8px 0; border-bottom:2px solid var(--ink); }}
th.num, td.num {{ text-align:right; }}
td {{ padding:8px 10px 8px 0; border-bottom:1px solid var(--rule); vertical-align:top; }}
td.q {{ max-width:38ch; }}
tr.miss td {{ background:#FBEFEA; }}
.open {{ list-style:none; }}
.open li {{ padding:7px 0; border-bottom:1px solid var(--rule); color:var(--muted); }}
.open li b {{ color:var(--ink); }}
.empty {{ color:var(--muted); border:1px dashed var(--rule); border-radius:3px; padding:16px; background:#fffdf6; }}
footer {{ margin-top:26px; padding-top:14px; border-top:1px solid var(--rule); font-size:12px; color:var(--muted); text-align:center; }}
@media (prefers-reduced-motion:reduce) {{ * {{ animation:none !important; transition:none !important; }} }}
</style>
</head>
<body>
<div class="wrap">
<div class="head"><div>
  <div class="eyebrow">Track record · public ledger</div>
  <h1>The scorecard</h1>
  <p class="sub">How right have the forecasts actually been? Every prediction is logged with a
  probability and scored once the outcome is known. Only resolved forecasts count — and the
  worst calls are shown first, because a track record that hides its misses is a story.</p>
</div>{MASCOTS.get("scorecard", "")}</div>
{denom}
<div class="card">{body}</div>
<footer><a href="index.html">&#9666; Back to the briefing</a> · updated {_esc(getattr(state, "generated", ""))} · Not financial advice.</footer>
</div>
</body>
</html>"""
