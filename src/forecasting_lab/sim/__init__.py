"""The strategy arena: a persistent paper-trading simulator.

Multiple strategies trade the same market side by side, bar by bar, with
turnover costs — and the arena's state persists to disk, so each run *continues*
the simulation rather than restarting it. The point is comparative and honest:
every strategy sees only history up to the current bar (weights are applied to
the *next* bar's returns), and the leaderboard always includes buy-and-hold and
random baselines. A strategy that can't beat those after costs isn't a strategy.

Not an execution simulator (no order book, no queue position — "HFT" at retail
data granularity is a fiction); it is a daily-bar research arena. Not financial
advice.
"""

from .data import synthetic_market
from .engine import Arena
from .strategies import ALL_STRATEGIES, Strategy

__all__ = ["Arena", "synthetic_market", "Strategy", "ALL_STRATEGIES"]
