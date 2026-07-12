"""The landing page — site/landing.html (P9-2: the Sakura-bar rebuild).

The storyboard (PHASE_P9.md): a WebGL hero (three.js — a drifting field of
verdict-card planes over a wireframe price surface) and GSAP ScrollTrigger
scenes that tell the platform's story in order — S1 the verdict card
assembles, S2 the dials fill, S3 the arena draws, S4 the receipts stamp,
S5 the honest close. Every number shown is server-rendered from the committed
artifacts (the top rated name's REAL rows, the arena ledger's REAL curve, the
regret ledger's REAL counts) — nothing is invented for drama, and when an
artifact is missing the section says so honestly.

Layering, honestly: the whole page is readable with NO JavaScript (the scenes
render statically stacked; the hero shows a CSS/SVG poster; the WebGL canvas
is only created BY JS). Reduced motion or the user kill-switch = the static
experience. If WebGL fails, the old 2D paper-mote canvas takes over. Budgets
pinned by test: HTML < 60KB; landing JS total (vendored incl.) < 250KB gz.
Self-contained: scripts come only from ./vendor/ + ./motion.js — zero
external fetches. Not financial advice.
"""

from __future__ import annotations

from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _esc

LABEL_TONE = {"STRONG BUY": UP, "BUY": UP, "HOLD": MUTED, "TRIM": DOWN, "AVOID": DOWN}
DIAL_LABELS = [("expected_return", "Return lean"), ("drawdown_risk", "Drawdown risk"),
               ("data_confidence", "Data confidence"), ("model_confidence", "Model confidence")]


# ------------------------------------------------------------- story data
def collect_story(verdicts_dir=None, arena_path=None, regret_path=None) -> dict:
    """The real numbers the scroll scenes choreograph — straight from the
    committed artifacts; None blocks render their honest fallbacks."""
    story: dict = {"card": None, "arena": None, "regret": None, "as_of": "", "audit": ""}
    try:
        from ..pipeline.verdicts import load_latest_verdicts

        loaded = load_latest_verdicts(verdicts_dir)
        if not loaded.get("empty"):
            payload = loaded["payload"]
            story["as_of"] = payload.get("as_of", "")
            story["audit"] = str(loaded.get("audit_sha", ""))[:12]
            rated = [(s, r) for s, r in payload.get("verdicts", {}).items()
                     if not str(r.get("label", "")).startswith("INSUFFICIENT")]
            if rated:
                sym, row = max(rated, key=lambda kv: kv[1].get("score", 0.0))
                comps = sorted(row.get("components", {}).items(),
                               key=lambda kv: -abs(kv[1].get("score", 0.0)))[:4]
                story["card"] = {
                    "symbol": sym, "label": row.get("label"),
                    "score": row.get("score", 0.0), "dials": row.get("dials", {}),
                    "components": [{"name": n, "score": c.get("score", 0.0),
                                    "detail": c.get("detail") or ""}
                                   for n, c in comps],
                }
    except Exception:  # noqa: BLE001 - the landing renders honestly without
        pass
    try:
        from ..agent_trader.arena_books import ArenaLedger

        led = ArenaLedger(path=arena_path) if arena_path else ArenaLedger()
        curves = {}
        # BOTH AIs when they exist (Codex review: "two AIs race" must not
        # silently drop one of them) + the benchmark
        for owner in ("claude", "codex", "SPY"):
            st = led.state.get(owner)
            if st and st.get("curve"):
                curves[owner] = [round(float(p["equity"]), 5) for p in st["curve"]][-40:]
        if curves.get("claude") or curves.get("codex"):
            story["arena"] = curves
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..calibration_log.regret import RegretLedger

        reg = RegretLedger(path=regret_path) if regret_path else RegretLedger()
        s = reg.summary()
        story["regret"] = {"recorded": s.get("recorded", 0),
                           "resolved": s.get("resolved", 0), "open": s.get("open", 0)}
    except Exception:  # noqa: BLE001
        pass
    return story


