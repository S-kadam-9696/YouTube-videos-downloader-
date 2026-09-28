"""Background yt-dlp downloads with progress tracking."""

import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict

from yt_dlp import YoutubeDL


# Shared download status store
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

    pattern = (
        r"(?i)\s*[\(\[][^)\]]*(?:"
        + "|".join(tags)
        + r")[^)\]]*[\)\]]"
    )

    cleaned = re.sub(pattern, "", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned or "video"


def _update_status(download_id: str, **fields: Any) -> None:
    """Thread-safe status update."""
    with _lock:
        if download_id in download_status:
            download_status[download_id].update(fields)


def _safe_path(value: str, default: str) -> Path:
    """Safely expand and resolve a path."""
    try:
        path = Path((value or default).strip()).expanduser()
        return path.resolve()
    except Exception:
        return Path(default).resolve()


def _find_downloaded_file(
    folder: Path,
    prepared_filename: str,
    mode: str,
    audio_format: str = "mp3",
    video_container: str = "mp4",
) -> Path | None:
    """Find the actual final downloaded file."""

    prepared = Path(prepared_filename)

    # First check the exact prepared filename.
    if prepared.exists():
        return prepared

    # Audio post-processing changes extension.
    if mode == "audio":
        audio_file = prepared.with_suffix(f".{audio_format}")

        if audio_file.exists():
            return audio_file

    # Video merging can change the final extension.
    if mode == "video":
        video_file = prepared.with_suffix(f".{video_container}")

        if video_file.exists():
            return video_file

    # Last fallback: newest file in the download folder.
    try:
        files = [
            p
            for p in folder.iterdir()
            if p.is_file()
        ]

        if files:
            return max(
                files,
                key=lambda p: p.stat().st_mtime,
            )
    except Exception:
        pass

    return None


def _progress_hook(download_id: str) -> callable:
    """Create a progress hook for yt-dlp."""

    def hook(d: Dict[str, Any]) -> None:
        status = d.get("status")

        if status == "downloading":
            percent = d.get("_percent_str", "0%")
            speed = d.get("_speed_str", "")
            eta = d.get("_eta")

            _update_status(
                download_id,
                status="downloading",
                percent=str(percent).strip(),
                speed=str(speed).strip(),
                eta=eta,
            )

        elif status == "finished":
            _update_status(
                download_id,
                status="processing",
                percent="100%",
            )

    return hook


def _download_worker(
    download_id: str,
    url: str,
    mode: str,
    config: Dict[str, Any],
) -> None:
    """Background worker thread for downloads."""

    try:
        _update_status(
            download_id,
            status="downloading",
        )

        if mode == "audio":
            save_path_key = "audio_save_path"
            default_folder = "./downloads/audio"
        else:
            save_path_key = "video_save_path"
            default_folder = "./downloads/video"

        folder = _safe_path(
            config.get(save_path_key),
            default_folder,
        )

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        audio_format = str(
            config.get("audio_format", "mp3")
        )

        video_container = str(
            config.get("video_container", "mp4")
        )

        # Use cleaned title for the filename.
        output_template = (
            str(folder)
            + "/%(title)s [%(id)s].%(ext)s"
        )

        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "progress_hooks": [
                _progress_hook(download_id)
            ],
            "outtmpl": output_template,
            "restrictfilenames": False,
            "writethumbnail": False,
        }

        if mode == "audio":
            ydl_opts["format"] = "bestaudio/best"

            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": str(
                        config.get(
                            "audio_quality",
                            "192",
                        )
                    ),
                }
            ]

        else:
            ydl_opts["format"] = config.get(
                "video_format",
                "bestvideo+bestaudio/best",
            )

            ydl_opts["merge_output_format"] = (
                video_container
            )

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                url,
                download=True,
            )

            prepared_filename = ydl.prepare_filename(
                info
            )

        final_file = _find_downloaded_file(
            folder=folder,
            prepared_filename=prepared_filename,
            mode=mode,
            audio_format=audio_format,
            video_container=video_container,
        )

        if final_file is None:
            raise FileNotFoundError(
                "Downloaded file could not be located."
            )

        title = _clean_title(
            info.get("title", "video")
        )

        _update_status(
            download_id,
            status="finished",
            percent="100%",
            filename=str(final_file),
            title=title,
            mode=mode,
            url=url,
            webpage_url=info.get(
                "webpage_url",
                url,
            ),
            duration=info.get("duration"),
            file_size=final_file.stat().st_size,
        )

    except Exception as err:
        _update_status(
            download_id,
            status="error",
            error=str(err),
        )


def start_download(
    url: str,
    mode: str,
    config: Dict[str, Any],
) -> str:
    """Start a background download."""

    if mode not in ("video", "audio"):
        raise ValueError(
            "mode must be 'video' or 'audio'"
        )

    if not url or not url.strip():
        raise ValueError(
            "URL cannot be empty"
        )

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
            "mode": mode,
            "url": url.strip(),
        }

    thread = threading.Thread(
        target=_download_worker,
        args=(
            download_id,
            url.strip(),
            mode,
            config,
        ),
        daemon=True,
    )

    thread.start()

    return download_id


def get_status(
    download_id: str,
) -> Dict[str, Any]:
    """Get status of a download."""

    with _lock:
        status = download_status.get(
            download_id
        )

        if status:
            return dict(status)

        return {
            "video_id": download_id,
            "status": "not_found",
        }


def get_all_statuses() -> Dict[str, Dict[str, Any]]:
    """Get status of all downloads."""

    with _lock:
        return {
            key: dict(value)
            for key, value in download_status.items()
        }
