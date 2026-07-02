"""CLI: sweep recent quant papers from arXiv and file a ranked digest.

Examples::

    python -m forecasting_lab.cli.research                  # -> inputs/
    python -m forecasting_lab.cli.research --top 15 --max-results 100
    python -m forecasting_lab.cli.research --categories q-fin.TR stat.ML
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categories", nargs="*", default=None, help="arXiv categories to sweep")
    ap.add_argument("--max-results", type=int, default=60)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", type=str, default=None, help="output dir (default: inputs/)")
    args = ap.parse_args(argv)

    from requests import RequestException

    from ..pipeline.research import ResearchPipeline

    pipe = ResearchPipeline(categories=args.categories, max_results=args.max_results, top=args.top)
    try:
        path = pipe.run(out_dir=None if args.out is None else Path(args.out))
    except RequestException as exc:
        print(f"arXiv fetch failed ({exc}). Check network and retry.")
        return 1
    print(f"Wrote digest to {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
