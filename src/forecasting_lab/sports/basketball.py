"""Basketball (NBA-style) Elo: home advantage + margin-of-victory adjustment.

Differences from tennis Elo (see :mod:`.elo`), following FiveThirtyEight's NBA
methodology:

- **Home advantage**: the home team gets a rating bonus (~100 Elo points in the
  NBA) inside the win-probability formula only — the stored rating is neutral.
- **Margin of victory**: a blowout carries more information than a 1-point win.
  The update is scaled by 538's multiplier, which grows with point margin and
  shrinks when the favorite wins big (autocorrelation guard):

      mult = ((margin + 3) ** 0.8) / (7.5 + 0.006 * elo_diff_winner)

- **Season carry-over**: teams revert 25% toward the mean between seasons
  (rosters change, but not completely).

The fit loop is strictly time-forward like the tennis model: record the
pre-game prediction, then update. Evaluate with Brier + reliability, never bare
accuracy — the home team wins ~60% of NBA games, so that's the base rate to beat.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .elo import expected_score


@dataclass
class BasketballElo:
    """Team Elo with home advantage and margin-of-victory updates."""

    base_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 100.0  # Elo points added to the home team's effective rating
    mov_enabled: bool = True
    season_reversion: float = 0.25  # fraction reverted to mean at a season boundary

    ratings: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    def rating(self, team: str) -> float:
        return self.ratings.get(team, self.base_rating)

    # ---- prediction ----------------------------------------------------
    def predict_proba(self, home: str, away: str, neutral: bool = False) -> float:
        """P(home team wins), including home advantage unless ``neutral``."""
        bonus = 0.0 if neutral else self.home_advantage
        return expected_score(self.rating(home) + bonus, self.rating(away))

    # ---- update --------------------------------------------------------
    def _mov_multiplier(self, margin: float, winner_elo_diff: float) -> float:
        """538's margin-of-victory multiplier (1.0 when MOV handling is off)."""
        if not self.mov_enabled:
            return 1.0
        return ((abs(margin) + 3.0) ** 0.8) / (7.5 + 0.006 * winner_elo_diff)

    def update(
        self,
        home: str,
        away: str,
        home_points: float,
        away_points: float,
        neutral: bool = False,
    ) -> None:
        """Apply one final score. Ties are not a thing in basketball."""
        if home_points == away_points:
            raise ValueError("basketball games cannot end tied")
        p_home = self.predict_proba(home, away, neutral=neutral)
        home_won = home_points > away_points
        margin = home_points - away_points

        bonus = 0.0 if neutral else self.home_advantage
        winner_elo_diff = (
            (self.rating(home) + bonus - self.rating(away))
            if home_won
            else (self.rating(away) - self.rating(home) - bonus)
        )
        mult = self._mov_multiplier(margin, winner_elo_diff)
        delta = self.k_factor * mult * ((1.0 if home_won else 0.0) - p_home)

        self.ratings[home] = self.rating(home) + delta
        self.ratings[away] = self.rating(away) - delta
        self.counts[home] = self.counts.get(home, 0) + 1
        self.counts[away] = self.counts.get(away, 0) + 1

    def new_season(self) -> None:
        """Revert every team ``season_reversion`` of the way toward the mean."""
        for team, r in self.ratings.items():
            self.ratings[team] = r + self.season_reversion * (self.base_rating - r)

    # ---- fit / evaluate ------------------------------------------------
    def fit(
        self,
        games: pd.DataFrame,
        *,
        home_col: str = "home",
        away_col: str = "away",
        home_pts_col: str = "home_pts",
        away_pts_col: str = "away_pts",
        date_col: str | None = "date",
        season_col: str | None = "season",
    ) -> pd.DataFrame:
        """Walk games chronologically; return pre-game predictions for scoring.

        The prediction target is ``y = 1[home won]`` with ``p_home`` — naturally
        non-degenerate because home teams lose 40% of the time. ``min_games``
        (the lesser of the two teams' prior game counts) supports burn-in
        filtering, and season boundaries trigger rating reversion.
        """
        df = games
        if date_col and date_col in df.columns:
            df = df.sort_values(date_col, kind="stable")

        records = []
        current_season = None
        for row in df.itertuples(index=False):
            if season_col and hasattr(row, season_col):
                season = getattr(row, season_col)
                if current_season is not None and season != current_season:
                    self.new_season()
                current_season = season

            home, away = getattr(row, home_col), getattr(row, away_col)
            hp, ap = getattr(row, home_pts_col), getattr(row, away_pts_col)
            p_home = self.predict_proba(home, away)
            records.append(
                {
                    "date": getattr(row, date_col) if date_col and hasattr(row, date_col) else None,
                    "home": home,
                    "away": away,
                    "p_home": p_home,
                    "y": 1 if hp > ap else 0,
                    "margin": hp - ap,
                    "min_games": min(self.counts.get(home, 0), self.counts.get(away, 0)),
                }
            )
            self.update(home, away, hp, ap)

        return pd.DataFrame.from_records(records)

    def leaderboard(self, top: int = 15) -> pd.DataFrame:
        items = sorted(self.ratings.items(), key=lambda kv: kv[1], reverse=True)
        return pd.DataFrame(items[:top], columns=["team", "rating"])


def synthetic_season(
    n_teams: int = 30,
    n_games: int = 2400,
    n_seasons: int = 2,
    seed: int = 0,
    home_advantage_pts: float = 2.5,
) -> pd.DataFrame:
    """Generate NBA-shaped results from latent team strengths.

    Scores are built from a latent strength gap plus home advantage plus noise,
    calibrated so home teams win ~60% and typical margins look like real box
    scores. Deterministic given ``seed``.
    """
    rng = np.random.default_rng(seed)
    teams = [f"TEAM{i:02d}" for i in range(n_teams)]
    rows = []
    game = 0
    for season in range(n_seasons):
        # strengths drift a little between seasons
        if season == 0:
            strength = rng.normal(0.0, 4.0, size=n_teams)
        else:
            strength = 0.75 * strength + rng.normal(0.0, 2.0, size=n_teams)  # noqa: F821
        for _ in range(n_games // n_seasons):
            i, j = rng.choice(n_teams, size=2, replace=False)
            expected_margin = strength[i] - strength[j] + home_advantage_pts
            margin = expected_margin + rng.normal(0, 11.0)  # NBA-like noise
            base = rng.integers(100, 121)
            hp = float(base + max(margin, 0) + rng.integers(0, 4))
            ap = float(base - min(margin, 0) + rng.integers(0, 4))
            if hp == ap:  # no ties
                hp += 1.0
            day = pd.Timestamp("2023-10-01") + pd.Timedelta(days=season * 365 + game % 170)
            rows.append((day, f"S{season}", teams[i], teams[j], hp, ap))
            game += 1
    return pd.DataFrame(rows, columns=["date", "season", "home", "away", "home_pts", "away_pts"])
