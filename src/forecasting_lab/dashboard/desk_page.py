"""The in-site desk chat — site/desk.html + site/desk-data.json (P10-1).

The Rallies chat shape with our honesty: a client-side DETERMINISTIC mirror
of flab-ask's six intents over a reduced, same-origin data bundle built from
the SAME committed artifacts the CLI reads. Intent patterns come from the one
exported ``desk_contract()`` (never re-hardcoded); every answer carries the
same receipts (as_of + audit hash or "no record"); unknown questions get the
honest capability list; there is NO LLM in the browser and no external fetch
— the page lazy-fetches only ./desk-data.json. Not financial advice.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..desk.ask import desk_contract
from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _esc, _json_html


# ------------------------------------------------------------- the bundle
def build_desk_data(verdicts_dir=None, arena_path=None, regret_path=None,
                    inputs_dir=None) -> dict:
    """The reduced, PUBLIC data bundle the chat answers from — the same
    artifacts, trimmed to what the six intents need."""
    bundle: dict = {"as_of": "", "audit": "", "verdicts": {}, "changes": [],
                    "has_prior": False, "arena": [], "regret": {}, "watchers": {},
                    "twins": {}, "core_etfs": {}}
    try:
        from ..pipeline.verdicts import load_latest_verdicts

        loaded = load_latest_verdicts(verdicts_dir)
        if not loaded.get("empty"):
            payload = loaded["payload"]
            bundle["as_of"] = payload.get("as_of", "")
            bundle["audit"] = str(loaded.get("audit_sha", ""))[:12]
            for sym, r in payload.get("verdicts", {}).items():
                comps = sorted(r.get("components", {}).items(),
                               key=lambda kv: -abs(kv[1].get("score", 0.0)))[:3]
                bundle["verdicts"][sym] = {
                    "label": r.get("label"), "score": r.get("score", 0.0),
                    "dials": r.get("dials", {}),
                    "comps": [[n, round(c.get("score", 0.0), 2),
                               (c.get("detail") or "")[:60]] for n, c in comps],
                    "missing": r.get("missing", []),
                }
            prior = loaded.get("prior")
            bundle["has_prior"] = prior is not None
            if prior:
                from .compare import materiality_changes

                bundle["changes"] = [
                    {"symbol": c["symbol"], "was": c["was"], "now": c["now"],
                     "why": c["why"][:80]}
                    for c in materiality_changes(payload, prior)[:12]]
    except Exception:  # noqa: BLE001 - the desk answers honestly from less
        pass
    try:
        from ..agent_trader.arena_books import ArenaLedger

        led = ArenaLedger(path=arena_path) if arena_path else ArenaLedger()
        for owner, st in sorted(led.state.items()):
            if st.get("curve"):
                ev = (st.get("events") or [])[-1:]
                bundle["arena"].append({
                    "owner": owner, "equity": st["curve"][-1]["equity"],
                    "last_mark": st["curve"][-1]["date"],
                    "first_mark": st["curve"][0]["date"],
                    "last_event": (f"{ev[0]['kind']} {ev[0]['date']}" if ev else ""),
                })
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..calibration_log.regret import RegretLedger

        reg = RegretLedger(path=regret_path) if regret_path else RegretLedger()
        bundle["regret"] = reg.summary()
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..pipeline.digest import read_latest_data

        feed = read_latest_data("watchers", out_dir=inputs_dir) or {}
        bundle["watchers"] = {
            "events": [{"date": e.get("date"), "kind": e.get("kind"),
                        "reason": (e.get("reason") or "")[:90]}
                       for e in feed.get("events", [])[:6]],
            "skips": [{"kind": s.get("kind"), "reason": (s.get("reason") or "")[:90]}
                      for s in feed.get("skips", [])[:5]],
        }
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..sources.instruments import CORE_ETFS, MUTUAL_FUND_TWINS, fund_twin

        bundle["twins"] = {f: {k: v for k, v in fund_twin(f).items() if k != "fund"}
                           for f in MUTUAL_FUND_TWINS}
        bundle["core_etfs"] = {s: m["expense_ratio"] for s, m in CORE_ETFS.items()}
    except Exception:  # noqa: BLE001
        pass
    return bundle


# ------------------------------------------------------------- the page
def render_desk_page() -> str:
    contract = desk_contract()
    chips = "".join(f'<button class="chip" data-q="{_esc(q)}">{_esc(q)}</button>'
                    for q in contract["chips"])
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The desk — ask the platform | The Verdict Desk</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);font-variant-numeric:tabular-nums}}
.wrap{{max-width:820px;margin:0 auto;padding:22px 18px 80px}}
a{{color:var(--accent);text-decoration:none}}
h1{{font:800 22px/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin:6px 0 4px}}
.sub{{color:var(--mut);font-size:12.5px;max-width:66ch;margin-bottom:16px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 18px}}
.chip{{font:600 12px/1 var(--mono);border:1px solid var(--rule);background:var(--card);
  color:var(--ink);border-radius:16px;padding:9px 13px;cursor:pointer}}
.chip:hover{{border-color:var(--accent)}}
#log{{display:flex;flex-direction:column;gap:12px;margin-bottom:18px}}
.msg{{max-width:64ch;border:1px solid var(--rule);border-radius:8px;padding:12px 15px;font-size:13.5px}}
.msg.q{{align-self:flex-end;background:var(--ink);color:var(--paper)}}
.msg.a{{align-self:flex-start;background:var(--card);white-space:pre-wrap}}
.msg .rcpt{{display:block;margin-top:8px;color:var(--faint);font-size:11px}}
.msg.a .rcpt{{border-top:1px solid var(--rule);padding-top:6px}}
.entry{{display:flex;gap:8px}}
.entry input{{flex:1;font:500 14px/1 var(--mono);border:1px solid var(--rule);
  border-radius:8px;padding:12px 14px;background:var(--card);color:var(--ink)}}
.entry button{{font:700 13px/1 var(--mono);text-transform:uppercase;border:0;
  background:var(--ink);color:var(--paper);border-radius:8px;padding:12px 18px;cursor:pointer}}
.note{{color:var(--faint);font-size:11.5px;margin-top:10px}}
footer{{margin-top:26px;padding-top:14px;border-top:1px solid var(--rule);
  font-size:11.5px;color:var(--faint);text-align:center}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body>
<div class="wrap">
<a href="index.html">&#9666; Platform</a>
<h1>The desk</h1>
<p class="sub">Ask the platform about its own artifacts — verdicts, changes, the arena,
the regret ledger, fund fees, the watchers. Every answer is DETERMINISTIC (no AI is
deciding a fact in your browser) and carries its receipts. Anything outside those six,
it honestly can&#8217;t answer.</p>
<div class="chips" id="chips">{chips}</div>
<div id="log" aria-live="polite"></div>
<div class="entry">
  <input id="q" type="text" placeholder="Ask about a verdict, the arena, the ledger&#8230;"
    aria-label="ask the desk">
  <button id="ask">Ask</button>
</div>
<p class="note">Answers come from the committed public artifacts (same-origin), computed
in your browser. Not financial advice — a research tool.</p>
<footer>The Verdict Desk · <a href="index.html">platform</a> ·
<a href="scorecard.html">scorecard</a> · <a href="arena.html">arena</a></footer>
</div>
<script id="contract" type="application/json">{_json_html(contract)}</script>
<script>{_DESK_JS}</script>
</body></html>"""