# ------------------------------------------------------------- scene HTML
def _scene_card(story: dict) -> str:
    card = story.get("card")
    if not card:
        return ('<div class="vcard" data-scene="card"><div class="vc-label" '
                f'style="color:{FAINT}">INSUFFICIENT EVIDENCE</div>'
                '<p class="vc-note">No rated artifact committed yet — the nightly build '
                'rates the tier, and this card fills with a real name. Honest empty, '
                'never a demo number.</p></div>')
    tone = LABEL_TONE.get(card["label"], FAINT)
    rows = "".join(
        f'<div class="crow"><span class="cname">{_esc(c["name"])}</span>'
        f'<span class="cscore" style="color:{UP if c["score"] >= 0 else DOWN}">'
        f'{c["score"]:+.2f}</span>'
        f'<span class="cdetail">{_esc(c["detail"][:56])}</span></div>'
        for c in card["components"])
    return (f'<div class="vcard" data-scene="card">'
            f'<div class="vc-sym">{_esc(card["symbol"])}</div>'
            f'<div class="vc-label" style="color:{tone}" data-count>'
            f'{_esc(card["label"])} {card["score"]:+.3f}</div>'
            f'{rows}'
            f'<div class="vc-asof">as of {_esc(story.get("as_of", ""))} · '
            f'audit {_esc(story.get("audit", ""))}</div></div>')


def _scene_dials(story: dict) -> str:
    card = story.get("card")
    dials = (card or {}).get("dials", {})
    out = []
    for key, label in DIAL_LABELS:
        v = dials.get(key)
        if v is None:
            arc, txt = 0.0, "n/a"
        else:
            arc = max(0.0, min(1.0, (v + 1) / 2 if key == "expected_return" else v))
            txt = f"{v:+.2f}" if key == "expected_return" else f"{v:.2f}"
        dash = f"{arc * 100:.1f} 100"
        out.append(
            f'<figure class="dial"><svg viewBox="0 0 36 20" aria-hidden="true">'
            f'<path d="M2 18 A16 16 0 0 1 34 18" fill="none" stroke="{RULE}" stroke-width="3"/>'
            f'<path d="M2 18 A16 16 0 0 1 34 18" fill="none" stroke="{ACCENT}" '
            f'stroke-width="3" pathLength="100" stroke-dasharray="{dash}" data-sweep/></svg>'
            f'<figcaption>{_esc(label)}<b>{_esc(txt)}</b></figcaption></figure>')
    return '<div class="dials" data-scene="dials">' + "".join(out) + "</div>"


def _scene_arena(story: dict) -> str:
    arena = story.get("arena")
    if not arena:
        return ('<p class="honest" data-scene="arena">The arena opens with the first '
                'marked books — two AIs under written mandates, benchmarks always on '
                'the board. Nothing races until it exists.</p>')

    def poly(vals: list[float]) -> str:
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1.0
        pts = [f"{i / max(1, len(vals) - 1) * 300:.1f},"
               f"{60 - (v - lo) / span * 50:.1f}" for i, v in enumerate(vals)]
        return " ".join(pts)

    tones = {"claude": ACCENT, "codex": "#8A5A00", "SPY": FAINT}
    names = {"claude": "claude&#8217;s book", "codex": "codex&#8217;s book",
             "SPY": "SPY benchmark"}
    lines, legend = "", ""
    for owner in ("SPY", "codex", "claude"):  # benchmark under, books on top
        if arena.get(owner):
            w = "2" if owner != "SPY" else "1.5"
            lines += (f'<polyline points="{poly(arena[owner])}" fill="none" '
                      f'stroke="{tones[owner]}" stroke-width="{w}" data-draw/>')
            legend += f'<i style="background:{tones[owner]}"></i>{names[owner]} '
    return (f'<div data-scene="arena"><svg class="race" viewBox="0 0 300 64" '
            f'role="img" aria-label="arena equity curves">{lines}</svg>'
            f'<p class="rlegend">{legend}· marked daily, no lookahead, '
            '7-day incubation</p></div>')


