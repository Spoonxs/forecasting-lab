# Plan: Claude Orchestration (parallel work on Max)

You have Max and want to run Claude in parallel. Here is the practical setup. The throughput win is real on the data and build projects; the bottleneck is usually context hygiene and usage limits, not raw parallelism.

## Core pattern: git worktrees
- One Claude Code session per worktree / feature branch, so parallel sessions do not collide on the same files.
- This is the canonical parallel pattern. Tools like the agent-orchestrator repos automate worktree-per-agent, but you can also just do it by hand with `git worktree add`.

## Context hygiene (the highest-leverage thing)
- A tight CLAUDE.md per project: 40 to 60 line root with conventions and architecture, everything else in skill files Claude pulls on demand. Past a couple hundred lines it stops reading the bottom.
- This does more for output quality than any plugin pack and costs zero installs.

## In-session parallelism
- Use the Task / subagent tool inside a session for parallelizable subtasks. The built-in primitives (an agent tool, a coordinator, worktree isolation) are enough; the Anthropic dynamic-workflows feature is the first-party way to spin up a fan-out / verifier / loop-until-done structure when a task warrants it.

## Usage management (important on Max with parallel sessions)
- Parallel sessions burn quota fast.
- ccusage and similar tools parse local logs, but Anthropic rate-limits on a rolling 5-hour window plus a weekly quota that counts cache reads, tool calls, and peak-hour multipliers. The local number can read 5% while you are already getting limited.
- Treat the local estimate as a rough gauge. Trust the server / usage page for the "am I about to hit the wall" question.

## A workflow that holds up
1. Planning session in plan mode: scope the work, write or refresh CLAUDE.md, break it into components.
2. Spawn parallel implementation sessions, one per component or worktree.
3. Integration / review session: pull diffs, review, merge.

Keep each session scoped to one project / worktree. Commit frequently. Review diffs before merge.

## Security at scale
- Do not install unvetted skills or MCP servers into orchestrated agents. With several parallel sessions the blast radius of a malicious skill is larger, not smaller. Vet first (see the Security section in claude-stack-resources.md), and use the quarantine pattern: agents that read untrusted content should not be the ones with privilege to act.

## Running the project briefs with Claude Code

The project files are briefs, not finished specs. The point is to hand each one to Claude Code and let it do the research and the build, not to have it pre-chewed for you:

- Point Claude Code at a brief and tell it to research the open specifics itself (the best alt-data source, the exact APIs, the Reddit `.json` endpoints, the clip-detection libraries) rather than working only from what is pre-listed.
- Have it scaffold the repo, write a CLAUDE.md, and stub the components, then you review and redirect.
- One brief per worktree/session, run in parallel per the setup above.

The briefs carry the goal, the components, and the guardrails. Claude Code does the digging and the typing.

---
*Last updated: June 2026*
