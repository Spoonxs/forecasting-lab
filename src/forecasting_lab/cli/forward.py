"""CLI: the forward paper-trading study on a real high-attention basket.

Each ``run`` pulls fresh real prices, marks the prior snapshot to market, and
records today's picks — so the study grows one honest out-of-sample mark per run.
Seed it once with ``--backfill``. Examples::

    python -m forecasting_lab.cli.forward run --backfill   # first time: seed + step
    python -m forecasting_lab.cli.forward run              # thereafter: one live mark
    python -m forecasting_lab.cli.forward status
"""

from __future__ import annotations

import argparse


def _print_board(ledger) -> None:
    board = ledger.leaderboard()
    if board.empty:
        print("No forward study yet. Run: flab-forward run --backfill")
        return
    live_from = ledger.live_started()
    print("\nForward study - real basket, marked to market (costs 10bps/turnover):")
    print(board.round(3).to_string(index=False))
    if live_from:
        print(f"\nLive out-of-sample marks began {live_from}. Everything before is backfill context.")
    else:
        print("\nAll marks are backfill so far - the live study begins on the next scheduled run.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="pull prices, mark to market, record today's picks")
    run.add_argument("--backfill", action="store_true", help="seed a curve from recent real history first")
    run.add_argument("--range", default="1y", help="history window to pull")
    sub.add_parser("status", help="print the study without stepping")
    args = ap.parse_args(argv)

    from ..forwardtest import ForwardLedger

    ledger = ForwardLedger()
    if args.cmd == "status":
        _print_board(ledger)
        return 0

    from requests import RequestException

    from ..forwardtest import THEME_BASKET
    from ..sim.data import real_market

    try:
        prices = real_market(THEME_BASKET, range_=args.range)
    except (RequestException, RuntimeError) as exc:
        print(f"Real-price fetch failed ({exc}). The forward study needs live prices.")
        return 1

    on_date = str(prices.index[-1])[:10]
    if args.backfill:
        n = ledger.backfill(prices)
        print(f"Backfilled {n} steps from real history.")
    ledger.step(prices, on_date=on_date, phase="live")
    ledger.save()
    print(f"Recorded a live mark for {on_date}.")
    _print_board(ledger)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
