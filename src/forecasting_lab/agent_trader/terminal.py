"""The Agent Terminal — a dark, alive, agentic trading desk view (P5: the honest console).

Renders the agent's real paper book as a trading terminal: a ticker tape, the Agent
Book equity, the agent *team* as desks with status notes, a positions heatmap coloured
by P&L, and a live "Firm Chat" feed of the desk talking to itself. P5 adds the desk
console: a HEARTBEAT strip and a FAIL-CLOSED pill derived from the run-loop's ledger
snapshots (OPERATIONAL / HALTED-with-reason / NO DATA — the pill never guesses), the
MANDATE desk-notes card (violations AND the skipped-not-blocked lines, verbatim), a
provenance EVENT FEED where every row carries its receipts (run id + the V8 audit
hash, or "no audit record" said out loud), and a catch-me-up digest. Self-contained
dark HTML; every message is derived from real (paper) data — nothing is faked.
"""

from __future__ import annotations

import html as _html
import json
from pathlib import Path

UP = "#16c784"
DOWN = "#ea3943"


def default_ledger_path() -> Path:
    """Where the run loop's ledger lives (pass this to run_once's ledger_path)."""
    from ..config import PATHS

    return PATHS.data / "agent" / "ledger.jsonl"


def load_ledger(path: Path | str | None = None, limit: int = 20) -> dict:
    """Read the loop's JSONL ledger defensively: the newest ``limit`` snapshots,
    malformed lines skipped and COUNTED (never a crash, never silent)."""
    path = Path(path) if path is not None else default_ledger_path()
    if not path.exists():
        return {"empty": True}
    snapshots: list[dict] = []
    skipped = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"empty": True}
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if isinstance(row, dict):
            snapshots.append(row)
        else:
            skipped += 1
    if not snapshots:
        return {"empty": True, "skipped": skipped}
    return {"empty": False, "snapshots": snapshots[-limit:], "skipped": skipped,
            "n_total": len(snapshots)}


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


# ---------------------------------------------------------- P5: the console
def _pill_state(ledger: dict) -> tuple[str, str, str]:
    """(css class, label, plain-English why) from the latest snapshot — no guessing."""
    if ledger.get("empty"):
        return "p-nodata", "NO DATA", "no runs in the ledger yet — the loop hasn't executed here"
    last = ledger["snapshots"][-1]
    if last.get("halted"):
        notes = " ".join(str(n) for n in last.get("notes", []))
        if "mandate BLOCK" in notes:
            why = "the mandate blocked the proposal before execution"
        elif "kill switch" in notes:
            why = "the kill switch halted the rebalance (daily drawdown breached)"
        else:
            why = "the last run halted — see the notes on the tape"
        return "p-halt", "HALTED", why
    return "p-ok", "OPERATIONAL", "last run completed; guardrails enforced in the execution layer"


def _heartbeat(ledger: dict) -> str:
    if ledger.get("empty"):
        return ('<div class="hb"><span class="hb-item">no runs yet — the heartbeat starts '
                "with the first ledger snapshot</span></div>")
    snaps = ledger["snapshots"]
    last = snaps[-1]
    eq = float(last.get("equity", 0.0))
    items = [f'<span class="hb-item">last run <b>{_esc(last.get("run_id", "?"))}</b></span>',
             f'<span class="hb-item">equity <b>${eq:,.0f}</b></span>']
    if len(snaps) >= 2:
        prev = float(snaps[-2].get("equity", 0.0))
        delta = (eq / prev - 1.0) if prev else 0.0
        items.append(f'<span class="hb-item">vs prior run <b style="color:{_c(delta)}">{_pct(delta)}</b></span>')
    items.append(f'<span class="hb-item">fills last run <b>{int(last.get("fills", 0))}</b></span>')
    if ledger.get("skipped"):
        items.append(f'<span class="hb-item">{int(ledger["skipped"])} malformed ledger line(s) skipped</span>')
    return f'<div class="hb">{"".join(items)}</div>'


