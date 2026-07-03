"""P6 — the go-live capital ladder.

Real capital is added one rung at a time, and a rung can only be climbed when the
promotion gate has cleared **and** a human explicitly confirms. No gate, no step; no
confirmation, no step. This is the structural version of "lose $100 first, then $1k,
then the $100k" — you can't skip to the top, and code can't advance itself.
"""

from __future__ import annotations

from dataclasses import dataclass

# paper → then real-money rungs
STEPS: tuple[float, ...] = (0.0, 100.0, 1_000.0, 10_000.0, 100_000.0)


@dataclass(frozen=True)
class LadderState:
    step: int = 0                      # index into STEPS (0 = paper)
    live_version: str | None = None    # the gate-cleared strategy version, if any

    @property
    def capital(self) -> float:
        return STEPS[self.step]

    @property
    def is_paper(self) -> bool:
        return self.step == 0


def can_advance(state: LadderState, *, gate_passed: bool, human_confirmed: bool) -> tuple[bool, str]:
    """Whether the ladder may climb one rung — and why not, if it can't."""
    if state.step >= len(STEPS) - 1:
        return False, "already at the top rung"
    if not gate_passed:
        return False, "blocked: the promotion gate has not cleared on real forward marks"
    if not human_confirmed:
        return False, "blocked: explicit human confirmation required for real capital"
    return True, f"cleared to advance to ${STEPS[state.step + 1]:,.0f}"


def advance(state: LadderState, *, gate_passed: bool, human_confirmed: bool,
            live_version: str | None = None) -> LadderState:
    """Climb one rung if (and only if) the gate cleared and a human confirmed; else no-op."""
    ok, _ = can_advance(state, gate_passed=gate_passed, human_confirmed=human_confirmed)
    if not ok:
        return state
    return LadderState(state.step + 1, live_version or state.live_version)
