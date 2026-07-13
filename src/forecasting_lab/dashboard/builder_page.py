"""The watcher builder — site/builder.html (P10-3, the agent-builder shape).

Rallies' "describe what to watch once, it runs 24/7" gallery, our honesty:
the five deterministic templates as cards with plain-language descriptions,
threshold controls BOUNDED to each template's stated valid range (from the
exported ``watchers_contract()`` — never re-hardcoded), a live JSON preview,
and copy-to-clipboard. The config stays a COMMITTED file — this page writes
nothing anywhere; it says so on screen. Not financial advice.
"""

from __future__ import annotations

from pathlib import Path

from ..pipeline.watchers import load_config, watchers_contract
from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _json_html


def render_builder_page() -> str:
    contract = watchers_contract()
    current = load_config()
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Watcher builder — The Verdict Desk</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);font-variant-numeric:tabular-nums}}
.wrap{{max-width:880px;margin:0 auto;padding:22px 18px 80px}}
a{{color:var(--accent);text-decoration:none}}
h1{{font:800 22px/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin:6px 0 4px}}
.sub{{color:var(--mut);font-size:12.5px;max-width:66ch;margin-bottom:16px}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-bottom:18px}}
.tmpl{{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:16px 18px}}
.tmpl h2{{font:800 13px/1.3 var(--mono);letter-spacing:.05em;text-transform:uppercase;display:flex;
  justify-content:space-between;align-items:center;gap:8px}}
.tmpl p{{color:var(--mut);font-size:12px;margin:8px 0 12px;min-height:54px}}
.tmpl label{{display:block;font:600 10.5px/1.5 var(--mono);text-transform:uppercase;
  letter-spacing:.05em;color:var(--mut)}}
.tmpl input[type=range]{{width:100%}}
.pval{{font:800 14px/1 var(--mono);color:var(--ink)}}
.bounds{{color:var(--faint);font-size:10.5px}}
.fixed{{color:var(--faint);font-size:10.5px;margin-top:6px}}
.tmpl input[type=checkbox]{{transform:scale(1.2)}}
.preview{{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:16px 18px}}
.preview h2{{font:800 13px/1.3 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin-bottom:8px}}
.preview textarea{{width:100%;height:200px;font:400 12px/1.5 var(--mono);border:1px solid var(--rule);
  border-radius:5px;padding:10px;background:var(--paper);color:var(--ink);resize:vertical}}
.actions{{display:flex;gap:10px;margin-top:10px;align-items:center}}
.actions button{{font:700 12px/1 var(--mono);text-transform:uppercase;border:0;background:var(--ink);
  color:var(--paper);border-radius:6px;padding:11px 16px;cursor:pointer}}
.actions .note{{color:var(--faint);font-size:11px}}
.howto{{color:var(--mut);font-size:12px;margin-top:12px;border-top:1px solid var(--rule);padding-top:10px}}
.howto code{{background:var(--paper);border:1px solid var(--rule);border-radius:3px;padding:1px 5px}}
footer{{margin-top:26px;padding-top:14px;border-top:1px solid var(--rule);
  font-size:11.5px;color:var(--faint);text-align:center}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body>
<div class="wrap">
<a href="index.html">&#9666; Platform</a>
<h1>Watcher builder</h1>
<p class="sub">The five deterministic templates — describe what to watch once, the nightly
run does the rest. Thresholds are bounded to each template&#8217;s stated valid range (from
the same contract the runner reads). <b>This page writes nothing anywhere</b>: the config is
a committed file, and committing it is your move.</p>
<div class="gallery" id="gallery"></div>
<div class="preview"><h2>data/watchers.json — live preview</h2>
  <textarea id="json" readonly aria-label="generated config"></textarea>
  <div class="actions">
    <button id="copy">Copy config</button>
    <span class="note" id="copied"></span>
  </div>
  <p class="howto">To apply: paste over <code>data/watchers.json</code> in the repo and
  commit — the next nightly run loads it (unknown keys are ignored; out-of-range values
  fall back to the stated defaults at your own risk of a stated skip). No server is
  involved, ever.</p>
