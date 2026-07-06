# quote-proxy — the TIER LIVE worker (optional)

Lets the static site compute **on-demand verdicts for any listed symbol**
(PLATFORM_PLAN §2b). Without it, on-demand symbols honestly render
"add to watchlist — full verdict on tomorrow's build". Nothing else breaks.

## Deploy (free tier: 100k req/day, 10ms CPU — plenty)
1. `npm i -g wrangler && wrangler login`
2. Edit `wrangler.toml`: set `ALLOWED_ORIGIN` to the site's real origin.
3. `wrangler deploy` → note the workers.dev URL.
4. Put that URL in the site config (`tier_live` worker_url) and rebuild.

## Contract
- `GET /bars/<SYMBOL>` → upstream 1y daily chart JSON, edge-cached
  (60s market hours / 1h closed, stale-while-revalidate; bad symbols
  negative-cached 24h). CORS locked to `ALLOWED_ORIGIN`. Per-IP token bucket
  (burst 30, ~0.5 req/s refill — per-isolate best effort).
- The CLIENT does the scoring, reading `data/verdicts/contract.json` — the
  same contract the Python engine exports. No number is ever re-hardcoded.

## Honesty notes
- Upstream (Yahoo) is free and brittle — the worker passes failures through
  as 502/404; the client states them, never invents bars.
- The worker adds NO components beyond price history: on-demand verdicts have
  fewer dials lit and say so (INSUFFICIENT EVIDENCE gates identically).
