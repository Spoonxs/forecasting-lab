"""Ticker recommendation pages — site/t/<SYM>.html (P6b section A).

Stock Taper statement shape × Rallies ratings scale, in the platform skin. Each
page renders the P6a verdict for one instrument: the recommendation header with
the four confidence dials as gauges, a "for YOUR profile" line that swaps the
label client-side from the embedded ``labels_by_profile`` matrix, the component
breakdown, going-well/concerning, the evidence card with a clickable receipts
drawer (audit hash + sources + freshness + contradictions on screen), an
analyst-consensus module (EXTERNAL OPINION, n/a until wired), news headlines,
a peer strip, the add-to-watchlist CTA, and the tier-live stub for on-demand
symbols. Everything server-rendered; degrades honestly (n/a price, INSUFFICIENT
EVIDENCE) and never fabricates. Not financial advice.
"""

from __future__ import annotations

import json

from ..signals.verdict import INSUFFICIENT
from .render import (
    ACCENT,
    CARD,
    DOWN,
    FAINT,
    INK,
    MASCOTS,
    MUTED,
    PAPER,
    RULE,
    UP,
    _esc,
    _pct,
    sparkline_svg,
)
from .tier_live import tier_live_js

LABEL_TONE = {
    "STRONG BUY": UP, "BUY": UP, "HOLD": MUTED,
    "TRIM": DOWN, "AVOID": DOWN, INSUFFICIENT: FAINT,
}
COMPONENT_LABEL = {
    "backtest": "Backtest (with costs)", "trend": "Trend & momentum",
    "residual_momentum": "Residual momentum", "squeeze": "Squeeze setup",
    "macro": "Macro regime", "yield": "Dividend yield", "news": "News tone",
}
DIAL_LABEL = {
    "expected_return": "Expected-return lean", "drawdown_risk": "Drawdown risk",
    "data_confidence": "Data confidence", "model_confidence": "Model confidence",
}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _json_html(obj) -> str:
    """JSON safe to embed inside a <script> tag: neutralize </script> breakout
    and the two JS line-separator code points (Codex review — XSS vector)."""
    return (json.dumps(obj)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace(" ", "\\u2028").replace(" ", "\\u2029"))


def _safe_symbol(sym: str) -> str | None:
    """A filesystem-safe symbol for the page filename, or None if it can't be one
    (Codex review — an artifact symbol with '/' or '..' must not escape site/t)."""
    s = str(sym).strip().upper()
    if s and all(c.isalnum() or c in ".-" for c in s) and ".." not in s:
        return s
    return None


def _safe_url(url) -> str | None:
    """Only http(s) link-outs; anything else (javascript:, data:) -> None so it
    renders as plain text (Codex review — scheme-based XSS)."""
    if isinstance(url, str) and url.lower().startswith(("http://", "https://")):
        return url
    return None


def _gauge(name: str, value: float, *, invert: bool = False) -> str:
    """A compact semicircle dial. ``invert`` = higher is worse (drawdown risk)."""
    v = max(0.0, min(1.0, float(value)))
    tone = DOWN if (invert and v > 0.5) else (UP if (not invert and v >= 0.5) else MUTED)
    # semicircle radius 40 centered (50,50); pathLength 100 so dasharray = pct
    arc = "M 10 50 A 40 40 0 0 1 90 50"
    return (
        f'<div class="gauge"><svg viewBox="0 0 100 62" role="img" '
        f'aria-label="{_esc(DIAL_LABEL.get(name, name))} {v:.0%}">'
        f'<path d="{arc}" fill="none" stroke="{RULE}" stroke-width="9" stroke-linecap="round"/>'
        f'<path d="{arc}" fill="none" stroke="{tone}" stroke-width="9" stroke-linecap="round" '
        f'pathLength="100" stroke-dasharray="{v * 100:.1f} 100"/>'
        f'<text x="50" y="48" text-anchor="middle" class="g-val">{v:.0%}</text></svg>'
        f'<div class="g-lab">{_esc(DIAL_LABEL.get(name, name))}</div></div>'
    )


