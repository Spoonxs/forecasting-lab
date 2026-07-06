/**
 * quote-proxy — the TIER LIVE edge worker (P6a step 4; PLATFORM_PLAN §2b + §10).
 *
 * A minimal, hardened proxy so the static site can compute on-demand verdicts
 * for ANY listed symbol: it fetches daily bars from the upstream chart API,
 * edge-caches them, and serves them CORS-locked to our origin. Deploy is
 * OPTIONAL — without it the site degrades to "add to watchlist" (stated in the
 * client, never silent).
 *
 * Hardening (Codex round-2, verified against Cloudflare free-tier limits):
 *  - symbol canonicalized UPPERCASE and pattern-validated; no batch queries
 *  - per-IP token bucket (per-isolate; a best-effort brake, documented)
 *  - per-symbol cache keys; market-hours TTL (60s open / 1h closed)
 *  - stale-while-revalidate headers; negative caching (24h) for bad symbols
 *  - CORS locked to ALLOWED_ORIGIN (never "*")
 */

import { ALLOWED_SYMBOLS } from "./allowlist.js"; // generated from the registry (see README)

const SYMBOL_RE = /^[A-Z][A-Z0-9.\-]{0,9}$/;
const UPSTREAM = "https://query1.finance.yahoo.com/v8/finance/chart/";
const BUCKET = new Map(); // ip -> {tokens, ts} — per-isolate best-effort brake

function corsHeaders(env) {
  return {
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN || "https://example.invalid",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Vary": "Origin",
  };
}

function tooMany(ip) {
  const now = Date.now();
  const b = BUCKET.get(ip) || { tokens: 30, ts: now };
  b.tokens = Math.min(30, b.tokens + ((now - b.ts) / 1000) * 0.5); // 0.5 tokens/s, burst 30
  b.ts = now;
  if (b.tokens < 1) { BUCKET.set(ip, b); return true; }
  b.tokens -= 1;
  BUCKET.set(ip, b);
  return false;
}

function marketOpenTtl() {
  // US-market-hours TTL, DST-safe by covering both offsets: 13:30-21:00 UTC
  // spans 9:30-16:00 ET in daylight AND standard time (Codex review fix)
  const d = new Date();
  const day = d.getUTCDay(), mins = d.getUTCHours() * 60 + d.getUTCMinutes();
  const open = day >= 1 && day <= 5 && mins >= 810 && mins <= 1260;
  return open ? 60 : 3600;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(env) });
    }
    const match = url.pathname.match(/^\/bars\/([^/]+)$/);
    if (!match) {
      return new Response("quote-proxy: GET /bars/<SYMBOL>", { status: 404, headers: corsHeaders(env) });
    }
    const symbol = decodeURIComponent(match[1]).trim().toUpperCase();
    if (!SYMBOL_RE.test(symbol) || !ALLOWED_SYMBOLS.has(symbol)) {
      // shape-valid but unlisted symbols are rejected here — the registry IS
      // the allowlist (Codex review), so this can't be a general quote proxy
      return new Response(JSON.stringify({ error: "symbol not in the listed-universe allowlist" }),
        { status: 400, headers: { ...corsHeaders(env), "Content-Type": "application/json",
                                  "Cache-Control": "public, max-age=86400" } });
    }
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (tooMany(ip)) {
      return new Response(JSON.stringify({ error: "rate limited — slow down" }),
        { status: 429, headers: { ...corsHeaders(env), "Content-Type": "application/json" } });
    }

    const cache = caches.default;
    const cacheKey = new Request(`https://cache.local/bars/${symbol}`);
    const hit = await cache.match(cacheKey);
    if (hit) {
      const fresh = new Response(hit.body, hit);
      fresh.headers.set("X-Cache", "HIT");
      Object.entries(corsHeaders(env)).forEach(([k, v]) => fresh.headers.set(k, v));
      return fresh;
    }

    const ttl = marketOpenTtl();
    let upstream;
    try {
      upstream = await fetch(`${UPSTREAM}${symbol}?range=1y&interval=1d`, {
        headers: { "User-Agent": "quote-proxy (personal research; contact via repo)" },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: "upstream unreachable", detail: String(err) }),
        { status: 502, headers: { ...corsHeaders(env), "Content-Type": "application/json" } });
    }

    // Codex review: only a CONFIRMED-unknown symbol (upstream 404) earns the
    // 24h negative cache; transient upstream trouble (429/5xx) is a 502 and
    // is NEVER cached — a Yahoo hiccup must not poison a symbol for a day.
    if (!upstream.ok && upstream.status !== 404) {
      return new Response(JSON.stringify({ error: "upstream unavailable", status: upstream.status }),
        { status: 502, headers: { ...corsHeaders(env), "Content-Type": "application/json",
                                  "Cache-Control": "no-store" } });
    }
    const status = upstream.ok ? 200 : 404;
    const body = upstream.ok
      ? await upstream.text()
      : JSON.stringify({ error: "unknown or delisted symbol", symbol });
    const response = new Response(body, {
      status,
      headers: {
        ...corsHeaders(env),
        "Content-Type": "application/json",
        "Cache-Control": upstream.ok
          ? `public, max-age=${ttl}, stale-while-revalidate=${ttl * 5}`
          : "public, max-age=86400",
        "X-Cache": "MISS",
      },
    });
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  },
};
