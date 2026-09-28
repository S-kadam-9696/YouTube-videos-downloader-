import asyncio
import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Allow running from project root or app directory
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from config import load_config, save_config
from models import SearchRequest, DownloadRequest, ConfigUpdateRequest
from search import search_youtube
from downloader import start_download, get_status, get_all_statuses


app = FastAPI(
    title="YT-DLP Web App",
    version="1.0.0",
)


# ── CORS ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Static files ─────────────────────────────────────────────────────

STATIC_DIR = APP_DIR / "static"

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )


# ── Root ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"

    if not index.exists():
        raise HTTPException(
            status_code=404,
            detail="index.html not found",
        )

    return HTMLResponse(
        content=index.read_text(encoding="utf-8")
    )


# ── Health check ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "yt-dlp-web-app",
    }


# ── Search ───────────────────────────────────────────────────────────

@app.post("/api/search")
async def api_search(req: SearchRequest):
    query = req.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    cfg = load_config()

    try:
        max_results = int(cfg.get("max_results", 10))

        results = await asyncio.to_thread(
            search_youtube,
            query,
            max_results,
        )

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ── Start download ──────────────────────────────────────────────────

@app.post("/api/download")
async def api_download(req: DownloadRequest):
    if req.mode not in ("video", "audio"):
        raise HTTPException(
            status_code=400,
            detail="mode must be 'video' or 'audio'",
        )

    if not req.url or not req.url.strip():
        raise HTTPException(
            status_code=400,
            detail="URL cannot be empty",
        )

    cfg = load_config()

    try:
        download_id = start_download(
            req.url.strip(),
            req.mode,
            cfg,
        )

        return {
            "success": True,
            "download_id": download_id,
            "id": download_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ── Single download status ──────────────────────────────────────────

@app.get("/api/status/{download_id}")
async def api_status(download_id: str):
    status = get_status(download_id)

    if status.get("status") == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Download not found",
        )

    return status


# ── All download statuses ───────────────────────────────────────────

@app.get("/api/status")
async def api_all_statuses():
    return get_all_statuses()


# ── Progress SSE ────────────────────────────────────────────────────

@app.get("/api/progress/{download_id}")
async def api_progress_sse(download_id: str):

    async def event_generator():
        while True:
            status = get_status(download_id)

            data = json.dumps(status)

            yield f"data: {data}\n\n"

            current_status = status.get("status")

            if current_status in (
                "finished",
                "completed",
                "error",
                "failed",
                "not_found",
            ):
                break

            await asyncio.sleep(0.8)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Configuration ───────────────────────────────────────────────────

@app.get("/api/config")
async def api_get_config():
    return load_config()


@app.post("/api/config")
async def api_update_config(
    cfg: ConfigUpdateRequest,
):
    current = load_config()

    patch = cfg.model_dump(
        exclude_none=True
    )

    current.update(patch)

    save_config(current)

    return {
        "success": True,
        "config": current,
    }


# ── Downloaded file ─────────────────────────────────────────────────

@app.get("/api/file/{download_id}")
async def api_download_file(download_id: str):
    status = get_status(download_id)

    if status.get("status") not in (
        "finished",
        "completed",
    ):
        raise HTTPException(
            status_code=404,
            detail="Download is not finished",
        )

    filename = status.get("filename")

    if not filename:
        raise HTTPException(
            status_code=404,
            detail="Downloaded file not found",
        )

    file_path = Path(filename)

    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Downloaded file does not exist",
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
