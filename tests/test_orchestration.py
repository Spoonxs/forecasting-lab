"""The orchestrator must be failure-tolerant: one bad job can't sink the run."""

import forecasting_lab.cli.run_all as run_all
from forecasting_lab.cli import cron


def test_run_all_isolates_failures(monkeypatch, capsys):
    calls = []

    def ok(name):
        calls.append(name)
        return f"{name} done"

    monkeypatch.setattr(run_all, "_job_research", lambda: ok("research"))
    monkeypatch.setattr(run_all, "_job_macro", lambda: ok("macro"))

    def boom():
        raise ConnectionError("venue blocked")

    monkeypatch.setattr(run_all, "_job_divergence", lambda limit: boom())

    rc = run_all.main(["--only", "research", "divergence", "macro"])
    out = capsys.readouterr().out
    assert rc == 0  # partial success is still success
    assert "[ok]   research" in out
    assert "[skip] divergence" in out
    assert "[ok]   macro" in out
    assert calls == ["research", "macro"]  # good jobs still ran despite the failure


def test_run_all_puts_dashboard_last(monkeypatch, capsys):
    order = []
    for job in ("research", "macro"):
        monkeypatch.setattr(run_all, f"_job_{job}", (lambda j: lambda: order.append(j) or j)(job))
    monkeypatch.setattr(run_all, "_job_dashboard", lambda: order.append("dashboard") or "dash")
    run_all.main(["--only", "dashboard", "research", "macro"])
    assert order[-1] == "dashboard"  # dashboard always rebuilds after data jobs


def test_cron_status_runs(capsys):
    # status must never raise regardless of platform / whether a task exists
    assert cron.main(["status"]) == 0


def test_cron_install_prints_cron_on_posix(monkeypatch, capsys):
    monkeypatch.setattr(cron.sys, "platform", "linux")
    rc = cron.main(["install", "--time", "07:30"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "30 7 * * *" in out and "flab" not in out.split("crontab")[0].lower() or "run_all" in out
