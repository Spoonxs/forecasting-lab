"""Market data for the arena.

The synthetic market is regime-aware: each asset's drift follows a slow AR(1),
so trends persist (momentum has something real to find) while noise dominates
day to day (nothing is free). Deterministic given the seed — which is what lets
the arena regenerate identical prices when resuming from saved state.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def synthetic_market(
    n_assets: int = 12,
    n_bars: int = 2000,
    seed: int = 0,
    drift_persistence: float = 0.992,
    drift_vol: float = 0.00022,
    noise_vol: float = 0.017,
) -> pd.DataFrame:
    """Daily close prices, one column per asset, ``n_bars`` rows.

    Each asset: ``r_t = mu_t + eps_t`` with ``mu_t = rho * mu_{t-1} + eta_t``.
    High ``rho`` makes multi-month trends; ``noise_vol >> drift_vol`` keeps the
    daily signal-to-noise realistic (mostly noise).
    """
    rng = np.random.default_rng(seed)
    names = [f"A{i:02d}" for i in range(n_assets)]
    mu = np.zeros(n_assets)
    rets = np.empty((n_bars, n_assets))
    for t in range(n_bars):
        mu = drift_persistence * mu + rng.normal(0, drift_vol, n_assets)
        rets[t] = mu + rng.normal(0, noise_vol, n_assets)
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    return pd.DataFrame(prices, columns=names)


def real_market(symbols: list[str], range_: str = "1y") -> pd.DataFrame:
    """Daily closes for real symbols via the Yahoo chart API (needs network).

    Symbols whose history can't be fetched are dropped; columns are aligned on
    the intersection of dates.
    """
    from ..signals.trending import TrendingFetcher

    fetcher = TrendingFetcher()
    series = {}
    for symbol in symbols:
        hist = fetcher.daily_history(symbol, range_=range_)
        if len(hist) >= 60:
            series[symbol] = hist.set_index("date")["close"]
    if not series:
        raise RuntimeError(f"no usable history for any of {symbols}")
    # Keep the DatetimeIndex: the arena reads positionally (.iloc) so it's
    # unaffected, and the forward study needs real dates to label its marks.
    return pd.DataFrame(series).dropna()
