"""CLI: scan today's trending stocks for NVIDIA/GME-shaped setups and file a digest.

Examples::

    python -m forecasting_lab.cli.trending            # live scan -> inputs/
    python -m forecasting_lab.cli.trending --count 20 --top 8 --out somewhere/
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=15, help="trending tickers to pull")
    ap.add_argument("--top", type=int, default=5, help="candidates per composite in the digest")
    ap.add_argument("--news-hours", type=int, default=48)
    ap.add_argument("--out", type=str, default=None, help="output dir (default: inputs/)")
    args = ap.parse_args(argv)

    from requests import RequestException

    from ..signals.trending import TrendingStocksPipeline

    pipe = TrendingStocksPipeline(count=args.count, top=args.top, news_hours=args.news_hours)
    try:
        path = pipe.run(out_dir=None if args.out is None else Path(args.out))
    except RequestException as exc:
        print(f"Live fetch failed ({exc}). Check network and retry.")
        return 1
    print(f"Wrote digest to {path}")
    print("Candidates, not buys. Not financial advice.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
