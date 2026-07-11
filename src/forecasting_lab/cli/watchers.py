"""CLI: run the watcher templates and file the dated feed (P6d).

Deterministic templates over public data (the store, the verdict artifacts,
the macro sidecars). Missing sources are honest, stated skips. Examples::

    python -m forecasting_lab.cli.watchers          # run + file the feed
    python -m forecasting_lab.cli.watchers --dry    # print, write nothing
"""

from __future__ import annotations

import argparse


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true", help="print events, write no feed")
    args = ap.parse_args(argv)

    from ..pipeline.watchers import run_watchers, write_watchers_feed

    result = run_watchers()
    for ev in result["events"]:
        print(f"[{ev['date']}] {ev['kind']}: {ev['reason']} (audit {ev['sha256'][:12]})")
    for sk in result["skips"]:
        print(f"skip {sk['kind']}: {sk['reason']}")
    if not result["events"]:
        print("no watcher events today")
    if not args.dry:
        path = write_watchers_feed(result)
        print(f"feed -> {path.name}" if path else "no dated events — no feed written")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
