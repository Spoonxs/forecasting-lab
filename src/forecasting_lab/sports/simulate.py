"""Monte Carlo tournament simulation.

Model each match as a Bernoulli trial on the Elo win probability, then simulate a
single-elimination bracket thousands of times to get title and finalist
distributions. Vectorised across simulations: the pairwise win-probability matrix
is computed once, then every round is a batched lookup + Bernoulli draw.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .elo import EloModel


def simulate_tournament(
    model: EloModel,
    bracket: list[str],
    surface: str | None = None,
    n_sims: int = 10_000,
    seed: int = 0,
) -> pd.DataFrame:
    """Simulate a single-elimination bracket ``n_sims`` times.

    Parameters
    ----------
    bracket:
        Player names in seeding/draw order. Length must be a power of two; index
        ``2i`` plays ``2i+1`` in round 1, and so on.

    Returns
    -------
    DataFrame indexed by player with columns ``p_title`` and ``p_final``
    (probability of reaching the championship match), sorted by ``p_title``.
    """
    n = len(bracket)
    if n < 2 or (n & (n - 1)) != 0:
        raise ValueError(f"bracket size must be a power of two >= 2, got {n}")
    if len(set(bracket)) != n:
        raise ValueError("bracket has duplicate players")

    # Pairwise probability matrix P[i, j] = P(i beats j).
    idx = np.arange(n)
    P = np.empty((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            P[i, j] = 0.5 if i == j else model.predict_proba(bracket[i], bracket[j], surface)

    rng = np.random.default_rng(seed)
    survivors = np.tile(idx, (n_sims, 1))  # (n_sims, n)
    reached_final = np.zeros(n, dtype=np.int64)

    while survivors.shape[1] > 1:
        a = survivors[:, 0::2]
        b = survivors[:, 1::2]
        if survivors.shape[1] == 2:  # this round produces the champion
            reached_final += np.bincount(a.ravel(), minlength=n)
            reached_final += np.bincount(b.ravel(), minlength=n)
        p_a = P[a, b]
        a_wins = rng.random(p_a.shape) < p_a
        survivors = np.where(a_wins, a, b)

    champions = survivors[:, 0]
    title_counts = np.bincount(champions, minlength=n)

    out = pd.DataFrame(
        {
            "player": bracket,
            "p_title": title_counts / n_sims,
            "p_final": reached_final / n_sims,
        }
    ).set_index("player")
    return out.sort_values("p_title", ascending=False)


def rounds_in_bracket(n_players: int) -> int:
    """Number of single-elimination rounds for ``n_players`` (a power of two)."""
    return int(math.log2(n_players))
