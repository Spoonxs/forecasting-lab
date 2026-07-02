"""Source layer: the tracked universe and the connectors that feed it.

The lab tracks 500+ sources simultaneously — the equity universe (S&P 500 +
liquid growth/meme names) plus market venues, sports leagues, macro series, and
research feeds. :mod:`registry` catalogs them and counts the total;
:mod:`universe` builds the equity list (live Wikipedia pull, bundled fallback);
:mod:`sec` and :mod:`fred` are working connectors (SEC needs a contact
User-Agent; both reachable). See ``flab-sources``.
"""

from .registry import SOURCES, source_count, source_table
from .universe import equity_universe, sp500_symbols

__all__ = ["equity_universe", "sp500_symbols", "SOURCES", "source_count", "source_table"]
