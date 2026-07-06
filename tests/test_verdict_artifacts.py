"""P6a step 3 — the TIER FULL artifact build (PLATFORM_PLAN §2b).

Properties pinned: the tier is registry-validated and deduplicated; the dated
payload is audit-hashed and replays byte-for-byte; contract.json equals the
live engine export exactly (the JS mirror's anchor); symbols with no evidence
are INSUFFICIENT EVIDENCE, never guessed; Claude's opinion artifact is dated +
deterministic; Codex's falls back to the last committed artifact WITH its date
and a stale flag — honest staleness, never silence.
"""

from __future__ import annotations

import json
from datetime import date

from forecasting_lab.calibration_log.audit import AuditTrail, canonical_json
from forecasting_lab.pipeline.verdicts import (
    build_verdicts,
    codex_opinion,
    load_watchlist,
    tier_full_symbols,
    verify_contract_roundtrip,
    write_claude_opinion,
    write_verdicts,
)
from forecasting_lab.signals.verdict import Component, scoring_contract


def _provider(symbol: str) -> dict:
    if symbol == "NVDA":  # rich evidence -> a real verdict
        return {n: Component(n, 0.5, 0.9) for n in
                ("backtest", "trend", "residual_momentum", "macro", "yield")}
    return {}  # everything else: no evidence -> INSUFFICIENT


def test_tier_is_registry_validated_and_deduplicated(tmp_path):
    wl = tmp_path / "watchlist.json"
    wl.write_text(json.dumps({"symbols": ["nvda", "VOO", "FAKETICKER99", "NVDA"]}),
                  encoding="utf-8")
    symbols = tier_full_symbols(watchlist_path=wl, trending=["GME", "NVDA"])
    assert symbols[0] == "VOO"  # core ETFs lead
    assert symbols.count("NVDA") == 1 and symbols.count("VOO") == 1
    assert "FAKETICKER99" not in symbols  # unknown names never enter the tier
    assert "GME" in symbols and len(symbols) > 400  # S&P universe fills the tail
    assert load_watchlist(tmp_path / "missing.json") == []  # honest empty


def test_payload_replays_byte_for_byte_and_contract_roundtrips(tmp_path):
    payload = build_verdicts(["NVDA", "VOO"], _provider, on=date(2026, 7, 5))
    audit = AuditTrail(tmp_path / "audit.jsonl")
    path, sha = write_verdicts(payload, out_dir=tmp_path, audit=audit)
    # the artifact on disk IS the canonical bytes that were hashed
    assert path.read_text(encoding="utf-8") == canonical_json(payload)
    replayed, sha2 = audit.replay("verdicts:2026-07-05")
    assert canonical_json(replayed) == canonical_json(payload) and sha == sha2
    # the written contract equals the live engine export exactly
    assert verify_contract_roundtrip(out_dir=tmp_path)
    written = json.loads((tmp_path / "contract.json").read_text(encoding="utf-8"))
    assert written == scoring_contract()


def test_no_evidence_means_insufficient_never_a_guess():
    payload = build_verdicts(["NVDA", "VOO"], _provider, on=date(2026, 7, 5))
    assert payload["verdicts"]["VOO"]["label"] == "INSUFFICIENT EVIDENCE"
    assert payload["verdicts"]["NVDA"]["label"] != "INSUFFICIENT EVIDENCE"
    matrix = payload["verdicts"]["NVDA"]["labels_by_profile"]
    assert len(matrix) == 27  # 3 horizons x 3 goals x 3 risk levels
    assert set(k.split("|")[1] for k in matrix) == {"grow", "income", "preserve"}
    assert set(k.split("|")[2] for k in matrix) == {"low", "med", "high"}


def test_claude_opinion_is_dated_deterministic_and_skips_insufficient(tmp_path):
    payload = build_verdicts(["NVDA", "VOO"], _provider, on=date(2026, 7, 5))
    path = write_claude_opinion(payload, out_dir=tmp_path, top_n=5)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["as_of"] == "2026-07-05" and artifact["model"] == "claude"
    symbols = {p["symbol"] for p in artifact["picks"]}
    assert "NVDA" in symbols and "VOO" not in symbols  # no opinion without evidence
    assert "research opinion" in artifact["caveat"]
    # deterministic: a second write produces identical bytes
    again = write_claude_opinion(payload, out_dir=tmp_path, top_n=5)
    assert again.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")


def test_codex_opinion_freshness_and_honest_fallback(tmp_path):
    payload = build_verdicts(["NVDA"], _provider, on=date(2026, 7, 5))
    # a working runner -> fresh dated artifact
    fresh = codex_opinion(payload, out_dir=tmp_path, runner=lambda p: "agree on NVDA")
    assert fresh["stale"] is False and fresh["as_of"] == "2026-07-05"
    # Codex review fix: the PERSISTED artifact never carries a stale flag —
    # staleness is computed at read time, so the file can't claim freshness
    persisted = json.loads((tmp_path / "codex.json").read_text(encoding="utf-8"))
    assert "stale" not in persisted
    # runner dies later -> the LAST committed artifact renders WITH its date
    later = build_verdicts(["NVDA"], _provider, on=date(2026, 7, 9))
    stale = codex_opinion(later, out_dir=tmp_path,
                          runner=lambda p: (_ for _ in ()).throw(OSError("no cli")))
    assert stale["as_of"] == "2026-07-05" and stale["stale"] is True
    assert stale["opinion"] == "agree on NVDA"
    # nothing ever committed -> the honest note, never silence
    empty = codex_opinion(later, out_dir=tmp_path / "fresh-dir", runner=None)
    assert empty["opinion"] is None and "no codex opinion committed" in empty["note"]