def _price_header(symbol: str, name: str, price, day_change, moves) -> str:
    px = f"${price:,.2f}" if _num(price) else "n/a"
    if _num(day_change):
        cls = "up" if day_change >= 0 else "down"
        chg = f'<span class="{cls}">{_pct(day_change, 2, signed=True)} today</span>'
    else:
        chg = '<span class="na">day change n/a</span>'  # honest: no true daily change offline
    # trailing moves are LABELED for what they are (Codex review: never a 5d return posing as day change)
    chips = ""
    if moves:
        chips = '<div class="moves">' + "".join(
            f'<span class="mv {"up" if _num(v) and v >= 0 else "down" if _num(v) else "na"}">'
            f'{_pct(v, 1, signed=True) if _num(v) else "n/a"} <em>{_esc(lbl)}</em></span>'
            for lbl, v in moves) + "</div>"
    return (f'<div class="pxhead"><div><div class="eyebrow">Recommendation</div>'
            f'<h1>{_esc(symbol)}</h1><div class="coname">{_esc(name)}</div></div>'
            f'<div class="pxr"><div class="px">{px}</div>{chg}{chips}</div></div>')


def _chart(spark: list | None) -> str:
    pills = "".join(f'<button class="pill{" on" if p == "1Y" else ""}" disabled>{p}</button>'
                    for p in ("1M", "3M", "6M", "1Y"))
    if spark and len([s for s in spark if s is not None]) >= 2:
        body = sparkline_svg([float(s) for s in spark if s is not None], width=680, height=150)
    else:
        body = ('<p class="na">Price chart needs the live feed — offline this instrument '
                'has no series. Split/dividend markers appear when the data carries them.</p>')
    return f'<div class="chart"><div class="pills">{pills}</div>{body}</div>'


def _dials(dials: dict) -> str:
    order = ("expected_return", "drawdown_risk", "data_confidence", "model_confidence")
    cells = []
    for k in order:
        raw = dials.get(k, 0.0)
        if k == "expected_return":  # signed [-1,1] -> [0,1] for the gauge
            cells.append(_gauge(k, (float(raw) + 1) / 2))
        else:
            cells.append(_gauge(k, raw, invert=(k == "drawdown_risk")))
    return f'<div class="dials">{"".join(cells)}</div>'


