# Master Index: Map & Research Backlog

The entry point for everything. Two systems, one set of infrastructure, plus what still needs research.

## The consolidation: two systems, not one pile

There isn't one thing to merge. There are two, and they share rails.

1. Planning system: grad school, finances, Putnam, the transfer. Reference docs you read and maintain, updated as facts change.
2. Build system: the four project briefs. Execution specs Claude Code runs, not docs you read.

Both run on the same infrastructure:
- Obsidian vault: the memory layer, holds every doc, linked with `[[brackets]]`.
- Claude Code: the execution engine, reads the vault and runs the work.
- Research pipeline: the invoke → fetch → process → store pattern, set up once and pointed at different sources, filing dated digests into `inputs/`.
- Orchestration plan: how Claude Code runs the multi-step builds (worktrees, subagents, bounded exits).
- CLAUDE.md: your profile and working preferences, loaded every session.

## Vault layout

```
brain/
  CLAUDE.md                      profile + how Claude works with you
  master-index.md                this file
  planning/
    grad-school-tracker.md
    finance-tracker.md
    Putnam-log.md                to start
    faculty-fit/                 one note per program  [TO RESEARCH]
    REU-tracker.md               [TO BUILD]
    Northwestern-transfer.md     Net Price Calculator  [OPEN]
  projects/
    forecasting-lab.md
    putnam-platform.md
    clipper.md
    skill-scanner.md
  stack/
    claude-stack-resources.md
    orchestration-plan.md
  inputs/                        auto-filed research digests
```

## The pipeline is the engine

The four-move pattern is reusable. Set it up once, then swap the source:
- Faculty-fit sweep: fetch program faculty pages + Google Scholar + arXiv, output one note per program into `faculty-fit/`.
- arXiv triage: fetch math.PR / q-fin / stat.ML feeds (plus autoarxiv to reproduce a paper), output a ranked "worth building" note.
- Market monitor: fetch the Polymarket + Kalshi APIs, output a dated cross-venue divergence digest into `inputs/`.

Build a pipeline only for things that recur. One-off lookups are cheaper to just ask.

## Research backlog: what needs researching

### Tier 1: grad and career (the real backlog, highest value, mostly undone)
This is where the open research is, and it is the work your grad tracker already flags as highest-leverage.
- Faculty fit per program: who works on probability / optimization / statistical ML, their recent papers, who is taking students. Fills `faculty-fit/`.
- Accepted-student profiles and the realistic bar: mathematicsgre.com and GradCafe. Find 2-3 profiles per program with a background like yours and record what they had.
- Deadline and requirement verification: the briefs use prior-cycle dates. Confirm each on the program's own page for your cycle.
- REU programs: the list, deadlines, and fee waivers. Fills `REU-tracker.md`.
- Northwestern Net Price Calculator with family numbers. Not research, a 20-minute data pull, still open.

### Tier 2: project research (mostly done; the rest is build-time)
The four briefs already carry the researched specifics: the Polymarket/Kalshi endpoints and gotchas, the Sackmann data and its license, the backtesting stack, the alt-data sources, the clip-detection recipe, the scanner threat patterns, and FSRS. What's left is build-time detail (exact endpoint schemas, the final library and alt-data-source choices), and Claude Code resolves that as it builds, using autoarxiv for papers and the pipeline for sources. Don't pre-research these; they settle at the keyboard.

### Tier 3: tooling (decide on demand)
Observability (Langfuse / Opik / plain logs), the scraping tool (yt-dlp / Bright Data / Playwright), and which MCPs to commit to. Pick each when a real need shows up, not before.

## Where to start
Stand up the research pipeline first. It runs Tier 1 faculty fit and Tier 2 paper triage on the same rails, which makes it the highest-leverage single thing to build: it turns the biggest open research bucket into something that runs on a schedule instead of by hand.

---

*Last updated: June 2026*
