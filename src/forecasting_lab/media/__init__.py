"""Media watch: autonomous insight from key figures and outlets.

"Being in the know" is a real, if hard, edge — the point of this layer is to not
miss the story (an NVIDIA theme, a GameStop spark, a policy shift) while it's
still building. It watches a configurable list of YouTube channels (news, tech,
finance, political commentary like HasanAbi) and topic queries, pulls what they
are talking about *today*, extracts the companies/tickers mentioned, and turns
that into a per-ticker "buzz" score that feeds the trending signal.

Robust by design (same ladder as Reddit): YouTube RSS titles+descriptions are the
primary signal (no fragile transcript scraping needed), with optional transcripts
as a bonus and Google News as a cross-check. Blocked on this sandbox network;
live in the cloud. Entity extraction maps company names -> tickers via SEC's
registry. Not financial advice — this surfaces attention, not truth.
"""

from .entities import build_name_index, extract_tickers
from .watchlist import WATCHLIST, Channel, channel_count
from .youtube import recent_videos, resolve_channel_id, video_details

__all__ = [
    "WATCHLIST", "Channel", "channel_count", "recent_videos",
    "resolve_channel_id", "video_details", "extract_tickers", "build_name_index",
]
