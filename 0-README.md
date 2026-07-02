# Bundle: Forecasting & Market Analytics Lab (its own repo)

The quant research platform. Now a **working, tested Python package** plus the
original briefs.

**Start here:** [`CLAUDE.md`](CLAUDE.md) (operating doc + guardrails) and
[`README.md`](README.md) (quickstart + headline result). Code lives in
`src/forecasting_lab/`; run `pytest` (159 tests) or `python -m forecasting_lab.cli.elo_backtest --synthetic`.

The briefs (domain knowledge, mapped to modules in `CLAUDE.md`):

- Hub: project-forecasting-lab.md
- Layers: signal-monitoring.md (data layer), ml-system-design.md (modeling layer)
- Feeds: research-sources.md (papers + bulk data), data-automation.md (ingestion pipeline)
- Shared: claude-stack-resources.md, claude-orchestration-plan.md, master-index.md
