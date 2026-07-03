# ONESHOT_PROMPT.md — the optimized prompt for a one-shot upgrade

This is the "way bigger, better prompt" — engineered so Claude Code can execute a
large upgrade autonomously and *verify its own work* with `/goal` + hooks. Don't
paste all phases at once (that fills context and lowers quality). Run **one phase
per `/goal`**, in order; each has a measurable finish line.

---

## Step 1 — Install the verification hooks (once)

Hooks make verification *deterministic and enforced* instead of hoping the model
remembers. Add to `.claude/settings.json` (I can install these for you):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command",
            "command": "cd \"$CLAUDE_PROJECT_DIR\" && python -m ruff check src tests --quiet && python -m pytest -q -p no:warnings --tb=line" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command",
            "command": "grep -Eq 'DISCORD_WEBHOOK|PEM|SECRET|API_KEY' <<< \"$CLAUDE_TOOL_INPUT\" && { echo 'blocked: possible secret in command' >&2; exit 2; } || exit 0" }
        ]
      }
    ]
  }
}
```

The first hook runs ruff + pytest after **every** file edit and feeds failures
straight back to Claude — so it can't drift past a broken test. The second blocks
any shell command that looks like it's about to leak a secret. Hooks *enforce*;
they don't plan. Planning is the prompt below + `/goal`.

## Step 2 — Prime the session

```
Read CLAUDE.md, design.md, and PLAN.md in full before doing anything.
The code is ground truth; the guardrails in CLAUDE.md are non-negotiable.
Work in the src/ layout. Determinism: explicit seeds, no wall-clock in logic.
Every new model/metric ships with a PROPERTY test (monotonic / zero-sum /
calibrated / leak-free), not just a golden number.
```

## Step 3 — Run the phases (one `/goal` each)

For large phases, ask for a plan first (plan mode), skim it, then fire `/goal`.
Run hands-off with `claude --permission-mode auto -p "/goal …"` if you want.

### Phase 0 — Evidence layer
```
Implement the prediction-evidence contract from design.md §7 and PLAN.md Phase 0.
Add a `Prediction` dataclass (probability, market_implied_prob, edge_vs_market,
drivers: list of (feature, value, contribution), caveat). Every pick the dashboard
surfaces must render its odds + an expandable "why" listing the top drivers.

/goal a Prediction type exists with a property test proving no pick renders
without a probability and >=1 driver; the dashboard shows odds + an evidence
expander for movers and market picks; pytest and ruff are green; and a browser
screenshot of the dashboard shows at least one pick with visible odds + "why".
```

### Phase 1 — Edge features
```
Implement PLAN.md Phase 1 features 1-4 (cross-venue lead-lag, attention-
acceleration z-score with persisted mention history, squeeze-setup composite,
favorite-longshot recalibration). Each: leak-free, scored Brier-skill-vs-market
under PurgedWalkForwardCV, with a property test (null/noise input -> ~0 skill).

/goal all four features are implemented with leak-free property tests (noise ->
~0 skill, pinned), each is wired into a pipeline/signal and surfaced with odds +
evidence, pytest and ruff are green, and RESULTS.md documents each feature's
out-of-sample Brier-skill-vs-market vs. its baseline.
```

### Phase 2 — Data scale
```
Implement PLAN.md Phase 2. Add FINRA short-interest, an options-chain (gamma)
source, an X/Twitter finance-voice list, and >=1 more sports league / market
venue. Add a small persisted tidy store so velocity/track-record features have
history. Every source degrades honestly (graceful zeros when blocked).

/goal flab-sources reports a materially larger tracked-source count, every new
source has a connector test and an honest-degradation path, the persistence store
has a round-trip test, and pytest + ruff are green.
```

### Phase 3 — Ahead-of-the-curve voices
```
Implement PLAN.md Phase 3. Log each tracked voice's named tickers with timestamps;
score voices by Brier-vs-market at call time and timing-lead (mention-vs-return
cross-correlation). Build an "Early & right" leaderboard weighted by record, never
followers, with weight decay on regression.

/goal a voice with random calls scores ~0 (pinned test), the leaderboard is
deterministic and dated, it renders on the dashboard with each voice's record and
lead, and pytest + ruff are green.
```

### Phase 4 — Promotion gate (NOT auto-execution)
```
Implement PLAN.md Phase 4: a paper->live promotion gate. A strategy passes only if,
out-of-sample: deflated Sharpe > 1.0, PBO < 0.2, positive Brier-skill-vs-market on
>= N real forward marks, survives modeled costs + turnover cap, and passes a risk
gate (fractional-Kelly <= 1/4 sizing, max per-name exposure, drawdown kill switch,
capital cap). Writes a signed dated promotion record. DO NOT wire any broker or
place any order — only produce the pass/fail decision and the record.

/goal the promotion gate returns pass/fail with all six criteria and a written
rationale, a property test proves an overfit/lucky strategy is REJECTED and a
genuinely-skilled synthetic one is promoted, no brokerage/order code exists, and
pytest + ruff are green.
```

### Phase 5 — UI / motion / best-picks lead
```
Apply design.md. Add tasteful self-contained motion (chart draw-on via
stroke-dasharray, KPI count-up, hover micro-transitions), all reduced-motion-gated.
Add a "Best picks right now" lead module ranking candidates across stocks / sports
/ markets by edge, each with odds + a "why" expander. No external assets/video.

/goal the dashboard shows a "best picks" lead with odds+evidence per pick, motion
is present but disabled under prefers-reduced-motion, the page renders with JS off,
desktop AND mobile screenshots look correct, and pytest + ruff are green.
```

---

## Why this prompt works (the technique)

- **One measurable `/goal` per phase.** The finish line is a *checkable condition*
  (tests pass + a screenshot shows X), not "make it better". The evaluator can
  verify it, so Claude iterates until it's truly done instead of stopping early.
- **Hooks enforce the floor.** ruff+pytest run after every edit; the model sees
  failures immediately and can't drift. Secrets are blocked at the shell.
- **Verification is visual where it matters.** Front-end goals require a
  screenshot comparison — the loop that catches "looks broken" that tests miss.
- **The honesty guardrails are *in the goal conditions*** (leak-free tests, odds+
  evidence, no broker code, reject-the-overfit test) — so "done" can't mean
  "cut a corner".
- **Scoped, sequential, grounded** in CLAUDE.md + design.md + PLAN.md, so each run
  has the context it needs and nothing it doesn't.

## Anti-patterns to avoid
- One giant `/goal` for all five phases (context blows out, quality drops).
- Vague conditions ("make it profitable", "make it nicer") — the evaluator can't
  check them and Claude will declare victory early. Always give a test or a screenshot.
- Letting a phase "pass" with a red test because a hook was skipped — never `--no-verify`.