def _components_table(components: dict, missing: list) -> str:
    rows = []
    for name, c in sorted(components.items(), key=lambda kv: -float(kv[1]["score"])):
        score = float(c["score"])
        cls = "up" if score > 0 else ("down" if score < 0 else "")
        rows.append(
            f'<tr><td>{_esc(COMPONENT_LABEL.get(name, name))}</td>'
            f'<td class="num {cls}">{score:+.2f}</td>'
            f'<td class="num">{float(c["confidence"]):.0%}</td>'
            f'<td>{_esc(c.get("detail", ""))}</td></tr>'
        )
    for name in missing:
        clean = name.replace("low-confidence: ", "")
        rows.append(f'<tr class="miss"><td>{_esc(COMPONENT_LABEL.get(clean, clean))}</td>'
                    f'<td class="num na">—</td><td class="num na">n/a</td>'
                    f'<td class="na">excluded — no data (never imputed)</td></tr>')
    return ('<table><thead><tr><th>component</th><th class="num">score</th>'
            '<th class="num">confidence</th><th>evidence</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _well_concerning(components: dict) -> str:
    good = [f'<li><b>{_esc(COMPONENT_LABEL.get(n, n))}</b> {float(c["score"]):+.2f} '
            f'· {_esc(c.get("detail", ""))}</li>'
            for n, c in components.items() if float(c["score"]) > 0]
    bad = [f'<li><b>{_esc(COMPONENT_LABEL.get(n, n))}</b> {float(c["score"]):+.2f} '
           f'· {_esc(c.get("detail", ""))}</li>'
           for n, c in components.items() if float(c["score"]) < 0]
    g = "".join(good) or "<li>nothing scored positive in the available evidence</li>"
    b = "".join(bad) or "<li>no negative drivers in the available evidence — the caveats still apply</li>"
    return ('<div class="wellcon"><div class="wc-good"><h4>What&#8217;s going well?</h4>'
            f'<ul>{g}</ul></div><div class="wc-bad"><h4>What&#8217;s concerning?</h4>'
            f'<ul>{b}</ul></div></div>')


def _receipts(symbol: str, row: dict, as_of: str, audit_sha: str) -> str:
    comps = row.get("components", {})
    src = "".join(f'<li>{_esc(COMPONENT_LABEL.get(n, n))}: {_esc(c.get("detail", "") or "—")}</li>'
                  for n, c in comps.items()) or "<li>no components carried evidence this build</li>"
    pos = [n for n, c in comps.items() if float(c["score"]) > 0]
    neg = [n for n, c in comps.items() if float(c["score"]) < 0]
    contra = ""
    if pos and neg:
        contra = (f'<p class="contra">The evidence disagrees — '
                  f'{_esc(", ".join(COMPONENT_LABEL.get(n, n) for n in pos))} lean up while '
                  f'{_esc(", ".join(COMPONENT_LABEL.get(n, n) for n in neg))} lean down. '
                  f'Kept on screen, not averaged away.</p>')
    return (
        '<details class="receipts"><summary>&#9782; Receipts — how this verdict was built</summary>'
        f'<div class="rc"><div class="rc-row"><span>audit hash</span>'
        f'<code>{_esc(audit_sha[:16] or "n/a")}</code></div>'
        f'<div class="rc-row"><span>as of</span><code>{_esc(as_of or "n/a")}</code></div>'
        f'<div class="rc-row"><span>data confidence</span>'
        f'<code>{row.get("dials", {}).get("data_confidence", 0):.0%}</code></div>'
        f'<h5>Sources behind each component</h5><ul class="rc-src">{src}</ul>'
        f'{contra}<p class="rc-cav">Verdicts are the operator&#8217;s research opinions, '
        'content-hashed and replayable — scored on the public ledger as outcomes accrue. '
        'Not financial advice.</p></div></details>'
    )


def _analyst_module(consensus: dict | None) -> str:
    if not consensus:
        body = ('<p class="na">n/a — the analyst-consensus feed is not configured. '
                'When wired it renders the external consensus label + average price target '
                'with a staleness stamp, clearly marked as third-party opinion.</p>')
    else:
        body = (f'<div class="ac"><div><span>consensus</span><b>{_esc(consensus["label"])}</b></div>'
                f'<div><span>avg price target</span><b>{_esc(consensus.get("target", "n/a"))}</b></div>'
                f'<div><span>as of</span><b>{_esc(consensus.get("as_of", "n/a"))}</b></div></div>')
    return (f'<div class="ext"><div class="ext-tag">External opinion</div>'
            f'<h3>Analyst consensus</h3>{body}</div>')


def _news(news: list | None) -> str:
    if not news:
        return '<p class="na">No headlines for this instrument in the latest scan.</p>'
    items = []
    for n in news[:8]:
        title = _esc(n.get("title", ""))
        url = _safe_url(n.get("url"))
        # real http(s) link-out only; anything else renders as plain text — never a faked or unsafe link
        cell = (f'<a href="{_esc(url)}" target="_blank" rel="noopener">{title}</a>'
                if url else title)
        items.append(f'<li>{cell}<span class="nd">{_esc(n.get("date", ""))}</span></li>')
    return f'<ul class="news">{"".join(items)}</ul>'


def build_verdict_pages(out_dir, *, verdicts_dir=None, tier_live_worker: str = "",
                        limit: int | None = None) -> list[str]:
    """Write site/t/<SYM>.html for every symbol in the latest verdict artifact,
    joining price/headline from the trending sidecar and names from the registry.
    Returns the built symbols (the home page links them). [] when no artifact."""
    from pathlib import Path

    from ..pipeline.digest import read_latest_data
    from ..pipeline.verdicts import load_latest_verdicts
    from ..sources.instruments import InstrumentRegistry

    loaded = load_latest_verdicts(verdicts_dir)
    if loaded.get("empty"):
        return []
    payload, contract, sha = loaded["payload"], loaded["contract"], loaded["audit_sha"]
    symbols = list(payload["verdicts"])
    if limit:
        symbols = symbols[:limit]

    movers = {c.get("ticker", "").upper(): c
              for c in (read_latest_data("trending-stocks") or {}).get("movers", [])}
    registry = InstrumentRegistry()
    out_dir = Path(out_dir) / "t"
    out_dir.mkdir(parents=True, exist_ok=True)

    built: list[str] = []
    for sym in symbols:
        safe = _safe_symbol(sym)
        if safe is None:  # never let a malformed artifact symbol write outside site/t
            continue
        row = payload["verdicts"][sym]
        inst = registry.get(sym)
        card = movers.get(sym.upper())
        news = [{"title": card["headline"], "date": payload["as_of"]}] if card and card.get("headline") else None
        peers = [_safe_symbol(s) for s in symbols if s != sym]
        peers = [p for p in peers if p][:6]
        moves = ([("5d", card.get("ret_5d")), ("60d", card.get("ret_60d"))] if card else None)
        html = render_verdict_page(
            sym, row, contract,
            name=inst.name if inst else sym,
            price=card.get("last") if card else None,
            day_change=None,  # no true daily change offline — the labeled moves carry the trend
            moves=moves,
            spark=card.get("spark") if card else None,
            news=news, peers=peers, as_of=payload["as_of"], audit_sha=sha,
            tier_live_worker=tier_live_worker,
        )
        (out_dir / f"{safe}.html").write_text(html, encoding="utf-8")
        built.append(sym)
    return built


def _peer_strip(peers: list | None, current: str) -> str:
    if not peers:
        return ""
    chips = "".join(f'<a href="{_esc(p)}.html">{_esc(p)}</a>' for p in peers if p != current)
    return f'<div class="peers">{chips}</div>' if chips else ""


def render_verdict_page(
    symbol: str,
    row: dict,
    contract: dict,
    *,
    name: str = "",
    price=None,
    day_change=None,
    moves: list | None = None,
    spark: list | None = None,
    news: list | None = None,
    peers: list | None = None,
    analyst: dict | None = None,
    as_of: str = "",
    audit_sha: str = "",
    tier_live_worker: str = "",
) -> str:
    label = row.get("label", INSUFFICIENT)
    tone = LABEL_TONE.get(label, FAINT)
    score = row.get("score", 0.0)
    matrix = row.get("labels_by_profile", {})
    reasons = "; ".join(row.get("reasons", []))
    sym_json = _json_html(symbol)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(symbol)} — recommendation | The Investment Platform</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);
  font-variant-numeric:tabular-nums}}