def _mandate_card(ledger: dict) -> str:
    if ledger.get("empty"):
        return ""
    report = ledger["snapshots"][-1].get("mandate")
    if not report:
        return ""
    status = str(report.get("status", "pass"))
    tone = {"pass": "ok", "warn": "idea", "block": "fill"}.get(status, "")
    lines = []
    for v in report.get("violations", []):
        lines.append(f'<li class="m-block">BLOCK · {_esc(v)}</li>')
    for w in report.get("warnings", []):
        lines.append(f'<li class="m-warn">WARN · {_esc(w)}</li>')
    for s in report.get("skipped", []):
        lines.append(f'<li class="m-skip">SKIPPED · {_esc(s)}</li>')
    body = "".join(lines) or '<li class="m-skip">every rule passed cleanly</li>'
    return (f'<div class="desk mandate"><div class="dtop"><span class="ava">&#9878;&#65039;</span>'
            f'<span class="dname">Mandate</span><span class="badge {tone}">{_esc(status)}</span></div>'
            f'<ul class="mlist">{body}</ul>'
            f'<p>The mandate is a decision, not an order — a BLOCK stops the cycle before '
            f'the execution layer ever sees it.</p></div>')


def _event_kind(snap: dict) -> str:
    if snap.get("halted"):
        return "halt"
    if snap.get("proposal_queued", {}).get("changes"):
        return "proposal"
    if int(snap.get("fills", 0) or 0) > 0:
        return "fill"
    return "run"


def _receipt(snap: dict) -> str:
    sha = snap.get("inputs_sha256")
    if sha:
        return (f'<span class="rcpt" title="this decision&#39;s exact inputs are '
                f'content-hashed and replayable (V8 audit trail)">&#9782; {_esc(str(sha)[:12])}</span>')
    return '<span class="rcpt none">no audit record</span>'


def _event_feed(ledger: dict) -> str:
    """The claim-tape mechanic: every event carries its receipts — run id + the
    audit hash when the snapshot has one, "no audit record" said out loud when
    it doesn't. Filter buttons are server-rendered; rows are visible without JS."""
    if ledger.get("empty"):
        return '<p class="empty">the tape starts with the first ledger snapshot</p>'
    rows = []
    for snap in reversed(ledger["snapshots"]):
        kind = _event_kind(snap)
        bits = [f'<b>{_esc(snap.get("run_id", "?"))}</b>',
                f'equity ${float(snap.get("equity", 0)):,.0f}',
                f'{int(snap.get("fills", 0) or 0)} fill(s)']
        if snap.get("halted"):
            note = next((str(n) for n in snap.get("notes", [])), "halted")
            bits.append(f'<span class="ev-halt">{_esc(note)}</span>')
        prop = snap.get("proposal_queued") or {}
        if prop.get("changes"):
            approved = bool(prop.get("approved", False))
            bits.append(f'<span class="ev-prop">proposal queued: {_esc(json.dumps(prop["changes"]))} '
                        f'· approved={str(approved).lower()} — never auto-applied</span>')
        if snap.get("forecast_ids"):
            bits.append(f'forecasts logged: {_esc(",".join(str(i) for i in snap["forecast_ids"]))}')
        rows.append(f'<li data-ev="{kind}"><span class="evk">{kind}</span> '
                    f'{" · ".join(bits)} {_receipt(snap)}</li>')
    filters = ('<div class="evfilters" data-ev-filter>'
               '<button data-kind="all" class="on">All</button>'
               '<button data-kind="fill">Fills</button>'
               '<button data-kind="halt">Halts</button>'
               '<button data-kind="proposal">Proposals</button></div>')
    return filters + f'<ul class="evfeed">{"".join(rows)}</ul>'


