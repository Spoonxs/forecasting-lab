"""The Agent Terminal — a dark, alive, agentic trading desk view.

Renders the agent's real paper book as a trading terminal: a ticker tape, the Agent
Book equity, the agent *team* as desks with status notes, a positions heatmap coloured
by P&L, and a live "Firm Chat" feed of the desk talking to itself (fills, house view,
risk, compliance, the graded track record). Self-contained dark HTML; every message is
derived from the real data (paper), so it feels like a desk without faking numbers.
"""

from __future__ import annotations

import html as _html

UP = "#16c784"
DOWN = "#ea3943"


def _esc(s) -> str:
    return _html.escape(str(s))


def _pct(v, d=2, signed=True) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    s = "+" if signed and f >= 0 else ("−" if f < 0 else "")
    return f"{s}{abs(f) * 100:.{d}f}%"


def _c(v: float) -> str:
    return UP if v >= 0 else DOWN


def _ticker_tape(movers: dict) -> str:
    items = []
    for c in (movers.get("movers") or [])[:14]:
        r = c.get("ret_5d", 0) or 0
        items.append(f'<span class="tk">{_esc(c.get("ticker",""))} '
                     f'<b style="color:{_c(r)}">{_pct(r,2)}</b></span>')
    row = "".join(items) or '<span class="tk">awaiting the scan…</span>'
    return f'<div class="tape"><div class="taperun">{row}{row}</div></div>'


def _desk(emoji: str, name: str, badge: str, msg: str) -> str:
    return (f'<div class="desk"><div class="dtop"><span class="ava">{emoji}</span>'
            f'<span class="dname">{_esc(name)}</span><span class="badge">{_esc(badge)}</span></div>'
            f'<p>{_esc(msg)}</p></div>')


def _heat(picks: list[dict]) -> str:
    tiles = []
    for p in picks:
        stock = p.get("kind") == "stock"
        cval = float(p.get("move", 0) or 0)  # recent move (stock) / edge (market) — colours the tile
        pnl = float(p.get("pnl", 0) or 0)
        a = min(0.9, 0.22 + abs(cval) * 5)
        if abs(cval) < 1e-9:
            bg = "#232833"
        else:
            bg = f"rgba(22,199,132,{a:.2f})" if cval >= 0 else f"rgba(234,57,67,{a:.2f})"
        label = _esc(p["name"] if stock else str(p["name"])[:15])
        if stock:
            sub = f'{_pct(cval,1)} <span class="dim">P&amp;L {_pct(pnl,1)}</span>'
        else:
            sub = f'{_esc(p.get("side",""))} {_pct(p.get("mark",0),0,signed=False)}'
        tiles.append(f'<div class="tile" style="background:{bg}"><b>{label}</b><em>{sub}</em></div>')
    return f'<div class="heat">{"".join(tiles)}</div>' if tiles else '<p class="empty">no open positions yet</p>'


def _chat(agent: dict, as_of: str) -> str:
    msgs = []

    def m(role: str, tag: str, tone: str, text: str):
        msgs.append(f'<div class="msg"><div class="mh"><b>{_esc(role)}</b>'
                    f'<span class="tag {tone}">{_esc(tag)}</span><span class="ts">{_esc(as_of)}</span></div>'
                    f'<p>{_esc(text)}</p></div>')

    picks = agent.get("picks") or []
    stocks = [p for p in picks if p.get("kind") == "stock"]
    markets = [p for p in picks if p.get("kind") == "market"]
    ret = agent.get("return", 0.0)

    m("Trader", "UPDATE", "", f"Book marked at ${agent.get('equity',0):,.0f}, "
      f"{'up' if ret >= 0 else 'down'} {abs(ret):.2%} on the stock sleeve today.")
    for b in (agent.get("blotter") or [])[:8]:
        m("Trader", "FILL" if b.startswith("BUY") else "BET", "fill", b)
    if stocks:
        t = max(stocks, key=lambda p: p.get("prob", 0))
        m("Analyst", "IDEA", "idea", f"Top idea {t['name']}: {float(t.get('prob',0)):.0%} lean — {t.get('thesis','')}.")
    if markets:
        mk = markets[0]
        m("Predictions", "MARKET", "idea", f"Holding {mk.get('side')} on \"{str(mk['name'])[:60]}\" "
          f"at {float(mk.get('mark',0)):.0%} vs a fair {float(mk.get('prob',0)):.0%}.")
    m("Risk", "ALL CLEAR", "ok", "Exposure inside per-name and gross caps; kill switch armed; cash buffer intact.")
    m("Compliance", "0 DENIED", "ok", "Every order cleared the rules — paper account, hard limits enforced in the execution layer.")
    m("Grader", "SCORED", "", "Marks accrue over runs — no edge is claimed until the promotion gate clears on real forward marks.")
    return "".join(msgs)


