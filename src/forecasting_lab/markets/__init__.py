"""Prediction-market clients and the cross-venue divergence screener.

The same real-world event is often listed on both Kalshi and Polymarket; the
price gap between them (after fees) is a clean, concrete signal. See
``project-forecasting-lab.md``.
"""

from .divergence import Divergence, find_divergences
from .kalshi import KalshiClient, KalshiSigner
from .matching import match_markets, match_titles, title_similarity
from .monitor import DivergencePipeline
from .polymarket import PolymarketClient, parse_orderbook, to_float

__all__ = [
    "PolymarketClient",
    "parse_orderbook",
    "to_float",
    "KalshiClient",
    "KalshiSigner",
    "find_divergences",
    "Divergence",
    "match_markets",
    "match_titles",
    "title_similarity",
    "DivergencePipeline",
]
