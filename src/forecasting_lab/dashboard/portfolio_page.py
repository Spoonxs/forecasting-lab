"""The portfolio page — site/portfolio.html (P6c section B).

Enter holdings (form or broker CSV, parsed IN-BROWSER) and see them evaluated
against the P6a verdicts + the mandate: concentration, ETF overlap, per-holding
verdicts, crowding, vs-SPY/vs-HYSA, the decision-friction flags, and advice with
reasons. Holdings live in localStorage ONLY — never uploaded, never committed
(the operator's privacy decision) — with a one-click passphrase-encrypted
export/import. A hide-values toggle blurs dollar amounts. A server-rendered demo
book means the page is never blank; the client re-evaluates on edit by reading
the SAME contract the Python engine exports (never re-hardcoded numbers).
Not financial advice — the operator's own research tool.
"""

from __future__ import annotations

import json

from ..signals.portfolio import evaluate_portfolio, portfolio_contract
from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _esc, _json_html

VERDICT_TONE = {"STRONG BUY": UP, "BUY": UP, "HOLD": MUTED, "TRIM": DOWN,
                "AVOID": DOWN, "INSUFFICIENT EVIDENCE": FAINT}
DEMO_HOLDINGS = [
    {"symbol": "VOO", "weight": 0.30}, {"symbol": "QQQ", "weight": 0.25},
    {"symbol": "NVDA", "weight": 0.20}, {"symbol": "SCHD", "weight": 0.15},
]


def _verdict_map(payload: dict) -> dict:
    return {s: {"label": r.get("label"), "score": r.get("score", 0.0)}
            for s, r in (payload.get("verdicts", {}) if payload else {}).items()}


def _holdings_rows(ev: dict) -> str:
    rows = []
    for h in ev.get("holdings", []):
        tone = VERDICT_TONE.get(h["label"], FAINT)
        score = "n/a" if h["score"] is None else f'{h["score"]:+.2f}'
        fr = "".join(f'<div class="fr">&#9888; {_esc(f)}</div>' for f in h["friction"])
        rows.append(
            f'<tr><td><a href="t/{_esc(h["symbol"])}.html">{_esc(h["symbol"])}</a></td>'
            f'<td class="num val">{h["weight"]:.0%}</td>'
            f'<td style="color:{tone}">{_esc(h["label"])}</td>'
            f'<td class="num">{score}</td><td>{fr}</td></tr>'
        )
    return "".join(rows)


def _advice_html(ev: dict) -> str:
    icons = {"block": "&#128721;", "overlap": "&#128260;", "crowding": "&#9888;",
             "friction": "&#9203;", "cash": "&#128176;", "unrated": "&#8709;"}
    items = "".join(f'<li class="ad-{a["kind"]}"><span>{icons.get(a["kind"], "&#8226;")}</span> '
                    f'{_esc(a["text"])}</li>' for a in ev.get("advice", []))
    return f'<ul class="advice">{items}</ul>' if items else '<p class="ok">Nothing flagged — the book is inside the mandate.</p>'


def render_portfolio_page(payload: dict, hysa_yield_pct: float | None = None) -> str:
    contract = portfolio_contract()
    vmap = _verdict_map(payload)
    demo = evaluate_portfolio(DEMO_HOLDINGS, {s: {"label": v["label"], "score": v["score"]}
                                              for s, v in vmap.items()},
                              hysa_yield_pct=hysa_yield_pct)
    if demo.get("empty"):
        demo = {"holdings": [], "advice": [], "cash": 0.0, "mandate_status": "pass",
                "blended_score": None, "vs_spy": None, "vs_hysa": None,
                "crowding": {"crowded": False, "top_name": None, "top_weight": 0.0}}
    blended = "n/a" if demo["blended_score"] is None else f'{demo["blended_score"]:+.3f}'
    vs_spy = "n/a" if demo["vs_spy"] is None else f'{demo["vs_spy"]:+.3f}'
    vs_hysa = "n/a" if demo["vs_hysa"] is None else f'{demo["vs_hysa"]:+.3f}'
    mstatus = demo["mandate_status"]
    mtone = {"block": DOWN, "warn": "#B8860B", "pass": UP}.get(mstatus, MUTED)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your portfolio — The Verdict Desk</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);font-variant-numeric:tabular-nums}}