def _scene_regret(story: dict) -> str:
    reg = story.get("regret") or {}
    n = reg.get("recorded", 0)
    if not n:
        return ('<p class="honest" data-scene="regret">The regret ledger opens with '
                'the first rated build — every surfaced call tracked against SPY, the '
                'HYSA, equal-weight, and doing nothing.</p>')
    chips = "".join(f'<span class="chip" data-stamp>{_esc(t)}</span>' for t in (
        f"{n} recommendations tracked",
        f"{reg.get('resolved', 0)} resolved · {reg.get('open', 0)} open",
        "vs SPY", "vs HYSA", "vs equal-weight", "vs doing nothing",
        "content-hashed · tamper-evident"))
    return f'<div class="chips" data-scene="regret">{chips}</div>'


# ------------------------------------------------------------- the page
def render_landing(story: dict | None = None) -> str:
    story = story or {"card": None, "arena": None, "regret": None, "as_of": "", "audit": ""}
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
body {{ background:var(--paper); color:var(--ink); font:400 16px/1.6 var(--mono); overflow-x:hidden; }}
#bg {{ position:fixed; inset:0; width:100vw; height:100vh; z-index:0; display:block; }}
#poster {{ position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(60vw 40vh at 75% 12%, rgba(47,125,49,.06), transparent 70%),
    radial-gradient(50vw 36vh at 15% 80%, rgba(198,57,44,.05), transparent 70%),
    linear-gradient(180deg, var(--paper), var(--paper)); }}
#poster svg {{ position:absolute; inset:0; width:100%; height:100%; opacity:.5;
  mix-blend-mode:multiply; }}
#grain {{ position:fixed; inset:0; z-index:1; pointer-events:none; opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");
  animation:grain 1.2s steps(3) infinite; }}
@keyframes grain {{ 0%,100%{{transform:translate(0,0)}} 33%{{transform:translate(-4px,3px)}} 66%{{transform:translate(3px,-4px)}} }}
.gnav {{ position:fixed; top:0; left:0; right:0; z-index:5; display:flex;
  justify-content:space-between; align-items:center; padding:14px 22px;
  background:rgba(251,247,235,.55); backdrop-filter:blur(10px);
  -webkit-backdrop-filter:blur(10px); border-bottom:1px solid var(--rule); }}
.gnav b {{ font:800 12px/1 var(--mono); letter-spacing:.28em; text-transform:uppercase; }}
.gnav nav a {{ font:700 11px/1 var(--mono); letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink); text-decoration:none; margin-left:18px;
  border-bottom:2px solid transparent; transition:border-color .3s var(--ease); }}
.gnav nav a:hover {{ border-bottom-color:var(--accent); }}
.rail {{ position:fixed; right:14px; top:50%; transform:translateY(-50%); z-index:2;
  writing-mode:vertical-rl; font:700 10px/1 var(--mono); letter-spacing:.5em;
  text-transform:uppercase; color:var(--faint); }}
.rail.left {{ right:auto; left:14px; }}
.wrap {{ position:relative; z-index:2; max-width:780px; margin:0 auto; padding:0 22px 90px; }}
.hero {{ min-height:92vh; display:flex; flex-direction:column; justify-content:center; padding:60px 0 30px; }}
.eyebrow {{ font:700 12px/1 var(--mono); letter-spacing:.5em; text-transform:uppercase; color:var(--accent); }}
.hero h1 {{ font:600 clamp(40px,8vw,88px)/1.02 var(--serif); letter-spacing:-.01em; margin:20px 0 0; text-wrap:balance; }}
.hero .deck {{ font:400 18px/1.6 var(--mono); color:var(--mut); max-width:52ch; margin-top:22px; }}
.hero .deck b {{ color:var(--ink); }}
.cta {{ display:inline-flex; gap:10px; align-items:center; margin-top:32px; align-self:flex-start;
  font:700 14px/1 var(--mono); letter-spacing:.03em; text-transform:uppercase; color:#fff;
  background:var(--ink); border-radius:8px; padding:15px 22px; text-decoration:none;
  transition:transform .3s var(--ease); }}
