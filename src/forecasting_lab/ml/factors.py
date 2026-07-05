"""Cross-sectional factor/residual layer (MASTER_PLAN V6).

Three estimation patterns adopted from the one rigorous open factor model in the
field review (Apache-2.0; re-implemented here, not ported):

1. **Weighted LS with exact zero-sum constraints** — categorical (sector-style)
   factor returns are forced to sum to zero cap-weighted across the market, via
   the KKT block system, so the market factor keeps the level and categories are
   strictly relative.
2. **As-of discipline** — every feature at date *t* is computed from rows
   strictly before *t* (the same contract as ``ml.features.lag_features``); a
   test mutates the future and asserts nothing changes.
3. **MAD winsorize → z-score** — robust cross-sectional prep that caps outliers
   at k median-absolute-deviations before normalising.

What we deliberately did NOT adopt: their in-sample factor-accept gate
(``after_var < before_var`` on the same fit window — the curve-fit trap). Here a
factor earns its place only by **out-of-sample rank IC under the purged
walk-forward CV** (:func:`walk_forward_rank_ic`), like every other edge.

The payoff feature is **residual momentum**: rank names by the trailing mean of
their *factor-residual* returns instead of raw returns — persistent stock-specific
drift is visible once common factor noise is regressed away.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .cv import PurgedWalkForwardCV
from .tune import rank_ic

# ---------------------------------------------------------------- robust prep


def mad_winsorize(values: np.ndarray, k: float = 5.0) -> np.ndarray:
    """Clamp values to ``median ± k * MAD`` (scaled to sigma-equivalents)."""
    v = np.asarray(values, dtype=float)
    med = float(np.nanmedian(v))
    mad = float(np.nanmedian(np.abs(v - med)))
    if mad == 0.0:
        return v.copy()
    sigma = 1.4826 * mad  # MAD -> sigma for a normal
    return np.clip(v, med - k * sigma, med + k * sigma)


def mad_winsorize_zscore(
    panel: pd.DataFrame,
    cols,
    date_col: str = "date",
    k: float = 5.0,
    suffix: str = "_rz",
) -> pd.DataFrame:
    """Per-date MAD-winsorize then z-score — robust cross-sectional features."""
    cols = [cols] if isinstance(cols, str) else list(cols)
    out = panel.copy()
    for col in cols:
        winsored = out.groupby(date_col)[col].transform(lambda s: mad_winsorize(s.to_numpy(), k=k))
        grp = winsored.groupby(out[date_col])
        mean = grp.transform("mean")
        std = grp.transform("std").replace(0, np.nan)
        out[col + suffix] = ((winsored - mean) / std).astype(float)
    return out


# ------------------------------------------------------- constrained WLS core


def weighted_lstsq(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """WLS via row-scaling by sqrt-weights (weights normalised to mean 1)."""
    w = np.asarray(weights, dtype=float)
    w = w / w.mean()
    root = np.sqrt(w)
    return np.linalg.lstsq(x * root[:, None], y * root, rcond=None)[0]


def constrained_lstsq(
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    constraints: np.ndarray,
) -> np.ndarray:
    """WLS with exact linear equality constraints ``C @ beta = 0`` (KKT block solve)."""
    constraints = np.asarray(constraints, dtype=float)
    if constraints.size == 0:
        return weighted_lstsq(x, y, weights)
    w = np.asarray(weights, dtype=float)
    w = w / w.mean()
    root = np.sqrt(w)
    xw = x * root[:, None]
    yw = y * root
    n_c = constraints.shape[0]
    kkt = np.block([
        [xw.T @ xw, constraints.T],
        [constraints, np.zeros((n_c, n_c))],
    ])
    rhs = np.r_[xw.T @ yw, np.zeros(n_c)]
    return np.linalg.lstsq(kkt, rhs, rcond=None)[0][: x.shape[1]]


def zero_sum_constraint(x_frame: pd.DataFrame, columns: list[str], weights: np.ndarray) -> np.ndarray:
    """One cap-weighted zero-sum row over ``columns`` of the exposure frame."""
    row = np.zeros(x_frame.shape[1])
    totals = x_frame[columns].multiply(weights, axis=0).sum()
    for col, total in totals.items():
        row[x_frame.columns.get_loc(col)] = float(total)
    scale = float(np.abs(row).sum())
    return row if scale == 0 else row / scale


# ------------------------------------------------------------ residual layer


def factor_residuals(
    panel: pd.DataFrame,
    factor_cols,
    *,
    ret_col: str = "ret",
    date_col: str = "date",
    weight_col: str | None = None,
    categorical_cols: list[str] | None = None,
    out_col: str = "resid",
) -> pd.DataFrame:
    """Per-date cross-sectional (constrained) WLS of returns on exposures.

    ``factor_cols`` must already be **as-of** (known before the return they
    model — lag them; see ``lag_features``). Categorical one-hot columns listed
    in ``categorical_cols`` get an exact cap-weighted zero-sum constraint.
    Returns the panel with the residual column added (NaN where a date has too
    few names to regress).
    """
    factor_cols = [factor_cols] if isinstance(factor_cols, str) else list(factor_cols)
    out = panel.copy()
    out[out_col] = np.nan
    for _, grp in out.groupby(date_col):
        rows = grp.dropna(subset=[*factor_cols, ret_col])
        if len(rows) <= len(factor_cols) + 1:
            continue
        x = np.column_stack([np.ones(len(rows))] + [rows[c].to_numpy(dtype=float) for c in factor_cols])
        y = rows[ret_col].to_numpy(dtype=float)
        w = (
            rows[weight_col].to_numpy(dtype=float)
            if weight_col is not None
            else np.ones(len(rows))
        )
        x_frame = pd.DataFrame(x, columns=["const", *factor_cols], index=rows.index)
        cats = [c for c in (categorical_cols or []) if c in factor_cols]
        constraints = (
            np.array([zero_sum_constraint(x_frame, cats, w)]) if cats else np.empty((0, 0))
        )
        beta = constrained_lstsq(x, y, w, constraints)
        out.loc[rows.index, out_col] = y - x @ beta
    return out


def residual_momentum(
    panel: pd.DataFrame,
    *,
    resid_col: str = "resid",
    entity_col: str = "ticker",
    date_col: str = "date",
    window: int = 10,
    out_col: str = "resid_mom",
) -> pd.DataFrame:
    """Trailing mean of residuals per entity, **lagged one period** (as-of)."""
    out = panel.sort_values([entity_col, date_col], kind="stable").copy()
    trail = (
        out.groupby(entity_col)[resid_col]
        .transform(lambda s: s.rolling(window, min_periods=max(2, window // 2)).mean())
    )
    out[out_col] = trail.groupby(out[entity_col]).shift(1)  # known BEFORE the bar it scores
    return out


def walk_forward_rank_ic(
    panel: pd.DataFrame,
    *,
    score_col: str,
    label_col: str,
    time_col: str = "date",
    cv: PurgedWalkForwardCV | None = None,
) -> float:
    """OOS rank IC: mean per-period Spearman on the purged CV's TEST folds only."""
    cv = cv or PurgedWalkForwardCV(n_splits=4, horizon=1)
    data = panel.dropna(subset=[score_col, label_col]).reset_index(drop=True)
    if data.empty:
        return 0.0
    times = data[time_col].to_numpy()
    ics: list[float] = []
    for _, test_idx in cv.split(times):
        ic = rank_ic(data.iloc[test_idx], score_col, label_col, time_col=time_col)
        ics.append(ic)
    return float(np.mean(ics)) if ics else 0.0


