"""Compare page + materiality change feed (P6b section C).

``site/compare.html`` (``?a=X&b=Y``) puts two built tickers side by side with a
per-component verdict and a winner per row (Stock Taper compare shape). It's
self-contained: a compact per-symbol map (label, score, components) is embedded
once, and the client reads the query string to render any pair — no fetch.

The **materiality change feed** diffs the two latest verdict artifacts and
attributes each label change to the component that moved it: "NVDA BUY → HOLD
because trend fell −0.31" — component-attributed, never vague. With only one
artifact it says so honestly ("first build — no changes yet").
"""

from __future__ import annotations

from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _esc, _json_html
from .verdict_page import COMPONENT_LABEL

VERDICT_TONE = {"STRONG BUY": UP, "BUY": UP, "HOLD": MUTED, "TRIM": DOWN,
                "AVOID": DOWN, "INSUFFICIENT EVIDENCE": FAINT}
_LABEL_ORDER = {"STRONG BUY": 4, "BUY": 3, "HOLD": 2, "TRIM": 1, "AVOID": 0,
                "INSUFFICIENT EVIDENCE": -1}


def compact_map(payload: dict) -> dict:
    """The per-symbol data the compare page needs (label, score, component scores)."""
    out = {}
    for sym, r in payload.get("verdicts", {}).items():
        out[sym] = {
            "label": r.get("label", "INSUFFICIENT EVIDENCE"),
            "score": r.get("score", 0.0),
            "components": {n: c["score"] for n, c in r.get("components", {}).items()},
        }
    return out


INSUFFICIENT = "INSUFFICIENT EVIDENCE"


def materiality_changes(payload: dict, prior: dict | None) -> list[dict]:
    """Label changes between two artifacts, each attributed to the component that
    actually drove it (moved in the label's direction), or to the evidence that
    appeared/dropped. ``dir`` is up|down|neutral — a transition to/from
    INSUFFICIENT EVIDENCE is NOT an up/down move. [] with no prior artifact."""
    if not prior:
        return []
    changes = []
    prev = prior.get("verdicts", {})
    for sym, r in payload.get("verdicts", {}).items():
        p = prev.get(sym)
        if not p:
            continue
        now_label, was_label = r.get("label"), p.get("label")
        if now_label == was_label:
            continue
        now_c = {n: c["score"] for n, c in r.get("components", {}).items()}
        was_c = {n: c["score"] for n, c in p.get("components", {}).items()}
        added = [n for n in now_c if n not in was_c]
        dropped = [n for n in was_c if n not in now_c]

        if now_label == INSUFFICIENT or was_label == INSUFFICIENT:
            # a rating appeared or disappeared — neither an upgrade nor a downgrade
            direction = "neutral"
            if was_label == INSUFFICIENT:
                why = "enough evidence to rate it now" + (
                    f" ({', '.join(COMPONENT_LABEL.get(n, n) for n in added)} added)" if added else "")
            else:
                why = "evidence fell below the floor" + (
                    f" ({', '.join(COMPONENT_LABEL.get(n, n) for n in dropped)} dropped)" if dropped else "")
        else:
            up = _LABEL_ORDER[now_label] > _LABEL_ORDER[was_label]
            direction = "up" if up else "down"
            want = 1 if up else -1
            # the driver must have moved IN the label's direction (Codex fix:
            # never "downgraded because Trend rose")
            aligned = [(n, now_c.get(n, 0.0) - was_c.get(n, 0.0))
                       for n in set(now_c) | set(was_c)
                       if (now_c.get(n, 0.0) - was_c.get(n, 0.0)) * want > 1e-9]
            if aligned:
                driver, delta = max(aligned, key=lambda kv: abs(kv[1]))
                why = f"{COMPONENT_LABEL.get(driver, driver)} {'rose' if delta > 0 else 'fell'} {delta:+.2f}"
            elif added:
                why = "gained " + ", ".join(COMPONENT_LABEL.get(n, n) for n in added)
            elif dropped:
                why = "lost " + ", ".join(COMPONENT_LABEL.get(n, n) for n in dropped)
            else:
                why = "the balance of evidence shifted"
        changes.append({"symbol": sym, "was": was_label, "now": now_label,
                        "why": why, "dir": direction})
    changes.sort(key=lambda c: -abs(_LABEL_ORDER.get(c["now"], 2) - _LABEL_ORDER.get(c["was"], 2)))
    return changes


def materiality_feed_html(changes: list[dict], has_prior: bool) -> str:
    """The change-feed block for the home page (server-rendered)."""
    if not has_prior:
        return ('<p class="mf-none">First build — no prior verdicts to compare against yet. '
                'Changes appear here once a second nightly build lands.</p>')
    if not changes:
        return '<p class="mf-none">No verdict changed since the last build.</p>'
    marks = {"up": ("&#9650;", UP), "down": ("&#9660;", DOWN), "neutral": ("&#9679;", MUTED)}
    rows = []
    for c in changes[:12]:
        arrow, tone = marks.get(c.get("dir", "neutral"), marks["neutral"])
        rows.append(
            f'<li><a href="t/{_esc(c["symbol"])}.html"><b>{_esc(c["symbol"])}</b></a> '
            f'<span class="mf-move" style="color:{tone}">{arrow} {_esc(c["was"])} &#8594; '
            f'{_esc(c["now"])}</span> <span class="mf-why">because {_esc(c["why"])}</span></li>'
        )
    return f'<ul class="mfeed">{"".join(rows)}</ul>'


