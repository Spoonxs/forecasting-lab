"""CLI: compose a daily alert from the latest digests and send it (free channels).

Discord is the recommended free channel (a channel webhook — no bot to host).
With nothing configured it still writes ``inputs/alerts.log``. Examples::

    python -m forecasting_lab.cli.alert --setup    # how to get a Discord webhook
    python -m forecasting_lab.cli.alert --test     # send a one-line test ping
    python -m forecasting_lab.cli.alert            # compose + send the real alert
    python -m forecasting_lab.cli.alert --dry-run  # print, don't send
"""

from __future__ import annotations

import argparse

_SETUP = """\
Free Discord alerts (~1 minute, no bot hosting):
  1. In your Discord server: Server Settings > Integrations > Webhooks > New Webhook
  2. Pick the channel you want alerts in, then click "Copy Webhook URL"
  3. Put it in your .env at the repo root:
         DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/....
  4. Verify:  flab-alert --test   (you should see a message appear in that channel)

Then every scheduled run (flab-run-all / the daily task / GitHub Actions) posts a
summary there. Prefer Telegram instead? Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID.
With neither set, alerts still land in inputs/alerts.log."""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--setup", action="store_true", help="print Discord/Telegram setup steps and exit")
    ap.add_argument("--test", action="store_true", help="send a one-line test ping")
    ap.add_argument("--dry-run", action="store_true", help="print the alert without sending")
    args = ap.parse_args(argv)

    if args.setup:
        print(_SETUP)
        return 0

    from ..alerts import build_alert, channels_configured, send

    if args.test:
        delivered = send("Test alert - if you see this, Forecasting Lab alerts work.", title="Forecasting Lab test")
        print(f"Test delivered to: {', '.join(delivered)}")
        if delivered == ["local"]:
            print("Only the local log so far. Run 'flab-alert --setup' to add a free Discord webhook.")
        return 0

    title, message, fields = build_alert()
    if args.dry_run:
        print(message)
        print(f"\n[dry-run] push channels configured: {channels_configured() or 'none (local log only)'}")
        return 0

    delivered = send(message, title=title, fields=fields)
    print(f"Alert delivered to: {', '.join(delivered)}")
    if delivered == ["local"]:
        print("Tip: 'flab-alert --setup' to add a free Discord webhook (or Telegram).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