.wrap{{max-width:900px;margin:0 auto;padding:20px 18px 70px}}
a{{color:var(--accent);text-decoration:none}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}}
.top a{{font:600 12px/1 var(--mono);text-transform:uppercase;letter-spacing:.06em}}
.eyebrow{{font:700 11px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--accent)}}
.card{{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:20px 22px;margin:14px 0}}
h1{{font:800 30px/1 var(--mono);letter-spacing:.04em;margin:6px 0}}
h3{{font:700 12px/1.3 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mut);margin:0 0 10px}}
.coname{{color:var(--mut);font-size:13px}}
.pxhead{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}}
.pxr{{text-align:right}} .px{{font:800 26px/1 var(--mono)}}
.up{{color:var(--up)}} .down{{color:var(--down)}} .na{{color:var(--faint)}}
.moves{{display:flex;gap:6px;justify-content:flex-end;margin-top:8px;flex-wrap:wrap}}
.mv{{font:600 11px/1 var(--mono);padding:4px 6px;border-radius:3px;background:var(--paper);border:1px solid var(--rule)}}
.mv em{{font-style:normal;color:var(--faint);font-weight:500}}
.mv.up{{color:var(--up)}} .mv.down{{color:var(--down)}}
.pills{{display:flex;gap:4px;margin-bottom:8px}}
.pill{{font:600 11px/1 var(--mono);border:1px solid var(--rule);background:var(--paper);
  color:var(--mut);border-radius:4px;padding:6px 10px}}