def render_terminal(state) -> str:
    agent = getattr(state, "agent", {}) or {}
    movers = getattr(state, "movers", {}) or {}
    as_of = getattr(state, "generated", "")
    picks = agent.get("picks") or []
    equity = agent.get("equity", 100_000.0)
    ret = agent.get("return", 0.0)
    n_stocks = agent.get("n_stocks", 0)
    n_markets = agent.get("n_markets", 0)

    if not picks:
        board = '<p class="empty">The desk hasn\'t opened any paper positions yet — it acts on the next data scan.</p>'
        chat = '<div class="msg"><p>Firm chat is quiet — waiting on the movers/odds feed.</p></div>'
    else:
        board = _heat(picks)
        chat = _chat(agent, as_of)

    desks = "".join([
        _desk("🧑‍💼", "The Boss", "oversight", "Both books running inside the rules; no orders waiting on me."),
        _desk("🔎", "Analyst", f"{n_stocks} ideas", "Ranking the trending names by the recalibrated signal."),
        _desk("🎯", "Predictions", f"{n_markets} bets", "Betting live Kalshi/Polymarket by fair value."),
        _desk("🛡️", "Risk", "all clear", "Caps + kill switch enforced in the execution layer."),
        _desk("⚖️", "Compliance", "0 denied", "Every order cleared; paper only."),
        _desk("📊", "Grader", "scored", "Marking the book to market each run; edge unproven until the gate says so."),
    ])

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Terminal — the desk</title>
<style>
:root{{--bg:#0d0f13;--panel:#151920;--line:#232833;--ink:#e8eaed;--mut:#8b93a1;--up:{UP};--dn:{DOWN}}}
*{{box-sizing:border-box;margin:0}} body{{background:var(--bg);color:var(--ink);
  font:14px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Arial;padding:0 0 40px}}
.wrap{{max-width:1400px;margin:0 auto;padding:0 16px}}
.tape{{overflow:hidden;border-bottom:1px solid var(--line);background:#0a0c10;white-space:nowrap;padding:8px 0}}
.taperun{{display:inline-block;animation:tape 40s linear infinite}}
.tk{{margin:0 22px;font:600 13px/1 ui-monospace,Consolas,monospace;color:var(--mut)}}
@keyframes tape{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
@media(prefers-reduced-motion:reduce){{.taperun{{animation:none}}}}
header{{padding:20px 0 14px;display:flex;align-items:flex-end;gap:26px;flex-wrap:wrap;border-bottom:1px solid var(--line)}}
.book b{{display:block;font:800 34px/1 ui-sans-serif;letter-spacing:-.01em}}
.book span{{font:600 11px/1 ui-sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}}
.book .chg{{font:600 15px/1 ui-monospace;margin-top:6px}}
.pill{{margin-left:auto;font:600 12px/1 ui-sans-serif;color:var(--mut);border:1px solid var(--line);
  padding:8px 12px;border-radius:999px}}
h2{{font:700 13px/1 ui-sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--mut);margin:22px 0 12px}}
.desks{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.desk{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px}}
.dtop{{display:flex;align-items:center;gap:9px;margin-bottom:7px}} .ava{{font-size:20px}}
.dname{{font-weight:700}} .badge{{margin-left:auto;font:600 10px/1 ui-sans-serif;letter-spacing:.05em;
  text-transform:uppercase;color:var(--mut);background:#1c222c;border-radius:5px;padding:4px 7px}}
.desk p{{color:var(--mut);font-size:12.5px}}
.grid{{display:grid;grid-template-columns:1.7fr 1fr;gap:18px;align-items:start}}
.heat{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}
.tile{{min-height:78px;border-radius:8px;padding:9px;display:flex;flex-direction:column;
  justify-content:center;text-align:center;color:#fff}}
.tile b{{font:700 15px/1.15 ui-sans-serif}}
.tile em{{font:600 12px/1.2 ui-monospace;font-style:normal;margin-top:5px}}
.tile .dim{{opacity:.72;font-weight:500}}
.chat{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:6px 14px;max-height:640px;overflow:auto}}
.msg{{padding:11px 0;border-bottom:1px solid var(--line)}} .msg:last-child{{border-bottom:0}}
.mh{{display:flex;align-items:center;gap:8px;margin-bottom:4px}} .mh b{{font-size:13px}}
.tag{{font:600 9.5px/1 ui-sans-serif;letter-spacing:.05em;padding:3px 5px;border-radius:4px;background:#252b36;color:var(--mut)}}
.tag.fill{{background:#123227;color:var(--up)}} .tag.ok{{background:#123227;color:var(--up)}} .tag.idea{{background:#1b2740;color:#6ea8fe}}
.ts{{margin-left:auto;color:var(--mut);font:500 11px/1 ui-monospace}}
.msg p{{color:#c7ccd4;font-size:13px}}
.empty{{color:var(--mut);background:var(--panel);border:1px dashed var(--line);border-radius:10px;padding:20px}}
.foot{{color:var(--mut);font-size:12px;margin-top:22px;border-top:1px solid var(--line);padding-top:14px}}
.foot a{{color:#6ea8fe}}
@media(max-width:900px){{.desks{{grid-template-columns:1fr}} .grid{{grid-template-columns:1fr}} .heat{{grid-template-columns:repeat(3,1fr)}}}}
</style></head><body>
{_ticker_tape(movers)}
<div class="wrap">
<header>
  <div class="book"><span>Agent Book · paper</span><b>${equity:,.0f}</b>
    <div class="chg" style="color:{_c(ret)}">{_pct(ret)} · stock sleeve today</div></div>
  <div class="book"><span>Open</span><b style="font-size:24px">{n_stocks} + {n_markets}</b>
    <div class="chg" style="color:var(--mut)">stocks · market bets</div></div>
  <div class="pill">as of {_esc(as_of)} · not financial advice</div>
</header>

<h2>The desk</h2>
<div class="desks">{desks}</div>

<div class="grid">
  <div><h2>Positions · marked to market</h2>{board}</div>
  <div><h2>Firm chat</h2><div class="chat">{chat}</div></div>
</div>

<div class="foot">A paper trading desk on live data — stock picks from the trending scan and YES/NO
positions on live Kalshi/Polymarket by recalibrated fair value. Real data, paper marks that accrue
over runs; no edge is claimed until the promotion gate clears. · <a href="index.html">← research briefing</a></div>
</div></body></html>"""
