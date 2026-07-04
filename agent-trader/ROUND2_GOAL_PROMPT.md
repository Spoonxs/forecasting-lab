# Round-2 build plan + ready-to-fire /goal prompt

*Turns the `SOURCES_ROUND2_ASSESSMENT.md` findings into an executable plan. The condensed
`/goal` string (under the 4000-char cap) is at the bottom — paste it after `/goal `. The
full phase detail is above it for reference.*

## The plan (ranked, each ships with a property test — never a golden number)

**P1 — `signals/deception`: earnings-call deception feature (the one genuinely new edge).**
Follow Larcker–Zakolyukina 2012: label calls from *subsequent restatements* (objective,
as-of-knowable); extract linguistic markers (extreme vs non-extreme positive emotion,
anxiety words, shareholder-value refs, general-knowledge hedges); score OOS under
`ml.PurgedWalkForwardCV`; beat a financial-variable baseline; report Brier + skill-vs-base.
*Done when:* a null/shuffled-label control pins to ~0 skill (test), and the feature surfaces
on the dashboard "Edge research" panel with its OOS skill + drivers. Treat the Reddit
"Sonnet>Opus" claim as a hypothesis to test, not evidence.

**P2 — Fleet-level multiple-testing + honest default (from Engo Arena).**
Add family-wise **FDR control across the strategy fleet** to `agent_trader/fleet.py` (we
already have per-strategy PBO/deflated-Sharpe; add the cross-strategy correction so
"N candidates, 0 survive" is possible), and make the arena's default **hold the benchmark
(e.g. SPY) when nothing survives the gate.** *Done when:* a fleet of pure-noise strategies
yields 0 promoted and a 100%-benchmark allocation (test), and a seeded-skilled one survives.

**P3 — `openfactor` as a leakage-aware factor/residual layer for `ml/`.**
Vendor or wrap `ralliesai/openfactor` (verify licence first) to pull the free R2 factor
snapshots; expose cross-sectional style exposures + idiosyncratic residual returns as
features the GBM ranker trains on. Keep its `as_of`-prior-close discipline. Adopt its
**admit-a-factor-only-if-it-reduces-OOS-idiosyncratic-variance** gate for any new feature.
*Done when:* residual-ranked IC under purged CV beats raw-return ranking on the same names,
and null features pin to ~0 IC (test).

**P4 — Data-freshness audit layer in `pipeline/` (anti-agent-leakage).**
Every datum carries fetch-time + age; a check fails loudly when data exceeds its as-of
budget; each step can surface raw output before use. Defends against an LLM coding agent
silently inserting caches/fallbacks that break point-in-time correctness. *Done when:* a
stale-data injection test raises, and freshness metadata is attached end-to-end.

**P5 — Velora disciplines: Mandate validator + refuse-uncomputable-metrics.**
A machine-checkable **Mandate** (max-position%, min-cash%, sector caps, forbidden tickers)
validates every proposal before the execution layer (`agent_trader/execution.py`); and
`eval`/`predictions.py` **refuse to report a metric that isn't point-in-time computable**
(e.g. no alpha without a stored entry-date benchmark). *Done when:* a mandate-violating
proposal is rejected by code (test), and an un-anchored alpha call returns "n/a", not a number.

**P6 — Subagent-isolation scoring for LLM signals (`media/voices`, `research_log`).**
Score anonymized inputs in an isolated context so the model can't map financials→identity;
blunts training-data contamination. *Done when:* scoring is invariant to identity-swap on a
control set (test).

**P7 (optional) — Harness plumbing from openprophet + what-if shadows from get-rich-slow.**
Phased-heartbeat loop, SSE live desk, **fail-closed permission gate**, deterministic bracket
exits, vector setup-memory for `agent_trader`; and N-parameter "what-if shadow" variants
tracked against the same forward marks in `forwardtest/`. Keep the deterministic decider
between proposal and order.

**Guardrails (unchanged, enforced throughout):** time-respecting purged CV; no look-ahead
/ as-of features; model costs; calibration over accuracy (Brier + reliability, beat base
rate); survivorship-bias-free universe; LLM proposes / deterministic code decides; paper
until the promotion gate clears + human confirm.

---

## Ready-to-fire /goal string (copy after `/goal `, ~1.9k chars)

Build, test, and commit the Round-2 adoptions from agent-trader/SOURCES_ROUND2_ASSESSMENT.md, in order, each as its own PR with a property test (not a golden number), running `pytest` + `ruff check src tests` before calling any step done. (1) Add `signals/deception`: an earnings-call linguistic-deception feature labeled from subsequent restatements, scored OOS under ml.PurgedWalkForwardCV, beating a financial-variable baseline, reporting Brier + skill-vs-base; a shuffled-label control must pin to ~0 skill; surface it on the dashboard Edge-research panel. (2) Add family-wise FDR multiple-testing control across the strategy fleet in agent_trader/fleet.py, plus an honest default that holds the benchmark when nothing survives the gate; a noise fleet must promote 0 and allocate 100% benchmark. (3) Integrate ralliesai/openfactor (verify licence) as a leakage-aware factor/residual feature layer for the GBM ranker using its free R2 snapshots and as_of prior-close discipline; residual-ranked IC must beat raw-return ranking and null features pin to ~0 IC; adopt its accept-only-if-reduces-OOS-idiosyncratic-variance gate for new features. (4) Add a data-freshness audit layer to pipeline/: timestamp+age on every datum, a loud failure when data exceeds its as-of budget; a stale-data injection test must raise. (5) Add a machine-checkable Mandate validator to agent_trader/execution.py that rejects proposals violating position/cash/sector/forbidden rules, and make eval/predictions refuse to report any metric not point-in-time computable. (6) Use subagent-isolation (anonymized inputs, isolated context) for LLM scoring in media/voices and research_log; scoring must be invariant to identity-swap. Respect every CLAUDE.md guardrail (purged CV, no look-ahead, model costs, calibration-over-accuracy, survivorship-free, LLM-proposes/code-decides, paper-until-gate). Done when all six are implemented, tested green, ruff-clean, and committed.
