"""CLI: the fast intraday refresh — the market-hours heartbeat.

Runs only the cheap, fast-moving jobs (auto-resolve settled forecasts, trending
stocks, live prediction-market odds, macro) and rebuilds the dashboard, so an
open page picks up fresh numbers within minutes. The slow/heavy jobs (arXiv
research, media watch, the arena, the forward study) stay on the once-a-day
``flab-run-all`` schedule — no need to redo them every 30 minutes.

    flab-intraday                 # refresh movers + odds + macro, rebuild dashboard
    flab-intraday --alert         # also send the alert if anything is flagged
"""

from __future__ import annotations

import argparse

FAST_JOBS = ["resolve", "trending", "divergence", "macro", "dashboard"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alert", action="store_true", help="also send an alert when something is flagged")
    args = ap.parse_args(argv)

    from .run_all import main as run_all_main

    jobs = list(FAST_JOBS)
    if args.alert:
        jobs.append("alert")
    # smaller pulls than the daily run so the refresh stays quick
    return run_all_main(["--only", *jobs, "--trending-count", "20", "--divergence-limit", "300"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
