"""The desk — the operator-facing question surface (P7).

``ask()`` answers a fixed set of questions deterministically from the
committed artifacts, every answer carrying its receipts. The Rallies chat
shape with our honesty: no LLM decides a fact, ever.
"""

from .ask import INTENTS, Answer, ask

__all__ = ["ask", "Answer", "INTENTS"]