.cta:hover {{ transform:translateX(4px); }}
.subcta {{ margin-top:14px; font:500 13px/1 var(--mono); color:var(--mut); }}
.subcta a {{ color:var(--accent); text-decoration:none; }}
.scrollcue {{ margin-top:8vh; font:700 11px/1 var(--mono); letter-spacing:.4em;
  text-transform:uppercase; color:var(--faint); animation:cue 2.2s var(--ease) infinite; }}
@keyframes cue {{ 0%,100%{{transform:translateY(0);opacity:.6}} 50%{{transform:translateY(8px);opacity:1}} }}
.scene {{ min-height:70vh; padding:60px 0; border-top:1px solid var(--rule);
  display:flex; flex-direction:column; justify-content:center; }}
.scene h2 {{ font:600 clamp(26px,4.4vw,40px)/1.1 var(--serif); margin:8px 0 18px; text-wrap:balance; }}
.scene .lead {{ color:var(--mut); max-width:58ch; margin-bottom:26px; }}
.vcard {{ background:var(--card); border:1px solid var(--rule); border-radius:6px;
  padding:22px 24px; max-width:520px; box-shadow:0 1px 0 var(--rule); }}
.vc-sym {{ font:800 22px/1 var(--mono); letter-spacing:.04em; }}
.vc-label {{ font:800 30px/1.15 var(--mono); margin:6px 0 14px; }}
.vc-note {{ color:var(--mut); font-size:14px; }}
.crow {{ display:grid; grid-template-columns:150px 60px 1fr; gap:10px; padding:8px 0;
  border-top:1px solid var(--rule); font-size:13px; align-items:baseline; }}
.cname {{ font-weight:700; text-transform:uppercase; letter-spacing:.04em; font-size:11px; color:var(--mut); }}
.cdetail {{ color:var(--faint); font-size:11.5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.vc-asof {{ margin-top:14px; color:var(--faint); font-size:11px; }}
.dials {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:18px; max-width:640px; }}
.dial svg {{ width:100%; }}
.dial figcaption {{ font:600 10.5px/1.5 var(--mono); text-transform:uppercase;
  letter-spacing:.05em; color:var(--mut); text-align:center; }}
.dial b {{ display:block; font:800 16px/1.2 var(--mono); color:var(--ink); }}
.race {{ width:100%; max-width:640px; }}
.rlegend {{ color:var(--mut); font-size:12.5px; margin-top:10px; }}
.rlegend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 5px 0 12px; vertical-align:-1px; }}
.chips {{ display:flex; flex-wrap:wrap; gap:10px; max-width:640px; }}
.chip {{ font:700 12px/1 var(--mono); border:1px solid var(--rule); background:var(--card);
  border-radius:5px; padding:10px 13px; }}
.honest {{ color:var(--mut); max-width:56ch; }}
footer {{ position:relative; z-index:2; text-align:center; padding:30px 22px 50px;
  font:400 12px/1.6 var(--mono); color:var(--faint); }}
@media (prefers-reduced-motion:reduce) {{
  #grain,.scrollcue {{ animation:none; }} .cta {{ transition:none; }}
}}
html.motion-off #grain, html.motion-off .scrollcue {{ animation:none; }}
</style></head><body>
<div id="poster" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
  <g fill="none" stroke="{RULE}" stroke-width=".22">
    <rect x="12" y="14" width="13" height="8" rx="1" transform="rotate(-9 18 18)"/>
    <rect x="66" y="10" width="14" height="8" rx="1" transform="rotate(7 73 14)"/>
    <rect x="40" y="30" width="12" height="7" rx="1" transform="rotate(-4 46 33)"/>
    <rect x="78" y="46" width="13" height="8" rx="1" transform="rotate(11 84 50)"/>
    <rect x="8" y="58" width="12" height="7" rx="1" transform="rotate(6 14 61)"/>
    <rect x="52" y="70" width="14" height="8" rx="1" transform="rotate(-7 59 74)"/>
    <path d="M0 84 Q 18 78 34 82 T 66 80 T 100 84" stroke="{ACCENT}" stroke-opacity=".35"/>
    <path d="M0 90 Q 22 86 40 89 T 74 87 T 100 90" stroke="{FAINT}" stroke-opacity=".4"/>
  </g></svg></div>
