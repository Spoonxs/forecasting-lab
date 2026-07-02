"""The watch list — ~100 voices across the lenses that move markets and politics.

Each entry is ``(name, lens, handle, news_query)``. The ``handle`` is a YouTube
``@handle`` resolved to a channel id at run time (cached); the ``news_query`` is a
reliable Google-News fallback that works even if a handle is wrong or a channel is
unreachable — so every voice is monitored regardless. Edit freely; this is data.

Triangulation is the point: no single pundit is an edge, but a shift that shows up
across finance media + macro + the relevant political/tech commentary at once is a
real "something is happening" signal. Attention, not truth — pundits are often
wrong or late. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    name: str
    lens: str  # markets | macro | tech | ai | crypto | politics | geo | news | vc
    handle: str | None = None  # YouTube @handle (resolved to a channel id at run time)
    channel_id: str | None = None  # set directly to skip resolution
    news_query: str | None = None  # Google News fallback (always works)


# (name, lens, handle, news_query)
_RAW: list[tuple[str, str, str | None, str]] = [
    # --- markets / financial news ---
    ("Bloomberg Television", "markets", "markets", "Bloomberg markets stocks"),
    ("CNBC", "markets", "CNBCtelevision", "CNBC stock market"),
    ("Yahoo Finance", "markets", "YahooFinance", "Yahoo Finance markets"),
    ("Reuters", "markets", "Reuters", "Reuters business markets"),
    ("Wall Street Journal", "markets", "wsj", "Wall Street Journal markets"),
    ("Financial Times", "macro", "FinancialTimes", "Financial Times economy"),
    ("MarketWatch", "markets", "marketwatch", "MarketWatch stocks"),
    ("Benzinga", "markets", "Benzinga", "Benzinga stocks movers"),
    ("Real Vision", "markets", "RealVisionFinance", "Real Vision finance"),
    ("tastylive", "markets", "tastyliveshow", "options trading tastylive"),
    ("rareliquid", "markets", "rareliquid", "stock analysis investment banking"),
    ("Joseph Carlson", "markets", "JosephCarlsonShow", "Joseph Carlson dividend investing"),
    # --- finance YouTubers / retail ---
    ("Meet Kevin", "markets", "MeetKevin", "Meet Kevin stocks Tesla"),
    ("Graham Stephan", "markets", "GrahamStephan", "Graham Stephan investing"),
    ("Andrei Jikh", "markets", "AndreiJikh", "Andrei Jikh investing crypto"),
    ("The Plain Bagel", "markets", "ThePlainBagel", "investing explained finance"),
    ("Patrick Boyle", "macro", "PatrickBoyleOnFinance", "Patrick Boyle finance markets"),
    ("Ben Felix", "markets", "BenFelixCSI", "Ben Felix evidence based investing"),
    ("New Money", "markets", "NewMoneyYT", "value investing stocks"),
    ("Coffeezilla", "markets", "Coffeezilla", "crypto fraud scam investigation"),
    ("Financial Times money", "markets", None, "personal finance markets"),
    ("Aswath Damodaran", "markets", "AswathDamodaranOnValuation", "Damodaran valuation"),
    # --- macro / economics ---
    ("Economics Explained", "macro", "EconomicsExplained", "economy recession GDP"),
    ("Money & Macro", "macro", "MoneyMacro", "macroeconomics inflation"),
    ("Joseph Wang (Fed Guy)", "macro", "JosephWang", "Federal Reserve liquidity rates"),
    ("George Gammon", "macro", "GeorgeGammon", "George Gammon macro Fed"),
    ("Forward Guidance", "macro", "ForwardGuidancepod", "macro rates Fed policy"),
    ("Blockworks Macro", "macro", "Blockworks_", "macro markets Fed"),
    ("Lyn Alden", "macro", None, "Lyn Alden macro"),
    ("The Economist", "macro", "TheEconomist", "The Economist global economy"),
    # --- tech ---
    ("MKBHD", "tech", "mkbhd", "MKBHD tech gadgets Apple"),
    ("Linus Tech Tips", "tech", "LinusTechTips", "PC hardware GPU tech"),
    ("The Verge", "tech", "TheVerge", "The Verge technology"),
    ("Fireship", "tech", "Fireship", "software developer tech news"),
    ("ColdFusion", "tech", "ColdFusion", "tech company history business"),
    ("TechCrunch", "vc", "TechCrunch", "TechCrunch startups funding"),
    ("CNET", "tech", "CNET", "CNET tech reviews"),
    ("Marques on cars/tech", "tech", None, "consumer tech launches"),
    # --- AI ---
    ("Lex Fridman", "ai", "lexfridman", "Lex Fridman AI podcast"),
    ("Two Minute Papers", "ai", "TwoMinutePapers", "AI research papers"),
    ("Yannic Kilcher", "ai", "YannicKilcher", "machine learning research"),
    ("AI Explained", "ai", "aiexplained-official", "AI models GPT frontier"),
    ("Matthew Berman", "ai", "matthew_berman", "AI tools LLM open source"),
    ("David Shapiro", "ai", "DaveShap", "AI AGI automation"),
    ("bycloud", "ai", "bycloudAI", "AI research LLM"),
    ("Wes Roth", "ai", "WesRoth", "AI news OpenAI"),
    # --- crypto ---
    ("Coin Bureau", "crypto", "CoinBureau", "crypto bitcoin ethereum"),
    ("Bankless", "crypto", "Bankless", "ethereum defi crypto"),
    ("Altcoin Daily", "crypto", "AltcoinDaily", "bitcoin altcoin crypto news"),
    ("Benjamin Cowen", "crypto", "intothecryptoverse", "bitcoin cycle analysis"),
    ("DataDash", "crypto", "DataDash", "crypto market analysis"),
    ("Anthony Pompliano", "crypto", "AnthonyPompliano", "bitcoin macro Pomp"),
    ("Real Vision Crypto", "crypto", None, "crypto macro digital assets"),
    ("Digital Asset News", "crypto", "DigitalAssetNewsDAN", "crypto regulation news"),
    # --- political commentary (spread across the spectrum for balance) ---
    ("HasanAbi", "politics", "hasanabi", "Hasan Piker politics"),
    ("The David Pakman Show", "politics", "thedavidpakmanshow", "David Pakman politics"),
    ("The Young Turks", "politics", "TheYoungTurks", "TYT politics news"),
    ("Secular Talk", "politics", "SecularTalk", "Kyle Kulinski politics"),
    ("Breaking Points", "politics", "breakingpoints", "Breaking Points politics"),
    ("Philip DeFranco", "politics", "phillyd", "DeFranco news roundup"),
    ("Tim Pool", "politics", "Timcast", "Timcast politics"),
    ("Ben Shapiro", "politics", "BenShapiro", "Ben Shapiro politics"),
    ("PBS NewsHour", "news", "PBSNewsHour", "PBS NewsHour politics"),
    ("Forbes Breaking News", "politics", "FBNBreakingNews", "Congress hearing policy"),
    ("The Hill", "politics", "TheHill", "The Hill Washington policy"),
    ("Pod Save America", "politics", None, "Pod Save America politics"),
    # --- geopolitics ---
    ("CaspianReport", "geo", "CaspianReport", "geopolitics analysis"),
    ("Peter Zeihan", "geo", "ZeihanonGeopolitics", "Peter Zeihan geopolitics"),
    ("RealLifeLore", "geo", "RealLifeLore", "geopolitics conflict analysis"),
    ("Johnny Harris", "geo", "johnnyharris", "geopolitics explainer"),
    ("VisualPolitik EN", "geo", "VisualPolitikEN", "geopolitics economics country"),
    ("Wendover Productions", "geo", "Wendoverproductions", "logistics economics infrastructure"),
    ("TLDR News Global", "geo", "TLDRNewsGlobal", "global politics explained"),
    # --- broad news orgs ---
    ("CNN", "news", "CNN", "CNN breaking news"),
    ("Fox News", "news", "FoxNews", "Fox News politics"),
    ("MSNBC", "news", "msnbc", "MSNBC politics"),
    ("BBC News", "news", "BBCNews", "BBC world news"),
    ("Al Jazeera English", "news", "aljazeeraenglish", "Al Jazeera world news"),
    ("DW News", "news", "dwnews", "DW news Europe economy"),
    ("Vox", "news", "Vox", "Vox explainer news"),
    ("Associated Press", "news", "AP", "AP breaking news"),
    ("The Guardian", "news", "TheGuardian", "Guardian news politics"),
    ("Sky News", "news", "SkyNews", "Sky News UK world"),
    ("NBC News", "news", "NBCNews", "NBC News"),
    ("60 Minutes", "news", "60minutes", "60 Minutes investigation"),
    ("VICE News", "news", "VICENews", "VICE News investigation"),
    ("France 24 English", "news", "FRANCE24English", "France 24 world news"),
    # --- VC / startups / business ---
    ("Y Combinator", "vc", "ycombinator", "Y Combinator startups"),
    ("a16z", "vc", "a16z", "Andreessen Horowitz venture tech"),
    ("This Week in Startups", "vc", "ThisWeekIn", "Jason Calacanis startups"),
    ("20VC", "vc", "20VC", "Harry Stebbings venture capital"),
    ("Lenny's Podcast", "vc", "LennysPodcast", "product startups growth"),
    ("All-In Podcast", "vc", "allin", "All-In podcast markets tech"),
    ("The Diary of a CEO", "vc", "TheDiaryOfACEO", "business founders"),
    ("Startup Istanbul / founders", "vc", None, "startup funding rounds"),
    # --- energy / commodities / industrials ---
    ("Rystad / energy", "macro", None, "oil gas energy prices"),
    ("Commodity markets", "macro", None, "commodities oil copper gold prices"),
    # --- theme catch-alls (news-query only) ---
    ("AI / semis theme", "ai", None, "NVIDIA OpenAI AI chips datacenter"),
    ("Meme-stock watch", "markets", None, "GameStop AMC short squeeze"),
    ("Bitcoin / crypto theme", "crypto", None, "bitcoin ETF crypto price"),
    ("Fed / rates theme", "macro", None, "Federal Reserve rate decision inflation"),
    ("Elections / policy theme", "politics", None, "election policy regulation markets"),
    ("EV / Tesla theme", "markets", None, "Tesla EV deliveries"),
    ("Biotech / GLP-1 theme", "markets", None, "GLP-1 Ozempic biotech"),
]

WATCHLIST: list[Channel] = [
    Channel(name=n, lens=lens, handle=h, news_query=q) for (n, lens, h, q) in _RAW
]


def channel_count() -> int:
    return len(WATCHLIST)
