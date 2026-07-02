"""Tennis Elo: global + surface-specific ratings.

Design follows the FiveThirtyEight tennis approach:
- Standard Elo logistic win probability.
- A per-player K-factor that starts high and decays with matches played, so new
  players move fast and established ratings are stable: ``K = 250 / (n + 5)^0.4``.
- Separate Hard / Clay / Grass ratings, blended with the global rating by a
  tunable ``surface_weight``.

The :meth:`EloModel.fit` loop is strictly time-forward: it records the *pre-match*
prediction, then updates ratings. That ordering is what keeps the held-out Brier
score honest — no look-ahead. See ``project-forecasting-lab.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

SURFACES = ("Hard", "Clay", "Grass")


def expected_score(rating_a: float, rating_b: float) -> float:
    """Elo win probability for A vs B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


@dataclass
class EloModel:
    """Stateful Elo with global and per-surface ratings.

    Parameters
    ----------
    base_rating:
        Starting rating for an unseen player (default 1500).
    surface_weight:
        Blend weight on the surface-specific probability vs the global one,
        in [0, 1]. 0 ignores surface; 1 uses surface only. Default 0.5.
    k_factor:
        If set, a constant K. If None (default), use the decaying 538 formula
        ``k_scale / (n + k_shift) ** k_decay``.
    """

    base_rating: float = 1500.0
    surface_weight: float = 0.5
    k_factor: float | None = None
    k_scale: float = 250.0
    k_shift: float = 5.0
    k_decay: float = 0.4

    global_ratings: dict[str, float] = field(default_factory=dict)
    surface_ratings: dict[str, dict[str, float]] = field(
        default_factory=lambda: {s: {} for s in SURFACES}
    )
    global_counts: dict[str, int] = field(default_factory=dict)
    surface_counts: dict[str, dict[str, int]] = field(
        default_factory=lambda: {s: {} for s in SURFACES}
    )

    # ---- rating access -------------------------------------------------
    def rating(self, player: str, surface: str | None = None) -> float:
        if surface in SURFACES:
            return self.surface_ratings[surface].get(player, self.base_rating)
        return self.global_ratings.get(player, self.base_rating)

    def _k(self, count: int) -> float:
        if self.k_factor is not None:
            return self.k_factor
        return self.k_scale / (count + self.k_shift) ** self.k_decay

    # ---- prediction ----------------------------------------------------
    def predict_proba(self, player_a: str, player_b: str, surface: str | None = None) -> float:
        """P(A beats B), blending global and surface ratings."""
        p_global = expected_score(self.rating(player_a), self.rating(player_b))
        if surface in SURFACES and self.surface_weight > 0:
            p_surf = expected_score(
                self.rating(player_a, surface), self.rating(player_b, surface)
            )
            return self.surface_weight * p_surf + (1.0 - self.surface_weight) * p_global
        return p_global

    # ---- update --------------------------------------------------------
    def update(self, winner: str, loser: str, surface: str | None = None) -> None:
        """Apply one match result to global and (if known) surface ratings."""
        rw, rl = self.rating(winner), self.rating(loser)
        e_w = expected_score(rw, rl)  # P(winner beats loser); loser's expected = 1 - e_w
        k_w = self._k(self.global_counts.get(winner, 0))
        k_l = self._k(self.global_counts.get(loser, 0))
        self.global_ratings[winner] = rw + k_w * (1.0 - e_w)
        self.global_ratings[loser] = rl - k_l * (1.0 - e_w)  # actual 0 minus expected (1 - e_w)
        self.global_counts[winner] = self.global_counts.get(winner, 0) + 1
        self.global_counts[loser] = self.global_counts.get(loser, 0) + 1

        if surface in SURFACES:
            sr = self.surface_ratings[surface]
            sc = self.surface_counts[surface]
            rws, rls = sr.get(winner, self.base_rating), sr.get(loser, self.base_rating)
            e_ws = expected_score(rws, rls)
            k_ws = self._k(sc.get(winner, 0))
            k_ls = self._k(sc.get(loser, 0))
            sr[winner] = rws + k_ws * (1.0 - e_ws)
            sr[loser] = rls - k_ls * (1.0 - e_ws)
            sc[winner] = sc.get(winner, 0) + 1
            sc[loser] = sc.get(loser, 0) + 1

    # ---- fit / evaluate ------------------------------------------------
    def fit(
        self,
        matches: pd.DataFrame,
        *,
        winner_col: str = "winner",
        loser_col: str = "loser",
        surface_col: str = "surface",
        date_col: str | None = "date",
        record: bool = True,
    ) -> pd.DataFrame:
        """Walk the matches chronologically, updating ratings.

        Each match is canonicalised to an (A, B) pair by name sort so the label
        ``y = 1[A won]`` is non-trivial (~balanced) — otherwise "predict the
        winner wins" would be a degenerate all-ones target. Returns a frame of
        *pre-match* predictions suitable for :mod:`forecasting_lab.eval`.

        The frame includes ``min_matches`` (the smaller of the two players'
        prior match counts) so callers can drop cold-start rows from evaluation
        while still training on them.
        """
        df = matches
        if date_col and date_col in df.columns:
            df = df.sort_values(date_col, kind="stable")

        records = []
        for row in df.itertuples(index=False):
            winner = getattr(row, winner_col)
            loser = getattr(row, loser_col)
            surface = getattr(row, surface_col, None) if surface_col else None
            if surface not in SURFACES:
                surface = None

            if record:
                # canonical ordering, independent of who won
                player_a, player_b = sorted((str(winner), str(loser)))
                p_a = self.predict_proba(player_a, player_b, surface)
                y = 1 if player_a == str(winner) else 0
                n_min = min(
                    self.global_counts.get(winner, 0), self.global_counts.get(loser, 0)
                )
                rec = {
                    "player_a": player_a,
                    "player_b": player_b,
                    "surface": surface,
                    "p_a": p_a,
                    "y": y,
                    "min_matches": n_min,
                }
                if date_col and date_col in df.columns:
                    rec["date"] = getattr(row, date_col)
                records.append(rec)

            self.update(winner, loser, surface)

        cols = ["date", "player_a", "player_b", "surface", "p_a", "y", "min_matches"]
        out = pd.DataFrame.from_records(records)
        if not out.empty:
            out = out[[c for c in cols if c in out.columns]]
        return out

    def leaderboard(self, top: int = 20) -> pd.DataFrame:
        """Current global ratings, highest first."""
        items = sorted(self.global_ratings.items(), key=lambda kv: kv[1], reverse=True)
        return pd.DataFrame(items[:top], columns=["player", "rating"])