<canvas id="bg" aria-hidden="true"></canvas><div id="grain" aria-hidden="true"></div>
<header class="gnav"><b>The Verdict Desk</b>
  <nav><a href="scorecard.html">Scorecard</a><a href="arena.html">Arena</a>
  <a href="index.html">Enter the desk &#8594;</a></nav></header>
<div class="rail" aria-hidden="true">EST. 2026 · PAPER FIRST · NOT FINANCIAL ADVICE</div>
<div class="rail left" aria-hidden="true">RECEIPTS ON EVERY VERDICT · SCORED IN PUBLIC</div>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">The Verdict Desk · paper first</div>
    <h1>Every verdict carries its receipts.</h1>
    <p class="deck">Search any listed stock or ETF and get an evidence-backed recommendation —
    built from walk-forward backtests with costs, live signals, and a track record scored in
    public. <b>A personal research tool, not financial advice.</b></p>
    <a class="cta" href="index.html">Enter the platform &#8594;</a>
    <div class="subcta">or jump to the <a href="scorecard.html">public scorecard</a></div>
    <div class="scrollcue">Scroll — the story shows its work &#8595;</div>
  </div>

  <section class="scene" id="s1">
    <div class="eyebrow">01 · The verdict</div>
    <h2>A recommendation is built, not declared.</h2>
    <p class="lead">Tonight&#8217;s top-rated name, exactly as the engine scored it —
    component by component, nothing averaged away.</p>
    {_scene_card(story)}
  </section>

  <section class="scene" id="s2">
    <div class="eyebrow">02 · The confidence budget</div>
    <h2>Four dials gate every label.</h2>
    <p class="lead">Return lean, drawdown risk, data confidence, model confidence —
    when the evidence can&#8217;t carry a label, the verdict says INSUFFICIENT, honestly.</p>
    {_scene_dials(story)}
  </section>

  <section class="scene" id="s3">
    <div class="eyebrow">03 · The arena</div>
    <h2>Two AIs race, benchmarks always on the board.</h2>
    <p class="lead">Written mandates, dated rebalances with receipts, a 7-day incubation
    before anything gets a label.</p>
    {_scene_arena(story)}
  </section>

  <section class="scene" id="s4">
    <div class="eyebrow">04 · The regret ledger</div>
    <h2>Was it actually right? The ledger answers.</h2>
    <p class="lead">Every surfaced call is tracked against the four things you could
    have done instead — including nothing.</p>
    {_scene_regret(story)}
  </section>

  <section class="scene" id="s5">
    <div class="eyebrow">05 · The honest close</div>
    <h2>Most models can&#8217;t beat the market. This one shows its work either way.</h2>
    <p class="lead">Calibrated isn&#8217;t the same as having an edge — the public ledger
    is the judge, and the misses stay pinned. Not financial advice.</p>
    <a class="cta" href="index.html">Open the desk &#8594;</a>
  </section>
