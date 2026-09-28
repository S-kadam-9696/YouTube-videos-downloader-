"""YouTube search and URL metadata module using yt-dlp."""

from typing import Any
from yt_dlp import YoutubeDL


def search_youtube(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    query = query.strip()

    if not query:
        return []

    # Direct YouTube URL
    if _is_youtube_url(query):
        return _get_video_info(query)

    # Normal YouTube search
    return _search_videos(query, max_results)


def _is_youtube_url(value: str) -> bool:
    value = value.lower().strip()

    return (
        value.startswith("https://www.youtube.com/")
        or value.startswith("http://www.youtube.com/")
        or value.startswith("https://youtube.com/")
        or value.startswith("http://youtube.com/")
        or value.startswith("https://youtu.be/")
        or value.startswith("http://youtu.be/")
        or value.startswith("www.youtube.com/")
        or value.startswith("youtu.be/")
    )


def _get_video_info(url: str) -> list[dict[str, Any]]:
    """Extract metadata for one YouTube video URL."""

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return []

    # Handle playlist/channel results safely
    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        results = []

        for entry in entries[:1]:
            if entry:
                results.append(_make_result(entry, url))

        return results

    return [_make_result(info, url)]


def _make_result(info: dict[str, Any], original_url: str) -> dict[str, Any]:
    video_id = info.get("id", "")

    return {
        "id": video_id,
        "title": info.get("title", "Untitled"),
        "url": original_url,
        "webpage_url": info.get("webpage_url", original_url),
        "channel": info.get(
            "channel",
            info.get("uploader", "Unknown"),
        ),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "view_count": info.get("view_count"),
    }


def _search_videos(
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search YouTube normally."""

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"ytsearch{max_results}:{query}",
            download=False,
        )

    results = []

    if info and info.get("entries"):
        for entry in info["entries"][:max_results]:
            if not entry:
                continue

            video_id = entry.get("id", "")

            results.append(
                {
                    "id": video_id,
                    "title": entry.get("title", "Untitled"),
                    "url": (
                        entry.get("webpage_url")
                        or entry.get("url")
                        or f"https://www.youtube.com/watch?v={video_id}"
                    ),
                    "webpage_url": (
                        entry.get("webpage_url")
                        or f"https://www.youtube.com/watch?v={video_id}"
                    ),
                    "channel": entry.get(
                        "channel",
                        entry.get("uploader", "Unknown"),
                    ),
                    "duration": entry.get("duration"),
                    "thumbnail": entry.get("thumbnail"),
                    "view_count": entry.get("view_count"),
                }
            )

    return results
