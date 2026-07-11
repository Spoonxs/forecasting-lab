"""The arena page — site/arena.html (P6c sections C+D on one surface).

The Rallies book layout with Engo honesty: each AI book is a position table
(stock · alloc · entry · notional · worth · P&L · P&L%) with TOTAL P&L and
AVAILABLE CASH, its mandate receipts (content hash + dated rebalance events)
on screen, SPY and HYSA benchmark rows ALWAYS on the board, a 7-day
"incubating" chip before any other label, and real open bring-your-own-model
slots — never fake competitors. Below it, the regret ledger: every surfaced
recommendation tracked against SPY / HYSA / equal-weight / do-nothing, with
honest zeros ("no resolved horizons yet") before results accrue.
Paper money. Not financial advice.
"""

from __future__ import annotations

from pathlib import Path

from ..agent_trader.arena_books import NOTIONAL, ArenaLedger, claude_book, codex_book
from ..calibration_log.regret import RegretLedger
from .render import ACCENT, CARD, DOWN, FAINT, INK, MUTED, PAPER, RULE, UP, _esc

BASELINE_LABELS = {"spy": "vs just buying SPY", "hysa": "vs parking it in the HYSA",
                   "equal_weight": "vs equal-weighting the rated basket",
                   "do_nothing": "vs doing nothing"}


def _money(x) -> str:
    return "n/a" if x is None else f"${x:,.2f}"


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:+.2%}"


def _tone(x) -> str:
    if x is None:
        return FAINT
    return UP if x >= 0 else DOWN


def _book_card(row: dict, thesis: str = "") -> str:
    status = row["status"]
    chip_bg = {"benchmark": MUTED, "incubating": "#B8860B", "live": UP}.get(status, MUTED)
    # the Rallies column order, faithfully: STOCK · ALLOCATION · P&L · P&L% ·
    # NOTIONAL · WORTH · ENTRY (fidelity pass)
    pos_rows = "".join(
        f'<tr><td><a href="t/{_esc(p["symbol"])}.html">{_esc(p["symbol"])}</a></td>'
        f'<td class="num">{p["alloc"]:.0%}</td>'
        f'<td class="num" style="color:{_tone(p["pnl"])}">{_money(p["pnl"])}</td>'
        f'<td class="num" style="color:{_tone(p["pnl_pct"])}">{_pct(p["pnl_pct"])}</td>'
        f'<td class="num">{_money(p["notional"])}</td>'
        f'<td class="num">{_money(p["worth"])}</td>'
        f'<td class="num">{_money(p["entry"]) if p["entry"] else "n/a"}</td></tr>'
        for p in row["positions"]
    )
    if not pos_rows:  # a pure-cash book (HYSA) still shows its one honest line
        pos_rows = ('<tr><td colspan="7" class="allcash">100% cash — earns the recorded '
                    'HYSA yield, nothing else</td></tr>')
    total_pnl = row.get("total_pnl")
    events = row.get("events", [])
    last_ev = events[-1] if events else None
    receipts = (f'book {_esc(str(row.get("book_sha", ""))[:12])} · '
                f'{len(events)} dated event{"s" if len(events) != 1 else ""}'
                + (f' · last: {_esc(last_ev["kind"])} {_esc(last_ev["date"])}' if last_ev else ""))
    thesis_html = f'<p class="thesis">{_esc(thesis)}</p>' if thesis else ""
    return f"""<div class="card book">
  <div class="bhead"><h2>{_esc(row["owner"])}</h2>
    <span class="chip" style="background:{chip_bg}">{_esc(status)}</span>
    <span class="asof">book dated {_esc(str(row.get("as_of") or "n/a"))}</span></div>
  {thesis_html}
  <table><thead><tr><th>stock</th><th class="num">allocation</th><th class="num">p&amp;l</th>
    <th class="num">p&amp;l%</th><th class="num">notional</th><th class="num">worth</th>
    <th class="num">entry</th></tr></thead><tbody>{pos_rows}</tbody>
  <tfoot><tr><td colspan="5">TOTAL P&amp;L</td>
    <td class="num" colspan="2" style="color:{_tone(total_pnl)}">{_money(total_pnl)}</td></tr>
  <tr><td colspan="5">AVAILABLE CASH</td>
    <td class="num" colspan="2">{_money(row.get("cash"))}</td></tr></tfoot></table>
  <p class="receipts">{receipts}</p>
</div>"""


