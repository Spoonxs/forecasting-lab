"""Notification transport — free channels, zero-config fallback.

Configure via the environment (see ``.env.example``):
- ``TELEGRAM_BOT_TOKEN`` + ``TELEGRAM_CHAT_ID`` — free Telegram bot (talk to
  @BotFather to make a bot, then get your chat id).
- ``DISCORD_WEBHOOK_URL`` — free Discord channel webhook.

With neither set, :func:`send` still records the alert to ``inputs/alerts.log``
so nothing is lost — you just read the log instead of getting a push. Every
channel is best-effort: a failing one is skipped, never raised.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ..config import PATHS
from ..utils.http import HttpClient

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def channels_configured() -> list[str]:
    """Which push channels are configured (excludes the always-on local log)."""
    out = []
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        out.append("telegram")
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        out.append("discord")
    return out


def _to_telegram(message: str, http: HttpClient) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    try:
        http.post(TELEGRAM_API.format(token=token), json={"chat_id": chat, "text": message})
        return True
    except Exception:  # noqa: BLE001 - one channel failing must not sink the rest
        return False


DISCORD_AMBER = 0xFFAE33  # matches the dashboard's accent


def _to_discord(message: str, http: HttpClient, title: str, fields: list | None) -> bool:
    """Post a Discord embed via a channel webhook. ``fields`` (section blocks)
    render more readably than a wall of text; falls back to a description."""
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return False
    embed = {
        "title": title,
        "color": DISCORD_AMBER,
        "footer": {"text": "candidates, not advice — forecasting-lab"},
    }
    if fields:
        embed["fields"] = fields[:25]  # Discord caps at 25 fields
    else:
        embed["description"] = message[:4000]
    try:
        http.post(url, json={"embeds": [embed]})
        return True
    except Exception:  # noqa: BLE001
        return False


def _to_local(message: str) -> bool:
    path = PATHS.inputs / "alerts.log"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n===== {stamp} =====\n{message}\n")
        return True
    except OSError:  # pragma: no cover
        return False


def send(
    message: str,
    title: str = "Forecasting Lab",
    fields: list | None = None,
    http: HttpClient | None = None,
) -> list[str]:
    """Deliver to every configured channel + the local log.

    ``message`` is the readable text (Telegram / local log); ``fields`` are
    optional Discord embed sections for a cleaner render. Returns the channels
    that accepted it (always includes ``local`` unless the file write fails)."""
    http = http or HttpClient()
    delivered = []
    if _to_telegram(message, http):
        delivered.append("telegram")
    if _to_discord(message, http, title, fields):
        delivered.append("discord")
    if _to_local(message):
        delivered.append("local")
    return delivered