</div>
<footer>The Verdict Desk · deterministic templates, receipts on every firing ·
not financial advice · <a href="index.html">platform</a></footer>
</div>
<script id="contract" type="application/json">{_json_html(contract)}</script>
<script id="current" type="application/json">{_json_html(current)}</script>
<script>{_BUILDER_JS}</script>
</body></html>"""


_BUILDER_JS = r"""
(function(){
  function J(id){try{return JSON.parse(document.getElementById(id).textContent||'null');}catch(e){return null;}}
  var C=J('contract'), CUR=J('current')||{}, state={};
  var gallery=document.getElementById('gallery'), out=document.getElementById('json');
  function clamp(v,p){v=Number(v);if(!isFinite(v))return p.default;
    v=Math.min(p.max,Math.max(p.min,v));
    if(p.type==='int')return Math.round(v);
    // step-round FROM min and normalize to the step's precision, then reclamp
    // (Codex review: 0.6/0.05 float noise emitted 0.6000000000000001)
    var dec=(String(p.step).split('.')[1]||'').length;
    v=Math.round((v-p.min)/p.step)*p.step+p.min;
    return Math.min(p.max,Math.max(p.min,Number(v.toFixed(dec))));}
  Object.keys(C.kinds).forEach(function(kind){
    var spec=C.kinds[kind], cur=CUR[kind]||{};
    state[kind]={enabled:cur.enabled!==false};
    Object.keys(spec.params).forEach(function(name){
      state[kind][name]=clamp(cur[name]!=null?cur[name]:spec.params[name].default,spec.params[name]);});
    Object.keys(spec.fixed||{}).forEach(function(k){state[kind][k]=spec.fixed[k];});

    var card=document.createElement('div');card.className='tmpl';
    var h=document.createElement('h2');
    var title=document.createElement('span');title.textContent=kind.replace(/_/g,' ');
    var toggle=document.createElement('input');toggle.type='checkbox';
    toggle.checked=state[kind].enabled;toggle.setAttribute('aria-label','enable '+kind);
    toggle.addEventListener('change',function(){state[kind].enabled=toggle.checked;emit();});
    h.appendChild(title);h.appendChild(toggle);card.appendChild(h);
    var p=document.createElement('p');p.textContent=spec.description;card.appendChild(p);
    Object.keys(spec.params).forEach(function(name){
      var ps=spec.params[name];
      var lab=document.createElement('label');
      lab.textContent=name.replace(/_/g,' ')+' ';
      var val=document.createElement('span');val.className='pval';
      val.textContent=state[kind][name];lab.appendChild(val);
      var r=document.createElement('input');r.type='range';
      r.min=ps.min;r.max=ps.max;r.step=ps.step;r.value=state[kind][name];
      r.setAttribute('aria-label',kind+' '+name);
      r.addEventListener('input',function(){
        state[kind][name]=clamp(r.value,ps);            // bounded, always
        val.textContent=state[kind][name];emit();});
      var b=document.createElement('div');b.className='bounds';
      b.textContent='valid range '+ps.min+' – '+ps.max+' (default '+ps.default+')';
      card.appendChild(lab);card.appendChild(r);card.appendChild(b);});
    var fixedKeys=Object.keys(spec.fixed||{});
    if(fixedKeys.length){var f=document.createElement('div');f.className='fixed';
      f.textContent='fixed: '+fixedKeys.map(function(k){return k+'='+spec.fixed[k];}).join(', ');
      card.appendChild(f);}
    gallery.appendChild(card);
  });
  function emit(){out.value=JSON.stringify(state,null,2);}
  emit();
  document.getElementById('copy').addEventListener('click',function(){
    out.select();
    var note=document.getElementById('copied');
    var done=function(){note.textContent='copied — paste over data/watchers.json and commit';};
    var fail=function(){                                   // honest failure (Codex review):
      var ok=false;try{ok=document.execCommand('copy');}catch(e){}
      note.textContent=ok?'copied — paste over data/watchers.json and commit'
        :'copy failed — select the text above and copy manually';};
    if(navigator.clipboard&&navigator.clipboard.writeText)
      navigator.clipboard.writeText(out.value).then(done,fail);
    else fail();
  });
})();
"""


def build_builder_page(out_dir) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    page = out / "builder.html"
    page.write_text(render_builder_page(), encoding="utf-8")
    return page
