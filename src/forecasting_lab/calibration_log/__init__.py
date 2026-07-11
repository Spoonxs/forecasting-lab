"""The calibration track record — the credibility artifact.

A clean, honest, Brier-scored forecasting log is the single most credible thing
you can put in front of a quant recruiter, more than any backtest. Every
prediction gets a probability; resolved ones get scored over time. See
``project-forecasting-lab.md``.
"""

from .audit import AuditTrail, canonical_json, content_hash
from .log import ForecastLog
from .regret import RegretLedger
from .resolve import venue_resolver

__all__ = ["ForecastLog", "venue_resolver", "AuditTrail", "canonical_json", "content_hash",
           "RegretLedger"]
