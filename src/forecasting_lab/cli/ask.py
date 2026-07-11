"""CLI: flab-ask — the local desk chat (P7).

Deterministic answers from the committed artifacts, with receipts::

    flab-ask "what's the verdict on NVDA"
    flab-ask "what changed today"
    flab-ask --llm "how's the arena going"   # codex rephrases; facts unchanged
"""

from __future__ import annotations

import argparse


def _codex_runner(prompt: str) -> str:
    import shutil
    import subprocess

    exe = shutil.which("codex")
    if not exe:
        raise RuntimeError("codex CLI not on PATH")
    proc = subprocess.run(  # noqa: S603 - fixed executable, prompt via stdin
        [exe, "exec", "--sandbox", "read-only", "-"],
        input=prompt, capture_output=True, text=True, timeout=300, check=False,
    )
    return proc.stdout or ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="+", help="the question, in plain words")
    ap.add_argument("--llm", action="store_true",
                    help="let the local codex CLI reword the answer (facts unchanged)")
    args = ap.parse_args(argv)

    from ..desk import ask
    from ..desk.ask import rephrase_with_llm

    answer = ask(" ".join(args.question))
    print(rephrase_with_llm(answer, _codex_runner) if args.llm else answer.render())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
