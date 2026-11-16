"""YouTube links for songs (#25)."""

import re
from urllib.parse import parse_qs, urlparse

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "music.youtube.com"}
PATH_PREFIXES = ("/embed/", "/shorts/", "/live/", "/v/")


def youtube_video_id(url: str) -> str | None:
    """Return the 11-character video id of a YouTube URL, or None."""
    text = url.strip()
    if "://" not in text:
        text = f"https://{text}"
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower().removeprefix("www.")
    candidate = None
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in YOUTUBE_HOSTS or host == "youtube-nocookie.com":
        if parsed.path.rstrip("/") == "/watch":
            candidate = (parse_qs(parsed.query).get("v") or [""])[0]
        else:
            for prefix in PATH_PREFIXES:
                if parsed.path.startswith(prefix):
                    candidate = parsed.path[len(prefix) :].split("/")[0]
                    break
    if candidate and VIDEO_ID.fullmatch(candidate):
        return candidate
    return None


def canonical_youtube_url(url: str) -> str | None:
    video_id = youtube_video_id(url)
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None
