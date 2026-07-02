"""CLI: fit a time-forward Elo model (tennis or basketball) and score its calibration.

Examples::

    python -m forecasting_lab.cli.elo_backtest --synthetic
    python -m forecasting_lab.cli.elo_backtest --years 2021 2022 2023 --tour atp
    python -m forecasting_lab.cli.elo_backtest --sport nba --synthetic
    python -m forecasting_lab.cli.elo_backtest --synthetic --simulate P030 P033 P015 P001
"""

from __future__ import annotations

import argparse

import numpy as np

from ..eval import summary
from ..eval.metrics import brier_score
from ..sports.elo import EloModel
from ..sports.simulate import simulate_tournament
from ..sports.tennis_data import load_matches, synthetic_matches


def _run_nba(args) -> int:
    """Fit + score the basketball Elo (synthetic season; real loaders welcome)."""
    from ..sports.basketball import BasketballElo, synthetic_season

    if not args.synthetic:
        print("NBA mode currently uses the synthetic season generator (pass --synthetic to silence this).\n")
    games = synthetic_season(seed=0)
    print(f"Loaded {len(games):,} games across {games['season'].nunique()} seasons.")

    model = BasketballElo(k_factor=args.k or 20.0)
    preds = model.fit(games)
    ev = preds[preds["min_games"] >= args.min_matches]
    y, p = ev["y"].to_numpy(), ev["p_home"].to_numpy()
    s = summary(y, p)
    base_brier = brier_score(y, np.full_like(p, float(np.mean(y))))

    print(f"\nEvaluated on {s['n']:,} games (min_games >= {args.min_matches}, K={args.k or 20}, home adv {model.home_advantage:.0f} Elo):")
    print(f"  Home base rate     {s['base_rate']:.4f}   (the baseline to beat)")
    print(f"  Brier score        {s['brier']:.4f}   (base-rate baseline {base_brier:.4f})")
    print(f"  Brier skill score  {s['brier_skill_score']:+.4f}   (>0 beats climatology)")
    print(f"  Log loss           {s['log_loss']:.4f}")
    print(f"  ECE                {s['ece']:.4f}   (calibration error; lower better)")

    if args.plot:
        from ..eval.calibration import plot_calibration

        plot_calibration(y, p, title=f"NBA Elo (Brier={s['brier']:.3f})", save_path=args.plot)
        print(f"\nSaved reliability diagram to {args.plot}")

    print("\nTop teams:")
    for _, row in model.leaderboard(8).iterrows():
        print(f"  {row['team']:<10} {row['rating']:.0f}")
    return 0


def _run_soccer(args) -> int:
    """Fit + score the soccer Elo (Davidson draw model) on a synthetic league."""
    from ..sports.soccer import SoccerElo, evaluate_rps, synthetic_league

    league = synthetic_league(seed=0)
    print(f"Loaded {len(league):,} matches across {league['season'].nunique()} seasons.")
    model = SoccerElo(k_factor=args.k or 20.0)
    preds = model.fit(league)
    ev = preds[preds["min_games"] >= args.min_matches]
    r = evaluate_rps(ev)
    br = r["base_rates"]
    print(f"\nEvaluated on {r['n']:,} matches (3-outcome, Davidson draw model, K={args.k or 20}):")
    print(f"  Outcome mix        home {br['home']:.2f} / draw {br['draw']:.2f} / away {br['away']:.2f}")
    print(f"  Ranked prob score  {r['rps']:.4f}   (base-rate baseline {r['rps_baseline']:.4f})")
    print(f"  RPS skill          {r['rps_skill']:+.4f}   (>0 beats climatology)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sport", default="tennis", choices=["tennis", "nba", "soccer"])
    ap.add_argument("--years", nargs="*", type=int, help="Sackmann seasons, e.g. 2021 2022 2023")
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--synthetic", action="store_true", help="use generated data (no network)")
    ap.add_argument("--surface-weight", type=float, default=0.5)
    ap.add_argument("--k", type=float, default=None, help="constant K-factor (default: 538 decaying)")
    ap.add_argument("--min-matches", type=int, default=10, help="burn-in filter for evaluation")
    ap.add_argument("--plot", type=str, default=None, help="path to save a reliability diagram (PNG)")
    ap.add_argument("--simulate", nargs="*", help="player names for a Monte Carlo bracket (power of 2)")
    ap.add_argument("--sims", type=int, default=10_000)
    args = ap.parse_args(argv)

    if args.sport == "nba":
        return _run_nba(args)
    if args.sport == "soccer":
        return _run_soccer(args)

    if args.synthetic or not args.years:
        if not args.synthetic:
            print("No --years given; using synthetic data. Pass --years 2022 2023 for real Sackmann data.\n")
        matches = synthetic_matches(seed=0)
    else:
        try:
            matches = load_matches(args.years, tour=args.tour)
        except RuntimeError as exc:
            print(exc)
            print("\nTip: run with --synthetic to use generated data offline.")
            return 1
    print(f"Loaded {len(matches):,} matches.")

    elo = EloModel(surface_weight=args.surface_weight, k_factor=args.k)
    preds = elo.fit(matches)
    ev = preds[preds["min_matches"] >= args.min_matches]
    y, p = ev["y"].to_numpy(), ev["p_a"].to_numpy()
    s = summary(y, p)

    base_rate = float(np.mean(y))
    base_brier = brier_score(y, np.full_like(p, base_rate))

    print(f"\nEvaluated on {s['n']:,} matches (min_matches >= {args.min_matches}, surface_weight={args.surface_weight}, K={args.k or '538'}):")
    print(f"  Brier score        {s['brier']:.4f}   (base-rate baseline {base_brier:.4f})")
    print(f"  Brier skill score  {s['brier_skill_score']:+.4f}   (>0 beats climatology)")
    print(f"  Log loss           {s['log_loss']:.4f}")
    print(f"  ECE                {s['ece']:.4f}   (calibration error; lower better)")
    print(f"  Accuracy @ 0.5     {s['accuracy_at_0.5']:.4f}   (context only - favorites win a lot)")

    if args.plot:
        from ..eval.calibration import plot_calibration

        fig = plot_calibration(y, p, title=f"Tennis Elo (Brier={s['brier']:.3f})", save_path=args.plot)
        print(f"\nSaved reliability diagram to {args.plot}")
        del fig

    if args.simulate:
        print(f"\nMonte Carlo bracket ({args.sims:,} sims):")
        sim = simulate_tournament(elo, args.simulate, surface="Hard", n_sims=args.sims)
        for player, row in sim.iterrows():
            print(f"  {player:<24} title {row['p_title']:.3f}   final {row['p_final']:.3f}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
