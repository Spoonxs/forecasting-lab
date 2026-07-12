"""The real nightly component provider (P8-3) — the audit's main fix.

`default_component_provider` fed the verdict engine 0–2 components, so the
coverage gate (correctly) rated nothing. This module computes real evidence
from the price panel, cross-sectionally, point-in-time:

- **trend** — the existing secular-momentum composite shape (ret_60d,
  pct_from_high, ret_20d) as a cross-sectional z, squashed to [-1, 1];
- **backtest** — a per-symbol walk-forward persistence check: did the sign of
  20d momentum predict the sign of the NEXT 5d over the past year? The lean is
  the current momentum sign scaled by that walk-forward hit rate — honestly
  caveated "not yet calibrated" with the sample size on screen;
- **residual_momentum** — each name's return minus beta × the equal-weight
  market, trailing mean, cross-sectional z (the V6 idea on live data);
- **squeeze** — the Reg-SHO short-volume ratio from the tidy store, when
  present and fresh;
- **news** — headline tone for names in the trending scan (minor weight);
- **macro** — the nowcast sidecar (P8-1), one regime for every symbol.

Everything scores AFTER the close it uses (`as_of` = the panel's last date;
the future guard strips anything later). A run MANIFEST is produced alongside:
which components were available for how many names, and why the rest are
missing — the coverage dashboard reads it. Missing stays missing; nothing is
imputed. Not financial advice.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from ..signals.verdict import Component
from .prices import _future_guard, panel_frame

TREND_WEIGHTS = {"ret_60d": 1.0, "pct_from_high": 0.75, "ret_20d": 0.75}
Z_SQUASH = 3.0            # cross-sectional z / 3, clipped — same family as default
RESID_WINDOW = 10         # trailing days of residual averaged
PERSISTENCE_STEP = 5      # walk-forward stride (days) for the backtest check
SQUEEZE_CENTER = 0.45     # Reg-SHO ratio around which pressure is neutral
SQUEEZE_MAX_AGE_DAYS = 7  # older short-volume facts don't fire


def _clip(x: float) -> float:
    return float(np.clip(x, -1.0, 1.0))


def _zmap(values: pd.Series) -> pd.Series:
    sd = values.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return values * 0.0
    return (values - values.mean()) / sd


# ------------------------------------------------------------- panel maths
def panel_components(frame: pd.DataFrame, as_of: date) -> dict[str, dict[str, Component]]:
    """trend + backtest + residual_momentum per symbol, from closes alone.
    Symbols missing from the frame simply have no entry (missing evidence)."""
    frame = _future_guard(frame, as_of)
    if frame.empty or len(frame) < 80:
        return {}
    rets = frame.pct_change().iloc[1:]
    mkt = rets.mean(axis=1)
    # ddof must MATCH Series.cov's (ddof=1) or every beta inflates by n/(n-1)
    # (Codex review)
    mkt_var = float(mkt.var(ddof=1)) or 1e-12

    feats = pd.DataFrame({
        "ret_20d": frame.iloc[-1] / frame.iloc[-21] - 1.0,
        "ret_60d": frame.iloc[-1] / frame.iloc[-61] - 1.0,
        "pct_from_high": frame.iloc[-1] / frame.max() - 1.0,
    })
    trend_raw = sum(w * _zmap(feats[c]) for c, w in TREND_WEIGHTS.items())

    resid_mom = {}
    for sym in frame.columns:
        r = rets[sym]
        beta = float(r.cov(mkt) / mkt_var)
        resid = r - beta * mkt
        resid_mom[sym] = float(resid.tail(RESID_WINDOW).mean())
    resid_z = _zmap(pd.Series(resid_mom))

    out: dict[str, dict[str, Component]] = {}
    for sym in frame.columns:
        comps: dict[str, Component] = {}
        comps["trend"] = Component(
            "trend", _clip(float(trend_raw[sym]) / Z_SQUASH), 0.6,
            f"secular-momentum composite z {float(trend_raw[sym]):+.2f} "
            f"(60d {feats.loc[sym, 'ret_60d']:+.1%})")
        hit, n = _persistence(frame[sym])
        if n >= 12:
            lean = np.sign(feats.loc[sym, "ret_20d"]) * (hit - 0.5) * 4.0
            comps["backtest"] = Component(
                "backtest", _clip(float(lean)), min(0.55, 0.25 + n / 100.0),
                f"walk-forward: 20d momentum called the next 5d {hit:.0%} of "
                f"{n} checks — not yet calibrated")
        comps["residual_momentum"] = Component(
            "residual_momentum", _clip(float(resid_z[sym]) / Z_SQUASH), 0.5,
            f"return minus beta x market, {RESID_WINDOW}d trailing "
            f"(z {float(resid_z[sym]):+.2f})")
        out[sym] = comps
    return out


PERSISTENCE_LOOKBACK = 252  # the check covers the trailing YEAR only — old
                            # regimes must not dominate the current lean (Codex)


def _persistence(closes: pd.Series) -> tuple[float, int]:
    """Walk-forward over the trailing year: at each stride, did sign(trailing
    20d ret) match sign(NEXT 5d ret)? Completed forward windows only."""
    px = closes.to_numpy(dtype=float)[-(PERSISTENCE_LOOKBACK + PERSISTENCE_STEP + 21):]
    hits = total = 0
    for t in range(21, len(px) - PERSISTENCE_STEP, PERSISTENCE_STEP):
        mom = px[t] / px[t - 20] - 1.0
        fwd = px[t + PERSISTENCE_STEP] / px[t] - 1.0
        if mom == 0 or fwd == 0:
            continue
        total += 1
        hits += int(np.sign(mom) == np.sign(fwd))
    return (hits / total if total else 0.5), total


# ------------------------------------------------------------- assembly
def build_real_provider(symbols: list[str], *, as_of: date,
                        panel_root=None, store=None,
                        inputs_dir=None) -> tuple:
    """(provider, manifest): the provider closure feeds `build_verdicts`; the
    manifest says what evidence existed and why the rest is missing."""
    frame = panel_frame(symbols, root=panel_root)
    per_symbol = panel_components(frame, as_of) if not frame.empty else {}

    from .digest import read_latest_data

    macro_comp = None
    macro = read_latest_data("macro-nowcast", out_dir=inputs_dir) or {}
    prob = macro.get("recession_prob_12m")
    if prob is not None:
        macro_comp = Component("macro", _clip(0.5 - float(prob)), 0.7,
                               f"recession odds {float(prob):.0%}")

    news_tone: dict[str, Component] = {}
    movers = (read_latest_data("trending-stocks", out_dir=inputs_dir) or {}).get("movers", [])
    for card in movers:
        sym, head = str(card.get("ticker", "")).upper(), card.get("headline") or ""
        if sym and head:
            try:
                from ..media.sentiment import score_text

                tone = float(score_text(head))
            except Exception:  # noqa: BLE001 - tone is optional garnish
                tone = 0.0
            news_tone[sym] = Component("news", _clip(tone), 0.4,
                                       f"headline tone {tone:+.2f}: {head[:60]}")

    squeeze: dict[str, Component] = {}
    if store is None:
        from ..sources.store import TidyStore

        store = TidyStore()
    try:
        df = store.load()
        sub = df[df["metric"] == "short_volume_ratio"] if not df.empty else df
        if not sub.empty:
            day = str(sub["date"].max())
            if (as_of - date.fromisoformat(day)).days <= SQUEEZE_MAX_AGE_DAYS:
                rows = sub[sub["date"] == day]
                for sym, val in zip(rows["entity"], rows["value"], strict=False):
                    squeeze[str(sym).upper()] = Component(
                        "squeeze", _clip((float(val) - SQUEEZE_CENTER) * 5.0), 0.4,
                        f"Reg-SHO short-volume ratio {float(val):.2f} ({day})")
    except Exception:  # noqa: BLE001 - a broken store is absent evidence
        pass

    def provider(symbol: str) -> dict[str, Component]:
        s = symbol.upper()
        comps = dict(per_symbol.get(s, {}))
        if macro_comp is not None:
            comps["macro"] = macro_comp
        if s in news_tone:
            comps["news"] = news_tone[s]
        if s in squeeze:
            comps["squeeze"] = squeeze[s]
        return comps

    manifest = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "panel_symbols": int(len(frame.columns)) if not frame.empty else 0,
        "panel_rows": int(len(frame)) if not frame.empty else 0,
        "requested_symbols": len(symbols),
        "components_available": {
            "trend": len(per_symbol),
            "backtest": sum(1 for c in per_symbol.values() if "backtest" in c),
            "residual_momentum": len(per_symbol),
            "macro": len(symbols) if macro_comp is not None else 0,
            "news": len(news_tone),
            "squeeze": len(squeeze),
            "yield": 0,
        },
        "missing_reasons": {
            "prices": ("no cached panel — run the price panel update"
                       if frame.empty else
                       f"{len(symbols) - len(per_symbol)} symbol(s) lack a usable "
                       "cached history (short, failed, or not yet fetched)"),
            "macro": None if macro_comp is not None else "no macro-nowcast sidecar yet",
            "news": "headline tone exists only for names in the trending scan",
            "squeeze": ("Reg-SHO facts fresh within "
                        f"{SQUEEZE_MAX_AGE_DAYS}d cover {len(squeeze)} name(s)"),
            "yield": "no per-instrument dividend-yield source yet — honestly absent",
        },
    }
    return provider, manifest


# ------------------------------------------------------------- the gates
RATED_GATE = 0.60  # the P8 acceptance bar: this share of the tier must rate


def coverage_stats(payload: dict, manifest: dict) -> dict:
    """The nightly acceptance numbers (Codex planning consult): published in
    the manifest and on the coverage panel; a miss is stated LOUDLY, never
    silently shipped as success."""
    verdicts = payload.get("verdicts", {})
    n = len(verdicts) or 1
    rated = sum(1 for r in verdicts.values()
                if not str(r.get("label", "")).startswith("INSUFFICIENT"))
    import statistics

    comp_counts = [len(r.get("components", {})) for r in verdicts.values()]
    # a true median (Codex review): the upper-middle shortcut overstated
    # coverage on even counts ([0,0,3,3] read as 3 instead of 1.5)
    median_components = float(statistics.median(comp_counts)) if comp_counts else 0.0
    failures = len((manifest.get("panel_run") or {}).get("failed", []))
    stats = {
        "n_symbols": len(verdicts),
        "rated": rated,
        "pct_rated": round(rated / n, 4),
        "median_components": median_components,
        "panel_failures": failures,
        "gate_pct_rated": RATED_GATE,
        "gate_passed": (rated / n) >= RATED_GATE,
    }
    return stats
