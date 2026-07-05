"""Gather everything the dashboard shows, offline-safe.

Each section degrades honestly: if an artifact doesn't exist yet (no arena
state, no digests, no resolved forecasts), the collector says so and the page
shows the exact command that creates it — an empty state is an invitation to
act, not an error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..config import PATHS
from ..eval.metrics import reliability_table, summary


@dataclass
class LabState:
    generated: str = ""
    tennis: dict = field(default_factory=dict)  # summary + reliability + leaderboard
    nba: dict = field(default_factory=dict)
    soccer: dict = field(default_factory=dict)
    arena: dict = field(default_factory=dict)  # leaderboard rows + equity curves
    forward: dict = field(default_factory=dict)  # real-basket forward study
    strategies: list = field(default_factory=list)  # plain-language rule per strategy
    macro: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    forecast_log: dict = field(default_factory=dict)
    digests: dict = field(default_factory=dict)  # slug -> {path, tables, headlines}
    movers: dict = field(default_factory=dict)  # structured trending stocks (sparklines + scores)
    market_edges: dict = field(default_factory=dict)  # structured cross-venue odds pairs
    edge_features: dict = field(default_factory=dict)  # Phase-1 edge features + their OOS skill
    voices: dict = field(default_factory=dict)  # Phase-3 "ahead of the curve" voice leaderboard
    agent: dict = field(default_factory=dict)  # the agent desk: paper picks/bets on real data
    feed: list = field(default_factory=list)  # the tape: picks/resolves/alerts, newest first
    scorecard: dict = field(default_factory=dict)  # the full forecast ledger for scorecard.html
    ledger: dict = field(default_factory=dict)  # the run-loop's ledger snapshots (agent terminal)


def _fit_tennis(seed: int = 0) -> dict:
    from ..sports.elo import EloModel
    from ..sports.tennis_data import synthetic_matches

    matches = synthetic_matches(seed=seed)
    model = EloModel(surface_weight=0.5)
    preds = model.fit(matches)
    ev = preds[preds["min_matches"] >= 10]
    y, p = ev["y"].to_numpy(), ev["p_a"].to_numpy()
    return {
        "summary": summary(y, p),
        "reliability": reliability_table(y, p, n_bins=10).to_dict("records"),
        "leaderboard": model.leaderboard(8).to_dict("records"),
        "label": "synthetic demo data",
    }


def _fit_nba(seed: int = 0) -> dict:
    from ..sports.basketball import BasketballElo, synthetic_season

    games = synthetic_season(seed=seed)
    model = BasketballElo()
    preds = model.fit(games)
    ev = preds[preds["min_games"] >= 15]
    y, p = ev["y"].to_numpy(), ev["p_home"].to_numpy()
    return {
        "summary": summary(y, p),
        "leaderboard": model.leaderboard(8).to_dict("records"),
        "label": "synthetic demo data",
    }


def _fit_soccer(seed: int = 1) -> dict:
    from ..sports.soccer import SoccerElo, evaluate_rps, synthetic_league

    league = synthetic_league(seed=seed)
    preds = SoccerElo().fit(league)
    ev = preds[preds["min_games"] >= 10]
    return {"eval": evaluate_rps(ev), "label": "synthetic league"}


def _strategy_cards() -> list[dict]:
    from ..sim.strategies import default_strategies

    return [
        {"name": s.name, "kind": getattr(s, "kind", ""), "description": getattr(s, "description", "")}
        for s in default_strategies()
    ]


def _macro() -> dict:
    try:
        from ..macro import macro_snapshot

        return {"empty": False, **macro_snapshot()}
    except Exception:  # pragma: no cover - offline
        return {"empty": True, "command": "flab-macro   (needs FRED; network required)"}


def _sources() -> dict:
    from ..sources.registry import source_count, source_table

    try:
        table = source_table()
        return {"total": source_count(), "rows": table.to_dict("records")}
    except Exception:  # pragma: no cover
        return {"total": 0, "rows": []}


def _forward_state() -> dict:
    from ..forwardtest import ForwardLedger

    ledger = ForwardLedger()
    board = ledger.leaderboard()
    if board.empty:
        return {"empty": True, "command": "flab-forward run --backfill"}
    curves_raw = ledger.curves()
    # thin for the SVG
    step = max(1, max(len(c) for c in curves_raw.values()) // 200)
    curves = {
        name: [round(pt["equity"], 5) for pt in pts[::step]]
        for name, pts in curves_raw.items()
    }
    return {
        "empty": False,
        "leaderboard": board.to_dict("records"),
        "curves": curves,
        "live_started": ledger.live_started(),
    }


def _arena_state() -> dict:
    from ..sim.engine import Arena

    arena = Arena()
    resumed = arena.load()
    if not resumed:
        return {"empty": True, "command": "flab-sim run --bars 250"}
    board = arena.leaderboard().reset_index()
    curves = arena.equity_curves()
    # thin the curves for the SVG (<= 240 points per line)
    step = max(1, len(curves) // 240)
    thinned = curves.iloc[::step]
    return {
        "empty": False,
        "bar": arena.bar,
        "total_bars": len(arena.prices),
        "leaderboard": board.to_dict("records"),
        "curves": {c: [round(v, 5) for v in thinned[c].tolist()] for c in thinned.columns},
        "pbo": arena.overfitting_pbo(),
        "gate": _arena_gate(arena),
        "crowding": arena.crowding(),
    }


def _arena_gate(arena) -> dict:
    """The gate stated in the open: fleet_decision over the arena's candidate
    strategies (the two controls are the benchmark, not candidates)."""
    try:
        from ..agent_trader.fleet import HoldBenchmark, fleet_decision

        candidates = {n: r for n, r in arena.returns.items()
                      if r and n not in ("buy_hold", "random")}
        if len(candidates) < 2:
            return {}
        decision = fleet_decision(candidates, as_of=f"bar {arena.bar}", benchmark="buy & hold")
        if isinstance(decision, HoldBenchmark):
            return {"k": len(candidates), "survivors": [], "hold": True,
                    "benchmark": decision.benchmark, "reason": decision.reason}
        return {"k": len(candidates), "survivors": list(decision.survivors),
                "hold": False, "benchmark": "buy & hold", "reason": ""}
    except Exception:  # pragma: no cover - defensive
        return {}


def _forecast_log() -> dict:
    from ..calibration_log import ForecastLog

    path = PATHS.root / "calibration_log.csv"
    if not path.exists():
        return {"empty": True, "command": 'flab-calibration record --question "..." --prob 0.35'}
    log = ForecastLog(path)
    resolved = log.resolved()
    if resolved.empty:
        return {
            "empty": True,
            "pending": int(len(log.to_frame())),
            "command": "flab-calibration resolve --id N --outcome 0|1",
        }
    return {
        "empty": False,
        "score": log.score(),
        "n_total": int(len(log.to_frame())),
        "beat": log.beat_market_score(),
    }


def _latest_digest(slug: str) -> dict:
    """Newest ``inputs/YYYY-MM-DD-<slug>.md``, parsed into tables + bullets."""
    candidates = sorted(PATHS.inputs.glob(f"*-{slug}.md"))
    if not candidates:
        return {"empty": True}
    path = candidates[-1]
    text = path.read_text(encoding="utf-8")
    sections: dict[str, dict] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = {"table": [], "bullets": [], "text": []}
        elif current:
            if line.startswith("|") and "---" not in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                sections[current]["table"].append(cells)
            elif line.startswith("- "):
                sections[current]["bullets"].append(line[2:].strip())
            elif line.startswith("  ") and sections[current]["bullets"] and line.strip().startswith("relevance"):
                # keep the explainable-ranking line attached to its paper
                sections[current]["bullets"][-1] += " — " + line.strip()
            elif line.strip() and not line.startswith(("*", "#", "---", " ")):
                sections[current]["text"].append(line.strip())
    return {"empty": False, "name": path.name, "sections": sections}


def collect_lab_state(seed: int = 0) -> LabState:
    state = LabState(generated=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    state.tennis = _fit_tennis(seed)
    state.nba = _fit_nba(seed)
    state.soccer = _fit_soccer(seed + 1)
    state.arena = _arena_state()
    state.forward = _forward_state()
    state.strategies = _strategy_cards()
    state.macro = _macro()
    state.sources = _sources()
    state.forecast_log = _forecast_log()
    state.digests = {
        "trending-stocks": _latest_digest("trending-stocks"),
        "market-divergence": _latest_digest("market-divergence"),
        "research-digest": _latest_digest("research-digest"),
        "media-watch": _latest_digest("media-watch"),
    }
    from ..pipeline.digest import read_latest_data

    state.movers = read_latest_data("trending-stocks") or {"empty": True}
    state.market_edges = read_latest_data("market-divergence") or {"empty": True}
    state.edge_features = _edge_features()
    state.voices = _voice_leaderboard(state.generated)
    state.agent = _agent_desk(state)
    state.feed = _feed(state)
    state.scorecard = _scorecard_state()
    try:
        from ..agent_trader.terminal import load_ledger

        state.ledger = load_ledger()
    except Exception:  # pragma: no cover - defensive
        state.ledger = {"empty": True}
    return state


def _feed(state) -> list:
    """The tape: picks (agent blotter), resolves (forecast log), alerts — newest first."""
    items: list[dict] = []
    for line in (state.agent or {}).get("blotter", [])[:10]:
        items.append({"kind": "pick", "text": str(line)})
    try:
        from ..calibration_log import ForecastLog

        log = ForecastLog()
        res = log.resolved().sort_values("resolved_date", ascending=False).head(10)
        for _, r in res.iterrows():
            hit = "hit" if int(r["outcome"]) == 1 else "miss (scored, kept on the board)"
            items.append({"kind": "resolve",
                          "text": f'{r["resolved_date"]}: "{r["question"]}" resolved — said '
                                  f'{float(r["prob"]):.0%}, outcome {int(r["outcome"])} · {hit}'})
    except Exception:  # pragma: no cover - defensive
        pass
    alerts = (state.digests or {}).get("media-watch") or {}
    if not alerts.get("empty"):
        for heading, content in list(alerts.get("sections", {}).items())[:1]:
            for b in content.get("bullets", [])[:5]:
                items.append({"kind": "alert", "text": f"{heading}: {b}"})
    return items


def _scorecard_state() -> dict:
    """The full forecast ledger for the scorecard page: score + rows, split
    resolved (worst first — the miss ledger) vs open (under audit)."""
    try:
        from ..calibration_log import ForecastLog

        log = ForecastLog()
        df = log.to_frame()
        if df.empty:
            return {"empty": True}
        outcome = pd.to_numeric(df["outcome"], errors="coerce")
        resolved = df[outcome.notna()].copy()
        open_rows = df[outcome.isna()]
        out: dict = {"empty": False, "n_resolved": int(len(resolved)), "n_open": int(len(open_rows))}
        if not resolved.empty:
            y = pd.to_numeric(resolved["outcome"]).astype(float)
            p = pd.to_numeric(resolved["prob"]).astype(float)
            resolved["sq_error"] = (p - y) ** 2
            resolved = resolved.sort_values("sq_error", ascending=False)  # misses pinned first
            out["score"] = log.score()
            out["beat"] = log.beat_market_score()
            out["reliability"] = reliability_table(y.to_numpy(), p.to_numpy(), n_bins=10).to_dict("records")
            out["rows"] = resolved.head(40).to_dict("records")
        else:
            out["rows"] = []
        out["open_rows"] = open_rows.head(40).to_dict("records")
        return out
    except Exception:  # pragma: no cover - defensive
        return {"empty": True}


def _agent_desk(state) -> dict:
    """The agent's paper book: stock picks from the live movers + bets on the live odds."""
    try:
        from ..agent_trader.desk import AgentLedger, build_desk

        return build_desk(state.movers, state.market_edges, state.generated, ledger=AgentLedger())
    except Exception:  # pragma: no cover - defensive
        return {}


