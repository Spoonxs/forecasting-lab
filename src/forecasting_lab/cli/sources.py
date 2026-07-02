"""CLI: report the tracked-source coverage (proves the 500+ promise).

Examples::

    python -m forecasting_lab.cli.sources
    python -m forecasting_lab.cli.sources --refresh   # re-pull the live S&P 500 list
"""

from __future__ import annotations

import argparse

from ..sources.registry import source_count, source_table


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="re-pull the live S&P 500 constituents")
    args = ap.parse_args(argv)

    table = source_table(refresh=args.refresh)
    total = source_count(refresh=args.refresh)
    print(table.to_string(index=False))
    print(f"\nTotal sources tracked simultaneously: {total}")
    print(f"{'MEETS' if total >= 500 else 'BELOW'} the 500-source floor.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
