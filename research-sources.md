# Research Sources: Where to Mine at Scale

The full breadth of places to pull research from for the quant and ML work: papers, practitioner forums, and bulk data. Built so you can automate ingestion rather than read tab by tab.

## One distinction that saves you a lot of wasted effort

There are two different things people mean by "scrape research to optimize off of," and they need different sources:

1. Ideas and methodology: papers, forum threads, blogs. You read or summarize these to learn techniques and find strategy ideas. This is not training data.
2. Training data: prices, fundamentals, alt-data. This is what a model trains on, and it lives in `signal-monitoring.md` and `ml-system-design.md`, not here.

This doc is mostly #1, plus the social sources that double as #2 features (Reddit/StockTwits sentiment). Do not confuse "200k forum posts" with "a training set for a price model." Forum text is a sentiment feature at most; the alpha data is market data.

## The efficient move: bulk dumps, not page-by-page scraping

For "hundreds of thousands of data points," scraping one page at a time is the slow, fragile way. The high-value sources publish bulk downloads:

- Stack Exchange Data Dump (archive.org): the full Q&A history of every Stack Exchange site, downloadable, no scraping. Quantitative Finance SE, Cross Validated (stats/ML), Data Science SE, and Money SE together are millions of structured, tagged, voted question-answer pairs. This is the single best bulk research corpus for your domains.
- arXiv bulk: the full metadata of ~2M+ papers is on Kaggle (the arXiv dataset), and full text is available via the arXiv S3 requester-pays bucket and OAI-PMH metadata harvesting. Do not scrape arxiv.org page by page.
- Academic Torrents: historical Reddit dumps (the Pushshift archives, since the live Pushshift API was restricted), plus many research datasets. This is how you get years of r/wallstreetbets or r/algotrading history at once.
- RePEc / IDEAS (ideas.repec.org): structured metadata for the world's economics and finance working papers, designed to be harvested.

Start with these four when you want mass data. Scrape live only for the recent tail the dumps do not cover yet.

## Academic papers (the highest-signal research)

- arXiv: the categories that matter for you are q-fin.* (CP computational finance, PM portfolio management, RM risk management, ST statistical finance, TR trading/microstructure, MF mathematical finance, EC economics), plus stat.ML, cs.LG, math.PR, math.OC. RSS per category for the ongoing feed; the Kaggle dataset for bulk; autoarxiv (swap arxiv to autoarxiv in a paper URL) to attempt a reproduction.
- SSRN, the Financial Economics Network: where finance and econ academics post working papers, often before journal publication. No clean API, so browse or scrape by network. The single best source for current quant-finance research.
- NBER working papers: free, high quality, economics and finance.
- Papers With Code (q-fin and ML sections): papers paired with their code, so you can go from claim to implementation.
- OpenReview: ICLR, NeurIPS, and other ML venue submissions with their peer reviews attached. The reviews tell you what is contested and what is strong. It has an API.
- Semantic Scholar (S2 API): a citation graph with a real API, so you can discover influential papers and traverse citations at scale rather than searching by hand.
- SSRN and Google Scholar alerts: set per-topic and per-author alerts for the faculty on your grad list (this also feeds the `faculty-fit/` research).

## Quant and trading forums (practitioner knowledge)

- Quantitative Finance Stack Exchange (quant.stackexchange.com): the main quant Q&A site. Use the data dump for bulk, the live site for recent threads.
- Cross Validated (stats.stackexchange.com): statistics and ML Q&A, same dump.
- Wilmott forums: the classic derivatives and vol practitioner forum.
- QuantConnect community and forum: strategy code and discussion, a lot of runnable examples.
- Elite Trader and Nuclear Phynance: older trading forums, still useful archives.
- Numerai forum (forum.numer.ai): an active community around the crowdsourced quant tournament, strong on feature engineering and validation discipline, which is exactly the ML skill set.
- Reddit, the relevant subs: r/quant, r/algotrading, r/quantfinance, r/options, r/SecurityAnalysis, r/MachineLearning, and r/wallstreetbets (for sentiment). Bulk history via Academic Torrents; recent via `.json` scraping with throttling.

## Practitioner research and aggregators (high quality, free)

- AQR research library: AQR publishes a large body of factor and quant research at near-academic quality, free. One of the best single sources on factors, momentum, and value.
- Quantpedia: an encyclopedia of trading strategies with references; part free, excellent for surveying what has been tried.
- Quantocracy (quantocracy.com): a daily aggregator of quant blogs. Point a feed at it and you get the practitioner firehose without hunting for blogs.
- Hudson & Thames (the mlfinlab project) blog: financial ML methodology, aligned with Lopez de Prado.
- QuantStart: tutorials on backtesting and quant methods.
- Firm engineering and research blogs: Jane Street, Two Sigma, Man AHL, and similar publish occasional deep technical posts.

## Code and datasets (to learn from and mine)

- GitHub curated lists: awesome-quant, awesome-systematic-trading. Start there and follow the references.
- Kaggle: datasets plus notebooks. The financial ML competitions and their public notebooks are a strong source of worked, critiqued code.
- Hugging Face: datasets and the papers feed.

## Video tutorials (craft, not alpha)

Algo-trading YouTube is a real source for one thing: learning how to build (a backtesting setup, a library, a technique). It is close to useless for the other thing: finding edge. Any strategy popular enough to be a video has been seen by everyone, so by construction it is not alpha. Use these to learn the craft, then validate rigorously per `ml-system-design.md`. Never deploy a strategy because a video showed a nice equity curve.

The filter that sorts signal from noise: does the channel show real, runnable code and discuss why strategies fail, or does it show equity curves and sell a course, signals, or a Discord? The first is worth your time; the second is marketing.

- The technical, code-showing channels (Python backtests, pattern detection, market-microstructure ideas with the actual code on screen) are the useful tier. neurotrader888 and CodeTradingCafe sit on that end. Treat any specific strategy as a teaching example, not a recommendation.
- Channels heavier on results, calls, or paid access: skip, or watch only for an occasional technique with the edge caveat doubled.
- To ingest any of them, use the `watch-video-skill` (transcript plus frames into notes). That also lets Claude assess a channel's actual technical depth before you sink hours in, which is the right way to vet a video source you are unsure about.

Bottom line: these are for technique and implementation patterns, not for what to trade.

## Automating the ingestion (the pipeline pattern)

Tie this to the `master-index.md` pipeline so it runs instead of piling up:

- Papers: arXiv RSS for your categories plus an SSRN and Scholar alert sweep, fed to a scheduled Claude task that summarizes the 3 to 5 most relevant and writes a dated, ranked note into `inputs/`. autoarxiv on the ones worth reproducing.
- Forums: load the Stack Exchange and Reddit bulk dumps once, index them, and query locally rather than re-scraping. Refresh with the recent tail on a schedule.
- Digest cadence: a weekly note is enough. The goal is a filtered, summarized feed in the vault, not a raw dump you never read.

## Practical notes

- Bulk download where a dump exists (Stack Exchange, arXiv, Academic Torrents, RePEc). It is faster, cleaner, and does not break.
- Use APIs where they exist (arXiv, Semantic Scholar, OpenReview, HN Algolia, Reddit `.json`).
- For sites without either, throttle and cache so you do not get IP-blocked and so you are not re-hitting a site while you iterate on parsing.
- Write your own short summaries rather than storing source text verbatim; cleaner for reuse and avoids copyright issues.

---

*This is a research-sourcing reference, not financial advice.*
*Last updated: June 2026*
