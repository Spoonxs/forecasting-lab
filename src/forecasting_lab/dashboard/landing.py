"""The landing page — site/landing.html (P6b section D).

The marketing/entry surface, in the Sakura treatment within the §10 restraint:
a full-viewport canvas particle layer (OUR motifs — drifting paper motes and tiny
candlesticks in the cream palette, not copied art), a film-grain overlay, a
display-serif hero (system serif stack, no external font), tracked eyebrows,
decisive easing, and scroll-reveal sections describing the platform's honesty —
each linking into the app. The app pages stay calmer; particles live only here.

Perf budgets (enforced by test): inline JS < 50KB, total page < 300KB, no
unsized elements (zero layout shift), and reduced-motion kills all motion.
Self-contained: no external font/script/stylesheet fetches. Not financial advice.
"""

from __future__ import annotations

from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _esc

_FEATURES = [
    ("Every verdict carries its receipts",
     "STRONG BUY to AVOID — or INSUFFICIENT EVIDENCE when the data can't carry a "
     "label. Each one shows its evidence, its four confidence dials, and a "
     "content-hashed audit trail you can replay.", "index.html", "See today's verdicts"),
    ("Scored on a public ledger",
     "Recommendations aren't opinions that vanish. Every call is logged and "
     "Brier-scored as outcomes land — the miss ledger stays pinned, worst first.",
     "scorecard.html", "Open the scorecard"),
    ("Two AIs, kept honest",
     "Claude and Codex each state a thesis and pick a book, marked daily against "
     "the benchmark. When they disagree, that disagreement is information — never "
     "averaged away.", "index.html#strategies", "Watch the arena"),
    ("Tuned to your goals",
     "Set your horizon, goal, and risk. Every verdict re-scores for you — reading "
     "the same contract the engine runs, never a different number.", "index.html",
     "Set your profile"),
]


def _feature_card(i: int, title: str, body: str, href: str, cta: str) -> str:
    return (
        f'<section class="reveal" style="--d:{i * 0.06:.2f}s">'
        f'<div class="eyebrow">0{i + 1}</div>'
        f'<h2>{_esc(title)}</h2><p>{_esc(body)}</p>'
        f'<a class="flink" href="{_esc(href)}">{_esc(cta)} &#8594;</a></section>'
    )


def render_landing() -> str:
    cards = "".join(_feature_card(i, *f) for i, f in enumerate(_FEATURES))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Verdict Desk — investment recommendations with receipts</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;
  --ease:cubic-bezier(.7,0,.2,1); }}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--paper); color:var(--ink); font:400 16px/1.6 var(--mono);
  overflow-x:hidden; }}
#bg {{ position:fixed; inset:0; width:100vw; height:100vh; z-index:0; display:block; }}
#grain {{ position:fixed; inset:0; z-index:1; pointer-events:none; opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");
  animation:grain 1.2s steps(3) infinite; }}
@keyframes grain {{ 0%,100%{{transform:translate(0,0)}} 33%{{transform:translate(-4px,3px)}} 66%{{transform:translate(3px,-4px)}} }}
.wrap {{ position:relative; z-index:2; max-width:760px; margin:0 auto; padding:0 22px 90px; }}
.hero {{ min-height:82vh; display:flex; flex-direction:column; justify-content:center; padding:60px 0 30px; }}
.eyebrow {{ font:700 12px/1 var(--mono); letter-spacing:.42em; text-transform:uppercase; color:var(--accent); }}
.hero h1 {{ font:600 clamp(40px,8vw,84px)/1.02 var(--serif); letter-spacing:-.01em; margin:20px 0 0; text-wrap:balance; }}
.hero .deck {{ font:400 18px/1.6 var(--mono); color:var(--mut); max-width:52ch; margin-top:22px; }}
.hero .deck b {{ color:var(--ink); }}
.cta {{ display:inline-flex; gap:10px; align-items:center; margin-top:32px; align-self:flex-start;
  font:700 14px/1 var(--mono); letter-spacing:.03em; text-transform:uppercase; color:#fff;
  background:var(--ink); border-radius:8px; padding:15px 22px; text-decoration:none;
  transition:transform .3s var(--ease); }}
