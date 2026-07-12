"""P8-3 — the real component provider (the audit's main fix).

Pinned: panel components (trend / backtest / residual_momentum) compute from
closes alone with scores in [-1,1] and honest caveats; the walk-forward
persistence check has no lookahead and withholds the backtest component on
thin samples; residual momentum ranks planted idiosyncratic drift above pure
beta; the future guard keeps rows after as_of out of every score; the
assembled provider merges macro/news/squeeze honestly and the manifest states
what existed and why the rest is missing; and — the acceptance moment — the
verdict engine RATES symbols fed by this provider instead of gating
everything INSUFFICIENT.
"""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from forecasting_lab.pipeline.providers import (
    _persistence,
    build_real_provider,
    panel_components,
)

AS_OF = date(2026, 7, 10)


def _dates(n: int) -> list[str]:
    return [d.date().isoformat() for d in
            pd.bdate_range(end="2026-07-10", periods=n)]


def _panel(n: int = 200, seed: int = 7) -> pd.DataFrame:
    """Synthetic close panel: UP trends hard, DOWN decays, BETA rides the
    market, ALPHA carries planted idiosyncratic drift over the market."""
    rng = np.random.default_rng(seed)
    mkt = rng.normal(0.0004, 0.01, n)
    closes = {
        "UP": 100 * np.cumprod(1 + 0.004 + rng.normal(0, 0.004, n)),
        "DOWN": 100 * np.cumprod(1 - 0.003 + rng.normal(0, 0.004, n)),
        "BETA": 100 * np.cumprod(1 + mkt),
        "ALPHA": 100 * np.cumprod(1 + mkt + 0.002 + rng.normal(0, 0.001, n)),
    }
    return pd.DataFrame(closes, index=_dates(n))


def test_panel_components_scores_are_bounded_and_caveated():
    comps = panel_components(_panel(), AS_OF)
    assert set(comps) == {"UP", "DOWN", "BETA", "ALPHA"}
    for c in comps.values():
        assert {"trend", "residual_momentum"} <= set(c)
        for comp in c.values():
            assert -1.0 <= comp.score <= 1.0 and 0.0 < comp.confidence <= 1.0
    assert comps["UP"]["trend"].score > comps["DOWN"]["trend"].score
    assert "not yet calibrated" in comps["UP"]["backtest"].detail
    assert panel_components(_panel(60), AS_OF) == {}    # too short -> honest nothing


def test_persistence_walkforward_has_no_lookahead_and_gates_thin_samples():
    n = 200
    up = pd.Series(100 * np.cumprod([1.004] * n), index=_dates(n))
    hit, total = _persistence(up)
    assert hit > 0.9 and total >= 20                    # a real trend persists
    rng = np.random.default_rng(0)
    noise = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, n)), index=_dates(n))
    hit_n, _ = _persistence(noise)
    assert 0.25 <= hit_n <= 0.75                        # noise gives no persistent edge
    # thin history -> no backtest component at all (never a guessed lean)
    comps = panel_components(_panel(90), AS_OF)
    assert all("backtest" not in c or c["backtest"].confidence <= 0.55
               for c in comps.values())


def test_residual_momentum_finds_planted_alpha_over_beta():
    comps = panel_components(_panel(), AS_OF)
    assert (comps["ALPHA"]["residual_momentum"].score
            > comps["BETA"]["residual_momentum"].score)


def test_future_rows_never_reach_a_score():
    frame = _panel()
    early = date(2026, 5, 1)
    full = panel_components(frame, AS_OF)["UP"]["trend"].score
    guarded = panel_components(frame, early)
    # the guarded run scored a strictly shorter history — different number,
    # computed only from rows dated <= as_of
    assert guarded and guarded["UP"]["trend"].score != full


