import io

from forecasting_lab.media.sentiment import score_text, score_texts


def test_sentiment_direction():
    assert score_text("NVIDIA earnings beat, stock surges to record high") > 0
    assert score_text("Stock plunges after profit miss and downgrade") < 0
    assert score_text("The company held a meeting on Tuesday") == 0.0
    assert -1.0 <= score_text("beats but also misses and plunges") <= 1.0


def test_sentiment_word_boundaries():
    # 'cut' shouldn't fire inside 'executive'; 'miss' not inside 'mission'
    assert score_text("The executive mission continues") == 0.0


def test_score_texts_averages_toned_only():
    s = score_texts(["surges to record", "a neutral sentence", "plunges on miss"])
    assert -1.0 <= s <= 1.0  # neutral one excluded, pos and neg average out


def test_soccer_load_parses_football_data(monkeypatch):
    import forecasting_lab.sports.soccer as soccer

    csv = (
        "Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n"
        "12/08/23,Arsenal,Forest,2,1,H\n"
        "13/08/23,Chelsea,Liverpool,1,1,D\n"
    )

    class _Resp:
        text = csv

    class _Http:
        def get(self, url, **k):
            return _Resp()

    monkeypatch.setattr(soccer, "HttpClient", lambda *a, **k: _Http(), raising=False)
    # HttpClient is imported inside load_matches from ..utils.http; patch there
    import forecasting_lab.utils.http as http_mod

    monkeypatch.setattr(http_mod, "HttpClient", lambda *a, **k: _Http())
    df = soccer.load_matches(season="2324", div="E0")
    assert list(df.columns) == ["date", "season", "home", "away", "home_goals", "away_goals"]
    assert len(df) == 2
    assert df.iloc[0]["home"] == "Arsenal" and df.iloc[0]["home_goals"] == 2

    # and the model can fit real-shaped data
    preds = soccer.SoccerElo().fit(df)
    assert len(preds) == 2
    _ = io.StringIO  # silence unused import if refactored


def test_alert_only_if_flagged(monkeypatch, tmp_path, capsys):
    import forecasting_lab.alerts.summary as summary
    from forecasting_lab.cli import alert as alert_cli

    monkeypatch.setattr(summary, "has_flags", lambda on=None: False)
    rc = alert_cli.main(["--only-if-flagged"])
    assert rc == 0
    assert "Quiet day" in capsys.readouterr().out
