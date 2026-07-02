"""Smoke tests for the CLI entry points (they must run end-to-end and exit 0)."""

from forecasting_lab.cli import calibration, elo_backtest, market_divergence, signal_scan


def test_elo_backtest_synthetic(capsys):
    assert elo_backtest.main(["--synthetic", "--min-matches", "5"]) == 0
    out = capsys.readouterr().out
    assert "Brier score" in out and "Brier skill score" in out


def test_elo_backtest_with_simulation(capsys):
    rc = elo_backtest.main(["--synthetic", "--simulate", "P000", "P001", "P002", "P003"])
    assert rc == 0
    assert "Monte Carlo" in capsys.readouterr().out


def test_signal_scan_demo_writes_digest(tmp_path):
    rc = signal_scan.main(["--demo", "--out", str(tmp_path), "--top", "5"])
    assert rc == 0
    files = list(tmp_path.glob("*-signal-digest.md"))
    assert len(files) == 1
    assert "Not financial advice" in files[0].read_text(encoding="utf-8")


def test_market_divergence_demo_writes_digest(tmp_path):
    rc = market_divergence.main(["--demo", "--out", str(tmp_path)])
    assert rc == 0
    assert list(tmp_path.glob("*-market-divergence.md"))


def test_calibration_cli_roundtrip(tmp_path, capsys):
    path = str(tmp_path / "cal.csv")
    assert calibration.main(["--path", path, "record", "--question", "Fed cut?", "--prob", "0.35"]) == 0
    assert calibration.main(["--path", path, "resolve", "--id", "1", "--outcome", "0"]) == 0
    assert calibration.main(["--path", path, "score"]) == 0
    assert "Brier score" in capsys.readouterr().out