def _slot_card(slot: dict) -> str:
    return (f'<div class="card slot"><h2>{_esc(slot["owner"])}</h2>'
            f'<span class="chip open">{_esc(slot["status"])}</span>'
            f'<p class="thesis">{_esc(slot.get("note", ""))}</p></div>')


def _regret_html(summary: dict) -> str:
    if not summary.get("resolved"):
        tracked = summary.get("recorded", 0)
        return ('<p class="empty">No resolved horizons yet — '
                f'{tracked} recommendation{"s" if tracked != 1 else ""} being tracked forward '
                'against SPY, the HYSA, an equal-weight basket, and doing nothing. '
                'The score arrives when the horizons do; nothing is claimed early.</p>')
    cells = []
    for key, label in BASELINE_LABELS.items():
        b = summary["baselines"].get(key) or {}
        if not b.get("n"):
            cells.append(f'<div class="reg"><span>{_esc(label)}</span><b>n/a</b><i>no marks</i></div>')
            continue
        cells.append(
            f'<div class="reg"><span>{_esc(label)}</span>'
            f'<b style="color:{_tone(b["mean_edge"])}">{b["beat_rate"]:.0%} beat</b>'
            f'<i>mean edge {b["mean_edge"]:+.2%} · n={b["n"]}</i></div>')
    return (f'<div class="stats">{"".join(cells)}</div>'
            f'<p class="fine">{summary["resolved"]} resolved · {summary["open"]} still open — '
            'every recommendation is scored, including the misses.</p>')


def render_arena_page(rows: list[dict], regret_summary: dict, as_of: str = "",
                      theses: dict | None = None) -> str:
    theses = theses or {}
    book_rows = [r for r in rows if "positions" in r]
    books = "".join(_book_card(r, theses.get(r["owner"], "")) for r in book_rows)
    slots = "".join(_slot_card(r) for r in rows if "positions" not in r)
    if not any(not r.get("benchmark") for r in book_rows):
        books = ('<div class="card"><p class="empty">No AI books race yet — the arena opens '
                 'with the first nightly verdict build. The benchmarks and the rules are '
                 'already on the board.</p></div>') + books
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The arena — AI books, raced honestly</title>
<style>
:root {{ --paper:{PAPER}; --card:{CARD}; --ink:{INK}; --mut:{MUTED}; --faint:{FAINT};
  --rule:{RULE}; --accent:{ACCENT}; --up:{UP}; --down:{DOWN};
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace; }}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--paper);color:var(--ink);font:400 14px/1.6 var(--mono);font-variant-numeric:tabular-nums}}
.wrap{{max-width:940px;margin:0 auto;padding:22px 18px 70px}}
a{{color:var(--accent);text-decoration:none}}
h1{{font:800 22px/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;margin:6px 0 4px}}
h2{{font:800 15px/1.2 var(--mono);text-transform:uppercase;letter-spacing:.04em;display:inline}}
.sub{{color:var(--mut);font-size:12.5px;max-width:70ch}}
.card{{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:18px 20px;margin:14px 0}}
.card.slot{{border-style:dashed;background:transparent}}
.bhead{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}}
.chip{{font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;color:#fff;
  border-radius:3px;padding:4px 8px}}
.chip.open{{background:transparent;color:var(--mut);border:1px dashed var(--faint)}}
.asof{{color:var(--faint);font-size:11.5px}}
.thesis{{color:var(--mut);font-size:12.5px;margin:4px 0 10px}}
table{{width:100%;border-collapse:collapse;font:400 13px/1.5 var(--mono)}}
th{{text-align:left;font:700 10.5px/1 var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--mut);
  border-bottom:2px solid var(--ink);padding:0 10px 8px 0}}