.pill.on{{background:var(--ink);color:var(--paper)}}
.chart svg{{width:100%;height:auto;display:block}}
.verdict{{text-align:center;padding:8px 0 4px}}
.vlabel{{font:800 34px/1.05 var(--mono);letter-spacing:.04em}}
.vscore{{font:600 13px/1 var(--mono);color:var(--mut);margin-top:6px}}
.forprofile{{margin-top:12px;font:600 13px/1.5 var(--mono);color:var(--mut);
  border-top:1px solid var(--rule);padding-top:12px}}
.forprofile b{{color:var(--ink)}}
.reasons{{color:var(--faint);font-size:12px;margin-top:8px;text-align:center}}
.dials{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}
.gauge{{text-align:center}} .gauge svg{{width:100%;max-width:120px}}
.g-val{{font:700 15px/1 var(--mono);fill:var(--ink)}}
.g-lab{{font:600 10.5px/1.3 var(--mono);text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin-top:2px}}
table{{width:100%;border-collapse:collapse;font:400 13px/1.5 var(--mono)}}
th{{text-align:left;font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;
  color:var(--mut);border-bottom:2px solid var(--ink);padding:0 10px 8px 0}}
th.num,td.num{{text-align:right}}
td{{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule)}}
tr.miss td{{color:var(--faint)}}
.wellcon{{display:grid;grid-template-columns:1fr 1fr;gap:0;border:1px solid var(--rule);
  border-radius:4px;overflow:hidden;margin-top:16px}}
.wellcon>div{{padding:14px 16px}} .wellcon>div:first-child{{border-right:1px solid var(--rule)}}
.wellcon h4{{font:700 11px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;margin-bottom:9px}}
.wc-good h4{{color:var(--up)}} .wc-bad h4{{color:var(--down)}}
.wellcon ul{{list-style:none}} .wellcon li{{font-size:12.5px;color:var(--mut);padding:3px 0}}
.wellcon li b{{color:var(--ink)}}
.receipts summary{{cursor:pointer;font:700 12px/1 var(--mono);text-transform:uppercase;
  letter-spacing:.05em;color:var(--mut);padding:6px 0}}
.rc{{margin-top:10px;font-size:12.5px}} .rc-row{{display:flex;justify-content:space-between;
  border-bottom:1px solid var(--rule);padding:6px 0}} .rc-row span{{color:var(--mut)}}
