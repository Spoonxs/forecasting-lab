"""CLI: maintain the public forecasting log (the calibration track record).

Examples::

    python -m forecasting_lab.cli.calibration record --question "Fed cuts in March?" --prob 0.35 --venue Kalshi
    python -m forecasting_lab.cli.calibration resolve --id 1 --outcome 0
    python -m forecasting_lab.cli.calibration score
    python -m forecasting_lab.cli.calibration show
"""

from __future__ import annotations

import argparse

from ..calibration_log import ForecastLog


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=None, help="log CSV path (default: calibration_log.csv at repo root)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="log a new forecast")
    rec.add_argument("--question", required=True)
    rec.add_argument("--prob", type=float, required=True)
    rec.add_argument("--venue", default="")
    rec.add_argument("--notes", default="")

    res = sub.add_parser("resolve", help="set the realized outcome (0/1)")
    res.add_argument("--id", type=int, required=True)
    res.add_argument("--outcome", type=int, choices=[0, 1], required=True)

    sub.add_parser("score", help="Brier / log loss / calibration over resolved forecasts")
    sub.add_parser("resolve-open", help="auto-resolve open forecasts from venue settlement")
    sub.add_parser("beat", help="beat-the-closing-line: your Brier vs the market's")
    sub.add_parser("show", help="print the whole log")

    args = ap.parse_args(argv)
    log = ForecastLog(args.path)

    if args.cmd == "record":
        fid = log.record(args.question, args.prob, venue=args.venue, notes=args.notes)
        print(f"Recorded forecast #{fid}: P={args.prob:.3f} - {args.question}")
    elif args.cmd == "resolve":
        log.resolve(args.id, args.outcome)
        print(f"Resolved forecast #{args.id} -> outcome {args.outcome}")
    elif args.cmd == "score":
        try:
            s = log.score()
        except ValueError as e:
            print(e)
            return 1
        print(f"Resolved forecasts: {s['n']}")
        print(f"  Brier score        {s['brier']:.4f}")
        print(f"  Brier skill score  {s['brier_skill_score']:+.4f}")
        print(f"  Log loss           {s['log_loss']:.4f}")
        print(f"  ECE                {s['ece']:.4f}")
    elif args.cmd == "resolve-open":
        from ..calibration_log import venue_resolver

        n = log.resolve_open(venue_resolver)
        print(f"Auto-resolved {n} forecast(s) from venue settlement.")
    elif args.cmd == "beat":
        b = log.beat_market_score()
        if not b.get("n"):
            print("No resolved forecasts with a recorded market price yet.")
            return 0
        print(f"Beat-the-closing-line over {b['n']} resolved forecasts:")
        print(f"  Your Brier         {b['model_brier']:.4f}")
        print(f"  Market Brier       {b['market_brier']:.4f}")
        print(f"  Skill vs market    {b['brier_skill_vs_market']:+.4f}   (>0 = edge over the price)")
        print(f"  Beat rate          {b['beat_rate']:.1%}")
    elif args.cmd == "show":
        df = log.to_frame()
        print(df.to_string(index=False) if len(df) else "Log is empty.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
