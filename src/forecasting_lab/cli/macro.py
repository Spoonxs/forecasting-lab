"""CLI: live macro nowcast from FRED (yield-curve recession probability + levels).

Examples::

    python -m forecasting_lab.cli.macro            # print the snapshot
    python -m forecasting_lab.cli.macro --digest   # also file a dated note into inputs/
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--digest", action="store_true", help="write a dated macro digest into inputs/")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args(argv)

    from requests import RequestException

    from ..macro import macro_snapshot

    try:
        snap = macro_snapshot()
    except RequestException as exc:
        print(f"FRED fetch failed ({exc}).")
        return 1

    ts = snap["term_spread"]
    print(f"10Y-3M term spread: {ts['value']} pts (as of {ts['date']})")
    prob = snap["recession_prob_12m"]
    print(f"12-month recession probability: {prob:.1%}" if prob is not None else "recession prob: n/a")
    print("\nLevels:")
    for label, v in snap["levels"].items():
        print(f"  {label:<16} {v['value']} ({v['date']})")

    if args.digest:
        from ..pipeline.digest import render_digest, write_dated_note

        lines = [f"- **12-month recession probability**: {prob:.1%} (from 10Y-3M spread {ts['value']} pts)"]
        for label, v in snap["levels"].items():
            lines.append(f"- {label}: {v['value']} ({v['date']})")
        body = render_digest(
            "Macro Nowcast",
            {"Yield-curve recession model": "\n".join(lines)},
            disclaimer="Estrella-Mishkin probit on the term spread; a model, not a forecast of certainty. Not financial advice.",
        )
        path = write_dated_note("macro-nowcast", body, out_dir=None if args.out is None else Path(args.out))
        print(f"\nWrote digest to {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
