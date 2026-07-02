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
from ..dashboard import collect_lab_state, render_dashboard


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
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
