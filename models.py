from pydantic import BaseModel
from typing import Optional


class SearchRequest(BaseModel):
    query: str


class DownloadRequest(BaseModel):
    url: str
    mode: str  # "video" or "audio"


class SearchResult(BaseModel):
    id: str
    title: str
    url: str
    channel: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    view_count: Optional[int] = None


class DownloadStatus(BaseModel):
    video_id: str
    status: str  # "queued" | "downloading" | "processing" | "finished" | "error"
    percent: Optional[str] = None
    speed: Optional[str] = None
    eta: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    video_save_path: Optional[str] = None
    audio_save_path: Optional[str] = None
    video_format: Optional[str] = None
    video_container: Optional[str] = None
    audio_format: Optional[str] = None
    audio_quality: Optional[str] = None
    max_results: Optional[int] = None
    parallel_downloads: Optional[int] = None
    embed_metadata: Optional[bool] = None
