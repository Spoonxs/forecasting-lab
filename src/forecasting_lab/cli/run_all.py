"""CLI: the orchestrator — run every pipeline, then rebuild the dashboard.

This is what the scheduler calls. Each job is isolated: one failing (network
blip, blocked venue) logs and is skipped, the rest still run, and the dashboard
always rebuilds from whatever landed. Examples::

    python -m forecasting_lab.cli.run_all                 # everything
    python -m forecasting_lab.cli.run_all --only research macro
    python -m forecasting_lab.cli.run_all --skip trending # e.g. skip the slow one
"""

from __future__ import annotations

import argparse
import traceback

JOBS = ("resolve", "research", "media", "trending", "divergence", "macro", "sim", "forward",
        "verdicts", "dashboard", "alert")


def _job_resolve():
    from ..calibration_log import ForecastLog, venue_resolver

    n = ForecastLog().resolve_open(venue_resolver)
    return f"auto-resolved {n} forecast(s) from venue settlement"


def _job_research():
    from ..pipeline.research import ResearchPipeline

    path = ResearchPipeline().run()
    return f"research digest -> {path.name}"


def _job_media():
    from ..media.watch import MediaWatchPipeline

    path = MediaWatchPipeline().run()
    return f"media digest -> {path.name}"


def _job_trending(count: int):
    from ..signals.trending import TrendingStocksPipeline

    path = TrendingStocksPipeline(count=count).run()
    return f"trending digest -> {path.name}"


def _job_divergence(limit: int):
    from ..markets.monitor import DivergencePipeline

    path = DivergencePipeline(limit=limit).run()
    return f"divergence digest -> {path.name}"


def _job_macro():
    from ..cli.macro import main as macro_main

    macro_main(["--digest"])
    return "macro digest filed"


def _job_sim(bars: int):
    from ..sim.engine import Arena

    arena = Arena()
    arena.load()
    ran = arena.run(bars)
    arena.save()
    return f"arena advanced {ran} bars (now at {arena.bar})"


def _job_forward():
    from ..forwardtest import THEME_BASKET, ForwardLedger
    from ..sim.data import real_market

    prices = real_market(THEME_BASKET)
    ledger = ForwardLedger()
    ledger.backfill(prices)  # no-op after the first run
    ledger.step(prices, on_date=str(prices.index[-1])[:10], phase="live")
    ledger.save()
    board = ledger.leaderboard()
    leader = board.iloc[0]["strategy"] if not board.empty else "n/a"
    return f"forward study marked ({int(board['live_marks'].max()) if not board.empty else 0} live marks; leader {leader})"


def _job_verdicts():
    # verdicts run AFTER trending/macro so the provider sees today's sidecars;
    # codex is skipped in unattended runs (zero-key decision — the last
    # committed opinion renders with its date)
    from ..cli.verdicts import main as verdicts_main

    verdicts_main(["--no-codex"])
    return "verdict artifacts rebuilt -> data/verdicts/"


def _job_dashboard():
    from ..cli.dashboard import main as dash_main

    dash_main([])
    return "dashboard rebuilt -> site/index.html"


def _job_alert():
    from ..alerts import build_alert, send

    title, message, fields = build_alert()
    delivered = send(message, title=title, fields=fields)
    return f"alert delivered to {', '.join(delivered)}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", choices=JOBS, help="run only these jobs")
    ap.add_argument("--skip", nargs="*", choices=JOBS, default=[], help="skip these jobs")
    ap.add_argument("--trending-count", type=int, default=25)
    ap.add_argument("--divergence-limit", type=int, default=800)
    ap.add_argument("--sim-bars", type=int, default=25)
    args = ap.parse_args(argv)

    jobs = list(args.only) if args.only else list(JOBS)
    jobs = [j for j in jobs if j not in args.skip]
    # dashboard then alert run last: dashboard reflects the data jobs, alert
    # summarizes what flagged after everything has landed.
    tail = [j for j in ("dashboard", "alert") if j in jobs]
    jobs = [j for j in jobs if j not in ("dashboard", "alert")] + tail

    runners = {
        "resolve": _job_resolve,
        "research": _job_research,
        "media": _job_media,
        "trending": lambda: _job_trending(args.trending_count),
        "divergence": lambda: _job_divergence(args.divergence_limit),
        "macro": _job_macro,
        "sim": lambda: _job_sim(args.sim_bars),
        "forward": _job_forward,
        "verdicts": _job_verdicts,
        "dashboard": _job_dashboard,
        "alert": _job_alert,
    }

    ok, failed = [], []
    for job in jobs:
        try:
            msg = runners[job]()
            print(f"[ok]   {job}: {msg}")
            ok.append(job)
        except Exception as exc:  # noqa: BLE001 - a job failure must not sink the run
            print(f"[skip] {job}: {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=1)
            failed.append(job)

    print(f"\nDone. {len(ok)} ok, {len(failed)} skipped" + (f" ({', '.join(failed)})" if failed else "") + ".")
    return 0  # a partial run is still a successful orchestration


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