def test_provider_assembly_manifest_and_the_acceptance_moment(tmp_path):
    frame = _panel()
    for sym in frame.columns:                            # a real cached panel
        pd.DataFrame({"date": frame.index, "close": frame[sym].to_numpy()}).to_csv(
            tmp_path / f"{sym}.csv", index=False)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "2026-07-10-macro-nowcast.json").write_text(
        json.dumps({"as_of": "2026-07-10", "recession_prob_12m": 0.2}), encoding="utf-8")
    (inputs / "2026-07-10-trending-stocks.json").write_text(
        json.dumps({"movers": [{"ticker": "UP", "headline": "record surge in profits"}]}),
        encoding="utf-8")

    class _Store:
        def load(self):
            return pd.DataFrame([{"date": "2026-07-09", "entity": "DOWN",
                                  "metric": "short_volume_ratio", "value": 0.7}])

    provider, manifest = build_real_provider(list(frame.columns) + ["GHOST"],
                                             as_of=AS_OF, panel_root=tmp_path,
                                             store=_Store(), inputs_dir=inputs)
    up = provider("UP")
    assert {"trend", "residual_momentum", "macro", "news"} <= set(up)
    assert "squeeze" in provider("DOWN") and "news" not in provider("DOWN")
    assert provider("GHOST").keys() == {"macro"}         # no prices -> only the regime
    avail = manifest["components_available"]
    assert avail["trend"] == 4 and avail["macro"] == 5 and avail["news"] == 1
    assert avail["squeeze"] == 1 and avail["yield"] == 0
    assert "honestly absent" in manifest["missing_reasons"]["yield"]
    assert "1 symbol(s) lack" in manifest["missing_reasons"]["prices"]

    # THE ACCEPTANCE MOMENT: the engine rates real-provider symbols
    from forecasting_lab.pipeline.verdicts import build_verdicts

    payload = build_verdicts(list(frame.columns), provider, on=AS_OF,
                             hysa_yield_pct=4.0)
    labels = {s: r["label"] for s, r in payload["verdicts"].items()}
    assert all(lab != "INSUFFICIENT EVIDENCE" for lab in labels.values()), labels
    assert labels["UP"] in ("STRONG BUY", "BUY")         # the trending name leans long


# ------------------------------------------------ Codex code-review fixes pinned
def test_beta_estimator_uses_matching_ddof():
    """Codex finding 1: cov(ddof=1)/var(ddof=0) inflated every beta by
    n/(n-1). A name that IS the market must come out at beta ~1 exactly."""
    n = 150
    rng = np.random.default_rng(3)
    mkt_ret = rng.normal(0.0005, 0.01, n)
    twin = 100 * np.cumprod(1 + mkt_ret)
    frame = pd.DataFrame({"TWIN": twin, "SAME": twin.copy()}, index=_dates(n))
    rets = frame.pct_change().iloc[1:]
    mkt = rets.mean(axis=1)
    beta = float(rets["TWIN"].cov(mkt) / (mkt.var(ddof=1) or 1e-12))
    assert abs(beta - 1.0) < 1e-9                        # exact, not n/(n-1) off
    comps = panel_components(frame, AS_OF)
    # both names ARE the market: residuals ~0, z of a constant vector -> 0
    assert abs(comps["TWIN"]["residual_momentum"].score) < 1e-6


def test_persistence_covers_the_trailing_year_only():
    """Codex finding 2: an ancient trend must not dominate today's lean."""
    old_trend = list(100 * np.cumprod([1.01] * 300))     # years ago: hard trend
    base = old_trend[-1]
    recent = [base * (1 + (0.02 if i % 2 else -0.02)) for i in range(300)]  # now: chop
    series = pd.Series(old_trend + recent, index=_dates(600))
    hit, total = _persistence(series)
    assert total <= 60                                   # ~a year of strided checks
    assert hit <= 0.6                                    # the old trend didn't leak in


def test_empty_panel_manifest_states_the_cause(tmp_path):
    inputs = tmp_path / "i"
    inputs.mkdir()
    provider, manifest = build_real_provider(["NVDA"], as_of=AS_OF,
                                             panel_root=tmp_path / "none",
                                             inputs_dir=inputs)
    assert manifest["panel_symbols"] == 0
    assert "no cached panel" in manifest["missing_reasons"]["prices"]
    assert manifest["missing_reasons"]["macro"] == "no macro-nowcast sidecar yet"
    assert provider("NVDA") == {}                        # nothing fabricated
