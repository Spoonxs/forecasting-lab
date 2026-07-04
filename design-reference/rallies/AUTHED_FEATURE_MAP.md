# Rallies — authed product feature map (every page & button)

*Full scan of the logged-in Rallies product (Pro tier, demo portfolio — no real broker
connected, so all figures are sample data). 14 authed screenshots in `./authed/` + a 42s
**walkthrough video** `authed/rallies-walkthrough.mp4`. The data-quality verdict is in
`RALLIES_TEARDOWN.md` (grade A−, cross-verified). 2026-07-04.*

**Global chrome:** left nav = **Today · Agents · Chat · Arena · Discover · More**; top-right
= **Search stocks**, **App** (download), **Me** (account/avatar). Clean white/system-font
SaaS; dark-mode capable.

## 1. Today / Portfolio — `/home` → `/home/portfolio` (`authed/01`)
The "net worth in one view" hub (banner: *"You're seeing a demo portfolio, connect your
accounts"*). Buttons/features: sub-tabs **Portfolio · Markets · Watchlist**; **Hide values**
toggle; timeframes **1D/1W/1M/YTD/All**; net-worth chart; **connected accounts** (demo:
Robinhood $531,716 · E-Trade $38,298 · Bank of America $78,098 · "See all"); **Add physical
asset**; **Add crypto wallet**; **AI Digest**; market rails **Indices · Trending · Gainers ·
Losers · Popular**; **Create watchlist**; lower tabs **Insights · Digest · Positions ·
Activity**; and a row of **suggested AI questions** ("Should I cut my CRWV risk after
today's…", "Is my GOOGL position too large…") that deep-link into Chat.

## 2. Agents — `/agents` (`authed/02`, `03`)
**Create Agent** + **Popular agents**. Agent creation is **conversational**: "Create Agent"
opens Chat prefilled with *"I want to build an agent…"* and autosends — you describe the
monitoring agent in natural language (24/7 agents that watch positions/markets and alert).

## 3. Chat — `/chat` (`authed/13`, `14`)
The copilot. Two modes: **Ask** and **Dashboards** (tabs). Composer has an **Intelligence**
selector (default "Instant"), **Voice input**, and **custom instructions** ("Set custom
instructions for personalized answers"). Quick-action chips: **Review Portfolio · Summarize
markets · Research · My Finances · More**. Verified behavior: genuinely **agentic** — a real
question ("NVDA price / P/E / PT") produced a visible plan ("Building a plan · 4 checks ·
Checking price moves · Pulling latest financials · Checking analyst ratings"), a cited
answer, **follow-up suggestions**, and an **"AI can make mistakes"** disclaimer. Per-chat
URLs (`/chat/{uuid}`), searchable "My Chats".

## 4. Arena — `/arena` (`authed/28` in parent folder)
Live board of **GPT · Grok · Gemini · Claude** each running a ~$100k **paper** book, shown
at **position level**: ticker, allocation %, P&L, P&L %, notional, worth, entry. Snapshot:
GPT +$71.5k (CRDO +105.9%), Grok +$43k (MU +182.8%, CRM −22.7% @56%), Gemini +$18k. **No SPY
benchmark line** on the board (a real transparency gap vs Engo). Transparent demo, no gate.

## 5. Discover — `/discover` (`authed/04`, `05`, `07`)
Three catalogs: **Hedge funds** (13F portfolios — Scion/Burry, Berkshire, Icahn, Baupost,
Jana, Dragoneer…) → `/discover/fund/{slug}` (holdings + 13F, `authed/05`); **Politicians**
(congressional disclosures — Tuberville, MTG, Gottheimer…); **Themes** (AI Infrastructure,
Tokenized Finance, Agent Economy, Retail Revenge, Loneliness Pandemic…) →
`/discover/theme/{slug}` (`authed/07`, theme constituents + performance).

## 6. Feed — `/feed` (`authed/06`)
Notifications & alerts stream (agent alerts, watchlist events).

## 7. Research — `/research/{TICKER}` + sub-tabs (`authed/27`, `08`–`12`)
The per-stock hub. Header line: price, market cap, P/E, day/YTD/TTM move, 52-wk range,
analyst consensus + avg PT (verified accurate — see teardown). Buttons: **Invest**,
**Watchlist**. **Chart** controls: timeframe (1Y…), **Line/Candle**, **Indicators**,
**Compare**. Sub-tabs, each its own route:
- **/financials** (`08`) — statements & metrics
- **/insiders** (`09`) — Form-4 insider trades
- **/analyst** (`10`) — ratings + price targets
- **/politicians** (`11`) — congressional trades in the name
- **/funds** (`12`) — 13F hedge-fund holders
Plus a live **peer strip** (AMD $517.82, MU $975.56, AVGO, TSM, ARM, ASML…), an AI-written
"latest research" summary, **Key Metrics**, **Analyst Consensus**, and **AI Q&A** ("Why are
investors worried about Nvidia's…").

## 8. Account / other
**Me** (avatar) = account menu (settings/logout, behind the menu). **More** = overflow nav.
**App** = mobile-app download. **Pricing** Free/Pro $8.25·mo/Enterprise (public).

---

**Coverage:** every top-level nav surface, the research sub-tabs, fund/theme detail pages,
agent-creation flow, and both chat modes are captured (14 authed stills + the 16-frame
walkthrough video). The only things not exercised: connecting a real broker via SnapTrade
(deliberately not done — would link real accounts) and the account/settings submenu.
Screenshots are kept local (gitignored) — only this markdown is committed.
