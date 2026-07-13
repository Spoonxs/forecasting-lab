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
    # P10-5: DEPLOYED — CORS locked to the real Pages origin, never a wildcard
    assert 'ALLOWED_ORIGIN = "https://spoonxs.github.io"' in toml
    config_lines = "\n".join(ln for ln in toml.splitlines()
                             if not ln.lstrip().startswith("#"))
    assert '"*"' not in config_lines and "REPLACE-ME" not in config_lines
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


# ------------------------------------------------ P10-5: the deployed worker wired
def test_worker_url_reads_the_committed_config_and_degrades_honestly(tmp_path, monkeypatch):
    from forecasting_lab.dashboard.tier_live import copy_contract, worker_url

    url = worker_url()
    assert url.startswith("https://") and "workers.dev" in url  # the deployed proxy
    # the contract lands at the SITE ROOT (the old data/verdicts path never
    # existed on Pages — the mirror's fetch would have 404'd)
    dest = copy_contract(tmp_path)
    assert dest is not None and dest.name == "contract.json"
    import json as _json

    assert "mutual_fund_twins" in _json.loads(dest.read_text(encoding="utf-8"))


def test_home_carries_the_live_preview_path():
    from forecasting_lab.dashboard.collect import collect_lab_state
    from forecasting_lab.dashboard.render import render_dashboard

    html = render_dashboard(collect_lab_state(seed=0))
    assert "TIER_LIVE" in html and "'/bars/'" in html
    assert "contract.json" in html
    assert "live preview" in html and "TIER_LIVE.verdict(b.dataset.s)" in html
    # the button only renders when a worker is configured (LP gates on workerUrl)
    assert "TIER_LIVE.workerUrl" in html
    # ticker pages fetch the contract RELATIVE to t/ (P10-5 path fix)
    from forecasting_lab.dashboard.tier_live import tier_live_js

    assert "'../contract.json'" in tier_live_js("https://x.workers.dev", "../contract.json")
