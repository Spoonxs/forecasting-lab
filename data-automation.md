# Data Collection & News Automation

Purpose: an automated digest of what's new in your areas (quant/finance, AI research, arXiv papers, specific researchers, REU/PhD announcements), filed into the second brain so you don't track it by hand.

> **Implemented in this repo:** `flab-run-all` runs every pipeline (research/arXiv,
> trending stocks, cross-venue divergence, macro, the arena) and rebuilds the dashboard,
> failure-tolerant so one blocked source never sinks the run. `flab-cron install` registers
> a real daily OS scheduled task (Windows Task Scheduler; prints a crontab line on POSIX).
> The n8n/VPS build below remains the path for a hosted pipeline as its own portfolio piece.

---

## Lightweight version (most of the value, near-zero maintenance)

### Option A: RSS reader
- [ ] Feedly or Inoreader (free tiers are fine)
- [ ] Subscribe to:
  - [ ] arXiv categories: math.PR (probability), math.OC (optimization), stat.ML, q-fin.* (quant finance)
  - [ ] Quant and firm engineering blogs
  - [ ] Google Scholar alerts for faculty on your target list
  - [ ] REU / NSF / program announcement feeds
- No server, no maintenance, no breakage.

### Option B: Scheduled Claude task → vault
- [ ] Claude Desktop → Schedule tab → New task
- [ ] Frequency: daily or weekly
- [ ] Prompt: *"Search for the latest in [quant research / applied math / AI / a specific topic]. Summarize the 3-5 most relevant items in a few sentences each, with source links, and write them to a dated note in my vault's Inputs folder."*
- [ ] Writes straight into the Obsidian vault, no server required.

Start with these two. They cover collect + summarize + file with almost no setup.

---

## Heavier version: self-hosted n8n on a VPS

Worth building if you want a fully custom pipeline, and it doubles as a portfolio piece alongside the Forecasting & Market Analytics Lab. n8n is open-source, node-based workflow automation: wire triggers to actions visually. The common pattern is fetch → summarize with an LLM → store/notify.

### Architecture
- VPS (~$5-12/mo: Hetzner, DigitalOcean, Linode)
- n8n via Docker
- Trigger: schedule (cron) or RSS/webhook
- Fetch: RSS feeds and official APIs where they exist; scrape directly where they don't (append `.json` to Reddit URLs, parse with BeautifulSoup/cheerio, use Playwright or Firecrawl for JS-heavy sites)
- Process: LLM node (Claude/OpenAI API) for summarization
- Store: Obsidian vault, Notion, a database, or Slack/email/Telegram
- Output: daily or weekly digest

### Build checklist
- [ ] Spin up the VPS, secure it (SSH keys, firewall, auto-updates)
- [ ] Install Docker + n8n
- [ ] First workflow: arXiv RSS → Claude summarize → vault
- [ ] Add sources incrementally
- [ ] Schedule it, watch for breakage
- [ ] Document it (README, architecture diagram) for the portfolio

### Real caveats (engineering, not legal)
- A VPS is a server you administer: security updates, uptime, cost. Scrapers break when sites change their markup; APIs change too. This is a small system you maintain.
- Write your own short summaries rather than pasting source text; original summaries are both cleaner and avoid copyright issues.
- LLM cost scales with volume, so batch and cap it.

---

## Watching video autonomously (key figures & outlets)

Implemented in `media/` (`flab-watch`): a ~100-voice watch list by `@handle`
(HasanAbi, Bloomberg, CNBC, Lex Fridman, Coin Bureau, geopolitics, …) across
lenses. Each run resolves handles → channel ids (cached), pulls the latest videos
(YouTube RSS → yt-dlp fallback) + a Google-News sweep, extracts the tickers and
themes named, and files a buzz digest that feeds the trending composite. It
auto-updates because "recent videos" is always live; blocked on this sandbox's
YouTube data endpoints, live in the cloud job.

**The `/watch` skills** (`bradautomates/claude-video`, `Newuxtreme/watch-video-skill`)
are the *interactive* deep-dive: both wrap **yt-dlp + ffmpeg (+ Whisper)** to pull
a timestamped transcript and scene frames from one video so you can ask questions
about it. Use them by hand when you want to actually watch a specific interview.
This repo deliberately does **not** auto-install and run them headless — running
unvetted third-party skills autonomously is the exact risk `claude-stack-resources.md`
warns about — so it reimplements the headless slice natively (`media/youtube.py`:
`video_details`, `transcript` via yt-dlp / youtube-transcript-api). Install the
skills for manual use; keep the pipeline on the vetted native path.

