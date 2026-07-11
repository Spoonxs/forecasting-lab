"""CLI: build the TIER FULL verdict artifacts (P6a).

Renders the nightly recommendation artifacts: per-symbol verdicts across the
profile matrix, the machine-readable scoring contract, and the AI opinion
files (Claude deterministic; Codex via the local CLI when available, else the
last committed artifact keeps rendering with its date). Examples::

    python -m forecasting_lab.cli.verdicts               # full tier
    python -m forecasting_lab.cli.verdicts --limit 50    # quick pass
    python -m forecasting_lab.cli.verdicts --no-codex    # skip the codex call
"""

from __future__ import annotations

import argparse
import shutil
import subprocess


def _codex_runner(prompt: str) -> str:
    exe = shutil.which("codex")
    if not exe:
        raise RuntimeError("codex CLI not on PATH")
    proc = subprocess.run(  # noqa: S603 - fixed executable, prompt via stdin
        [exe, "exec", "--sandbox", "read-only", "-"],
        input=prompt, capture_output=True, text=True, timeout=600, check=False,
    )
    return proc.stdout or ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None, help="cap the symbol count (debug)")
    ap.add_argument("--no-codex", action="store_true", help="skip the codex opinion call")
    args = ap.parse_args(argv)

    from ..pipeline.verdicts import (
        build_verdicts,
        codex_opinion,
        tier_full_symbols,
        verify_contract_roundtrip,
        write_claude_opinion,
        write_verdicts,
    )
    from ..sources.instruments import hysa_yield_pct

    symbols = tier_full_symbols()
    if args.limit:
        symbols = symbols[: args.limit]
    payload = build_verdicts(symbols, hysa_yield_pct=hysa_yield_pct())
    path, sha = write_verdicts(payload)
    print(f"verdicts -> {path.name} ({payload['n_symbols']} symbols, audit {sha[:12]})")
    if not verify_contract_roundtrip():  # unconditional — assert dies under -O (Codex review)
        raise RuntimeError("contract.json does not match the engine export — refusing to ship")
    print("contract.json verified against the live engine export")

    claude_path = write_claude_opinion(payload)
    print(f"claude opinion -> {claude_path.name}")

    from ..dashboard.tier_live import emit_worker_allowlist

    allow_path = emit_worker_allowlist()
    print(f"worker allowlist -> {allow_path}")
    codex = codex_opinion(payload, runner=None if args.no_codex else _codex_runner)
    state = "fresh" if not codex.get("stale") else f"stale (as of {codex.get('as_of')})"
    print(f"codex opinion: {state}")

    # the arena: Codex's book refreshes when the CLI is available; otherwise the
    # committed book keeps racing with its original date
    from ..agent_trader.arena_books import codex_book

    book = codex_book(payload, runner=None if args.no_codex else _codex_runner)
    print(f"codex book: {'dated ' + book['as_of'] if book else 'open slot (none committed yet)'}")

    # the regret ledger: record today's attractive verdicts, resolve elapsed
    # horizons — only with SAME-DAY closes; stale sidecar prices never
    # masquerade as today's marks (honest skip, stated)
    from ..calibration_log.regret import RegretLedger
    from ..dashboard.arena_page import sidecar_prices

    prices, px_date = sidecar_prices()
    if prices and px_date:
        ledger = RegretLedger()
        out = ledger.update_from_build(payload, prices, px_date, spy_price=prices.get("SPY"))
        ledger.save()
        note = "" if px_date == payload["as_of"] else f" (closes dated {px_date} — no new entries)"
        print(f"regret ledger: +{len(out['opened'])} tracked, "
              f"{len(out['resolved'])} horizons resolved{note}")
    else:
        print("regret ledger: no closes in the trending sidecar — nothing recorded (honest skip)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
