"""P6a step 4 — TIER LIVE plumbing (worker + client mirror; PLATFORM_PLAN §2b/§10).

Pinned: the worker ships with its hardening (CORS lock, token bucket, negative
caching, symbol validation, market-hours TTL); the client mirror references the
contract file and never re-hardcodes engine numbers; the no-worker default
renders the stated degradation message, never silence.
"""

from __future__ import annotations

import re
from pathlib import Path

from forecasting_lab.dashboard.tier_live import (
    CONTRACT_PATH,
    DEGRADATION_MESSAGE,
    tier_live_js,
)

WORKER_DIR = Path(__file__).resolve().parents[1] / "workers" / "quote-proxy"


def test_worker_ships_with_its_hardening():
    js = (WORKER_DIR / "worker.js").read_text(encoding="utf-8")
    assert "ALLOWED_ORIGIN" in js and '"*"' not in js.split("Access-Control")[1][:200]
    assert "tooMany" in js and "tokens" in js            # per-IP token bucket
    assert "max-age=86400" in js                          # negative caching for bad symbols
    assert "stale-while-revalidate" in js
    assert re.search(r"SYMBOL_RE\s*=", js)                # symbol validation, no batch
    assert "marketOpenTtl" in js and "1260" in js         # DST-safe market window
    # Codex round-4 fixes pinned:
    assert "ALLOWED_SYMBOLS.has(symbol)" in js            # the registry IS the allowlist
    assert '"no-store"' in js and "502" in js             # transient upstream never poisons the cache
    toml = (WORKER_DIR / "wrangler.toml").read_text(encoding="utf-8")
    assert "ALLOWED_ORIGIN" in toml and "REPLACE-ME" in toml  # must be set before deploy
    readme = (WORKER_DIR / "README.md").read_text(encoding="utf-8")
    assert "optional" in readme.lower() and "add to watchlist" in readme


def test_allowlist_is_generated_from_the_registry(tmp_path):
    from forecasting_lab.dashboard.tier_live import emit_worker_allowlist

    path = emit_worker_allowlist(tmp_path / "allowlist.js")
    js = path.read_text(encoding="utf-8")
    assert js.startswith("// GENERATED")
    assert '"NVDA"' in js and '"VOO"' in js and '"CASH.HYSA"' not in js
    assert js.count(",") > 8000  # brokerage scale
    # the committed copy exists next to the worker
    assert (WORKER_DIR / "allowlist.js").exists()


def test_client_mirror_reads_the_contract_never_hardcodes():
    js = tier_live_js(worker_url="https://w.example")
    assert CONTRACT_PATH in js
    assert "contract.insufficient_label" in js and "contract.min_weight_coverage" in js
    # no engine constants baked into the JS — the contract file is the source
    assert "0.45" not in js and "0.40" not in js and "STRONG BUY" not in js


def test_no_worker_default_states_the_degradation():
    js = tier_live_js()  # the default: no worker configured
    assert DEGRADATION_MESSAGE in js
    assert "add to watchlist" in DEGRADATION_MESSAGE
    assert "nothing is computed on the spot" in DEGRADATION_MESSAGE
