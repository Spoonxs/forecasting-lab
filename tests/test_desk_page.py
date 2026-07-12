"""P10-1 — the in-site desk chat.

Pinned: desk_contract() ships the EXACT pattern strings the Python engine
compiles (one source, no drift) and classify() uses them; the reduced
desk-data bundle carries what the six intents need (and nothing personal);
the page embeds the contract, fetches ONLY ./desk-data.json (same-origin),
answers via textContent (no innerHTML on user/artifact text), shows the
receipts + disclaimer on every answer, offers the Rallies question chips,
and contains NO LLM plumbing; the nav gains Desk.
"""

from __future__ import annotations

import json
import re
from datetime import date

from forecasting_lab.dashboard.desk_page import (
    build_desk_data,
    build_desk_page,
    render_desk_page,
)
from forecasting_lab.desk.ask import _RES, INTENT_PATTERNS, classify, desk_contract


def test_contract_ships_the_exact_compiled_patterns():
    c = desk_contract()
    assert c["patterns"] == INTENT_PATTERNS
    for k, pat in c["patterns"].items():
        assert _RES[k].pattern == pat                    # the engine compiles THESE
    assert c["order"] == ["fees", "changes", "arena", "regret", "watchers", "verdict"]
    assert c["rules"]["fees_requires_symbol"] is True
    assert len(c["chips"]) == 6 and "help" in c
    # the engine's classify still honors the shared table
    assert classify("is VTSAX cheap", {"VTSAX"}) == ("fees", "VTSAX")
    assert classify("what is the meaning of life", {"VTSAX"}) == ("help", None)


def test_bundle_is_reduced_and_public(tmp_path):
    from forecasting_lab.pipeline.verdicts import build_verdicts, write_verdicts
    from forecasting_lab.signals.verdict import Component

    payload = build_verdicts(
        ["NVDA", "VOO"],
        lambda s: ({n: Component(n, 0.5, 0.9, f"{n} detail " + "x" * 100) for n in
                    ("backtest", "trend", "residual_momentum", "macro", "yield")}
                   if s == "NVDA" else {}),
        on=date(2026, 7, 12))
    vdir = tmp_path / "v"
    write_verdicts(payload, out_dir=vdir)
    b = build_desk_data(verdicts_dir=vdir, arena_path=tmp_path / "a.json",
                        regret_path=tmp_path / "r.json", inputs_dir=tmp_path)
    assert b["as_of"] == "2026-07-12" and len(b["audit"]) == 12
    nvda = b["verdicts"]["NVDA"]
    assert nvda["label"] and len(nvda["comps"]) == 3     # top-3 only, reduced
    assert all(len(c[2]) <= 60 for c in nvda["comps"])   # details truncated
    assert b["regret"]["recorded"] == 0 and b["arena"] == []
    assert "VTSAX" in b["twins"] and b["core_etfs"]["VOO"] > 0
    blob = json.dumps(b)
    for banned in ("holdings", "journal", "flab_account"):
        assert banned not in blob                        # nothing personal, ever


def test_page_is_contract_driven_and_same_origin_only():
    html = render_desk_page()
    blob = html.split('id="contract" type="application/json">')[1].split("</script>")[0]
    parsed = json.loads(blob.replace("\\u003c", "<").replace("\\u003e", ">"))
    assert parsed["patterns"] == INTENT_PATTERNS         # one source of truth
    js = html.split("<script>")[-1]
    assert "new RegExp(C.patterns[k],'i')" in js         # compiled FROM the contract
    assert "C.bare_symbol_max_tokens" in js
    fetches = re.findall(r"fetch\('([^']+)'\)", js)
    assert fetches == ["desk-data.json"]                 # same-origin, nothing else
    assert "innerHTML" not in js and "textContent" in js # answers are text nodes
    for banned in ("http://", "https://", "XMLHttpRequest", "sendBeacon",
                   "openai", "anthropic", "llm"):
        assert banned not in js.lower()
    assert 'class="chip"' in html and html.count("data-q=") == 6
    assert "no AI is\ndeciding a fact" in html or "DETERMINISTIC" in html
    assert "not financial advice" in html.lower()


# ------------------------------------------------ Codex code-review fixes pinned
def test_fee_questions_reach_core_etfs_absent_from_the_artifact(tmp_path):
    """Codex finding 1: a core ETF with a published fee answers even when the
    artifact doesn't rate it — engine and mirror alike."""
    from forecasting_lab.desk.ask import ask

    a = ask("VOO fees", verdicts_dir=tmp_path / "none", arena_path=tmp_path / "a.json",
            regret_path=tmp_path / "r.json", inputs_dir=tmp_path)
    assert a.intent == "fees" and "0.03%" in a.text
    js = render_desk_page().split("<script>")[-1]
    assert "D.core_etfs||{}" in js.replace(" ", "")       # the mirror's known() too


def test_mirror_receipts_and_tokenizer_stay_honest():
    """Codex findings 2+3: the client never claims audit coverage the bundle
    doesn't carry, and the bare-symbol tokenizer comes from the contract."""
    js = render_desk_page().split("<script>")[-1]
    assert "audit-hashed in the feed" not in js
    assert "hashes live in the committed feed artifact" in js
    assert "new RegExp(C.symbol_token,'g')" in js         # contract-driven count
    assert "/[A-Za-z][A-Za-z.\\-]*/g" not in js           # the hardcoded one is gone


def test_build_writes_page_and_bundle_and_nav_links_it(tmp_path):
    page = build_desk_page(tmp_path, verdicts_dir=tmp_path / "none",
                           arena_path=tmp_path / "a.json",
                           regret_path=tmp_path / "r.json", inputs_dir=tmp_path)
    assert page.name == "desk.html"
    data = json.loads((tmp_path / "desk-data.json").read_text(encoding="utf-8"))
    assert data["verdicts"] == {} and data["as_of"] == ""  # honest empty bundle
    from forecasting_lab.dashboard.collect import collect_lab_state
    from forecasting_lab.dashboard.render import render_dashboard

    assert 'href="desk.html"' in render_dashboard(collect_lab_state(seed=0))