.wrap{{max-width:880px;margin:0 auto;padding:22px 18px 70px}}
a{{color:var(--accent);text-decoration:none}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
h1{{font:800 22px/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin:6px 0 4px}}
.sub{{color:var(--mut);font-size:12.5px;max-width:64ch}}
.card{{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:18px 20px;margin:14px 0}}
h3{{font:700 12px/1.3 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mut);margin:0 0 10px}}
.stats{{display:flex;gap:22px;flex-wrap:wrap;margin-bottom:14px}}
.stat span{{display:block;font:600 10px/1 var(--mono);text-transform:uppercase;color:var(--mut);margin-bottom:4px}}
.stat b{{font:800 20px/1 var(--mono)}}
.mtag{{display:inline-block;font:700 11px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;
  color:#fff;border-radius:3px;padding:5px 9px}}
table{{width:100%;border-collapse:collapse;font:400 13px/1.5 var(--mono)}}
th{{text-align:left;font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--mut);
  border-bottom:2px solid var(--ink);padding:0 10px 8px 0}}
th.num,td.num{{text-align:right}}
td{{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
.fr{{color:var(--down);font-size:11.5px;margin-top:2px}}
.advice{{list-style:none}}
.advice li{{display:flex;gap:8px;padding:7px 0;border-bottom:1px solid var(--rule);font-size:12.5px}}
.advice li:last-child{{border-bottom:0}}
.ad-block{{color:var(--down)}} .ad-crowding,.ad-friction{{color:#8a5a00}}
.ok{{color:var(--up);font-size:13px}}
.entry{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}}
.entry input{{font:500 13px/1 var(--mono);border:1px solid var(--rule);border-radius:5px;padding:9px 11px}}
.entry input#psym{{width:110px;text-transform:uppercase}} .entry input#pamt{{width:120px}}
button{{font:700 12px/1 var(--mono);border:1px solid var(--rule);background:var(--paper);color:var(--ink);
  border-radius:6px;padding:9px 13px;cursor:pointer}}
button.pri{{background:var(--ink);color:var(--paper);border-color:var(--ink)}}
.tools{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}}
label.csv{{display:inline-flex;align-items:center;gap:6px;font:700 12px/1 var(--mono);
  border:1px solid var(--rule);border-radius:6px;padding:9px 13px;cursor:pointer}}
label.csv input{{display:none}}
body.hidden .val{{filter:blur(6px);user-select:none}}
.demo{{font-size:11.5px;color:var(--faint);margin-top:8px}}
footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--faint);text-align:center}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
@media(max-width:560px){{.entry input{{flex:1}}}}
</style></head><body>
<div class="wrap">
<div class="top"><a href="index.html">&#9666; Platform</a>
  <button id="hideBtn" title="blur dollar values">&#128065; Hide values</button></div>
<h1>Your portfolio</h1>
<p class="sub">Entered here, evaluated against today&#8217;s verdicts and the mandate. Your holdings
stay in this browser only — never uploaded, never on a server. Not financial advice.</p>

<div class="card"><h3>Add holdings</h3>
  <div class="entry">
    <input id="psym" placeholder="TICKER" aria-label="ticker">
    <input id="pamt" placeholder="$ or weight%" aria-label="amount">
    <button class="pri" id="addBtn">Add</button>
    <button id="clearBtn">Clear all</button>
  </div>
  <div class="tools">
    <label class="csv">&#128194; Import broker CSV<input type="file" id="csv" accept=".csv"></label>
    <button id="expBtn">&#128274; Export (encrypted)</button>
    <button id="impBtn">Import</button>
  </div>
  <p class="demo">Showing a demo book until you add your own. Robinhood / Fidelity / Schwab CSV
  columns are auto-detected, parsed in your browser, never uploaded.</p>
</div>

<div class="card" id="evalCard">
  <div class="stats">
    <div class="stat"><span>Mandate</span><b><span class="mtag" id="mtag" style="background:{mtone}">{_esc(mstatus)}</span></b></div>
    <div class="stat"><span>Blended lean</span><b id="sBlended">{blended}</b></div>
    <div class="stat"><span>vs SPY</span><b id="sSpy">{vs_spy}</b></div>
    <div class="stat"><span>vs HYSA</span><b id="sHysa">{vs_hysa}</b></div>
  </div>
  <table><thead><tr><th>holding</th><th class="num">weight</th><th>verdict</th>
    <th class="num">score</th><th>friction</th></tr></thead>
    <tbody id="prows">{_holdings_rows(demo)}</tbody></table>
  <h3 style="margin-top:18px">Advice</h3>
  <div id="advice">{_advice_html(demo)}</div>
</div>

<footer>Research opinions, not financial advice. Holdings are stored only in your browser.
· <a href="index.html">platform</a> · <a href="scorecard.html">scorecard</a></footer>
</div>
<script id="contract" type="application/json">{_json_html(contract)}</script>
<script id="verdicts" type="application/json">{_json_html(vmap)}</script>
<script id="demo" type="application/json">{_json_html(DEMO_HOLDINGS)}</script>
<script>{_PORTFOLIO_JS.replace("HYSA_YIELD", json.dumps(hysa_yield_pct))}</script>
</body></html>"""


def build_portfolio_page(out_dir, *, verdicts_dir=None):
    """Write site/portfolio.html from the latest verdict artifact. Renders even
    without one (the demo book shows honest INSUFFICIENT + n/a) — never blank."""
    from pathlib import Path

    from ..pipeline.verdicts import load_latest_verdicts

    loaded = load_latest_verdicts(verdicts_dir)
    payload = {} if loaded.get("empty") else loaded["payload"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    page = out / "portfolio.html"
    page.write_text(render_portfolio_page(payload, hysa_yield_pct=payload.get("hysa_yield_pct")),
                    encoding="utf-8")
    return page


# the client-side evaluator — mirrors signals/portfolio.evaluate_portfolio, reading
# the SAME contract (thresholds + core_etf_holdings) so the numbers can't drift.
_PORTFOLIO_JS = r"""
(function(){
  function J(id){try{return JSON.parse(document.getElementById(id).textContent||'null');}catch(e){return null;}}
  var C=J('contract'), V=J('verdicts')||{}, DEMO=J('demo')||[], HY=HYSA_YIELD;
  var TONE={'STRONG BUY':'#2F7D31','BUY':'#2F7D31','HOLD':'#6B6864','TRIM':'#C6392C','AVOID':'#C6392C','INSUFFICIENT EVIDENCE':'#9A958C'};
  function esc(x){return String(x).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function load(){try{return JSON.parse(localStorage.getItem('flab_holdings'))||null;}catch(e){return null;}}
  function save(h){localStorage.setItem('flab_holdings',JSON.stringify(h));}
  function norm(raw){var agg={};raw.forEach(function(r){var s=String(r.symbol||'').trim().toUpperCase();
    if(!s)return; var v=(r.dollars!=null)?+r.dollars:(r.weight!=null?+r.weight:NaN);
    if(isNaN(v)||v<0)return; agg[s]=(agg[s]||0)+v;});
    var tot=0;Object.keys(agg).forEach(function(k){tot+=agg[k];}); if(tot<=0)return [];
    var scale=tot>1.0001?tot:1; return Object.keys(agg).map(function(s){return {symbol:s,weight:agg[s]/scale};});}
  function expo(sym,w){var h=C.core_etf_holdings[sym]; if(h){var o={};Object.keys(h).forEach(function(n){o[n]=w*h[n];});return o;} var o={};o[sym]=w;return o;}
  function evalBook(hold){
    if(!hold.length) return {empty:true};
    var invested=0;hold.forEach(function(h){invested+=h.weight;}); if(invested<=0)invested=1;
    var cash=Math.max(0,1-hold.reduce(function(a,h){return a+h.weight;},0));
    var cap=C.max_position_pct;
    // look-through crowding
    var lt={};hold.forEach(function(h){var e=expo(h.symbol,h.weight);Object.keys(e).forEach(function(n){lt[n]=(lt[n]||0)+e[n];});});
    var topN=null,topW=0;Object.keys(lt).forEach(function(n){if(lt[n]/invested>topW){topW=lt[n]/invested;topN=n;}});
    // overlaps
    var ov=[];for(var i=0;i<hold.length;i++)for(var j=i+1;j<hold.length;j++){
      var ea=expo(hold[i].symbol,hold[i].weight),eb=expo(hold[j].symbol,hold[j].weight),bo=0,nm=[];
      Object.keys(ea).forEach(function(n){if(eb[n]!=null){bo+=Math.min(ea[n],eb[n]);nm.push(n);}});
      if(bo>C.overlap_report_floor)ov.push({a:hold[i].symbol,b:hold[j].symbol,bo:bo,names:nm});}
    ov.sort(function(a,b){return b.bo-a.bo;});
    // per-holding + mandate + blended
    var rows=[],rw=0,rs=0,unrated=[],block=[];
    hold.forEach(function(h){var v=V[h.symbol]||{},lab=(v.label||'INSUFFICIENT EVIDENCE'),
      rated=(v&&'score'in v&&String(lab).toUpperCase().indexOf('INSUFFICIENT')!==0),
      sc=rated?+v.score:null,inv=h.weight/invested,fr=[];
      if((lab==='STRONG BUY'||lab==='BUY')&&inv>=cap-1e-9)fr.push('already '+Math.round(inv*100)+'% of invested — at/over the '+Math.round(cap*100)+'% cap');
      if(inv>cap+1e-9)block.push(h.symbol+': '+Math.round(inv*100)+'% exceeds the '+Math.round(cap*100)+'% cap');
      if(rated){rw+=h.weight;rs+=h.weight*sc;}else unrated.push(h.symbol);
      rows.push({symbol:h.symbol,weight:h.weight,label:lab,score:sc,friction:fr});});
    rows.sort(function(a,b){return (a.score===null)-(b.score===null)||(b.score||0)-(a.score||0);});
    if(cash< (C.min_cash_pct||0)-1e-12)block.push('cash '+Math.round(cash*100)+'% below the floor');
    var blended=rw>0?rs/rw:null;
    var spy=V.SPY&&String(V.SPY.label).toUpperCase().indexOf('INSUFFICIENT')!==0?+V.SPY.score:null;
    var vspy=(blended!=null&&spy!=null)?blended-spy:null;
    var vhysa=(blended!=null&&HY!=null)?blended-HY/100:null;
    var advice=[];block.forEach(function(b){advice.push({kind:'block',text:b});});
    ov.slice(0,3).forEach(function(o){advice.push({kind:'overlap',text:o.a+' + '+o.b+' overlap ~'+Math.round(o.bo*100)+'% ('+o.names.slice(0,3).join(', ')+') — doubling the same names'});});
    if(topW>C.crowding_overlap_flag&&topN)advice.push({kind:'crowding',text:topN+' is ~'+Math.round(topW*100)+'% of the book once you look through the ETFs'});
    if(unrated.length)advice.push({kind:'unrated',text:'no verdict yet for '+unrated.join(', ')+' — excluded from the blended score, not guessed'});
    if(cash>0)advice.push({kind:'cash',text:Math.round(cash*100)+'% in cash'});
    rows.forEach(function(r){r.friction.forEach(function(f){advice.push({kind:'friction',text:r.symbol+': attractive, but '+f});});});
    return {rows:rows,cash:cash,mandate:block.length?'block':'pass',blended:blended,vspy:vspy,vhysa:vhysa,advice:advice};}
  function fmt(x){return x==null?'n/a':(x>=0?'+':'')+x.toFixed(3);}
  function render(){
    var hold=load(); var ev=evalBook(norm(hold||DEMO));
    if(ev.empty)return;
    document.getElementById('sBlended').textContent=fmt(ev.blended);
    document.getElementById('sSpy').textContent=fmt(ev.vspy);
    document.getElementById('sHysa').textContent=fmt(ev.vhysa);
    var mt=document.getElementById('mtag');mt.textContent=ev.mandate;
    mt.style.background=ev.mandate==='block'?'#C6392C':'#2F7D31';
    document.getElementById('prows').innerHTML=ev.rows.map(function(r){
      var sc=r.score==null?'n/a':(r.score>=0?'+':'')+r.score.toFixed(2);
      var fr=r.friction.map(function(f){return '<div class="fr">⚠ '+esc(f)+'</div>';}).join('');
      return '<tr><td><a href="t/'+esc(r.symbol)+'.html">'+esc(r.symbol)+'</a></td>'
        +'<td class="num val">'+Math.round(r.weight*100)+'%</td>'
        +'<td style="color:'+(TONE[r.label]||'#9A958C')+'">'+esc(r.label)+'</td>'
        +'<td class="num">'+sc+'</td><td>'+fr+'</td></tr>';}).join('');
    var ic={block:'🛑',overlap:'🔄',crowding:'⚠',friction:'⏳',cash:'💰',unrated:'∅'};
    document.getElementById('advice').innerHTML=ev.advice.length?('<ul class="advice">'+ev.advice.map(function(a){
      return '<li class="ad-'+a.kind+'"><span>'+(ic[a.kind]||'•')+'</span> '+esc(a.text)+'</li>';}).join('')+'</ul>')
      :'<p class="ok">Nothing flagged — the book is inside the mandate.</p>';}
  // controls
  function add(){var s=document.getElementById('psym').value.trim().toUpperCase(),a=document.getElementById('pamt').value.trim();
    if(!s||!a)return; var h=load()||[]; var pct=a.indexOf('%')>=0; var v=parseFloat(a.replace(/[$,%]/g,''));
    if(isNaN(v))return; h.push(pct?{symbol:s,weight:v/100}:{symbol:s,dollars:v}); save(h);
    document.getElementById('psym').value='';document.getElementById('pamt').value='';render();}
  document.getElementById('addBtn').addEventListener('click',add);
  document.getElementById('clearBtn').addEventListener('click',function(){localStorage.removeItem('flab_holdings');render();});
  document.getElementById('hideBtn').addEventListener('click',function(){document.body.classList.toggle('hidden');});
  // CSV import (client-side; never uploaded)
  // quoted-field splitter: broker values like "$12,345.67" carry commas (Codex fix)
  function cells(ln){var out=[],cur='',q=false;for(var i=0;i<ln.length;i++){var ch=ln[i];
    if(q){if(ch==='"'){if(ln[i+1]==='"'){cur+='"';i++;}else q=false;}else cur+=ch;}
    else if(ch==='"')q=true;else if(ch===','){out.push(cur);cur='';}else cur+=ch;}
    out.push(cur);return out;}
  function money(x){var v=parseFloat(String(x==null?'':x).replace(/[$,\s]/g,''));return isNaN(v)?NaN:v;}
  document.getElementById('csv').addEventListener('change',function(e){var f=e.target.files[0];if(!f)return;
    var rd=new FileReader();rd.onload=function(){var lines=String(rd.result).split(/\r?\n/).filter(Boolean);
      if(!lines.length)return; var head=cells(lines[0]).map(function(x){return x.trim().toLowerCase();});
      var si=head.findIndex(function(h){return /symbol|ticker/.test(h);});
      var vi=head.findIndex(function(h){return /market value|value|current value/.test(h);});
      var qi=head.findIndex(function(h){return /quantity|shares|qty/.test(h);});
      var pi=head.findIndex(function(h){return /price/.test(h);});
      if(si<0)return; var h=[];
      lines.slice(1).forEach(function(ln){var c=cells(ln);var s=(c[si]||'').trim().toUpperCase();
        if(!s||/^(cash|total)/i.test(s))return;
        // shares alone are NOT dollars — quantity only counts with a price column (Codex fix)
        var val=vi>=0?money(c[vi]):(qi>=0&&pi>=0?money(c[qi])*money(c[pi]):NaN);
        if(!isNaN(val)&&val>0)h.push({symbol:s,dollars:val});});
      if(h.length){save(h);render();}
      else alert('No holdings recognized — need symbol + market value (or shares + price) columns.');}; rd.readAsText(f);});
  // passphrase-encrypted export / import (AES-GCM via Web Crypto)
  async function keyFrom(pass,salt){var enc=new TextEncoder();
    var k=await crypto.subtle.importKey('raw',enc.encode(pass),'PBKDF2',false,['deriveKey']);
    return crypto.subtle.deriveKey({name:'PBKDF2',salt:salt,iterations:1e5,hash:'SHA-256'},k,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);}
  document.getElementById('expBtn').addEventListener('click',async function(){var h=load();if(!h){alert('No holdings to export yet.');return;}
    var pass=prompt('Passphrase to encrypt your export:');if(!pass)return;
    var salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12));
    var key=await keyFrom(pass,salt),ct=await crypto.subtle.encrypt({name:'AES-GCM',iv:iv},key,new TextEncoder().encode(JSON.stringify(h)));
    var blob=btoa(String.fromCharCode.apply(null,salt)+String.fromCharCode.apply(null,iv)+String.fromCharCode.apply(null,new Uint8Array(ct)));
    var a=document.createElement('a');a.href='data:text/plain,'+encodeURIComponent(blob);a.download='portfolio.flab';a.click();});
  document.getElementById('impBtn').addEventListener('click',function(){var inp=document.createElement('input');inp.type='file';inp.accept='.flab';
    inp.onchange=function(e){var f=e.target.files[0];if(!f)return;var rd=new FileReader();rd.onload=async function(){
      var pass=prompt('Passphrase to decrypt:');if(!pass)return;try{var raw=atob(String(rd.result).trim());
      var b=new Uint8Array(raw.length);for(var i=0;i<raw.length;i++)b[i]=raw.charCodeAt(i);
      var salt=b.slice(0,16),iv=b.slice(16,28),ct=b.slice(28);var key=await keyFrom(pass,salt);
      var pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:iv},key,ct);save(JSON.parse(new TextDecoder().decode(pt)));render();}
      catch(err){alert('Could not decrypt — wrong passphrase or corrupt file.');}};rd.readAsText(f);};inp.click();});
  render();
})();
"""
