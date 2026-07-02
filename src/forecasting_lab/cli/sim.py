"""CLI: the strategy arena — advance the persistent sim and print the leaderboard.

Each ``run`` continues from saved state (the sim is "always running"; you feed it
bars when you check in). Examples::

    python -m forecasting_lab.cli.sim run --bars 250      # advance ~a trading year
    python -m forecasting_lab.cli.sim run --bars 250      # continues where it left off
    python -m forecasting_lab.cli.sim status              # leaderboard without advancing
    python -m forecasting_lab.cli.sim reset               # start the arena over
    python -m forecasting_lab.cli.sim run --real NVDA MU SOXL META --bars 200
"""

from __future__ import annotations

import argparse

from ..sim.engine import Arena


def _print_board(arena: Arena) -> None:
    board = arena.leaderboard()
    if board["bars"].max() == 0:
        print("No bars simulated yet. Run: flab-sim run --bars 250")
        return
    print(f"\nArena leaderboard after {int(board['bars'].max())} bars (costs 10bps/turnover):")
    print(board.round(3).to_string())
    best = board.index[0]
    print(f"\nCurrent leader: {best}")
    print("Baselines (buy_hold, random) are in the table - beating the market, not just moving, is the bar.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="advance the sim")
    run.add_argument("--bars", type=int, default=250)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--cost-bps", type=float, default=10.0)
    run.add_argument("--real", nargs="*", default=None, metavar="SYMBOL",
                     help="use real Yahoo daily history for these symbols (non-persistent)")

    status = sub.add_parser("status", help="print the leaderboard without advancing")
    status.add_argument("--seed", type=int, default=0)

    sub.add_parser("reset", help="delete saved state")

    args = ap.parse_args(argv)

    if args.cmd == "reset":
        Arena().reset()
        print("Arena state cleared.")
        return 0

    if args.cmd == "status":
        arena = Arena(seed=args.seed)
        arena.load()
        _print_board(arena)
        return 0

    # run
    if args.real:
        from requests import RequestException

        from ..sim.data import real_market

        try:
            prices = real_market(args.real)
        except (RequestException, RuntimeError) as exc:
            print(f"Real-data fetch failed ({exc}). Falling back needs --real omitted.")
            return 1
        arena = Arena(prices=prices, cost_bps=args.cost_bps, warmup=min(130, len(prices) // 3),
                      state_path=None)
        ran = arena.run(args.bars)
        print(f"Simulated {ran} bars on real history for {list(prices.columns)}.")
        _print_board(arena)
        return 0

    arena = Arena(seed=args.seed, cost_bps=args.cost_bps)
    resumed = arena.load()
    ran = arena.run(args.bars)
    arena.save()
    print(f"{'Resumed and advanced' if resumed else 'Started arena;'} {ran} bars "
          f"(cursor now at bar {arena.bar}/{len(arena.prices)}).")
    _print_board(arena)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