def _voice_leaderboard(generated: str) -> dict:
    """The 'ahead of the curve' voice leaderboard, dated to this run (synthetic
    demonstration until live calls accrue — the engine + guarantees are real)."""
    try:
        from ..media.voices import voice_leaderboard_report

        return voice_leaderboard_report(seed=11, as_of=str(generated)[:10])
    except Exception:  # pragma: no cover - defensive
        return {"rows": []}


def _edge_features() -> dict:
    """Each Phase-1 edge feature with its out-of-sample Brier-skill (deterministic,
    synthetic demonstration that the feature is leak-free and extracts real signal —
    live skill accrues as data fills)."""
    from ..markets.leadlag import leadlag_skill_report
    from ..ml.factors import residual_momentum_skill_report
    from ..signals.attention import attention_skill_report
    from ..signals.deception import deception_skill_report
    from ..signals.squeeze import squeeze_skill_report

    try:
        from ..eval.recalibration import recalibration_skill_report

        recal = recalibration_skill_report(seed=7)
        return {
            "empty": False,
            "rows": [
                {"name": "Cross-venue lead-lag",
                 "skill": leadlag_skill_report(seed=7)["brier_skill_vs_baseline"],
                 "what": "Which venue moves first; the laggard converges to the leader.",
                 "status": "live on matched Kalshi/Polymarket pairs"},
                {"name": "Attention acceleration",
                 "skill": attention_skill_report(seed=7)["brier_skill_vs_baseline"],
                 "what": "Mentions rising faster than a name's own baseline — the leading edge of a trend.",
                 "status": "accruing (needs a few days of history)"},
                {"name": "Squeeze setup",
                 "skill": squeeze_skill_report(seed=7)["brier_skill_vs_baseline"],
                 "what": "High short interest + days-to-cover, gated by a volume/gap ignition.",
                 "status": "dormant (short-interest feed is Phase 2)"},
                {"name": "Favorite-longshot recalibration",
                 "skill": recal["brier_skill_vs_market"],
                 "what": "Corrects the price bias: longshots overpriced, favorites underpriced.",
                 "status": "live on market picks (default correction until fit on resolutions)"},
                {"name": "Residual momentum (factor-neutral)",
                 "skill": residual_momentum_skill_report(seed=7)["oos_rank_ic_residual"],
                 "what": "Rank names by factor-residual drift, not raw returns (OOS rank IC, purged CV).",
                 "status": "synthetic demonstration (real factor exposures are a later data source)"},
                {"name": "Earnings-call deception language (L-Z 2012)",
                 "skill": deception_skill_report(seed=7)["brier_skill_vs_base"],
                 "what": "Lexical deception markers in executive narratives — classification skill, NOT a return edge.",
                 "status": "synthetic demonstration (real transcripts are a later data source)"},
            ],
        }
    except Exception:  # pragma: no cover - defensive
        return {"empty": True}


def latest_digest_dir() -> Path:
    return PATHS.inputs
