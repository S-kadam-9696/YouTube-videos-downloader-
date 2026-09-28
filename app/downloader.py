"""Background yt-dlp downloads with progress tracking."""
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict

from yt_dlp import YoutubeDL

# Shared download status store: key = download_id
download_status: Dict[str, Dict[str, Any]] = {}
_lock = threading.RLock()


def _clean_title(title: str) -> str:
    """Clean title of common metadata tags."""
    if not title:
        return "video"
    tags = [
        "official",
        "music video",
        "video",
        "audio",
        "lyric",
        "lyrics",
        "clip",
        "visualizer",
        "hd",
        "4k",
        "hq",
        "1080p",
        "720p",
        "explicit",
        "live",
        "performance",
        "remastered",
    ]
    pattern = r"(?i)\s*[\(\[][^)\]]*(?:" + "|".join(tags) + r")[^)\]]*[\)\]]"
    return re.sub(pattern, "", title).strip()


def _update_status(download_id: str, **fields: Any) -> None:
    """Thread-safe status update."""
    with _lock:
        if download_id in download_status:
            download_status[download_id].update(fields)


def _safe_path(value: str, default: str) -> Path:
    """Safely expand and resolve a path."""
    path = Path((value or default).strip()).expanduser()
    try:
        return path.resolve()
    except Exception:
        return Path(default).resolve()


def _progress_hook(download_id: str) -> callable:
    """Create a progress hook for yt-dlp."""

    def hook(d: Dict[str, Any]) -> None:
        status = d.get("status")
        if status == "downloading":
            _update_status(
                download_id,
                status="downloading",
                percent=d.get("_percent_str", "0%").strip(),
                speed=d.get("_speed_str", "").strip(),
                eta=d.get("_eta"),
            )
        elif status == "finished":
            _update_status(download_id, status="processing", percent="100%")

    return hook


def _download_worker(
    download_id: str, url: str, mode: str, config: Dict[str, Any]
) -> None:
    """Background worker thread for downloads."""
    try:
        _update_status(download_id, status="downloading")

        folder = _safe_path(
            config.get("audio_save_path" if mode == "audio" else "video_save_path"),
            f"./downloads/{mode}",
        )
        folder.mkdir(parents=True, exist_ok=True)

        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "noplaylist": True,
            "progress_hooks": [_progress_hook(download_id)],
            "outtmpl": str(folder / "%(title)s.%(ext)s"),
            "restrictfilenames": False,
            "writethumbnail": False,
        }

        if mode == "audio":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": config.get("audio_format", "mp3"),
                    "preferredquality": str(config.get("audio_quality", "192")),
                }
            ]
        else:
            ydl_opts["format"] = config.get("video_format", "bestvideo+bestaudio/best")
            ydl_opts["merge_output_format"] = config.get("video_container", "mp4")

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            _update_status(
                download_id,
                status="finished",
                percent="100%",
                filename=str(folder / Path(filename).name),
            )
    except Exception as err:
        _update_status(download_id, status="error", error=str(err))


def start_download(url: str, mode: str, config: Dict[str, Any]) -> str:
    """Start a background download and return the download ID."""
    if mode not in ("video", "audio"):
        raise ValueError("mode must be 'video' or 'audio'")

    download_id = uuid.uuid4().hex
    with _lock:
        download_status[download_id] = {
            "video_id": download_id,
            "status": "queued",
            "percent": "0%",
            "speed": "",
            "eta": None,
            "filename": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_download_worker, args=(download_id, url.strip(), mode, config), daemon=True
    )
    thread.start()
    return download_id


def get_status(download_id: str) -> Dict[str, Any]:
    """Get the current status of a download by ID."""
    with _lock:
        status = download_status.get(download_id)
        if status:
            return dict(status)
        return {"video_id": download_id, "status": "not_found"}


def get_all_statuses() -> Dict[str, Dict[str, Any]]:
    """Get the status of all downloads."""
    with _lock:
        return {key: dict(value) for key, value in download_status.items()}
