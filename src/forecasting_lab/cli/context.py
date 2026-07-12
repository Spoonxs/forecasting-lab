"""CLI: flab-context — file the 13F + congress context digests (P7).

Best-effort by design: blocked feeds are stated skips, every datum carries
its staleness, and nothing here enters a verdict. Examples::

    python -m forecasting_lab.cli.context           # both sweeps
    python -m forecasting_lab.cli.context --skip-13f
"""

from __future__ import annotations

import argparse


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-13f", action="store_true")
    ap.add_argument("--skip-congress", action="store_true")
    args = ap.parse_args(argv)

    from ..pipeline.digest import write_dated_data

    if not args.skip_13f:
        from ..sources.store import TidyStore
        from ..sources.thirteenf import fetch_13f_digest

        d13 = fetch_13f_digest(store=TidyStore())
        path = write_dated_data("thirteenf", d13)
        print(f"13F: {len(d13['managers'])} manager(s), {len(d13['skips'])} skip(s) "
              f"-> {path.name}")
        for s in d13["skips"]:
            print(f"  skip {s['manager']}: {s['reason']}")

    if not args.skip_congress:
        from ..sources.congress import fetch_congress_digest

        dcg = fetch_congress_digest()
        path = write_dated_data("congress", dcg)
        print(f"congress: {len(dcg['trades'])} trade(s) in window, "
              f"{len(dcg['skips'])} skip(s) -> {path.name}")
        for s in dcg["skips"]:
            print(f"  skip {s['chamber']}: {s['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