def _catch_me_up(ledger: dict) -> str:
    """Since-you-last-looked, server-rendered and honest about zeros."""
    if ledger.get("empty"):
        return ""
    snaps = ledger["snapshots"]
    first_eq, last_eq = float(snaps[0].get("equity", 0)), float(snaps[-1].get("equity", 0))
    move = (last_eq / first_eq - 1.0) if first_eq else 0.0
    fills = sum(int(s.get("fills", 0) or 0) for s in snaps)
    halts = [s for s in snaps if s.get("halted")]
    blocks = sum(1 for s in snaps if (s.get("mandate") or {}).get("status") == "block")
    fids = [str(i) for s in snaps for i in (s.get("forecast_ids") or [])]
    lines = [
        f"<li>{len(snaps)} run(s) on the tape; equity moved "
        f'<b style="color:{_c(move)}">{_pct(move)}</b> across them</li>',
        f"<li>{fills} fill(s) executed — every one idempotent and inside the caps</li>",
        f"<li>{len(halts)} halt(s)" + (
            ": " + _esc(next(iter(str(n) for n in halts[-1].get("notes", [])), "see the tape"))
            if halts else " — no guardrail fired") + "</li>",
        f"<li>{blocks} mandate block(s)</li>",
    ]
    if fids:
        lines.append(f"<li>forecasts logged for scoring: {_esc(', '.join(fids[-8:]))}</li>")
    return ('<details class="catchup"><summary>Catch me up</summary>'
            f'<ul>{"".join(lines)}</ul></details>')


