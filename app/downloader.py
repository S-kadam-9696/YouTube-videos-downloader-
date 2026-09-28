"""Temporary background YouTube downloads."""

import re
import threading
import uuid
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL


download_status: dict[str, dict[str, Any]] = {}
_lock = threading.RLock()


def _clean_title(title: str) -> str:
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
    with _lock:
        if download_id in download_status:
            download_status[download_id].update(fields)


def _safe_path(value: str | None, default: str) -> Path:
    try:
        return Path((value or default).strip()).expanduser().resolve()
    except Exception:
        return Path(default).resolve()


def _find_downloaded_file(
    folder: Path,
    prepared_filename: str,
    mode: str,
    audio_format: str,
    video_container: str,
) -> Path | None:

    prepared = Path(prepared_filename)

    if prepared.exists():
        return prepared

    if mode == "audio":
        candidate = prepared.with_suffix(f".{audio_format}")
        if candidate.exists():
            return candidate

    if mode == "video":
        candidate = prepared.with_suffix(f".{video_container}")
        if candidate.exists():
            return candidate

    try:
        files = [
            p for p in folder.iterdir()
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


def _progress_hook(download_id: str):
    def hook(data: dict[str, Any]) -> None:

        if data.get("status") == "downloading":
            _update_status(
                download_id,
                status="downloading",
                percent=str(
                    data.get("_percent_str", "0%")
                ).strip(),
                speed=str(
                    data.get("_speed_str", "")
                ).strip(),
                eta=data.get("_eta"),
            )

        elif data.get("status") == "finished":
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
    config: dict[str, Any],
) -> None:

    folder: Path | None = None
    final_file: Path | None = None

    try:
        _update_status(
            download_id,
            status="downloading",
            percent="0%",
        )

        # Render temporary storage.
        # Files are removed after the download response.
        if mode == "audio":
            folder = Path("/tmp/youtube-downloader/audio")
            audio_format = str(
                config.get("audio_format", "mp3")
            )
            video_container = "mp4"
        else:
            folder = Path("/tmp/youtube-downloader/video")
            audio_format = "mp3"
            video_container = str(
                config.get("video_container", "mp4")
            )

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_template = (
            str(folder)
            + "/%(title)s [%(id)s].%(ext)s"
        )

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "outtmpl": output_template,
            "progress_hooks": [
                _progress_hook(download_id)
            ],
            "restrictfilenames": False,
            "writethumbnail": False,
        }

        if mode == "audio":
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
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
            options["format"] = config.get(
                "video_format",
                "bestvideo+bestaudio/best",
            )
            options["merge_output_format"] = video_container

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                url,
                download=True,
            )

            prepared_filename = ydl.prepare_filename(info)

        final_file = _find_downloaded_file(
            folder,
            prepared_filename,
            mode,
            audio_format,
            video_container,
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

    except Exception as exc:
        _update_status(
            download_id,
            status="error",
            error=str(exc),
        )


def start_download(
    url: str,
    mode: str,
    config: dict[str, Any],
) -> str:

    if mode not in {"video", "audio"}:
        raise ValueError(
            "mode must be 'video' or 'audio'"
        )

    if not url.strip():
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


def get_status(download_id: str):
    with _lock:
        status = download_status.get(download_id)

        if status:
            return dict(status)

        return {
            "video_id": download_id,
            "status": "not_found",
        }


def get_all_statuses():
    with _lock:
        return {
            key: dict(value)
            for key, value in download_status.items()
        }
