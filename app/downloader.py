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
    pattern = r"(?i)\s*[\(\[][^"]
