"""The decision journal — site/journal.html (P6d section A).

"I followed this / I ignored this" clicks from the ticker and portfolio pages
land in localStorage; this page lists them and joins each entry CLIENT-SIDE
against the embedded PUBLIC regret artifact, so an aged decision shows what
following actually did vs SPY / HYSA once its horizon resolved. Honest states
everywhere: "not yet resolved" before the horizon, "not tracked" when the
regret ledger never opened that name (it only tracks attractive verdicts).

The journal itself never leaves the browser — no fetch, no upload, ever (the
operator's privacy decision §11); the ONLY server-side content on this page is
the public regret data every visitor can already see. Not financial advice.
"""

from __future__ import annotations

from pathlib import Path

from ..calibration_log.regret import RegretLedger
from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _json_html


def regret_join_rows(ledger: RegretLedger) -> list[dict]:
    """The PUBLIC reduction of the regret ledger the journal joins against:
    one row per tracked entry, keyed by symbol + the artifact date the decision
    was made on. Nothing personal is in here — it's the same public artifact
    the arena page renders."""
    rows = []
    for r in ledger.entries:
        e = r["entry"]
        row = {"symbol": e["symbol"], "as_of": e["date"],
               "horizon_days": e["horizon_days"], "resolved": "resolution" in r}
        if row["resolved"]:
            res = r["resolution"]
            row["return"] = res["return"]
            row["edge_spy"] = res["edge_vs"]["spy"]
            row["edge_hysa"] = res["edge_vs"]["hysa"]
        rows.append(row)
    return rows


def render_journal_page(regret_rows: list[dict], as_of: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your decision journal — The Verdict Desk</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);font-variant-numeric:tabular-nums}}
.wrap{{max-width:880px;margin:0 auto;padding:22px 18px 70px}}
a{{color:var(--accent);text-decoration:none}}
h1{{font:800 22px/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin:6px 0 4px}}
.sub{{color:var(--mut);font-size:12.5px;max-width:66ch}}
.card{{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:18px 20px;margin:14px 0}}
table{{width:100%;border-collapse:collapse;font:400 13px/1.5 var(--mono)}}
th{{text-align:left;font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--mut);
  border-bottom:2px solid var(--ink);padding:0 10px 8px 0}}
td{{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
.up{{color:var(--up)}} .down{{color:var(--down)}} .na{{color:var(--faint)}}
.act{{font:700 11px/1 var(--mono);text-transform:uppercase;letter-spacing:.04em}}
.note{{color:var(--mut);font-size:11.5px;display:block;margin-top:2px}}
.mini{{font:600 10.5px/1 var(--mono);border:1px solid var(--rule);background:var(--paper);
  color:var(--mut);border-radius:4px;padding:4px 7px;cursor:pointer}}
.empty{{color:var(--mut);font-size:13px}}
footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--faint);text-align:center}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body>
<div class="wrap">
<a href="index.html">&#9666; Platform</a>
<h1>Your decision journal</h1>
<p class="sub">Every "I followed / I ignored" you logged, scored against what actually happened
once the horizon resolved. This page reads only your browser&#8217;s local storage — your
decisions are never uploaded, never on a server. Not financial advice.</p>

<div class="card" id="jcard">
  <p class="empty" id="jempty">No decisions logged yet — the &#10003; / &#10007; buttons live on
  every ticker page and the portfolio page. Log one and it appears here, scored honestly
  once its horizon resolves.</p>
  <table id="jtable" style="display:none"><thead><tr><th>date</th><th>symbol</th>
    <th>decision</th><th>verdict then</th><th>outcome so far</th><th></th></tr></thead>
    <tbody id="jrows"></tbody></table>
</div>

