import threading
import uuid
from pathlib import Path
from typing import Dict, Any
from yt_dlp import YoutubeDL

# Shared download status store: key = download_id
download_status: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


import re

def _clean_title(title: str) -> str:
    """Aggressively clean the title of common tags in brackets or parentheses."""
    if not title:
        return "video"
    
    # Common tags that signify metadata rather than content
    tags = [
        "official", "music video", "video", "audio", "lyric", "lyrics", 
        "clip", "visualizer", "hd", "4k", "hq", "1080p", "720p", 
        "explicit", "live", "performance", "remastered", "4k video", "hd video"
    ]
    
    # Match any (...) or [...] that contains one of the tags
    pattern = r"(?i)\s*[\(\[][^\]\)]*(?:" + "|".join(tags) + r")[^\]\)]*[\)\]]"
    
    # Apply cleaning
    title = re.sub(pattern, "", title)
    
    # Clean up double spaces and trim
    title = re.sub(r"\s+", " ", title).strip()
    
    return title

def _clean_str(s: str) -> str:
    """Remove ANSI escape codes such as color formatting."""
    if not s:
        return ""
    return re.sub(r'\x1b\[[0-9;]*m', '', str(s)).strip()

def _make_progress_hook(download_id: str):
    def progress_hook(d: dict):
        info = d.get("info_dict", {})
        with _lock:
            if d["status"] == "downloading":
                download_status[download_id] = {
                    "status": "downloading",
                    "percent": _clean_str(d.get("_percent_str", "0%")),
                    "speed": _clean_str(d.get("_speed_str", "")),
                    "eta": _clean_str(d.get("_eta_str", "")),
                    "filename": info.get("title", ""),
                }
            elif d["status"] == "finished":
                download_status[download_id] = {
                    "status": "processing",
                    "percent": "100%",
                    "speed": "",
                    "eta": "",
                    "filename": info.get("title", ""),
                }
            elif d["status"] == "error":
                download_status[download_id] = {
                    "status": "error",
                    "percent": "",
                    "speed": "",
                    "eta": "",
                    "error": str(d.get("error", "Unknown error")),
                }
    return progress_hook


def _ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def _run_download_video(download_id: str, url: str, config: dict):
    save_path = config["video_save_path"]
    _ensure_dir(save_path)

    embed = config.get("embed_metadata", True)
    postprocessors = []
    if embed:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        postprocessors.append({"key": "EmbedThumbnail"})

    opts = {
        "format": config["video_format"],
        "replace_in_metadata": [
            ("title", r"(?i)\s*[\(\[][^\]\)]*(?:Official|Audio|Lyric|Music|Explicit|Video|HD|4K|HQ|Live|Performance|Remastered|Lyrics|Clip|Visualizer|Lyric Video|Audio Video|Music Video|Official Video|Official Audio|4K Video|HD Video|1080p|720p).*?[\)\]]", ""),
            ("title", r"\s{2,}", " "),
        ],
        "outtmpl": f"{save_path}/%(title)s.%(ext)s",
        "merge_output_format": config["video_container"],
        "postprocessors": postprocessors,
        "writethumbnail": embed,
        "progress_hooks": [_make_progress_hook(download_id)],
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
    }

    try:
        with YoutubeDL(opts) as ydl:
            # 1. Extract metadata first (without downloading)
            info = ydl.extract_info(url, download=False)
            
            # 2. Clean the title string in Python
            info['title'] = _clean_title(info.get('title', 'video'))
            
            # 3. Process the download using the cleaned info dict
            # This ensures outtmpl uses the modified title
            ydl.process_info(info)

        with _lock:
            if download_status.get(download_id, {}).get("status") != "error":
                download_status[download_id] = {
                    **download_status.get(download_id, {}),
                    "status": "finished",
                    "percent": "100%",
                }
    except Exception as e:
        with _lock:
            download_status[download_id] = {
                "status": "error",
                "error": str(e),
            }


def _run_download_audio(download_id: str, url: str, config: dict):
    save_path = config["audio_save_path"]
    _ensure_dir(save_path)

    embed = config.get("embed_metadata", True)

    # Post-processor order matters: extract audio first, then tag, then embed art
    postprocessors = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": config["audio_format"],
            "preferredquality": config["audio_quality"],
        },
    ]
    if embed:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        postprocessors.append({"key": "EmbedThumbnail"})

    opts = {
        "format": "bestaudio/best",
        # Aggressively clean the title of common tags and brackets
        "replace_in_metadata": [
            ("title", r"(?i)\s*[\(\[][^\]\)]*(?:Official|Audio|Lyric|Music|Explicit|Video|HD|4K|HQ|Live|Performance|Remastered|Lyrics|Clip|Visualizer|Lyric Video|Audio Video|Music Video|Official Video|Official Audio|4K Video|HD Video|1080p|720p).*?[\)\]]", ""),
            ("title", r"\s{2,}", " "),
        ],
        "outtmpl": f"{save_path}/%(title)s.%(ext)s",
        "postprocessors": postprocessors,
        "writethumbnail": embed,
        "progress_hooks": [_make_progress_hook(download_id)],
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
    }

    try:
        with YoutubeDL(opts) as ydl:
            # 1. Extract metadata first (without downloading)
            info = ydl.extract_info(url, download=False)
            
            # 2. Clean the title string in Python
            info['title'] = _clean_title(info.get('title', 'audio'))
            
            # 3. Process the download using the cleaned info dict
            ydl.process_info(info)

        with _lock:
            if download_status.get(download_id, {}).get("status") != "error":
                download_status[download_id] = {
                    **download_status.get(download_id, {}),
                    "status": "finished",
                    "percent": "100%",
                }
    except Exception as e:
        with _lock:
            download_status[download_id] = {
                "status": "error",
                "error": str(e),
            }


def start_download(url: str, mode: str, config: dict) -> str:
    """Start a download in a background thread. Returns a download_id for polling."""
    download_id = str(uuid.uuid4())
    with _lock:
        download_status[download_id] = {"status": "queued", "percent": "0%"}

    target = _run_download_video if mode == "video" else _run_download_audio
    t = threading.Thread(target=target, args=(download_id, url, config), daemon=True)
    t.start()
    return download_id


def get_status(download_id: str) -> Dict[str, Any]:
    with _lock:
        return download_status.get(download_id, {"status": "not_found"})


def get_all_statuses() -> Dict[str, Any]:
    with _lock:
        return dict(download_status)
