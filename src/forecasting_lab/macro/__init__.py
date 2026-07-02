"""Macro nowcasting from FRED — recession odds and the current dashboard read.

The headline is the **yield-curve recession probability**: the 10Y-3M Treasury
term spread inverting has preceded every US recession in the modern record, and
the NY Fed publishes a probit that maps the spread to a 12-month recession
probability. We implement that mapping (Estrella-Mishkin style) and add a plain
macro snapshot. Calibration is the point — a recession probability is only
useful if 30% means 30%.
"""

from .nowcast import macro_snapshot, recession_probability

__all__ = ["recession_probability", "macro_snapshot"]