<footer>Research opinions, not financial advice. The journal is stored only in your browser.
· <a href="index.html">platform</a> · <a href="portfolio.html">portfolio</a>
· <a href="arena.html">arena</a></footer>
</div>
<script id="regret" type="application/json">{_json_html(regret_rows)}</script>
<script>{_JOURNAL_JS}</script>
</body></html>"""


# reads flab_journal (browser-local) + the embedded PUBLIC regret rows; renders
# the join. No fetch / no upload path exists anywhere in this script (pinned).
_JOURNAL_JS = r"""
(function(){
  function J(id){try{return JSON.parse(document.getElementById(id).textContent||'null')||[];}catch(e){return [];}}
  function esc(x){return String(x).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  var REG=J('regret');
  function load(){try{return JSON.parse(localStorage.getItem('flab_journal'))||[];}catch(e){return [];}}
  function save(j){localStorage.setItem('flab_journal',JSON.stringify(j));}
  function match(en){ // join key: symbol + the artifact date the decision was made on
    for(var i=0;i<REG.length;i++) if(REG[i].symbol===en.symbol&&REG[i].as_of===en.as_of) return REG[i];
    return null;}
  function pct(x){return (x>=0?'+':'')+(100*x).toFixed(2)+'%';}
  function outcome(en){
    var m=match(en);
    if(!m) return '<span class="na">not tracked — the regret ledger only opens attractive verdicts</span>';
    if(!m.resolved) return '<span class="na">not yet resolved ('+m.horizon_days+'d horizon)</span>';
    var flip=en.action==='ignored'?-1:1, verb=en.action==='ignored'?'ignoring':'following';
    var parts=[];
    if(m.edge_spy!=null){var e=flip*m.edge_spy;
      parts.push('<span class="'+(e>=0?'up':'down')+'">'+verb+' '+(e>=0?'beat':'lagged')+' SPY by '+pct(Math.abs(e)===e?e:e)+'</span>');}
    if(m.edge_hysa!=null){var h=flip*m.edge_hysa;
      parts.push('<span class="'+(h>=0?'up':'down')+'">vs HYSA '+pct(h)+'</span>');}
    parts.push('<span class="na">the pick itself: '+pct(m['return'])+'</span>');
    return parts.join(' · ');}
  function render(){
    var j=load();
    document.getElementById('jempty').style.display=j.length?'none':'';
    document.getElementById('jtable').style.display=j.length?'':'none';
    document.getElementById('jrows').innerHTML=j.map(function(en,i){
      var note=en.note?'<span class="note">'+esc(en.note)+'</span>':'';
      return '<tr><td>'+esc(en.date)+'</td>'
        +'<td><a href="t/'+esc(en.symbol)+'.html">'+esc(en.symbol)+'</a></td>'
        +'<td class="act">'+(en.action==='followed'?'✓ followed':'✗ ignored')+'</td>'
        +'<td>'+esc(en.label)+' ('+((en.score>=0?'+':'')+Number(en.score).toFixed(2))+')'+note+'</td>'
        +'<td>'+outcome(en)+'</td>'
        +'<td><button class="mini" data-i="'+i+'" data-k="note">note</button> '
        +'<button class="mini" data-i="'+i+'" data-k="del">×</button></td></tr>';
    }).join('');}
  document.getElementById('jrows').addEventListener('click',function(ev){
    var t=ev.target; if(!t.dataset||t.dataset.i==null)return;
    var j=load(), i=+t.dataset.i; if(!j[i])return;
    if(t.dataset.k==='del'){j.splice(i,1);}
    else{var n=prompt('Note for '+j[i].symbol+':',j[i].note||''); if(n===null)return; j[i].note=n;}
    save(j); render();});
  render();
})();
"""


def build_journal_page(out_dir, *, regret_path=None) -> Path:
    """Write site/journal.html. The embedded regret rows are public data; the
    page renders its honest empty state with no ledger at all."""
    ledger = RegretLedger(path=regret_path) if regret_path else RegretLedger()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    page = out / "journal.html"
    page.write_text(render_journal_page(regret_join_rows(ledger)), encoding="utf-8")
    return page
