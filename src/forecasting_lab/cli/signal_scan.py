"""CLI: compute squeeze + momentum composites and file a dated signal digest.

Examples::

    python -m forecasting_lab.cli.signal_scan --demo
    python -m forecasting_lab.cli.signal_scan --csv my_features.csv --top 15
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ..signals import flag_candidates, momentum_composite, squeeze_composite
from ..signals.digest import write_signal_digest


def _demo_frame(n: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "ticker": [f"TKR{i:02d}" for i in range(n)],
            "short_pct_float": rng.uniform(0, 40, n),
            "days_to_cover": rng.uniform(0.5, 12, n),
            "social_velocity_z": rng.normal(0, 2, n),
            "volume_spike": rng.uniform(0.5, 9, n),
            "call_put_ratio": rng.uniform(0.3, 5, n),
            "borrow_fee": rng.uniform(0, 120, n),
            "earnings_accel": rng.normal(0, 1, n),
            "analyst_revision": rng.normal(0, 1, n),
            "rel_strength": rng.uniform(0, 100, n),
            "pct_from_52w_high": -rng.uniform(0, 50, n),
            "rev_growth": rng.uniform(-20, 80, n),
        }
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", type=str, help="CSV of per-ticker features (one row per ticker)")
    src.add_argument("--demo", action="store_true", help="use a generated demo universe")
    ap.add_argument("--ticker-col", default="ticker")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--threshold", type=float, default=0.9, help="flag percentile (top decile = 0.9)")
    ap.add_argument("--out", type=str, default=None, help="output dir (default: inputs/)")
    args = ap.parse_args(argv)

    df = _demo_frame() if args.demo else pd.read_csv(args.csv)
    sq = squeeze_composite(df)
    mo = momentum_composite(df)

    print("Top squeeze candidates:")
    print(flag_candidates(sq, "squeeze", args.threshold)[[args.ticker_col, "squeeze"]].head(args.top).to_string(index=False))
    print("\nTop momentum candidates:")
    print(flag_candidates(mo, "momentum", args.threshold)[[args.ticker_col, "momentum"]].head(args.top).to_string(index=False))

    out_dir = None if args.out is None else __import__("pathlib").Path(args.out)
    path = write_signal_digest(sq, mo, ticker_col=args.ticker_col, top=args.top, out_dir=out_dir)
    print(f"\nWrote digest to {path}")
    print("Reminder: surfaces candidates, not buys. Not financial advice.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