</div>
<footer>The Verdict Desk · research opinions, scored on a public ledger · not financial advice ·
<a href="index.html" style="color:var(--accent)">enter &#8594;</a></footer>
<script src="vendor/gsap.min.js"></script>
<script src="vendor/ScrollTrigger.min.js"></script>
<script src="motion.js"></script>
<script>
(function(){{
  var off = window.flabMotion ? flabMotion.off()
    : (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  if (off || !window.gsap || !window.ScrollTrigger) return;  // static page stands
  gsap.registerPlugin(ScrollTrigger);
  var EASE = 'power3.out';
  // S1 the card assembles, row by row
  gsap.from('#s1 .vcard', {{ y: 40, opacity: 0, duration: .6, ease: EASE,
    scrollTrigger: {{ trigger: '#s1', start: 'top 70%' }} }});
  gsap.from('#s1 .crow', {{ y: 18, opacity: 0, stagger: .12, duration: .45, ease: EASE,
    scrollTrigger: {{ trigger: '#s1 .vcard', start: 'top 65%' }} }});
  // S2 the dials fill (scrubbed sweep to the server-rendered truth)
  document.querySelectorAll('#s2 [data-sweep]').forEach(function(p){{
    var final_ = p.getAttribute('stroke-dasharray');
    gsap.fromTo(p, {{ attr: {{ 'stroke-dasharray': '0 100' }} }},
      {{ attr: {{ 'stroke-dasharray': final_ }}, ease: 'none',
        scrollTrigger: {{ trigger: '#s2', start: 'top 75%', end: 'center center', scrub: true }} }});
  }});
  // S3 the arena lines draw
  document.querySelectorAll('#s3 [data-draw]').forEach(function(pl){{
    var len = pl.getTotalLength ? pl.getTotalLength() : 600;
    pl.style.strokeDasharray = len; pl.style.strokeDashoffset = len;
    gsap.to(pl, {{ strokeDashoffset: 0, ease: 'none',
      scrollTrigger: {{ trigger: '#s3', start: 'top 70%', end: 'center center', scrub: true }} }});
  }});
  // S4 the receipts stamp down
  gsap.from('#s4 [data-stamp]', {{ scale: 1.35, opacity: 0, stagger: .09, duration: .35,
    ease: 'back.out(1.7)', scrollTrigger: {{ trigger: '#s4', start: 'top 70%' }} }});
  // S5 the close
  gsap.from('#s5 h2, #s5 .lead, #s5 .cta', {{ y: 24, opacity: 0, stagger: .1, duration: .5,
    ease: EASE, scrollTrigger: {{ trigger: '#s5', start: 'top 75%' }} }});
  // LIVE kill (Codex review): if the switch flips after load, every trigger
  // jumps to its END state (content fully visible) and dies
  gsap.ticker.add(function killWatch() {{
    if (!(window.flabMotion && flabMotion.off())) return;
    ScrollTrigger.getAll().forEach(function (st) {{ st.progress(1); st.kill(); }});
    gsap.globalTimeline.clear();
    gsap.set('#s1 .vcard, #s1 .crow, #s4 [data-stamp], #s5 h2, #s5 .lead, #s5 .cta',
      {{ clearProps: 'all' }});
    gsap.ticker.remove(killWatch);
  }});
}})();
</script>
<script type="module">
// The WebGL hero: drifting verdict-card planes over a wireframe price surface.
// Only runs with motion ON; failure falls back to the 2D paper-mote canvas.
const off = window.flabMotion ? flabMotion.off()
  : (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
const bg = document.getElementById('bg');
function motes() {{  // the P6b fallback layer, unchanged in spirit
  const x = bg.getContext('2d'); let W, H; const P = [];
  const size = () => {{ W = bg.width = innerWidth; H = bg.height = innerHeight; }};
  size(); addEventListener('resize', size);
  const N = Math.min(64, Math.round(W * H / 24000));
  for (let i = 0; i < N; i++) P.push({{ x: Math.random() * W, y: Math.random() * H,
    s: 1 + Math.random() * 3, vy: .15 + Math.random() * .4, sw: Math.random() * 6.28,
    c: Math.random() < .35, up: Math.random() < .5 }});
  (function draw() {{
    if (window.flabMotion && flabMotion.off()) {{ x.clearRect(0, 0, W, H); return; }}
    x.clearRect(0, 0, W, H);
    for (const p of P) {{ p.y += p.vy; p.sw += .01; p.x += Math.sin(p.sw) * .3;
      if (p.y > H + 8) {{ p.y = -8; p.x = Math.random() * W; }}
      if (p.c) {{ x.globalAlpha = .28; x.fillStyle = p.up ? '{UP}' : '{DOWN}';
        const w = p.s * 1.4; x.fillRect(p.x - w / 2, p.y - p.s * 2, w, p.s * 4);
        x.fillRect(p.x - .4, p.y - p.s * 3.2, .8, p.s * 6.4); }}
      else {{ x.globalAlpha = .2; x.fillStyle = '{INK}';
        x.beginPath(); x.arc(p.x, p.y, p.s * .7, 0, 6.28); x.fill(); }} }}
    x.globalAlpha = 1; requestAnimationFrame(draw);
  }})();
}}
if (off) {{ /* static poster only */ }}
else {{
  try {{
    const THREE = await import('./vendor/three.module.min.js');
    const renderer = new THREE.WebGLRenderer({{ canvas: bg, antialias: true, alpha: true }});
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0xfbf7eb, 8, 26);
    const cam = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, .1, 40);
    cam.position.set(0, 1.2, 9);
    const cards = new THREE.Group();
    const geo = new THREE.PlaneGeometry(1.1, .7);
    const mats = [0xffffff, 0xfffdf6, 0xf4efe0].map(c =>
      new THREE.MeshBasicMaterial({{ color: c, transparent: true, opacity: .9, side: THREE.DoubleSide }}));
    const edge = [0x2f7d31, 0xc6392c].map(c =>
      new THREE.MeshBasicMaterial({{ color: c, transparent: true, opacity: .8, side: THREE.DoubleSide }}));
    for (let i = 0; i < 46; i++) {{
      const m = new THREE.Mesh(geo, mats[i % 3]);
      m.position.set((Math.random() - .5) * 18, (Math.random() - .3) * 9, -Math.random() * 16);
      m.rotation.set((Math.random() - .5) * .7, (Math.random() - .5) * .9, (Math.random() - .5) * .3);
      m.userData = {{ vy: .0015 + Math.random() * .003, vr: (Math.random() - .5) * .0012 }};
      cards.add(m);
      if (i % 5 === 0) {{  // a thin accent bar riding some cards
        const bar = new THREE.Mesh(new THREE.PlaneGeometry(1.1, .06), edge[i % 2]);
        bar.position.copy(m.position); bar.position.y += .38; bar.rotation.copy(m.rotation);
        bar.userData = m.userData; cards.add(bar);
      }}
    }}
    scene.add(cards);
    const surf = new THREE.Mesh(new THREE.PlaneGeometry(40, 18, 64, 24),
      new THREE.MeshBasicMaterial({{ color: 0x1d5c2e, wireframe: true, transparent: true, opacity: .10 }}));
    surf.rotation.x = -Math.PI / 2.25; surf.position.set(0, -3.4, -6);
    scene.add(surf);
    const pos = surf.geometry.attributes.position;
    const resize = () => {{ renderer.setSize(innerWidth, innerHeight);
      cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); }};
    resize(); addEventListener('resize', resize);
    let hidden = false;
    const onVis = () => {{ hidden = document.hidden; }};
    document.addEventListener('visibilitychange', onVis);
    function dispose() {{  // a real kill: free the GPU + drop the listeners (Codex review)
      renderer.clear();
      scene.traverse(o => {{ if (o.geometry) o.geometry.dispose();
        if (o.material) (Array.isArray(o.material) ? o.material : [o.material])
          .forEach(m => m.dispose()); }});
      renderer.dispose();
      removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVis);
    }}
    let t = 0;
    (function loop() {{
      if (window.flabMotion && flabMotion.off()) {{ dispose(); return; }}
      requestAnimationFrame(loop);
      if (hidden) return;
      t += .008;
      for (const m of cards.children) {{
        m.position.y += m.userData.vy; m.rotation.y += m.userData.vr;
        if (m.position.y > 6) m.position.y = -4;
      }}
      for (let i = 0; i < pos.count; i++)
        pos.setZ(i, Math.sin(i * .35 + t * 2) * .22 + Math.cos(i * .13 + t) * .18);
      pos.needsUpdate = true;
      cam.position.y = 1.2 - (scrollY || 0) * .0012;   // subtle scroll parallax
      renderer.render(scene, cam);
    }})();
  }} catch (e) {{ motes(); }}  // WebGL unavailable -> the 2D layer
}}
</script>
</body></html>"""


def build_landing(out_dir, *, verdicts_dir=None, arena_path=None, regret_path=None):
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "landing.html"
    path.write_text(render_landing(collect_story(
        verdicts_dir=verdicts_dir, arena_path=arena_path, regret_path=regret_path)),
        encoding="utf-8")
    return path
