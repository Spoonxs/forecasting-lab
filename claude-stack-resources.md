# Claude Stack: Resources & Links

Everything from our conversation pulled together: official courses, prompting references, skills/plugins, scraping and data sources, MCP connectors for design/coding/planning, and learning references. Every link you gave me is preserved.

## Official Anthropic courses (free)

The valuable part of that "20 resources" article. Anthropic hosts these free on Skilljar. Verify each resolves before relying on it.

- Claude 101: https://anthropic.skilljar.com/claude-101
- AI Fluency (framework foundations): https://anthropic.skilljar.com/ai-fluency-framework-foundations
- Introduction to MCP: https://anthropic.skilljar.com/introduction-to-model-context-protocol
- Intro to Agent Skills: https://anthropic.skilljar.com/introduction-to-agent-skills
- MCP: Advanced Topics: https://anthropic.skilljar.com/model-context-protocol-advanced-topics
- AI Fluency for Students: https://anthropic.skilljar.com/ai-fluency-for-students
- AI Fluency for Educators: https://anthropic.skilljar.com/ai-fluency-for-educators
- Building with the Claude API: https://anthropic.skilljar.com/claude-with-the-anthropic-api
- Claude with Amazon Bedrock: https://anthropic.skilljar.com/claude-in-amazon-bedrock
- Claude with Google Vertex AI: https://anthropic.skilljar.com/claude-with-google-vertex

High-value four: Claude 101, Intro to MCP, MCP Advanced, Agent Skills. The API course matters once you start the forecasting lab's backend. The rest of that article is a marketing funnel pushing paid products (theclaudekit), so take the courses and skip the upsells.

## Prompting (getting prompting right)

Primary sources beat any leak. Start here:

- Anthropic prompt engineering guide: https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- Anthropic's published system prompts (release notes): https://platform.claude.com/docs/en/release-notes/system-prompts
- Anthropic Fable 5 / Mythos 5 model docs (real, official): https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5

Reference, treat as unverified:

- System prompt leak collection (asgeirtj): https://github.com/asgeirtj/system_prompts_leaks/tree/main
  - Fable 5 file: https://github.com/asgeirtj/system_prompts_leaks/blob/main/Anthropic/claude-fable-5.md
  - Useful for seeing how a long multi-section prompt is structured. Not a reliable record of what any model runs.
- Claude Code leaked source (codeaashu): https://github.com/codeaashu/claude-code
  - The CLI harness, not the model. Good worked example of agentic tool/prompt design (tool schemas, context assembly).

## Skills & Plugins (Claude Code ecosystem)

From the Reddit threads you shared.

- Official Anthropic skills: check docs.claude.com / platform.claude.com and Anthropic's GitHub org for the current repo.
- Repomix: https://github.com/yamadashy/repomix (packs a repo into one file; less essential inside Claude Code since it greps natively)
- ccusage: https://github.com/ryoppippi/ccusage (token spend per session; see the rate-limit caveat in the orchestration plan)
- Find Skills (vercel-labs): lets Claude pick the right skill for a goal. `npx skills add github.com/vercel-labs/skills --skill find-skills`
- awesome-claude-code (curated list): https://github.com/hesreallyhim/awesome-claude-code
- awesome-claude-skills (ComposioHQ): https://github.com/ComposioHQ/awesome-claude-skills
- awesome-claude-skills (travisvn): https://github.com/travisvn/awesome-claude-skills

The threads listed dozens more, mostly self-promo. Skip the 100+ skill mega-collections; they bloat context. A tight CLAUDE.md beats a plugin pack.

## MCP connections (design, coding, planning)

