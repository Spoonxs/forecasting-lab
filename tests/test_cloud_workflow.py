"""The cloud automation must stay wired correctly (schedule -> run_all -> Pages)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    return doc, text


def test_daily_workflow_is_scheduled_and_runs_everything():
    doc, text = _load("daily.yml")
    triggers = doc.get("on", doc.get(True))  # PyYAML maps bare `on:` to True
    assert "schedule" in triggers and "workflow_dispatch" in triggers
    assert any("cron" in s for s in triggers["schedule"])
    # runs the orchestrator and publishes the dashboard
    assert "forecasting_lab.cli.run_all" in text
    assert "upload-pages-artifact" in text and "deploy-pages" in text
    # SEC needs a contact UA in the cloud too
    assert "SEC_USER_AGENT" in text


def test_ci_workflow_lints_and_tests():
    doc, text = _load("ci.yml")
    assert "pytest" in text and "ruff check" in text
