import asyncio
import json
import sys
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Allow running from project root or app dir
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config, save_config
from models import SearchRequest, DownloadRequest, ConfigUpdateRequest
from search import search_youtube
from downloader import start_download, get_status, get_all_statuses

app = FastAPI(title="YT-DLP Web App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@app.post("/api/search")
async def api_search(req: SearchRequest):
    cfg = load_config()
    try:
        results = await asyncio.to_thread(search_youtube, req.query, cfg["max_results"])
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download")
async def api_download(req: DownloadRequest):
    if req.mode not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="mode must be 'video' or 'audio'")
    cfg = load_config()
    download_id = start_download(req.url, req.mode, cfg)
    return {"success": True, "download_id": download_id}


@app.get("/api/status/{download_id}")
async def api_status(download_id: str):
    status = get_status(download_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Download not found")
    return status


@app.get("/api/status")
async def api_all_statuses():
    return get_all_statuses()


@app.get("/api/progress/{download_id}")
async def api_progress_sse(download_id: str):
    """Server-Sent Events endpoint for live progress streaming."""
    async def event_generator():
        while True:
            status = get_status(download_id)
            data = json.dumps(status)
            yield f"data: {data}\n\n"

            if status.get("status") in ("finished", "error", "not_found"):
                break
            await asyncio.sleep(0.8)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/config")
async def api_get_config():
    return load_config()


@app.post("/api/config")
async def api_update_config(cfg: ConfigUpdateRequest):
    current = load_config()
    patch = cfg.model_dump(exclude_none=True)
    current.update(patch)
    save_config(current)
    return {"success": True, "config": current}