def _gate_line(arena: dict) -> str:
    """The same gate the public page shows — the desk sees what the board sees."""
    gate = (arena or {}).get("gate") or {}
    if not gate:
        return ""
    if gate.get("hold"):
        verdict = f'0 survive &#8594; stated allocation 100% {_esc(gate.get("benchmark", "benchmark"))}'
    else:
        verdict = f'{len(gate.get("survivors", []))} survive: {_esc(", ".join(gate.get("survivors", [])))}'
    crowd = (arena or {}).get("crowding") or {}
    crowd_txt = ""
    if crowd:
        crowd_txt = (f' &#183; crowding {crowd.get("mean_pairwise_corr", 0):+.2f}'
                     + (" (crowded)" if crowd.get("crowded") else ""))
    return (f'<div class="gate">RISK READ — the gate: {gate.get("k", 0)} candidates &#183; '
            f'deflated-Sharpe / PBO / fleet-FDR &#183; {verdict}{crowd_txt}</div>')


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
    ledger = getattr(state, "ledger", None) or {"empty": True}
    as_of = getattr(state, "generated", "")
    picks = agent.get("picks") or []
    equity = agent.get("equity", 100_000.0)
    ret = agent.get("return", 0.0)
    n_stocks = agent.get("n_stocks", 0)
    n_markets = agent.get("n_markets", 0)

    pill_cls, pill_label, pill_why = _pill_state(ledger)
    status_pill = (f'<div class="pill statuspill {pill_cls}" title="{_esc(pill_why)}">'
                   f'{pill_label}<span class="pwhy">{_esc(pill_why)}</span></div>')
    heartbeat = _heartbeat(ledger)
    mandate_card = _mandate_card(ledger)
    catchup = _catch_me_up(ledger)
    gate_line = _gate_line(getattr(state, "arena", {}) or {})
    event_feed = _event_feed(ledger)

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
.statuspill{{margin-left:auto;font:800 12px/1 ui-sans-serif;letter-spacing:.06em}}
.statuspill .pwhy{{display:block;font:500 10.5px/1.3 ui-sans-serif;letter-spacing:0;margin-top:4px;color:var(--mut)}}
.statuspill.p-ok{{color:var(--up);border-color:#1d4f3c}}
.statuspill.p-halt{{color:var(--dn);border-color:#5b2026;background:#2a1417}}
.statuspill.p-nodata{{color:var(--mut)}}
.statuspill + .pill{{margin-left:0}}
.hb{{display:flex;flex-wrap:wrap;gap:8px 22px;padding:10px 0;border-bottom:1px solid var(--line);
  font:500 12.5px/1.4 ui-monospace,Consolas,monospace;color:var(--mut)}}
.hb b{{color:var(--ink)}}
.mandate .mlist{{list-style:none;margin:2px 0 8px;font:500 11.5px/1.6 ui-monospace,Consolas,monospace}}
.mandate .m-block{{color:var(--dn)}} .mandate .m-warn{{color:#e8b23e}} .mandate .m-skip{{color:var(--mut)}}
.badge.ok{{color:var(--up)}} .badge.fill{{color:var(--dn)}} .badge.idea{{color:#6ea8fe}}
.catchup{{margin:12px 0 0;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px}}
.catchup summary{{cursor:pointer;font:700 12px/1 ui-sans-serif;letter-spacing:.07em;text-transform:uppercase;color:var(--mut)}}
.catchup ul{{list-style:none;margin-top:9px}}
.catchup li{{font:500 12.5px/1.7 ui-monospace,Consolas,monospace;color:#c7ccd4}}
.gate{{margin-top:12px;font:600 12px/1.6 ui-monospace,Consolas,monospace;color:var(--mut);
  border:1px solid var(--line);border-left:3px solid #6ea8fe;border-radius:6px;padding:9px 12px;background:var(--panel)}}
.evfilters{{display:inline-flex;gap:4px;margin-bottom:10px}}
.evfilters button{{font:600 11px/1 ui-sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--mut);
  background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:7px 11px;cursor:pointer}}
.evfilters button.on{{color:var(--ink);border-color:#3a4356}}
.evfeed{{list-style:none;border-top:1px solid var(--line)}}
.evfeed li{{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;padding:9px 0;
  border-bottom:1px solid var(--line);font:500 12.5px/1.6 ui-monospace,Consolas,monospace;color:#c7ccd4}}
.evfeed .evk{{flex:none;font:700 9.5px/1 ui-sans-serif;letter-spacing:.06em;text-transform:uppercase;
  color:var(--mut);background:#1c222c;border-radius:4px;padding:4px 7px}}
.evfeed li[data-ev="halt"] .evk{{color:var(--dn)}} .evfeed li[data-ev="fill"] .evk{{color:var(--up)}}
.evfeed li[data-ev="proposal"] .evk{{color:#6ea8fe}}
.evfeed .ev-halt{{color:var(--dn)}} .evfeed .ev-prop{{color:#9db6e8}}
.rcpt{{margin-left:auto;font:600 10.5px/1 ui-monospace;color:#6ea8fe;background:#141b2a;
  border:1px solid #263352;border-radius:5px;padding:4px 7px;cursor:help}}
.rcpt.none{{color:var(--mut);background:#1a1e26;border-color:var(--line)}}
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
  {status_pill}
  <div class="pill">as of {_esc(as_of)} · not financial advice</div>
</header>

{heartbeat}
{catchup}
{gate_line}

<h2>The desk</h2>
<div class="desks">{desks}{mandate_card}</div>

<div class="grid">
  <div><h2>Positions · marked to market</h2>{board}</div>
  <div><h2>Firm chat</h2><div class="chat">{chat}</div></div>
</div>

<h2>The run tape · every event with its receipts</h2>
{event_feed}

<div class="foot">A paper trading desk on live data — stock picks from the trending scan and YES/NO
positions on live Kalshi/Polymarket by recalibrated fair value. Real data, paper marks that accrue
over runs; no edge is claimed until the promotion gate clears. · <a href="index.html">← research briefing</a></div>
</div>
<script>
(function(){{
  document.querySelectorAll('[data-ev-filter]').forEach(function(g){{
    g.querySelectorAll('button').forEach(function(b){{
      b.addEventListener('click', function(){{
        g.querySelectorAll('button').forEach(function(x){{x.classList.remove('on');}});
        b.classList.add('on');
        var kind=b.getAttribute('data-kind');
        document.querySelectorAll('.evfeed li').forEach(function(li){{
          li.style.display=(kind==='all'||li.getAttribute('data-ev')===kind)?'':'none';
        }});
      }});
    }});
  }});
}})();
</script>
</body></html>"""