.cta:hover {{ transform:translateX(4px); }}
.subcta {{ margin-top:14px; font:500 13px/1 var(--mono); color:var(--mut); }}
.subcta a {{ color:var(--accent); text-decoration:none; }}
section.reveal {{ padding:38px 0; border-top:1px solid var(--rule);
  opacity:0; transform:translateY(24px); transition:opacity .7s var(--ease) var(--d,0s), transform .7s var(--ease) var(--d,0s); }}
section.reveal.in {{ opacity:1; transform:none; }}
section.reveal h2 {{ font:600 clamp(24px,4vw,36px)/1.1 var(--serif); margin:10px 0 12px; text-wrap:balance; }}
section.reveal p {{ color:var(--mut); max-width:60ch; }}
.flink {{ display:inline-block; margin-top:16px; font:700 13px/1 var(--mono); letter-spacing:.03em;
  text-transform:uppercase; color:var(--accent); text-decoration:none;
  border-bottom:2px solid transparent; transition:border-color .3s var(--ease); }}
.flink:hover {{ border-bottom-color:var(--accent); }}
footer {{ position:relative; z-index:2; text-align:center; padding:30px 22px 50px;
  font:400 12px/1.6 var(--mono); color:var(--faint); }}
@media (prefers-reduced-motion:reduce) {{
  #grain {{ animation:none; }} section.reveal {{ opacity:1; transform:none; transition:none; }}
  .cta {{ transition:none; }}
}}
</style></head><body>
<canvas id="bg" aria-hidden="true"></canvas><div id="grain" aria-hidden="true"></div>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">Personal research platform</div>
    <h1>Investment verdicts, with receipts.</h1>
    <p class="deck">Search any listed stock or ETF and get an evidence-backed recommendation —
    built from backtests with costs, live signals, and a track record that&#8217;s scored in
    public. <b>A personal research tool, not financial advice.</b></p>
    <a class="cta" href="index.html">Enter the platform &#8594;</a>
    <div class="subcta">or jump to the <a href="scorecard.html">public scorecard</a></div>
  </div>
  {cards}
</div>
<footer>The Verdict Desk · research opinions, scored on a public ledger · not financial advice ·
<a href="index.html" style="color:var(--accent)">enter &#8594;</a></footer>
<script>
(function(){{
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  // scroll reveals (cheap; runs even with reduced motion since it just shows content)
  if('IntersectionObserver' in window){{
    var io=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add('in');io.unobserve(e.target);}}}});}},{{rootMargin:'-10% 0px'}});
    document.querySelectorAll('.reveal').forEach(function(s){{io.observe(s);}});
  }} else {{ document.querySelectorAll('.reveal').forEach(function(s){{s.classList.add('in');}}); }}
  if(reduce) return;  // no particle animation under reduced motion
  var c=document.getElementById('bg'), x=c.getContext('2d'), W,H,P=[];
  function size(){{ W=c.width=innerWidth; H=c.height=innerHeight; }}
  size(); addEventListener('resize',size);
  var UP='{UP}', DOWN='{DOWN}', N=Math.min(56, Math.round(W*H/26000));
  for(var i=0;i<N;i++) P.push({{x:Math.random()*W,y:Math.random()*H,
    s:1+Math.random()*3, vy:.15+Math.random()*.4, sway:Math.random()*6.28,
    t:Math.random()<.35?'c':'m', up:Math.random()<.5}});
  function draw(){{
    x.clearRect(0,0,W,H);
    for(var i=0;i<P.length;i++){{ var p=P[i]; p.y+=p.vy; p.sway+=.01; p.x+=Math.sin(p.sway)*.3;
      if(p.y>H+8){{p.y=-8;p.x=Math.random()*W;}}
      if(p.t==='m'){{ x.globalAlpha=.20; x.fillStyle='{INK}';
        x.beginPath(); x.arc(p.x,p.y,p.s*.7,0,6.28); x.fill(); }}
      else {{ x.globalAlpha=.28; x.fillStyle=p.up?UP:DOWN; var w=p.s*1.4;
        x.fillRect(p.x-w/2,p.y-p.s*2,w,p.s*4);            // body
        x.fillRect(p.x-.4,p.y-p.s*3.2,.8,p.s*6.4); }}     // wick
    }}
    x.globalAlpha=1; requestAnimationFrame(draw);
  }}
  requestAnimationFrame(draw);
}})();
</script>
</body></html>"""


def build_landing(out_dir):
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "landing.html"
    path.write_text(render_landing(), encoding="utf-8")
    return path
