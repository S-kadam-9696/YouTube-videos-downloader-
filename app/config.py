import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "video_save_path": "./downloads/video",
    "audio_save_path": "./downloads/audio",
    "video_format": "bestvideo+bestaudio/best",
    "video_container": "mp4",
    "audio_format": "mp3",
    "audio_quality": "192",
    "max_results": 10,
    "parallel_downloads": 2,
    "embed_metadata": True,
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Merge with defaults to ensure all keys exist
    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
