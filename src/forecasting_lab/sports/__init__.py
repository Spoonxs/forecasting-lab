"""Sports models. Tennis first — Elo works well there and the data is clean.

Data: Jeff Sackmann / Tennis Abstract (CC BY-NC-SA 4.0 — attribution required,
non-commercial only). See ``project-forecasting-lab.md``.
"""

from .elo import EloModel, expected_score
from .simulate import simulate_tournament

__all__ = ["EloModel", "expected_score", "simulate_tournament"]