Design:
- Claude Design (Anthropic's canvas + design tools, chat-driven): https://claude.ai/design
- Figma: the official Figma Dev Mode MCP for design-to-code.
- AI media generation, for clipper thumbnails and visuals: Higgsfield and similar. Check for an official MCP and verify the source before install.

Coding:
- GitHub's official MCP server (issues, PRs, repo actions).
- Filesystem MCP (local file access).
- Context7 for docs lookup (cuts hallucinated API calls; find the official repo).
- E2B: isolated sandbox VM for running agent-written or untrusted code safely. https://github.com/e2b-dev/E2B

Planning:
- Linear MCP (issues / project tracking).
- Notion MCP (docs / databases).
- A calendar MCP (Google Calendar) for scheduling.

Web scraping / browser automation:
- Firecrawl (scrape and crawl, returns LLM-ready markdown; official MCP available): https://www.firecrawl.dev
- Playwright (Microsoft's browser automation; official Playwright MCP for driving a real browser on dynamic sites).
- Use these for JS-heavy or login-gated sites; for simple pages, direct requests plus a parser are lighter.

Caution: lists of "official" MCP servers in hype threads are often fabricated. Verify each repo and npm package actually exists and is published by the named org before installing. An unverified MCP server runs with your data and keys (this is exactly what the skill scanner project is for).

## Scraping & data sources

Use an API when there is a good free one, scrape directly when there is not.

- Hacker News: free and open API, no signup. Official: https://github.com/HackerNews/API and Algolia search: https://hn.algolia.com/api. Use it.
- Reddit: the official API needs a registered app and has limits, so for personal-scale data just scrape it. Append `.json` to any Reddit URL to get structured JSON without OAuth (a subreddit, a post, a user page all work), or parse https://old.reddit.com which has cleaner HTML. Set a real User-Agent (Reddit blocks empty or default ones) and space out requests so you do not get rate-limited or IP-blocked. The throttling is for your own sake; a banned IP kills the scraper.
- YouTube and X video: yt-dlp handles both (video, audio, subtitles, metadata). The `watch-video-skill` wraps it for Claude.
- Y Combinator: https://www.ycombinator.com/companies and https://www.ycombinator.com/rfs (Requests for Startups) for venture signal.
- JS-heavy or login-gated sites: Playwright (drives a real browser) or Firecrawl (https://www.firecrawl.dev) instead of raw requests.

Practical scraping notes:
- Parse static HTML with BeautifulSoup/lxml (Python) or cheerio (JS); use Playwright for rendered content.
- Rotate User-Agents and add delays at volume; add proxies if you scale up and start getting blocked.
- Cache raw responses so you are not re-hitting a site while you iterate on parsing.

For research-grade sources (papers, quant forums, bulk data dumps for the ML work), see `research-sources.md`.

Crypto / memecoin risk data (your links):
- https://rugcheck.xyz/
- https://birdeye.so/
- http://photon-sol.tinyastro.io/

Your original references:
- Faceless/AI channel example: https://www.youtube.com/@DAGOLDENTOOTH and https://www.youtube.com/watch?v=InH25PzMqpk
- Sports prediction video: https://www.youtube.com/watch?v=LkJpNLIaeVk
- Passive income subreddit: https://www.reddit.com/r/passive_income/?f=flair_name%3A%22Offering%20Advice%2FResource%22

## Learning / setup references

- Nate Herk, "I Turned Claude Fable Into The Ultimate Second Brain" (Jun 2026): https://www.youtube.com/watch?v=8QQ_INxAhRs
  - Builds a personal Claude operating system on a "four Cs" framework: context (a routing tree of files and folders), connections (static vs live data), capabilities (skills and workflows), and cadence (scheduled automation). Decent scaffold; skip the creator funnel.
  - The four Cs map onto what you are building: context = CLAUDE.md routing, connections = MCP and data sources, capabilities = skills, cadence = the orchestration plan.

## Installing skills and MCP servers

A skill is markdown your agent executes and an MCP server is code it runs, so the one precaution worth taking is to skim the source before installing anything that touches your keys or makes network calls (skills.sh already shipped a skill that stole environment variables). Easiest way without it being a chore: point Claude Code at the repo and have it read through and flag anything that calls home or grabs credentials. Prefer project-level installs (.claude/skills/) over global so a sketchy one stays scoped to one repo.

---
*Last updated: June 2026*