# --------------------------------------------------- live metadata (optional)


def openfactor_r2_metadata(timeout: float = 10.0, fetcher=None) -> dict | None:
    """Latest openfactor R2 snapshot metadata, or None (offline/blocked/absent).

    Research-grade weekly data (~1000 US names, 102 factors) — never intraday;
    treat its ``latest`` date as the as-of. Honest degradation: any failure is
    None, never a fabricated payload.
    """
    url = "https://openfactor-data.rallies.ai/factors/openfactor-us1000/latest.json"
    try:
        if fetcher is not None:
            payload = fetcher(url)
        else:  # pragma: no cover - network path
            import requests

            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
        return payload if isinstance(payload, dict) and "latest" in payload else None
    except Exception:
        return None


# ------------------------------------------------ synthetic skill demonstration


def residual_momentum_skill_report(seed: int = 0, alpha_strength: float = 1.0) -> dict:
    """OOS rank-IC of residual momentum vs raw momentum on a planted-alpha market.

    Synthetic market: one common factor moves everything through per-name betas;
    a small persistent stock-specific drift (the plantable alpha) hides under it.
    Raw momentum mostly ranks beta noise; residual momentum recovers the drift.
    ``alpha_strength=0`` removes the alpha — both must then pin ~0 (the guard).
    """
    rng = np.random.default_rng(seed)
    n_names, n_periods = 30, 160
    beta = rng.uniform(0.5, 1.5, n_names)
    alpha = alpha_strength * rng.normal(0.0, 0.0015, n_names)  # persistent per-name drift
    factor = rng.normal(0.0, 0.02, n_periods)
    eps = rng.normal(0.0, 0.004, (n_periods, n_names))
    rets = factor[:, None] * beta[None, :] + alpha[None, :] + eps

    rows = [
        {"date": t, "ticker": i, "ret": rets[t, i], "beta_exposure": beta[i]}
        for t in range(n_periods)
        for i in range(n_names)
    ]
    panel = pd.DataFrame(rows)
    # forward relative return = next period's cross-sectionally demeaned return
    panel = panel.sort_values(["ticker", "date"], kind="stable")
    panel["fwd"] = panel.groupby("ticker")["ret"].shift(-1)
    panel["fwd"] = panel["fwd"] - panel.groupby("date")["fwd"].transform("mean")

    panel = mad_winsorize_zscore(panel, "beta_exposure", date_col="date")
    panel = factor_residuals(panel, ["beta_exposure_rz"], ret_col="ret", date_col="date")
    panel = residual_momentum(panel, window=20)
    # raw momentum: same trailing window on RAW returns, same lag
    panel = panel.sort_values(["ticker", "date"], kind="stable")
    raw_trail = panel.groupby("ticker")["ret"].transform(
        lambda s: s.rolling(20, min_periods=10).mean()
    )
    panel["raw_mom"] = raw_trail.groupby(panel["ticker"]).shift(1)

    cv = PurgedWalkForwardCV(n_splits=4, horizon=1)
    return {
        "oos_rank_ic_residual": walk_forward_rank_ic(
            panel, score_col="resid_mom", label_col="fwd", time_col="date", cv=cv
        ),
        "oos_rank_ic_raw": walk_forward_rank_ic(
            panel, score_col="raw_mom", label_col="fwd", time_col="date", cv=cv
        ),
    }
