"""Forward paper-trading study — watch the strategies play out in real time.

The arena replays synthetic history in bulk. This is different and stricter: on
each run it records what every strategy would hold *today* on a real basket of
high-attention tickers, and on the next run it marks that snapshot to market with
the realized return since. Nothing is scored until time actually passes, so the
live portion is genuinely out-of-sample — you cannot peek at a return that
doesn't exist yet. Persisted to ``data/forward/ledger.json`` and committed by the
daily cloud job, it accumulates into an honest track record of "did these rules
work, going forward?"

Seeded with a backfill from recent real history (labeled ``backfill``) so there's
a curve on day one; every subsequent run appends a ``live`` mark. The live tail
is the study; the backfill is just context. Not financial advice.
"""

from .ledger import THEME_BASKET, ForwardLedger

__all__ = ["ForwardLedger", "THEME_BASKET"]
