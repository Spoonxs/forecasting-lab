"""YouTube access: resolve handles, list recent videos, pull details/transcripts.

Backends, tried in order for resilience (the same "don't give up" ladder used
elsewhere):
1. **Channel RSS** (``feeds/videos.xml?channel_id=``) — one request, latest ~15
   videos with title+description+date. Lightest; primary in the cloud.
2. **yt-dlp** — lists a channel's recent uploads and pulls per-video details and
   subtitles. This is the same tool the interactive ``/watch`` and
   ``watch-video-skill`` wrap (see ``data-automation.md``); here it's used
   headlessly so the daily job needs no human in the loop.

``resolve_channel_id`` turns a ``@handle`` into the ``UC...`` id by reading the
channel page (works even where the data endpoints are blocked), so the watchlist
can be maintained as human-friendly handles. All functions degrade to empty/None
rather than raising — one dead channel must never sink the sweep.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..utils.cache import DiskCache
from ..utils.http import HttpClient

RSS = "https://www.youtube.com/feeds/videos.xml"
_NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
_UC_RE = re.compile(r"(UC[0-9A-Za-z_-]{22})")


def _client() -> HttpClient:
    return HttpClient(user_agent="Mozilla/5.0 (research; forecasting-lab)")


def resolve_channel_id(handle: str, refresh: bool = False) -> str | None:
    """Resolve a ``@handle`` (or bare name) to its ``UC...`` channel id, cached.

    Reads the public channel page and extracts the id. Channel ids are stable,
    so the cache TTL is long. Returns None if it can't be resolved."""
    handle = handle.lstrip("@")
    cache = DiskCache("youtube_ids", ttl=30 * 24 * 3600)
    if not refresh:
        hit = cache.get(handle)
        if hit:
            return hit
    try:
        resp = _client().get(f"https://www.youtube.com/@{handle}")
        m = _UC_RE.search(resp.text)
        if m:
            cache.set(handle, m.group(1))
            return m.group(1)
    except Exception:  # noqa: BLE001 - unresolved handle is not fatal
        pass
    return None


def parse_feed(xml_bytes: bytes) -> list[dict]:
    """Channel RSS -> [{title, description, published, video_id}]."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    out = []
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = re.sub(r"\s+", " ", entry.findtext("atom:title", "", _NS)).strip()
        vid = entry.findtext("{http://www.youtube.com/xml/schemas/2015}videoId") or ""
        group = entry.find("media:group", _NS)
        desc = ""
        if group is not None:
            desc = re.sub(r"\s+", " ", group.findtext("media:description", "", _NS) or "").strip()
        published = (entry.findtext("atom:published", "", _NS) or "")[:10]
        if title:
            out.append({"title": title, "description": desc, "published": published, "video_id": vid})
    return out


def _recent_via_ytdlp(channel_id: str, limit: int = 10) -> list[dict]:
    """Recent uploads via yt-dlp flat playlist. Empty on any failure."""
    try:
        import yt_dlp
    except ImportError:
        return []
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True,
            "playlistend": limit, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=False)
        return [
            {"title": e.get("title", ""), "description": "", "published": "", "video_id": e.get("id", "")}
            for e in (info.get("entries") or [])
            if e.get("title")
        ]
    except Exception:  # noqa: BLE001
        return []


def recent_videos(channel_id: str, http: HttpClient | None = None, limit: int = 10) -> list[dict]:
    """Latest videos for a channel: RSS first, yt-dlp fallback. Never raises."""
    client = http or _client()
    try:
        resp = client.get(RSS, params={"channel_id": channel_id})
        vids = parse_feed(resp.content)
        if vids:
            return vids[:limit]
    except Exception:  # noqa: BLE001
        pass
    return _recent_via_ytdlp(channel_id, limit=limit)


def recent_videos_by_handle(handle: str, limit: int = 10) -> list[dict]:
    """Convenience: resolve a ``@handle`` then fetch its recent videos."""
    cid = resolve_channel_id(handle)
    return recent_videos(cid, limit=limit) if cid else []


def video_details(video_id: str) -> dict:
    """Per-video details via yt-dlp (title, description, date, views, channel).

    The native, headless equivalent of the interactive ``/watch`` skills. Empty
    dict if yt-dlp is unavailable or the fetch fails."""
    try:
        import yt_dlp
    except ImportError:
        return {}
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        return {
            "title": info.get("title", ""),
            "description": (info.get("description") or "")[:2000],
            "upload_date": info.get("upload_date", ""),
            "view_count": info.get("view_count"),
            "duration": info.get("duration"),
            "channel": info.get("channel", ""),
        }
    except Exception:  # noqa: BLE001
        return {}


def transcript(video_id: str) -> str:
    """Best-effort full transcript via youtube-transcript-api. '' if unavailable."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        return " ".join(seg.text for seg in fetched)
    except Exception:  # noqa: BLE001
        return ""