# the client mirror: intents from the CONTRACT (one source), answers composed
# from the same artifacts, receipts identical in shape. esc() everywhere.
_DESK_JS = r"""
(function(){
  function J(id){try{return JSON.parse(document.getElementById(id).textContent||'null');}catch(e){return null;}}
  function esc(x){return String(x).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  var C=J('contract'), D=null, RES={};
  C.order.forEach(function(k){RES[k]=new RegExp(C.patterns[k],'i');});
  var SYM=new RegExp(C.symbol_token,'g');
  function load(cb){
    if(D){cb();return;}
    fetch('desk-data.json').then(function(r){return r.json();})
      .then(function(d){D=d;cb();})
      .catch(function(){D={verdicts:{},arena:[],regret:{},watchers:{},twins:{},core_etfs:{},changes:[],has_prior:false,as_of:'',audit:''};cb();});
  }
  function known(){var k={};Object.keys(D.verdicts||{}).forEach(function(s){k[s]=1;});
    Object.keys(D.twins||{}).forEach(function(s){k[s]=1;});
    Object.keys(D.core_etfs||{}).forEach(function(s){k[s]=1;});return k;}
  function findSym(q){var ks=known(),hits=(q.match(SYM)||[]).map(function(t){return t.toUpperCase();})
      .filter(function(t){return ks[t];});
    return hits.length?hits.sort(function(a,b){return b.length-a.length;})[0]:null;}
  function classify(q){
    var sym=findSym(q);
    for(var i=0;i<C.order.length;i++){var k=C.order[i];
      if(!RES[k].test(q))continue;
      if(k==='fees'&&!sym)continue;             // the contract rule
      if(k==='verdict'&&!sym)continue;
      return [k,sym];}
    if(sym&&(q.match(new RegExp(C.symbol_token,'g'))||[]).length<=C.bare_symbol_max_tokens)
      return ['verdict',sym];
    return ['help',null];}
  function rcpt(){return D.as_of?('as of '+D.as_of+' · audit '+D.audit):'no record';}
  function fmt(n,d){return (n>=0?'+':'')+Number(n).toFixed(d==null?2:d);}
  var A={
    verdict:function(sym){
      var t=D.twins[sym], target=t?t.twin:sym, v=D.verdicts[target];
      var via=t?(' (a mutual fund — scored via its ETF twin '+target+')'):'';
      if(!v)return [sym+': no verdict in the current artifact — add it to the watchlist and tomorrow’s build scores it fully.',rcpt()];
      var dl=v.dials||{},why=(v.comps||[]).map(function(c){return c[0]+' '+fmt(c[1])+' ('+(c[2]||'no detail')+')';}).join('; ')||'no components present';
      var miss=(v.missing&&v.missing.length)?(' Missing evidence: '+v.missing.join(', ')+'.'):'';
      return [sym+via+': '+v.label+' at '+fmt(v.score,3)+'. Dials — return lean '+fmt(dl.expected_return)+', drawdown risk '+Number(dl.drawdown_risk||0).toFixed(2)+', data confidence '+Number(dl.data_confidence||0).toFixed(2)+', model confidence '+Number(dl.model_confidence||0).toFixed(2)+'. Top drivers: '+why+'.'+miss,rcpt()];},
    changes:function(){
      if(!D.as_of)return ['No verdict artifact yet — nothing to compare.',rcpt()];
      if(!D.has_prior)return ['Only one artifact so far — changes appear once a second nightly build lands.',rcpt()];
      if(!D.changes.length)return ['No verdict changed since the last build.',rcpt()];
      return [D.changes.length+' verdict(s) moved: '+D.changes.map(function(c){return c.symbol+' '+c.was+' -> '+c.now+' ('+c.why+')';}).join('; ')+'.',rcpt()];},
    arena:function(){
      if(!D.arena.length)return ['The arena has no books yet — it opens with the first nightly verdict build.','no record'];
      var latest=D.arena.map(function(r){return r.last_mark;}).sort().pop();
      return ['The board — '+D.arena.map(function(r){return r.owner+': equity '+Number(r.equity).toFixed(4)+(r.last_event?(' [last '+r.last_event+']'):'');}).join('; ')+'. Benchmarks are always on it; nothing gets a label before a 7-day track record.','arena marks through '+latest];},
    regret:function(){
      var s=D.regret||{};
      if(!s.resolved)return ['No resolved horizons yet — '+(s.recorded||0)+' recommendation(s) being tracked against SPY, the HYSA, equal-weight, and doing nothing. The score arrives when the horizons do.',(s.recorded||0)+' recorded · '+(s.open||0)+' open'];
      var parts=[];Object.keys(s.baselines||{}).forEach(function(b){var x=s.baselines[b];
        if(x&&x.n)parts.push('vs '+b+': beat '+Math.round(x.beat_rate*100)+'% of '+x.n+' (mean edge '+fmt(x.mean_edge*100)+'%)');});
      return [s.resolved+' resolved, '+s.open+' open. '+parts.join('; ')+'. Every recommendation is scored, including the misses.',s.recorded+' recorded, content-hashed + replayable'];},
    fees:function(sym){
      var t=D.twins[sym];
      if(t){var m=t.fee_multiple,tail=(m!=null&&m>=1.5)?(' — about '+m+'x the twin’s fee'):((m!=null&&m<=0.67)?(' — the fund is actually the cheaper wrapper ('+m+'x)'):'' );
        return [sym+' is a mutual fund; its ETF twin is '+t.twin+' (same exposure). Fees: '+(t.fund_expense_ratio*100).toFixed(2)+'% (fund) vs '+(t.twin_expense_ratio*100).toFixed(2)+'% (ETF)'+tail+'.','published expense ratios, shipped in the scoring contract'];}
      var er=D.core_etfs[sym];
      if(er!=null)return [sym+' costs '+(er*100).toFixed(2)+'% a year.','published expense ratio'];
      return ['No expense-ratio data bundled for '+sym+' — honest n/a.',rcpt()];},
    watchers:function(){
      var w=D.watchers||{},ev=w.events||[],sk=w.skips||[];
      if(!ev.length&&!sk.length)return ['No watcher feed yet — the templates run with the daily build.','no record'];
      var lines=ev.map(function(e){return '['+e.date+'] '+e.kind+': '+e.reason;}).join('; ')||'no template fired — quiet by the stated thresholds';
      var skips=sk.length?(' Skips: '+sk.map(function(s){return s.kind+' ('+s.reason+')';}).join('; ')+'.'):'';
      return [lines+'.'+skips,ev.length?(ev.length+' event(s) — hashes live in the committed feed artifact'):'honest skips only'];}
  };
  function answer(q){
    var c=classify(q),intent=c[0],sym=c[1];
    if(intent==='help')return [C.help,''];
    return A[intent](sym);}
  var log=document.getElementById('log');
  function say(cls,text,receipts){
    var div=document.createElement('div');div.className='msg '+cls;
    div.textContent=text;
    if(receipts){var r=document.createElement('span');r.className='rcpt';
      r.textContent='['+receipts+'] '+C.disclaimer;div.appendChild(r);}
    log.appendChild(div);div.scrollIntoView({block:'nearest'});}
  function ask(q){
    q=(q||'').trim();if(!q)return;
    say('q',q,'');
    load(function(){var a=answer(q);say('a',a[0],a[1]);});
    document.getElementById('q').value='';}
  document.getElementById('ask').addEventListener('click',function(){ask(document.getElementById('q').value);});
  document.getElementById('q').addEventListener('keydown',function(e){if(e.key==='Enter')ask(e.target.value);});
  document.getElementById('chips').addEventListener('click',function(e){
    if(e.target.dataset&&e.target.dataset.q)ask(e.target.dataset.q);});
})();
"""


def build_desk_page(out_dir, *, verdicts_dir=None, arena_path=None,
                    regret_path=None, inputs_dir=None) -> Path:
    """Write site/desk.html + site/desk-data.json (the reduced public bundle)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "desk-data.json").write_text(
        json.dumps(build_desk_data(verdicts_dir=verdicts_dir, arena_path=arena_path,
                                   regret_path=regret_path, inputs_dir=inputs_dir),
                   separators=(",", ":")), encoding="utf-8")
    page = out / "desk.html"
    page.write_text(render_desk_page(), encoding="utf-8")
    return page
