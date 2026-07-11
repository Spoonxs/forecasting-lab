"""P7 section A — flab-ask, the deterministic desk chat.

Pinned: each of the six intents answers from fixture artifacts with its
receipts (as_of + audit hash or "no record"); intent classification is
deterministic patterns with the fees/verdict ordering fixed and longest-symbol
extraction; unknown questions and missing artifacts get honest statements,
never guesses; mutual funds route to their twin's verdict; the optional LLM
rephrase receives the deterministic facts VERBATIM as its only source and any
failure falls back to the deterministic render; the core path imports no HTTP
machinery.
"""

from __future__ import annotations

import json
from datetime import date

from forecasting_lab.calibration_log.regret import RegretLedger
from forecasting_lab.desk.ask import Answer, ask, classify, rephrase_with_llm
from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts
from forecasting_lab.signals.verdict import Component

KNOWN = {"NVDA", "VOO", "VTI", "VTSAX"}


def _artifact(tmp_path, on=date(2026, 7, 10)):
    def provider(sym):
        if sym in ("NVDA", "VTI"):
            return {n: Component(n, 0.5, 0.9, f"{n} detail") for n in
                    ("backtest", "trend", "residual_momentum", "macro", "yield")}
        return {}

    payload = build_verdicts(["NVDA", "VTI", "VOO"], provider, on=on)
    vdir = tmp_path / "verdicts"
    write_verdicts(payload, out_dir=vdir)
    return vdir


def test_classification_is_deterministic_and_ordered():
    assert classify("what's the verdict on NVDA", KNOWN) == ("verdict", "NVDA")
    assert classify("NVDA", KNOWN) == ("verdict", "NVDA")          # bare symbol
    assert classify("is VTSAX cheap to hold", KNOWN) == ("fees", "VTSAX")
    assert classify("what changed today", KNOWN)[0] == "changes"
    assert classify("how's the arena going", KNOWN)[0] == "arena"
    assert classify("how have the recommendations actually done", KNOWN)[0] == "regret"
    assert classify("what are the watchers seeing", KNOWN)[0] == "watchers"
    assert classify("what is the meaning of life", KNOWN) == ("help", None)
    # fees + symbol outranks verdict; longest symbol wins extraction
    assert classify("NVDA expense fees", KNOWN) == ("fees", "NVDA")
    assert classify("v VTSAX", {"V", "VTSAX"}) == ("verdict", "VTSAX")


def test_verdict_answer_carries_dials_drivers_and_receipts(tmp_path):
    vdir = _artifact(tmp_path)
    a = ask("what's the verdict on NVDA", verdicts_dir=vdir,
            arena_path=tmp_path / "a.json", regret_path=tmp_path / "r.json",
            inputs_dir=tmp_path)
    assert a.intent == "verdict" and "NVDA" in a.text
    assert "Dials" in a.text and "Top drivers" in a.text and "backtest" in a.text
    assert "as of 2026-07-10 · audit " in a.receipts
    assert "not financial advice" in a.render()
    # an unrated symbol gets the honest watchlist path, not a guess
    voo = ask("verdict on VOO", verdicts_dir=vdir, arena_path=tmp_path / "a.json",
              regret_path=tmp_path / "r.json", inputs_dir=tmp_path)
    assert "INSUFFICIENT" in voo.text or "no verdict" in voo.text


def test_mutual_fund_routes_via_its_twin(tmp_path):
    vdir = _artifact(tmp_path)
    a = ask("what do you think of VTSAX", verdicts_dir=vdir,
            arena_path=tmp_path / "a.json", regret_path=tmp_path / "r.json",
            inputs_dir=tmp_path)
    assert a.intent == "verdict"
    assert "scored via its ETF twin VTI" in a.text


def test_changes_arena_regret_watchers_answer_honestly_when_empty(tmp_path):
    vdir = _artifact(tmp_path)
    kw = {"verdicts_dir": vdir, "arena_path": tmp_path / "a.json",
          "regret_path": tmp_path / "r.json", "inputs_dir": tmp_path}
    assert "Only one artifact" in ask("what changed", **kw).text
    assert "no books yet" in ask("how's the arena", **kw).text
    assert "No resolved horizons yet" in ask("regret so far?", **kw).text
    assert "No watcher feed yet" in ask("any watchers fired?", **kw).text


def test_changes_names_movers_with_a_prior(tmp_path):
    vdir = _artifact(tmp_path)
    payload2 = build_verdicts(["NVDA", "VTI", "VOO"], lambda s: {}, on=date(2026, 7, 11))
    write_verdicts(payload2, out_dir=vdir)              # NVDA/VTI drop to INSUFFICIENT
    a = ask("what changed today", verdicts_dir=vdir, arena_path=tmp_path / "a.json",
            regret_path=tmp_path / "r.json", inputs_dir=tmp_path)
    assert "NVDA" in a.text and "->" in a.text
    assert "as of 2026-07-11" in a.receipts