.rc h5{{font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:12px 0 6px}}
.rc-src{{list-style:none}} .rc-src li{{padding:3px 0;color:var(--mut)}}
.contra{{background:#fbefe9;border:1px solid #e7c9bd;border-radius:4px;padding:9px 12px;margin:10px 0;color:#7a2e17;font-size:12px}}
.rc-cav{{color:var(--faint);font-size:11.5px;margin-top:10px}}
.ext{{position:relative}} .ext-tag{{font:700 9.5px/1 var(--mono);text-transform:uppercase;
  letter-spacing:.06em;color:var(--mut);background:var(--paper);border:1px solid var(--rule);
  border-radius:3px;padding:4px 7px;display:inline-block;margin-bottom:8px}}
.ac{{display:flex;gap:26px;flex-wrap:wrap}} .ac span{{display:block;font:600 10px/1 var(--mono);
  text-transform:uppercase;color:var(--mut);margin-bottom:4px}} .ac b{{font:700 18px/1 var(--mono)}}
.news{{list-style:none}} .news li{{display:flex;justify-content:space-between;gap:12px;
  padding:8px 0;border-bottom:1px solid var(--rule)}} .news li:last-child{{border-bottom:0}}
.nd{{color:var(--faint);font-size:11px;white-space:nowrap}}
.peers{{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}}
.peers a{{font:600 12px/1 var(--mono);border:1px solid var(--rule);background:var(--paper);
  border-radius:999px;padding:7px 11px}}
.cta{{background:var(--accent);color:#fff;border:0;border-radius:4px;padding:11px 16px;
  font:700 13px/1 var(--mono);cursor:pointer}}
.cta-note{{color:var(--mut);font-size:12px;margin-top:8px}}
footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--faint);text-align:center}}
@media(max-width:620px){{.dials{{grid-template-columns:repeat(2,1fr)}}
  .wellcon{{grid-template-columns:1fr}} .wellcon>div:first-child{{border-right:0;border-bottom:1px solid var(--rule)}}}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body><div class="wrap">
<div class="top"><a href="../index.html">&#9666; Platform</a>{MASCOTS.get("movers", "")}</div>

<div class="card">{_price_header(symbol, name or symbol, price, day_change, moves)}{_chart(spark)}</div>

<div class="card">
  <div class="verdict"><div class="vlabel" style="color:{tone}" id="vlabel">{_esc(label)}</div>
    <div class="vscore">score {score:+.3f} · default profile (1–5y · grow)</div></div>
  {_dials(row.get("dials", {}))}
  <div class="forprofile">For <b id="profName">your profile</b>:
    <b id="profLabel" style="color:{tone}">{_esc(label)}</b>
    <span id="profHint" class="na"></span></div>
  {'<div class="reasons">' + _esc(reasons) + "</div>" if reasons else ""}
</div>

<div class="card"><h3>Evidence — component breakdown</h3>
  {_components_table(row.get("components", {}), row.get("missing", []))}
  {_well_concerning(row.get("components", {}))}
  {_receipts(symbol, row, as_of, audit_sha)}
</div>

<div class="card">{_analyst_module(analyst)}</div>

<div class="card"><h3>Recent headlines</h3>{_news(news)}</div>

<div class="card"><h3>Peers</h3>{_peer_strip(peers, symbol) or '<p class="na">No sibling pages built yet.</p>'}
  <div style="margin-top:16px"><button class="cta" id="watchBtn">+ Add {_esc(symbol)} to watchlist</button>
    <p class="cta-note">Watchlisting promotes {_esc(symbol)} to the nightly <b>full</b> tier —
    every component, scored and audit-hashed. Until then, on-demand symbols show a
    price-only preview (below) or this INSUFFICIENT-EVIDENCE state.</p></div>
</div>

<footer>Not financial advice — a personal research opinion, scored on the public ledger.
· <a href="../scorecard.html">scorecard</a> · <a href="../index.html">platform</a></footer>
</div>
<script id="matrix" type="application/json">{_json_html(matrix)}</script>
<script>
(function(){{
  var matrix=JSON.parse(document.getElementById('matrix').textContent||'{{}}');
  var HN={{"0-1y":"0–1y","1-5y":"1–5y","5y+":"5y+"}};
  function profile(){{ try{{return JSON.parse(localStorage.getItem('flab_profile'))||{{}};}}catch(e){{return {{}};}} }}
  function apply(){{
    var p=profile(), h=p.horizon||'1-5y', g=p.goal||'grow', r=p.risk||'med', key=h+'|'+g+'|'+r;
    var lab=matrix[key]; if(!lab) return;
    document.getElementById('profName').textContent=(HN[h]||h)+' · '+g+' · '+r+' risk';
    var el=document.getElementById('profLabel'); el.textContent=lab;
    var tone={{'STRONG BUY':'{UP}','BUY':'{UP}','HOLD':'{MUTED}','TRIM':'{DOWN}','AVOID':'{DOWN}'}}[lab]||'{FAINT}';
    el.style.color=tone;
    document.getElementById('profHint').textContent=
      (lab!==document.getElementById('vlabel').textContent)?' (differs from the default)':'';
  }}
  apply();
  var b=document.getElementById('watchBtn');
  if(b) b.addEventListener('click',function(){{
    var wl; try{{wl=JSON.parse(localStorage.getItem('flab_watchlist'))||[];}}catch(e){{wl=[];}}
    var s={sym_json}; if(wl.indexOf(s)<0) wl.push(s);
    localStorage.setItem('flab_watchlist',JSON.stringify(wl));
    b.textContent='\\u2713 '+s+' on your watchlist';
  }});
}})();
{tier_live_js(tier_live_worker)}
</script>
</body></html>"""
