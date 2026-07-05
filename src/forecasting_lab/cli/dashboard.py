"""CLI: build the lab dashboard (a single static HTML file).

Examples::

    python -m forecasting_lab.cli.dashboard              # -> site/index.html
    python -m forecasting_lab.cli.dashboard --open       # build and open in browser
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from ..config import PATHS
from ..dashboard import collect_lab_state, render_dashboard, render_scorecard


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=str, default=None, help="output path (default: site/index.html)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--open", action="store_true", help="open the page in a browser")
    args = ap.parse_args(argv)

    out = Path(args.out) if args.out else PATHS.root / "site" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    state = collect_lab_state(seed=args.seed)
    out.write_text(render_dashboard(state), encoding="utf-8")
    print(f"Dashboard written to {out}")

    # the public Brier scorecard page (honest denominator, miss ledger pinned)
    scorecard = out.parent / "scorecard.html"
    scorecard.write_text(render_scorecard(state), encoding="utf-8")
    print(f"Scorecard written to {scorecard}")

    # also render the dark, agentic Agent Terminal alongside it
    from ..agent_trader.terminal import render_terminal

    terminal = out.parent / "agent.html"
    terminal.write_text(render_terminal(state), encoding="utf-8")
    print(f"Agent terminal written to {terminal}")

    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