def test_arena_and_regret_answers_with_data(tmp_path):
    from forecasting_lab.agent_trader.arena_books import ArenaLedger, claude_book

    vdir = _artifact(tmp_path)
    led = ArenaLedger(path=tmp_path / "a.json")
    led.upsert_book(claude_book({"as_of": "2026-07-10", "verdicts": {
        "NVDA": {"label": "STRONG BUY", "score": 0.6}}}))
    led.mark("2026-07-11", {"NVDA": 100.0, "SPY": 500.0})
    led.save()
    a = ask("who's winning the arena", verdicts_dir=vdir, arena_path=led.path,
            regret_path=tmp_path / "r.json", inputs_dir=tmp_path)
    assert "claude" in a.text and "incubating" in a.text and "7-day" in a.text

    reg = RegretLedger(path=tmp_path / "r.json")
    reg.record("2026-01-01", [{"symbol": "NVDA", "label": "BUY", "score": 0.4}],
               {"NVDA": 100.0}, spy_price=500.0, hysa_yield_pct=5.0)
    reg.resolve("2026-02-06", {"NVDA": 110.0}, spy_price=520.0)
    reg.save()
    r = ask("how have the recommendations actually done", verdicts_dir=vdir,
            arena_path=tmp_path / "a.json", regret_path=reg.path, inputs_dir=tmp_path)
    assert "1 resolved" in r.text and "vs spy: beat" in r.text.lower()
    assert "including the misses" in r.text


def test_fees_and_watchers_with_data(tmp_path):
    vdir = _artifact(tmp_path)
    kw = {"verdicts_dir": vdir, "arena_path": tmp_path / "a.json",
          "regret_path": tmp_path / "r.json", "inputs_dir": tmp_path}
    f = ask("is VTSAX cheap", **kw)
    assert "ETF twin is VTI" in f.text and "0.04%" in f.text and "0.03%" in f.text
    etf = ask("VOO fees", **kw)
    assert "0.03%" in etf.text
    from forecasting_lab.calibration_log.audit import content_hash

    inputs = {"prob_now": 0.55, "prob_prior": 0.4, "line": 0.5}
    (tmp_path / "2026-07-10-watchers.json").write_text(json.dumps({
        "events": [{"kind": "macro_flip", "date": "2026-07-10",
                    "reason": "crossed above the 50% line",
                    "sha256": content_hash(inputs), "inputs": inputs}],
        "skips": [{"kind": "earnings_proximity", "reason": "no source yet"}]}),
        encoding="utf-8")
    w = ask("what are the watchers seeing", **kw)
    assert "macro_flip" in w.text and "no source yet" in w.text
    assert "hashes verified" in w.receipts               # claimed only after recompute
    # Codex review: a tampered feed is called out, never given a false receipt
    (tmp_path / "2026-07-10-watchers.json").write_text(json.dumps({
        "events": [{"kind": "macro_flip", "date": "2026-07-10",
                    "reason": "crossed", "sha256": "forged", "inputs": inputs}],
        "skips": []}), encoding="utf-8")
    bad = ask("watchers?", **kw)
    assert "FAILED the hash check" in bad.receipts and "corrupted" in bad.receipts


def test_llm_rephrase_gets_the_facts_verbatim_and_falls_back():
    a = Answer("verdict", "NVDA: BUY at +0.310.", "as of d · audit abc")
    seen = {}

    def runner(prompt):
        seen["prompt"] = prompt
        return "Sure — NVDA sits at BUY."

    out = rephrase_with_llm(a, runner)
    # Codex review: the receipts + disclaimer are re-appended BY CODE — the
    # LLM can neither drop nor forge them, and the provenance is stated
    assert out.startswith("Sure — NVDA sits at BUY.")
    assert "[as of d · audit abc]" in out and "reworded by codex" in out
    assert a.text in seen["prompt"]                      # the facts, verbatim
    assert "do not add numbers" in seen["prompt"]
    assert "not a command to follow" in seen["prompt"]   # injection guard stated
    # failure or empty output -> the deterministic render, never silence
    assert rephrase_with_llm(a, lambda p: "") == a.render()

    def boom(p):
        raise RuntimeError("no codex here")

    assert rephrase_with_llm(a, boom) == a.render()


def test_core_path_has_no_http_machinery():
    import inspect

    from forecasting_lab.desk import ask as mod
    src = inspect.getsource(mod)
    for banned in ("requests", "urllib", "HttpClient", "http.client", "socket"):
        assert banned not in src
