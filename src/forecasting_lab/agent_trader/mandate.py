"""The mandate validator — deterministic pass/warn/BLOCK on every proposal (V4).

The pattern (from the one honest repo in the field review, rewritten here): the
operator writes rules once; every strategy proposal is machine-checked against
them BEFORE the execution layer sees it. Three semantics that keep the check
honest rather than theatrical:

- **Concentration is measured on INVESTED capital**, not total equity — 20% of a
  half-invested book is 40% of the risk actually taken.
- **Sells always pass.** A rule may block increasing an exposure, never reducing
  one — a mandate that traps you in a position is worse than none.
- **Missing data skips the rule, loudly.** No sector map for a symbol means that
  rule is skipped with a note — never a false block, never a silent pass.

This is a *decision*, not an order: the loop consults it and refuses to
rebalance on BLOCK. Unknown rule types warn (a typo must not become a silent
no-op), and the report always says exactly which rule fired on which symbol.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KNOWN_RULE_TYPES = {
    "forbidden_ticker",
    "max_position_pct",
    "min_cash_pct",
    "max_sector_pct",
}

BLOCK, WARN, PASS = "block", "warn", "pass"


@dataclass(frozen=True)
class Rule:
    """One mandate rule. ``value`` is a fraction for the *_pct types."""

    type: str
    value: float | None = None
    tickers: tuple[str, ...] = ()
    sector: str | None = None


@dataclass
class MandateReport:
    status: str = PASS  # "pass" | "warn" | "block"
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.status == BLOCK

    def _escalate(self, to: str) -> None:
        order = {PASS: 0, WARN: 1, BLOCK: 2}
        if order[to] > order[self.status]:
            self.status = to

    def block(self, msg: str) -> None:
        self.violations.append(msg)
        self._escalate(BLOCK)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self._escalate(WARN)

    def skip(self, msg: str) -> None:
        self.skipped.append(msg)


def check_mandate(
    targets: dict[str, float],
    rules: list[Rule],
    *,
    current_weights: dict[str, float] | None = None,
    sectors: dict[str, str] | None = None,
) -> MandateReport:
    """Validate proposed target weights against the mandate.

    ``current_weights`` lets the sells-always-pass semantics work: a target at or
    below the current exposure never blocks. ``sectors`` maps symbol -> sector;
    symbols missing from it skip sector rules with a note.
    """
    report = MandateReport()
    current = current_weights or {}
    invested = sum(w for w in targets.values() if w > 0)

    for rule in rules:
        if rule.type not in KNOWN_RULE_TYPES:
            report.warn(f"unknown rule type {rule.type!r} — check the mandate spelling")
            continue

        if rule.type == "forbidden_ticker":
            for sym in rule.tickers:
                if targets.get(sym, 0.0) > current.get(sym, 0.0):
                    report.block(f"{sym}: forbidden ticker — buying is not allowed")

        elif rule.type == "max_position_pct":
            if rule.value is None:
                report.warn("max_position_pct rule has no value — skipped")
                continue
            if invested <= 0:
                report.skip("max_position_pct: nothing invested — rule not applicable")
                continue
            for sym, w in targets.items():
                share = w / invested  # concentration of the capital actually at risk
                if share > rule.value and w > current.get(sym, 0.0):
                    report.block(
                        f"{sym}: {share:.0%} of invested capital exceeds the "
                        f"{rule.value:.0%} cap (and the proposal increases it)"
                    )

        elif rule.type == "min_cash_pct":
            if rule.value is None:
                report.warn("min_cash_pct rule has no value — skipped")
                continue
            cash = 1.0 - sum(targets.values())
            if cash < rule.value - 1e-12:
                report.block(f"cash {cash:.0%} below the {rule.value:.0%} floor")

        elif rule.type == "max_sector_pct":
            if rule.value is None or rule.sector is None:
                report.warn("max_sector_pct rule needs value and sector — skipped")
                continue
            if sectors is None:
                report.skip(f"max_sector_pct({rule.sector}): no sector data — skipped, not blocked")
                continue
            unknown = [s for s in targets if s not in sectors and targets[s] > 0]
            if unknown:
                report.skip(
                    f"max_sector_pct({rule.sector}): no sector for {', '.join(sorted(unknown))} — "
                    "those symbols skipped, not blocked"
                )
            if invested <= 0:
                continue
            exposure = sum(
                w / invested for s, w in targets.items() if sectors.get(s) == rule.sector
            )
            grew = any(
                targets.get(s, 0.0) > current.get(s, 0.0)
                for s in targets
                if sectors.get(s) == rule.sector
            )
            if exposure > rule.value and grew:
                report.block(
                    f"sector {rule.sector}: {exposure:.0%} of invested capital exceeds "
                    f"the {rule.value:.0%} cap"
                )

    return report