th.num,td.num{{text-align:right}}
td{{padding:7px 10px 7px 0;border-bottom:1px solid var(--rule)}}
tfoot td{{font:700 12px/1.5 var(--mono);text-transform:uppercase;border-bottom:0;padding-top:10px}}
.receipts{{color:var(--faint);font-size:11px;margin-top:10px}}
.allcash{{color:var(--mut);font-size:12px}}
.empty{{color:var(--mut);font-size:13px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:10px 0}}
.reg{{border:1px solid var(--rule);border-radius:4px;padding:12px}}
.reg span{{display:block;font:600 10px/1.3 var(--mono);text-transform:uppercase;color:var(--mut);margin-bottom:6px}}
.reg b{{font:800 18px/1 var(--mono)}} .reg i{{display:block;font:400 11px/1.4 var(--mono);color:var(--faint);font-style:normal;margin-top:4px}}
.fine{{color:var(--faint);font-size:11.5px}}
footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--faint);text-align:center}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body>
<div class="wrap">
<a href="index.html">&#9666; Platform</a>
<h1>The arena</h1>
<p class="sub">AI-built paper books ({_money(NOTIONAL)} each), raced under a written mandate:
scheduled rebalances only, costs charged, cash earns the HYSA yield, picks dated before marks.
The benchmark is always on the board, and nothing gets a label before a 7-day track record.
{_esc("As of " + as_of + "." if as_of else "No verdict artifact yet.")}</p>
{books}
{slots}
<div class="card"><h2>The regret ledger</h2>
<p class="thesis">Every recommendation this platform surfaces is scored against the four things
you could have done instead. This is the honest definition of "was it worth it".</p>
{_regret_html(regret_summary)}</div>
<footer>Paper money. Research opinions, not financial advice.
· <a href="index.html">platform</a> · <a href="portfolio.html">portfolio</a>
· <a href="scorecard.html">scorecard</a></footer>
</div>
</body></html>"""


def build_arena_page(out_dir, *, verdicts_dir=None, ledger_path=None,
                     codex_dir=None, regret_path=None) -> Path:
    """Write site/arena.html. With a verdict artifact the books are (re)built
    and marked from the trending sidecar's closes; without one the page renders
    the rules, the benchmarks and the open slots — honestly, never blank."""
    from ..pipeline.verdicts import load_latest_verdicts

    loaded = load_latest_verdicts(verdicts_dir)
    payload = {} if loaded.get("empty") else loaded["payload"]
    led = ArenaLedger(path=ledger_path)
    theses = {}
    rows: list[dict] = []
    if payload:
        cb_claude = claude_book(payload)
        theses["claude"] = cb_claude.get("thesis", "")
        led.upsert_book(cb_claude)
        cb_codex = codex_book(payload, out_dir=codex_dir)  # committed artifact at build time
        if cb_codex:
            theses["codex"] = cb_codex.get("thesis", "")
            led.upsert_book(cb_codex)
        prices, px_date = sidecar_prices()
        if prices and px_date:
            # marks are dated by the closes' OWN date, never the build's
            led.mark(px_date, prices, hysa_yield_pct=payload.get("hysa_yield_pct"))
        led.save()
        rows = led.rows(payload["as_of"], prices=prices or {})
    else:
        from ..agent_trader.arena_books import OPEN_SLOTS

        # benchmarks are ALWAYS on the board (Codex review) — undated, unmarked
        # placeholders with honest n/a rather than fabricated dates or equity
        bench = [{"owner": o, "benchmark": True, "status": "benchmark", "as_of": None,
                  "book_sha": "benchmark", "positions": [], "cash": None,
                  "equity": None, "total_pnl": None, "events": []}
                 for o in ("SPY", "HYSA")]
        rows = bench + [dict(s) for s in OPEN_SLOTS]
    regret = RegretLedger(path=regret_path) if regret_path else RegretLedger()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    page = out / "arena.html"
    page.write_text(render_arena_page(rows, regret.summary(),
                                      as_of=payload.get("as_of", ""), theses=theses),
                    encoding="utf-8")
    return page


def sidecar_prices() -> tuple[dict, str | None]:
    """(closes, digest date) from the newest trending sidecar; ({}, None)
    offline. The date rides along so stale closes can never masquerade as
    today's marks (Codex review)."""
    try:
        import json

        from ..config import PATHS

        candidates = sorted(PATHS.inputs.glob("*-trending-stocks.json"))
        if not candidates:
            return {}, None
        digest_date = candidates[-1].name[:10]  # <YYYY-MM-DD>-trending-stocks.json
        movers = json.loads(candidates[-1].read_text(encoding="utf-8")).get("movers", [])
        return {str(c["ticker"]).upper(): float(c["last"])
                for c in movers if c.get("last")}, digest_date
    except Exception:  # pragma: no cover - defensive
        return {}, None
