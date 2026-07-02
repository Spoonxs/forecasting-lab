"""Soccer Elo with a draw model (three outcomes: home / draw / away).

Tennis and basketball are two-outcome; soccer needs a third. This uses the
**Davidson (1970)** extension of the Bradley-Terry model, which adds a draw
parameter ``nu`` on top of the Elo win-odds:

    let d = 10 ** ((R_home + home_adv - R_away) / 400)   # home:away odds
    P(home) = d            / (d + 1/d ... )   -> normalised with the draw term
    P(draw) = nu * sqrt(...) ...

Concretely, with ``g = 10**((R_home + home_adv - R_away)/400)``:

    P(home) = g / (g + 1 + nu*sqrt(g))
    P(away) = 1 / (g + 1 + nu*sqrt(g))
    P(draw) = nu*sqrt(g) / (g + 1 + nu*sqrt(g))

``nu`` controls draw frequency (≈1.0 → ~26% draws, realistic for league play).
Updates use the standard Elo delta on the home-win score (win=1, draw=0.5,
loss=0). Evaluate with the **ranked probability score** (RPS) — the proper
multi-class analogue of Brier for ordered outcomes — against the base-rate model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

OUTCOMES = ("home", "draw", "away")


def match_probs(rating_home: float, rating_away: float, home_adv: float, nu: float) -> tuple[float, float, float]:
    """Davidson (home, draw, away) probabilities. Sums to 1."""
    g = 10 ** ((rating_home + home_adv - rating_away) / 400.0)
    denom = g + 1.0 + nu * math.sqrt(g)
    return g / denom, nu * math.sqrt(g) / denom, 1.0 / denom


def ranked_probability_score(probs, outcome_idx: int) -> float:
    """RPS for one ordered 3-outcome forecast (0 best). Proper scoring rule."""
    cum_p, cum_o, total = 0.0, 0.0, 0.0
    for k in range(len(probs)):
        cum_p += probs[k]
        cum_o += 1.0 if k == outcome_idx else 0.0
        total += (cum_p - cum_o) ** 2
    return total / (len(probs) - 1)


@dataclass
class SoccerElo:
    """Team Elo with a Davidson draw model and home advantage."""

    base_rating: float = 1500.0
    k_factor: float = 20.0
    home_adv: float = 60.0  # Elo points (~league home edge)
    nu: float = 1.05  # draw propensity
    season_reversion: float = 0.25

    ratings: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    def rating(self, team: str) -> float:
        return self.ratings.get(team, self.base_rating)

    def predict(self, home: str, away: str, neutral: bool = False) -> tuple[float, float, float]:
        adv = 0.0 if neutral else self.home_adv
        return match_probs(self.rating(home), self.rating(away), adv, self.nu)

    def update(self, home: str, away: str, home_goals: int, away_goals: int, neutral: bool = False) -> None:
        adv = 0.0 if neutral else self.home_adv
        # expected home score under the win/draw/loss = 1/0.5/0 convention
        p_home, p_draw, _ = match_probs(self.rating(home), self.rating(away), adv, self.nu)
        exp_home = p_home + 0.5 * p_draw
        if home_goals > away_goals:
            actual = 1.0
        elif home_goals == away_goals:
            actual = 0.5
        else:
            actual = 0.0
        delta = self.k_factor * (actual - exp_home)
        self.ratings[home] = self.rating(home) + delta
        self.ratings[away] = self.rating(away) - delta
        self.counts[home] = self.counts.get(home, 0) + 1
        self.counts[away] = self.counts.get(away, 0) + 1

    def new_season(self) -> None:
        for team, r in self.ratings.items():
            self.ratings[team] = r + self.season_reversion * (self.base_rating - r)

    def fit(self, matches: pd.DataFrame, *, date_col: str = "date", season_col: str | None = "season") -> pd.DataFrame:
        """Walk matches; return pre-match (home, draw, away) probs + outcome idx."""
        df = matches.sort_values(date_col, kind="stable") if date_col in matches.columns else matches
        rows, current = [], None
        for r in df.itertuples(index=False):
            if season_col and hasattr(r, season_col):
                s = getattr(r, season_col)
                if current is not None and s != current:
                    self.new_season()
                current = s
            home, away = r.home, r.away
            hg, ag = int(r.home_goals), int(r.away_goals)
            p = self.predict(home, away)
            outcome = 0 if hg > ag else (1 if hg == ag else 2)
            rows.append(
                {
                    "home": home, "away": away,
                    "p_home": p[0], "p_draw": p[1], "p_away": p[2],
                    "outcome": outcome,
                    "min_games": min(self.counts.get(home, 0), self.counts.get(away, 0)),
                }
            )
            self.update(home, away, hg, ag)
        return pd.DataFrame(rows)


def evaluate_rps(preds: pd.DataFrame) -> dict:
    """Mean RPS of the model vs a static base-rate (climatology) model."""
    probs = preds[["p_home", "p_draw", "p_away"]].to_numpy()
    outcomes = preds["outcome"].to_numpy()
    model = float(np.mean([ranked_probability_score(probs[i], outcomes[i]) for i in range(len(preds))]))
    base = np.bincount(outcomes, minlength=3) / len(outcomes)
    base_rps = float(np.mean([ranked_probability_score(base, o) for o in outcomes]))
    return {
        "n": int(len(preds)),
        "rps": model,
        "rps_baseline": base_rps,
        "rps_skill": 1.0 - model / base_rps if base_rps else 0.0,
        "base_rates": {"home": float(base[0]), "draw": float(base[1]), "away": float(base[2])},
    }


_FOOTBALL_DATA = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"


def load_matches(season: str = "2324", div: str = "E0") -> pd.DataFrame:
    """Real match results from football-data.co.uk (free).

    ``season`` is their code (e.g. "2324" = 2023/24); ``div`` is the division
    (E0 = Premier League, D1 = Bundesliga, SP1 = La Liga, I1 = Serie A, F1 = Ligue 1).
    Returns the same shape as :func:`synthetic_league`: date/season/home/away/
    home_goals/away_goals. Works from any unblocked network (incl. GitHub runners)."""
    import io

    from ..utils.http import HttpClient

    url = _FOOTBALL_DATA.format(season=season, div=div)
    text = HttpClient().get(url).text
    raw = pd.read_csv(io.StringIO(text))
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce"),
            "season": f"{div}-{season}",
            "home": raw["HomeTeam"].astype("string"),
            "away": raw["AwayTeam"].astype("string"),
            "home_goals": pd.to_numeric(raw["FTHG"], errors="coerce"),
            "away_goals": pd.to_numeric(raw["FTAG"], errors="coerce"),
        }
    )
    return out.dropna(subset=["home", "away", "home_goals", "away_goals", "date"]).reset_index(drop=True)


def synthetic_league(n_teams: int = 20, n_seasons: int = 3, seed: int = 0) -> pd.DataFrame:
    """Double round-robin seasons from latent strengths (Poisson goals w/ home edge)."""
    rng = np.random.default_rng(seed)
    teams = [f"CLUB{i:02d}" for i in range(n_teams)]
    strength = rng.normal(0, 0.30, n_teams)
    rows, day = [], pd.Timestamp("2023-08-01")
    for season in range(n_seasons):
        strength = 0.8 * strength + rng.normal(0, 0.2, n_teams)
        fixtures = [(i, j) for i in range(n_teams) for j in range(n_teams) if i != j]
        rng.shuffle(fixtures)
        for k, (i, j) in enumerate(fixtures):
            # intercept/edge tuned so outcome rates look like a real league
            # (~44% home, ~22% draw, ~34% away)
            lam_home = math.exp(0.05 + strength[i] - strength[j] + 0.25)
            lam_away = math.exp(0.05 + strength[j] - strength[i])
            hg, ag = int(rng.poisson(lam_home)), int(rng.poisson(lam_away))
            rows.append((day + pd.Timedelta(days=season * 300 + k // 8), f"S{season}", teams[i], teams[j], hg, ag))
    return pd.DataFrame(rows, columns=["date", "season", "home", "away", "home_goals", "away_goals"])
