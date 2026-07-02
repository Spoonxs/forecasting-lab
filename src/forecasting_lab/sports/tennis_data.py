"""Load Jeff Sackmann / Tennis Abstract match data.

Source: https://github.com/JeffSackmann/tennis_atp (and ``tennis_wta``).
License: CC BY-NC-SA 4.0 — attribution required, **non-commercial only**. Fine for
a research/portfolio project; if the lab ever turns commercial this data cannot be
used commercially, so keep that boundary in from the start.

CSVs are downloaded once to ``data/tennis/`` and re-read from there. For tests and
offline work, :func:`synthetic_matches` generates a realistic winner/loser frame
with no network.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..config import PATHS

# Multiple "ports" to the same data — tried in order. jsDelivr's GitHub mirror is
# a better CDN and dodges some raw.githubusercontent blocks; the raw host is the
# canonical fallback. If all fail, download_year raises with the manual path.
_MIRRORS = [
    "https://cdn.jsdelivr.net/gh/JeffSackmann/tennis_{tour}@master/{tour}_matches_{year}.csv",
    "https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master/{tour}_matches_{year}.csv",
]
_RAW = _MIRRORS[1]  # kept for back-compat references
_USE_COLS = [
    "tourney_date",
    "surface",
    "winner_name",
    "loser_name",
    "winner_id",
    "loser_id",
    "score",
    "round",
    "tourney_name",
]


def _csv_path(tour: str, year: int) -> Path:
    return PATHS.data / "tennis" / f"{tour}_matches_{year}.csv"


def download_year(year: int, tour: str = "atp", force: bool = False) -> Path:
    """Fetch one season CSV to the local cache and return its path.

    Raises a clear, actionable ``RuntimeError`` if the Sackmann repo can't be
    reached (some networks block it) — fall back to a manual download or
    :func:`synthetic_matches`.
    """
    from requests import RequestException

    from ..utils.http import HttpClient

    path = _csv_path(tour, year)
    if path.exists() and not force:
        return path
    client = HttpClient()
    errors = []
    for template in _MIRRORS:
        url = template.format(tour=tour, year=year)
        try:
            resp = client.get(url)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
            return path
        except RequestException as exc:
            errors.append(f"{url} -> {exc}")
    raise RuntimeError(
        "Could not download Sackmann data from any mirror "
        f"({'; '.join(errors)}). It may be blocked on this network. Either download "
        f"{tour}_matches_{year}.csv manually from github.com/JeffSackmann/tennis_{tour} "
        f"into {path.parent}/, or use synthetic_matches() / the --synthetic CLI flag."
    )


def load_matches(years, tour: str = "atp", download: bool = True) -> pd.DataFrame:
    """Load and tidy one or more seasons.

    Returns columns ``[date, winner, loser, surface, winner_id, loser_id,
    score, round, tourney]`` sorted ascending by date. ``date`` is a real
    ``datetime64`` parsed from Sackmann's ``YYYYMMDD`` integer.
    """
    if isinstance(years, int):
        years = [years]
    frames = []
    for year in years:
        path = _csv_path(tour, year)
        if not path.exists():
            if not download:
                raise FileNotFoundError(
                    f"{path} not found and download=False. Call download_year({year})."
                )
            path = download_year(year, tour=tour)
        df = pd.read_csv(path, usecols=lambda c: c in _USE_COLS, low_memory=False)
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["tourney_date"], format="%Y%m%d", errors="coerce"),
            "winner": raw["winner_name"].astype("string"),
            "loser": raw["loser_name"].astype("string"),
            "surface": raw.get("surface", pd.Series(index=raw.index, dtype="string")),
            "winner_id": raw.get("winner_id"),
            "loser_id": raw.get("loser_id"),
            "score": raw.get("score"),
            "round": raw.get("round"),
            "tourney": raw.get("tourney_name"),
        }
    )
    out = out.dropna(subset=["winner", "loser", "date"])
    return out.sort_values("date", kind="stable").reset_index(drop=True)


def synthetic_matches(
    n_players: int = 64,
    n_matches: int = 4000,
    seed: int = 0,
    surfaces=("Hard", "Clay", "Grass"),
) -> pd.DataFrame:
    """Generate a realistic winner/loser frame from latent player skills.

    Each player has a global skill and a small per-surface offset. Match outcomes
    are drawn from the Elo logistic on the true skill gap, so a fitted
    :class:`~forecasting_lab.sports.elo.EloModel` should recover skill order and
    beat the 0.25 Brier base rate. Deterministic given ``seed``.
    """
    rng = np.random.default_rng(seed)
    players = [f"P{i:03d}" for i in range(n_players)]
    skill = rng.normal(1500, 200, size=n_players)
    surf_offset = {s: rng.normal(0, 60, size=n_players) for s in surfaces}

    start = np.datetime64("2018-01-01")
    rows = []
    for m in range(n_matches):
        i, j = rng.choice(n_players, size=2, replace=False)
        surface = surfaces[rng.integers(len(surfaces))]
        ri = skill[i] + surf_offset[surface][i]
        rj = skill[j] + surf_offset[surface][j]
        p_i = 1.0 / (1.0 + 10.0 ** ((rj - ri) / 400.0))
        if rng.random() < p_i:
            w, ll = i, j
        else:
            w, ll = j, i
        day = start + np.timedelta64(int(m * 7 // max(1, n_matches // 365)), "D")
        rows.append((pd.Timestamp(day), players[w], players[ll], surface))

    return pd.DataFrame(rows, columns=["date", "winner", "loser", "surface"]).sort_values(
        "date", kind="stable"
    ).reset_index(drop=True)
