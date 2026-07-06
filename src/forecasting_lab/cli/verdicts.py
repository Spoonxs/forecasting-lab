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
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