## Running it for free (no subscription)

You never have to pay a subscription. Three $0 paths, pick by how "always-on" you
need:

1. **Your own PC (already set up, simplest).** `flab-cron install` registered a
   Windows Task that runs `flab-run-all` daily — free, runs whenever your machine
   is on. Add free phone alerts (below) and you'll actually hear about moves. Only
   gap: it doesn't run while the PC is off.
2. **GitHub Actions (free cloud, daily).** `.github/workflows/daily.yml` runs the
   whole suite in GitHub's cloud and publishes the dashboard to Pages — free
   (unlimited minutes on public repos), no server. Best-effort cron timing, so
   it's for daily cadence, not real-time.
3. **Oracle Cloud Always Free (free always-on VPS).** Unlike AWS/GCP's 12-month
   trials, Oracle's Always Free ARM VM (up to 4 cores / 24 GB) has *no time limit*.
   Run the pipeline on a cron there for intraday cadence, and — if you want the
   n8n portfolio piece — self-host n8n via Docker on the same box for $0. (Sign-up
   wants a card for identity but isn't charged on Always Free; idle instances can
   occasionally be reclaimed, so keep it lightly busy.)

**Free alerts (the "don't miss out" piece):** `flab-alert` posts a summary as a
**Discord embed** (recommended — a channel *webhook*, no bot to host) or to a
**Telegram bot**, and always writes `inputs/alerts.log` with nothing configured.
It's the last step of `flab-run-all`, so any path above pings you when a
divergence, trending-buzz spike, or forward-study move flags. Setup (~1 min):
`flab-alert --setup` prints the steps → paste `DISCORD_WEBHOOK_URL` into `.env` →
`flab-alert --test` to confirm. (A one-way webhook is the right tool here; a true
gateway bot only matters if you want to *type commands back*, which needs an
always-on host — the Oracle Always Free box can run one later if you want that.)

Recommendation for your goal (catch moves early, no subscription, resume value):
run the **local task now** with **Telegram alerts** (zero setup beyond a bot
token), and when you want always-on intraday, move `flab-run-all` to an **Oracle
Always Free** box — optionally fronted by self-hosted n8n so you get the visual
portfolio artifact too. n8n the software is free; only paid hosting is optional.

## Beyond n8n: the wider automation & RAG toolbox

n8n is fine, but for *this* project the honest recommendation is **you already
have the right amount**: `flab-run-all` + GitHub Actions (cloud) or `flab-cron`
(local) is a failure-tolerant scheduler with zero servers to babysit. Reach for
heavier tools only when a real need appears. The map:

- **Orchestration / scheduling** — *GitHub Actions* (what we use; free, no server).
  Step up to **Prefect** or **Dagster** (Python-native DAGs, retries, data-asset
  lineage, observability) when jobs get interdependent; **Windmill** (scripts →
  scheduled workflows + UI, a leaner self-hosted n8n); **Temporal** for durable
  long-running workflows; **Airflow** only if you must (heavy); **Modal** /
  **Cloud Run Jobs** for serverless compute on a schedule.
- **Ingestion / scraping** — **Firecrawl** and **Crawl4AI** (LLM-ready markdown
  from any page), **Apify** / **Bright Data** (managed scraping at scale),
  **Playwright** (JS-heavy/login-gated), **trafilatura** / **newspaper3k** (clean
  article text), **feedparser** (RSS, which we already lean on). RSS + official
  APIs first; scrape only what has neither.
- **RAG / storage** (if you add semantic search over your digests & papers) —
  **LlamaIndex** or **Haystack** for the pipeline (cleaner than LangChain for pure
  RAG), embeddings via a small local model or an API, and a vector store: start
  with **DuckDB** or **pgvector** (you likely already have Postgres/SQLite),
  graduate to **Qdrant** / **LanceDB** / **Chroma** only at scale. For finance
  specifically, chunk filings/transcripts, embed, and retrieve — but remember
  retrieval quality and *point-in-time* discipline matter more than the store.
- **What to skip for now:** a bespoke VPS + n8n, a managed vector DB, and any
  "agent framework" — they add ops burden the research loop doesn't need yet. The
  pipeline pattern (`pipeline.Pipeline` → dated digest in `inputs/`) plus the
  scheduler is the 90% solution; add a vector store the day you want to *ask
  questions across* the accumulated digests rather than just read the latest.

---

*Last updated: 2026-07-01*
