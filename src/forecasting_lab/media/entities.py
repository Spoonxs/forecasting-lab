"""Map free text (video titles, headlines) to tickers and themes.

Precision over recall: rather than matching all ~10k SEC names (which turns
"Apple pie" into AAPL), we match a curated alias set for the high-attention
names that actually move on news, plus explicit ``$CASHTAGS``. Themes that have
no single ticker (AI, crypto) are tracked separately so "OpenAI" surfaces as an
*AI theme* signal rather than a phantom stock.
"""

from __future__ import annotations

import re

# Curated company -> ticker aliases for the theme universe + mega-caps.
CURATED_ALIASES: dict[str, list[str]] = {
    "NVDA": ["nvidia"],
    "AMD": ["advanced micro devices"],
    "TSLA": ["tesla"],
    "GME": ["gamestop"],
    "AMC": ["amc entertainment"],
    "COIN": ["coinbase"],
    "MSTR": ["microstrategy", "strategy inc"],
    "PLTR": ["palantir"],
    "SMCI": ["supermicro", "super micro"],
    "ARM": ["arm holdings"],
    "MU": ["micron"],
    "AVGO": ["broadcom"],
    "TSM": ["taiwan semiconductor", "tsmc"],
    "META": ["meta platforms", "facebook", "instagram"],
    "AMZN": ["amazon"],
    "GOOGL": ["alphabet", "google"],
    "AAPL": ["apple inc", "iphone"],
    "MSFT": ["microsoft"],
    "NFLX": ["netflix"],
    "RBLX": ["roblox"],
    "HOOD": ["robinhood"],
}

# Non-ticker themes -> keywords. Attention here is a sector signal, not a stock.
THEMES: dict[str, list[str]] = {
    "AI": ["openai", "chatgpt", "artificial intelligence", "ai chips", "anthropic", "llm"],
    "crypto": ["bitcoin", "btc", "ethereum", "crypto", "solana"],
    "rates": ["rate cut", "rate hike", "fed ", "inflation", "cpi"],
    "meme": ["short squeeze", "meme stock", "wallstreetbets", "wsb"],
}

_CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")


def build_name_index(tickers: list[str] | None = None) -> dict[str, str]:
    """alias(lowercased) -> ticker. Restricted to ``tickers`` if given."""
    index: dict[str, str] = {}
    for ticker, aliases in CURATED_ALIASES.items():
        if tickers and ticker not in tickers:
            continue
        for alias in aliases:
            index[alias.lower()] = ticker
    return index


def extract_tickers(text: str, name_index: dict[str, str] | None = None) -> set[str]:
    """Tickers mentioned via ``$CASHTAG`` or a curated company-name alias."""
    index = name_index if name_index is not None else build_name_index()
    found: set[str] = set()
    for m in _CASHTAG.findall(text.upper()):
        found.add(m)
    low = text.lower()
    for alias, ticker in index.items():
        if re.search(rf"\b{re.escape(alias)}\b", low):
            found.add(ticker)
    return found


def extract_themes(text: str) -> set[str]:
    """Themes (AI, crypto, rates, meme) present in the text."""
    low = text.lower()
    return {theme for theme, kws in THEMES.items() if any(k in low for k in kws)}
