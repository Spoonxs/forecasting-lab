from datetime import date
from types import SimpleNamespace

import forecasting_lab.alerts.notify as notify
from forecasting_lab.alerts.notify import channels_configured, send
from forecasting_lab.alerts.summary import _first_table_first_column, compose_alert


def _redirect_inputs(monkeypatch, module, tmp_path):
    # PATHS.inputs is a property on a frozen dataclass; swap the whole binding.
    monkeypatch.setattr(module, "PATHS", SimpleNamespace(inputs=tmp_path))


def test_local_log_fallback_always_delivers(tmp_path, monkeypatch):
    # no channels configured -> still delivered to the local log
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    _redirect_inputs(monkeypatch, notify, tmp_path)
    delivered = send("hello world")
    assert delivered == ["local"]
    assert "hello world" in (tmp_path / "alerts.log").read_text(encoding="utf-8")


def test_telegram_and_discord_sent_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord/webhook")
    _redirect_inputs(monkeypatch, notify, tmp_path)
    assert set(channels_configured()) == {"telegram", "discord"}

    posted = []

    class _Http:
        def post(self, url, **kwargs):
            posted.append((url, kwargs.get("json")))

    delivered = send("ping", http=_Http())
    assert delivered == ["telegram", "discord", "local"]
    assert any("api.telegram.org" in u for u, _ in posted)
    # Discord uses a rich embed, not plain content
    discord_payload = next(j for u, j in posted if "discord" in u)
    assert "embeds" in discord_payload and discord_payload["embeds"][0]["description"]


def test_one_channel_failing_does_not_sink_others(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord/webhook")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    _redirect_inputs(monkeypatch, notify, tmp_path)

    class _Http:
        def post(self, url, **kwargs):
            raise ConnectionError("discord down")

    delivered = send("ping", http=_Http())
    assert "discord" not in delivered  # failed
    assert "local" in delivered  # but the log still captured it


def test_first_table_first_column_extracts_data_rows():
    md = "## Flags\n| event | edge |\n| --- | --- |\n| Fed cut | 0.03 |\n| CPI | 0.02 |\n\nfootnote"
    assert _first_table_first_column(md, 3) == ["Fed cut", "CPI"]


def test_compose_alert_is_always_sendable(tmp_path, monkeypatch):
    # empty inputs -> quiet-day message, still valid
    import forecasting_lab.alerts.summary as summary

    _redirect_inputs(monkeypatch, summary, tmp_path)
    msg = compose_alert(on=date(2026, 7, 2))
    assert "Forecasting Lab - 2026-07-02" in msg
    assert "Quiet day" in msg and "not advice" in msg


def test_compose_alert_surfaces_flags(tmp_path, monkeypatch):
    import forecasting_lab.alerts.summary as summary

    _redirect_inputs(monkeypatch, summary, tmp_path)
    (tmp_path / "2026-07-02-market-divergence.md").write_text(
        "## Flags\n| event | net_edge |\n| --- | --- |\n| Fed cut in March | 0.03 |\n", encoding="utf-8"
    )
    (tmp_path / "2026-07-02-trending-stocks.md").write_text(
        "## Fast\n| ticker | fast_money |\n| --- | --- |\n| GME | 6.7 |\n| META | 1.1 |\n", encoding="utf-8"
    )
    msg = compose_alert(on=date(2026, 7, 2))
    assert "Fed cut in March" in msg
    assert "GME" in msg and "Quiet day" not in msg


def test_alert_cli_setup_and_test(tmp_path, monkeypatch, capsys):
    from forecasting_lab.cli import alert as alert_cli

    assert alert_cli.main(["--setup"]) == 0
    out = capsys.readouterr().out
    assert "Webhooks" in out and "DISCORD_WEBHOOK_URL" in out

    # --test with no channels configured -> local only, still exits 0
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    _redirect_inputs(monkeypatch, notify, tmp_path)
    assert alert_cli.main(["--test"]) == 0
    assert "local" in capsys.readouterr().out
