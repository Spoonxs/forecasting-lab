"""CLI: score cross-venue (Kalshi vs Polymarket) price divergence and file a digest.

Three modes::

    python -m forecasting_lab.cli.market_divergence --live               # fetch both venues, auto-match
    python -m forecasting_lab.cli.market_divergence --demo               # built-in sample
    python -m forecasting_lab.cli.market_divergence --csv matched.csv    # your own matched pairs

``--live`` runs the full :class:`~forecasting_lab.markets.monitor.DivergencePipeline`
(fetch -> title-match -> score after fees -> dated digest). Auto-matched titles
are candidates — verify resolution criteria before believing any gap. With
``--csv``, supply columns ``event, kalshi_yes, poly_yes`` (YES probs in [0, 1]).
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from ..markets.divergence import find_divergences
from ..pipeline.digest import render_digest, write_dated_note


def _demo_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event": ["Fed cuts in March", "Election turnout > 60%", "Team X wins title", "CPI > 3%"],
            "kalshi_yes": [0.40, 0.50, 0.61, 0.22],
            "poly_yes": [0.46, 0.505, 0.60, 0.30],
        }
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", type=str, help="matched markets CSV (event, kalshi_yes, poly_yes)")
    src.add_argument("--demo", action="store_true", help="use a built-in sample of matched markets")
    src.add_argument("--live", action="store_true", help="fetch both venues and auto-match titles")
    ap.add_argument("--threshold", type=float, default=0.0, help="minimum net edge to flag (dollars/contract)")
    ap.add_argument("--contracts", type=float, default=1.0)
    ap.add_argument("--match-threshold", type=float, default=0.5, help="title-similarity floor for --live")
    ap.add_argument("--limit", type=int, default=200, help="markets per venue for --live")
    ap.add_argument("--out", type=str, default=None, help="output dir (default: inputs/)")
    args = ap.parse_args(argv)

    if args.live:
        from requests import RequestException

        from ..markets.monitor import DivergencePipeline

        pipe = DivergencePipeline(
            match_threshold=args.match_threshold,
            edge_threshold=args.threshold,
            limit=args.limit,
        )
        try:
            path = pipe.run(out_dir=None if args.out is None else Path(args.out))
        except RequestException as exc:
            print(f"Live fetch failed ({exc}). Try --demo, or --csv with your own pairs.")
            return 1
        print(f"Wrote digest to {path}")
        print("Auto-matched titles are candidates - verify resolution criteria. Not financial advice.")
        return 0

    matched = _demo_frame() if args.demo else pd.read_csv(args.csv)
    flags = find_divergences(matched, contracts=args.contracts, threshold=args.threshold)

    if flags.empty:
        print("No after-fee divergences cleared the threshold.")
        body = "No after-fee divergences cleared the threshold today."
    else:
        print(flags.to_string(index=False))
        table = ["| " + " | ".join(flags.columns) + " |", "| " + " | ".join(["---"] * len(flags.columns)) + " |"]
        for _, r in flags.iterrows():
            table.append("| " + " | ".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in r) + " |")
        body = "\n".join(table)

    digest = render_digest(
        "Cross-Venue Divergence Digest",
        {"Flagged markets (net of fees)": body},
        on=date.today(),
        disclaimer=(
            "Verify both contracts resolve on identical criteria before believing any 'arb'. "
            "Not financial advice."
        ),
    )
    out_dir = None if args.out is None else Path(args.out)
    path = write_dated_note("market-divergence", digest, out_dir=out_dir)
    print(f"\nWrote digest to {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
