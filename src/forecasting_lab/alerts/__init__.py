"""Free alerting: ping your phone when something flags — no subscription.

Sends to a Telegram bot and/or a Discord webhook (both free) if configured via
environment variables, and *always* appends to a local ``inputs/alerts.log`` so
it works with zero config out of the box. This is the piece that turns the daily
run from "a digest you might read" into "you actually hear about the NVIDIA/GME/BTC
move" — and it runs on the scheduler you already have (`flab-cron` locally, or the
GitHub Actions cloud job). Not financial advice.
"""

from .notify import channels_configured, send
from .summary import build_alert, compose_alert

__all__ = ["send", "channels_configured", "compose_alert", "build_alert"]
