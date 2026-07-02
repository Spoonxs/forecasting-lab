import pytest

from forecasting_lab.sports import tennis_data
from forecasting_lab.sports.tennis_data import synthetic_matches


def test_synthetic_matches_deterministic_and_valid():
    a = synthetic_matches(n_players=16, n_matches=200, seed=5)
    b = synthetic_matches(n_players=16, n_matches=200, seed=5)
    assert a.equals(b)  # same seed -> identical
    assert {"date", "winner", "loser", "surface"}.issubset(a.columns)
    assert (a["winner"] != a["loser"]).all()  # no self-matches
    assert a["date"].is_monotonic_increasing


def test_download_year_wraps_network_errors(monkeypatch):
    from requests import RequestException

    import forecasting_lab.utils.http as http_mod

    class _Boom:
        def get(self, url, **kwargs):
            raise RequestException("blocked")

    monkeypatch.setattr(http_mod, "HttpClient", lambda *a, **k: _Boom())
    # a far-future season is guaranteed not to be cached, so it attempts a fetch
    with pytest.raises(RuntimeError, match="Could not download"):
        tennis_data.download_year(3999, tour="atp")
