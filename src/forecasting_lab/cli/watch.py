"""CLI: watch key figures/outlets and file a media digest (tickers + themes).

Examples::

    python -m forecasting_lab.cli.watch            # sweep the watch list -> inputs/
    python -m forecasting_lab.cli.watch --top 15
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args(argv)

    from requests import RequestException

    from ..media.watch import MediaWatchPipeline

    pipe = MediaWatchPipeline(top=args.top)
    try:
        path = pipe.run(out_dir=None if args.out is None else Path(args.out))
    except RequestException as exc:
        print(f"Media sweep failed ({exc}).")
        return 1
    print(f"Wrote digest to {path}")
    if getattr(pipe, "buzz", None):
        top = sorted(pipe.buzz.items(), key=lambda kv: kv[1], reverse=True)[:8]
        print("Most-named tickers:", ", ".join(f"{t}({c})" for t, c in top))
    else:
        print("No media reachable here (works in the cloud).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