def render_compare_page(payload: dict, default_a: str = "", default_b: str = "") -> str:
    """site/compare.html — two built tickers side by side, component-by-component."""
    cmap = compact_map(payload)
    syms = sorted(cmap)
    da = default_a if default_a in cmap else (syms[0] if syms else "")
    db = default_b if default_b in cmap else (syms[1] if len(syms) > 1 else "")
    opts = "".join(f'<option value="{_esc(s)}">{_esc(s)}</option>' for s in syms)
    comp_labels = _json_html(COMPONENT_LABEL)
    da_json = _json_html(da)
    db_json = _json_html(db)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Compare — The Verdict Desk</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);font-variant-numeric:tabular-nums}}
.wrap{{max-width:820px;margin:0 auto;padding:22px 18px 70px}}
a{{color:var(--accent);text-decoration:none}}
h1{{font:800 22px/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin:6px 0 16px}}
.pick{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:18px}}
.pick select{{font:600 14px/1 var(--mono);color:var(--ink);background:var(--card);
  border:1px solid var(--rule);border-radius:6px;padding:10px 12px}}
.pick .vs{{font:700 12px/1 var(--mono);color:var(--mut)}}
table{{width:100%;border-collapse:collapse;font:400 13px/1.5 var(--mono)}}
th{{font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--mut);
  border-bottom:2px solid var(--ink);padding:0 10px 8px 0}}
th.c,td.c{{text-align:center}}
td{{padding:9px 10px 9px 0;border-bottom:1px solid var(--rule)}}
.win{{background:#eef5ec}}
.hd td{{font-weight:700;font-size:16px}}
.na{{color:var(--faint)}}
footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--faint);text-align:center}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body><div class="wrap">
<div><a href="index.html">&#9666; Platform</a></div>
<h1>Compare</h1>
<div class="pick"><select id="a">{opts}</select><span class="vs">vs</span><select id="b">{opts}</select></div>
<div id="cmp"></div>
<footer>Per-component verdicts, side by side — research opinions, not financial advice.</footer>
</div>
<script id="cmap" type="application/json">{_json_html(cmap)}</script>
<script>
(function(){{
  var M=JSON.parse(document.getElementById('cmap').textContent||'{{}}');
  var TONE={{'STRONG BUY':'{UP}','BUY':'{UP}','HOLD':'{MUTED}','TRIM':'{DOWN}','AVOID':'{DOWN}','INSUFFICIENT EVIDENCE':'{FAINT}'}};
  var LAB={comp_labels};
  function esc(x){{return String(x).replace(/[&<>"']/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];}});}}
  var qs=new URLSearchParams(location.search);
  var a=document.getElementById('a'), b=document.getElementById('b');
  function pick(sel,v){{ if(v&&M[v.toUpperCase()]) sel.value=v.toUpperCase(); }}
  pick(a, qs.get('a')|| {da_json}); pick(b, qs.get('b')|| {db_json});
  function fmt(v){{ return (v>=0?'+':'')+v.toFixed(2); }}
  function render(){{
    var A=M[a.value], B=M[b.value]; if(!A||!B){{document.getElementById('cmp').innerHTML='';return;}}
    var keys={{}}; Object.keys(A.components).forEach(function(k){{keys[k]=1;}}); Object.keys(B.components).forEach(function(k){{keys[k]=1;}});
    var rows='<tr class="hd"><td>overall</td><td class="c" style="color:'+(TONE[A.label]||'{FAINT}')+'">'+esc(A.label)+'</td>'
      +'<td class="c" style="color:'+(TONE[B.label]||'{FAINT}')+'">'+esc(B.label)+'</td></tr>';
    Object.keys(keys).sort().forEach(function(k){{
      var av=A.components[k], bv=B.components[k];
      var aw=(av!=null&&bv!=null&&av>bv)?' win':'', bw=(av!=null&&bv!=null&&bv>av)?' win':'';
      rows+='<tr><td>'+esc(LAB[k]||k)+'</td>'
        +'<td class="c'+aw+'">'+(av!=null?fmt(av):'<span class="na">n/a</span>')+'</td>'
        +'<td class="c'+bw+'">'+(bv!=null?fmt(bv):'<span class="na">n/a</span>')+'</td></tr>';
    }});
    document.getElementById('cmp').innerHTML='<table><thead><tr><th>component</th>'
      +'<th class="c">'+esc(a.value)+'</th><th class="c">'+esc(b.value)+'</th></tr></thead><tbody>'+rows+'</tbody></table>';
    history.replaceState(null,'','?a='+encodeURIComponent(a.value)+'&b='+encodeURIComponent(b.value));
  }}
  a.addEventListener('change',render); b.addEventListener('change',render); render();
}})();
</script>
</body></html>"""


def build_compare_page(out_dir, *, verdicts_dir=None) -> bool:
    """Write site/compare.html from the latest artifact. False if none exists."""
    from pathlib import Path

    from ..pipeline.verdicts import load_latest_verdicts

    loaded = load_latest_verdicts(verdicts_dir)
    if loaded.get("empty"):
        return False
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "compare.html").write_text(render_compare_page(loaded["payload"]), encoding="utf-8")
    return True
