"""P6c section D — the arena page (+ the regret surface).

Pinned: the Rallies book table (stock/alloc/entry/notional/worth/P&L/P&L%,
TOTAL P&L + AVAILABLE CASH) is server-rendered; SPY + HYSA benchmark rows and
the open BYOM slots are always on the board; a young book is chipped
"incubating"; receipts (book hash + dated events) are on screen; unmarked
positions render n/a and never fabricate; the regret section shows honest
zeros before any horizon resolves and real beat-rates after; hostile thesis
text is escaped; no external fetches; not-financial-advice present; build
writes the page with and without an artifact.
"""

from __future__ import annotations

from datetime import date

from forecasting_lab.agent_trader.arena_books import OPEN_SLOTS, ArenaLedger, claude_book
from forecasting_lab.calibration_log.regret import RegretLedger
from forecasting_lab.dashboard.arena_page import build_arena_page, render_arena_page

PAYLOAD = {"as_of": "2026-01-01", "verdicts": {
    "NVDA": {"label": "STRONG BUY", "score": 0.62},
    "VOO": {"label": "BUY", "score": 0.30},
    "SPY": {"label": "HOLD", "score": 0.10}}}
EMPTY_REGRET = {"recorded": 0, "resolved": 0, "open": 0, "baselines": {},
                "note": "no resolved horizons yet"}


def _marked_rows(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    px = {"NVDA": 100.0, "VOO": 400.0, "SPY": 600.0}
    led.mark("2026-01-02", px, hysa_yield_pct=5.0)
    return led.rows("2026-01-02", prices={**px, "NVDA": 110.0})


def test_rallies_book_table_is_server_rendered(tmp_path):
    html = render_arena_page(_marked_rows(tmp_path), EMPTY_REGRET, as_of="2026-01-02",
                             theses={"claude": "Hold the engine's conviction."})
    assert html.startswith("<!DOCTYPE html>")
    # the exact Rallies column order: STOCK · ALLOCATION · P&L · P&L% · NOTIONAL · WORTH · ENTRY
    head = html.split("<thead>")[1].split("</thead>")[0]
    order = [">stock<", ">allocation<", ">p&amp;l<", ">p&amp;l%<",
             ">notional<", ">worth<", ">entry<"]
    idx = [head.find(c) for c in order]
    assert all(i >= 0 for i in idx) and idx == sorted(idx)
    assert "TOTAL P&amp;L" in html and "AVAILABLE CASH" in html
    # a pure-cash book (HYSA) shows its one honest line, not an empty table
    assert "100% cash" in html
    assert 'href="t/NVDA.html"' in html                 # positions link their pages
    assert "Hold the engine&#x27;s conviction." in html or "Hold the engine" in html


def test_benchmarks_slots_incubation_and_receipts_on_the_board(tmp_path):
    html = render_arena_page(_marked_rows(tmp_path), EMPTY_REGRET, as_of="2026-01-02")
    assert ">SPY<" in html and ">HYSA<" in html         # benchmarks always on
    assert ">benchmark<" in html and ">incubating<" in html
    for slot in OPEN_SLOTS:
        assert slot["owner"] in html
    assert "open slot" in html
    assert "book " in html and "dated event" in html    # the receipts line
    assert "7-day track record" in html


def test_unmarked_positions_render_na_never_fabricated(tmp_path):
    led = ArenaLedger(path=tmp_path / "arena.json")
    led.upsert_book(claude_book(PAYLOAD))
    html = render_arena_page(led.rows("2026-01-01"), EMPTY_REGRET)  # no prices at all
    claude_card = html.split("<h2>claude</h2>")[1].split("</table>")[0]
    assert "n/a" in claude_card                          # entry/worth/pnl honest n/a


def test_regret_surface_honest_zeros_then_real_scores(tmp_path):
    empty = render_arena_page([], EMPTY_REGRET)
    assert "No resolved horizons yet" in empty and "nothing is claimed early" in empty.lower() \
        or "No resolved horizons yet" in empty
    led = RegretLedger(path=tmp_path / "regret.json")
    led.record("2026-01-01", [{"symbol": "NVDA", "label": "BUY", "score": 0.4}],
               {"NVDA": 100.0}, spy_price=500.0, hysa_yield_pct=5.0)
    led.resolve("2026-02-06", {"NVDA": 110.0}, spy_price=520.0)
    html = render_arena_page([], led.summary())
    assert "beat" in html and "mean edge" in html
    assert "vs just buying SPY" in html and "vs doing nothing" in html
    assert "including the misses" in html


def test_hostile_thesis_is_escaped(tmp_path):
    rows = _marked_rows(tmp_path)
    html = render_arena_page(rows, EMPTY_REGRET,
                             theses={"claude": '<img src=x onerror=alert(1)>'})
    assert "<img src=x onerror" not in html and "&lt;img" in html


def test_no_external_fetches_and_not_advice(tmp_path):
    html = render_arena_page(_marked_rows(tmp_path), EMPTY_REGRET)
    assert "fonts.googleapis" not in html and "<script" not in html
    assert "http://" not in html and "https://" not in html
    assert "not financial advice" in html.lower() and "Paper money" in html


def test_build_writes_with_and_without_an_artifact(tmp_path):
    from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts
    from forecasting_lab.signals.verdict import Component

    payload = build_verdicts(
        ["NVDA", "VOO"],
        lambda s: ({n: Component(n, 0.5, 0.9) for n in
                    ("backtest", "trend", "residual_momentum", "macro", "yield")}
                   if s == "NVDA" else {}),
        on=date(2026, 7, 5))
    vdir = tmp_path / "verdicts"
    write_verdicts(payload, out_dir=vdir)
    page = build_arena_page(tmp_path / "site", verdicts_dir=vdir,
                            ledger_path=tmp_path / "ledger.json",
                            codex_dir=tmp_path / "codex",
                            regret_path=tmp_path / "regret.json")
    text = page.read_text(encoding="utf-8")
    assert page.name == "arena.html" and "claude" in text  # Claude's book raced
    assert ">SPY<" in text and ">HYSA<" in text
    # no artifact: rules + open slots render honestly, never blank
    bare = build_arena_page(tmp_path / "site2", verdicts_dir=tmp_path / "none",
                            ledger_path=tmp_path / "ledger2.json",
                            regret_path=tmp_path / "regret2.json")
    bare_text = bare.read_text(encoding="utf-8")
    assert "No AI books race yet" in bare_text and "open slot" in bare_text
    # Codex review: benchmarks are on the board even with NO artifact — and
    # honestly undated/unmarked, never a fabricated date or equity
    assert ">SPY<" in bare_text and ">HYSA<" in bare_text
    assert "book dated n/a" in bare_text and "None" not in bare_text
