# OPERATOR RUNBOOK — the first-push checklist

*Everything is built (P1–P5 rigor + P6a–P6e platform) and runs locally.
Nothing is live until YOU flip these switches, in order. Each step says what
turns on. Nothing here risks money — the platform is research + paper only.*

## 0. Before you push (once, local)
- `pip install -e ".[all]" && python -m pytest` — the full suite must be green.
- `flab-run-all` — the daily orchestrator end-to-end (jobs may skip honestly
  on this network; the run still completes and rebuilds `site/`).
- Open `site/index.html` in a browser and click around — landing, a ticker
  page, portfolio, arena, journal, compare, scorecard.
- Check `git status` — your personal data never appears (holdings/journal are
  browser-local; `.gitignore` allows only the public `data/` artifacts).

## 1. `git push` (the switch)
Create the GitHub repo (public — the free-Actions/Pages decision, §11) and
push `master`. **What turns on:** nothing yet — but the code, the committed
verdict artifacts, and the three workflows (`daily.yml`, `intraday.yml`,
`deploy.yml` — the on-push Pages sync) are now on GitHub, ready to be enabled.

## 2. Enable GitHub Actions
Repo → Settings → Actions → allow workflows. **What turns on:** the nightly
full run (`daily.yml`: resolve → research → media → trending → divergence →
macro → sim → forward → verdicts → watchers → dashboard → alert) and the
market-hours refresh (`intraday.yml`, every ~30 min: resolve/trending/
divergence/macro/watchers/dashboard). Free-tier honest: latency floor is the
cron cadence, and rate-limited jobs skip with a stated reason.

## 3. Enable GitHub Pages
Repo → Settings → Pages → Source: **GitHub Actions** (`deploy.yml` publishes
the built site on every push; the cron workflows share its `pages`
concurrency group). **What turns on:** the site is public at
`https://<you>.github.io/<repo>/` and refreshes with every workflow run —
verdicts, arena marks, the regret ledger, watcher events, all with receipts.

## 4. Optional: phone alerts (one token, free)
Create a Telegram bot (@BotFather) and put `TELEGRAM_BOT_TOKEN` +
`TELEGRAM_CHAT_ID` in the repo's Actions secrets (or a Discord webhook URL as
`DISCORD_WEBHOOK_URL`). **What turns on:** the daily digest + watcher firings land
on your phone. Without it, alerts append to `inputs/alerts.log` — stated,
never silent.

## 5. ~~Optional~~ DONE (2026-07-13): the TIER LIVE worker
`cd workers/quote-proxy && wrangler deploy` after setting `ALLOWED_ORIGIN` in
`wrangler.toml` to your Pages URL. **What turns on:** on-demand price previews
for any of the ~11k listed symbols (allowlist = the registry, regenerated
nightly). Without it, unbuilt symbols honestly say "add to watchlist — full
verdict on tomorrow's build".

## 6. Optional: Codex refresh (zero-key, local)
Run `flab-verdicts` (without `--no-codex`) on the machine where the `codex`
CLI is authenticated, then commit the refreshed `data/` artifacts. **What
turns on:** Codex's opinion and arena book update; cloud builds keep rendering
the last committed artifacts WITH their dates.

## Rollback / kill
Disable the two workflows (Settings → Actions) and the site freezes at its
last honest build. Nothing else is running anywhere.

*Not financial advice. Paper and research only — there is no brokerage
connection to turn on.*
