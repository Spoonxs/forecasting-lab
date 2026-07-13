"""CLI: build the lab dashboard (a single static HTML file).

Examples::

    python -m forecasting_lab.cli.dashboard              # -> site/index.html
    python -m forecasting_lab.cli.dashboard --open       # build and open in browser
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from ..config import PATHS
from ..dashboard import (
    build_arena_page,
    build_compare_page,
    build_desk_page,
    build_journal_page,
    build_portfolio_page,
    build_verdict_pages,
    collect_lab_state,
    render_dashboard,
    render_scorecard,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=str, default=None, help="output path (default: site/index.html)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--open", action="store_true", help="open the page in a browser")
    args = ap.parse_args(argv)

    out = Path(args.out) if args.out else PATHS.root / "site" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    state = collect_lab_state(seed=args.seed)
    out.write_text(render_dashboard(state), encoding="utf-8")
    print(f"Dashboard written to {out}")

    # the public Brier scorecard page (honest denominator, miss ledger pinned)
    scorecard = out.parent / "scorecard.html"
    scorecard.write_text(render_scorecard(state), encoding="utf-8")
    print(f"Scorecard written to {scorecard}")

    # the ticker recommendation pages (site/t/<SYM>.html) from the verdict artifact
    from ..dashboard.tier_live import copy_contract, worker_url

    wu = worker_url()
    built = build_verdict_pages(out.parent, tier_live_worker=wu)
    if copy_contract(out.parent):
        print(f"Tier-live: contract copied{' + worker ' + wu if wu else ' (no worker configured)'}")
    print(f"Ticker pages written: {len(built)} -> {out.parent / 't'}")

    # the full listed-symbol index for the home search (lazy-fetched, same-origin)
    from ..dashboard.tier_live import write_universe_json

    uni = write_universe_json(out.parent)
    print(f"Universe index written -> {uni.name}")

    # the compare page (two tickers side-by-side, per component)
    if build_compare_page(out.parent):
        print(f"Compare page written -> {out.parent / 'compare.html'}")

    # the portfolio page (holdings stay browser-local; demo book server-rendered)
    port = build_portfolio_page(out.parent)
    print(f"Portfolio page written -> {port.name}")

    # the AI arena + the regret ledger surface (paper books, benchmarks always on)
    arena = build_arena_page(out.parent)
    print(f"Arena page written -> {arena.name}")

    # the decision journal (browser-local entries join the public regret rows)
    journal = build_journal_page(out.parent)
    print(f"Journal page written -> {journal.name}")

    # the in-site desk chat (deterministic, same-origin bundle; P10)
    desk = build_desk_page(out.parent)
    print(f"Desk page written -> {desk.name} (+ desk-data.json)")

    # the watcher builder (contract-bounded, writes nothing; P10)
    from ..dashboard.builder_page import build_builder_page

    builder = build_builder_page(out.parent)
    print(f"Builder page written -> {builder.name}")

    # the motion layer + vendored libs (P9) — copied local, zero external fetches
    from ..dashboard.assets_pipe import copy_assets

    assets = copy_assets(out.parent)
    print(f"Assets copied: {len(assets)} (vendor + motion.js)")

    # the landing page (Sakura treatment; the marketing entry into the app)
    from ..dashboard.landing import build_landing

    land = build_landing(out.parent)
    print(f"Landing written -> {land.name}")

    # also render the dark, agentic Agent Terminal alongside it
    from ..agent_trader.terminal import render_terminal

    terminal = out.parent / "agent.html"
    terminal.write_text(render_terminal(state), encoding="utf-8")
    print(f"Agent terminal written to {terminal}")

    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
