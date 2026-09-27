# YT-DLP Web App

A modern, self-hosted YouTube downloader with a sleek dark UI. Search YouTube, preview results, and download videos or audio — all from your browser.

![App Screenshot](screenshots/home.png)
![App Settings](screenshots/settings.png)
![App Downloads](screenshots/downloads.png)    

## Features

- 🔍 **YouTube Search** — powered by `yt-dlp`, returns thumbnails, duration, channel, and view counts
- 🎬 **Video Download** — best quality, configurable format and container (MP4, MKV, WebM)
- 🎵 **Audio Extraction** — FFmpeg-powered, supports MP3, AAC, FLAC, WAV, Opus
- 📊 **Live Progress** — real-time download progress via Server-Sent Events (%, speed, ETA)
- ⚙️ **Settings Panel** — configure save paths, formats, quality, and result limits
- 🗂️ **Downloads Tab** — track all active and past downloads with status badges

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) on your system PATH *(required for audio extraction)*

## Installation

```bash
# Clone or download the project
cd "YT-DLP Web App"

# Install Python dependencies
pip install fastapi uvicorn[standard] yt-dlp pydantic
```

## Usage

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open **http://localhost:8000** in your browser.

## Project Structure

```
YT-DLP Web App/
├── run.py                  ← Convenience entry point
├── requirements.txt
├── downloads/
│   ├── video/              ← Saved videos
│   └── audio/              ← Saved audio
└── app/
    ├── main.py             ← FastAPI routes
    ├── config.py           ← Config persistence
    ├── models.py           ← Pydantic schemas
    ├── search.py           ← YouTube search
    ├── downloader.py       ← Download + progress tracking
    ├── config.json         ← User settings (auto-generated)
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Search YouTube (`{ "query": "..." }`) |
| `POST` | `/api/download` | Start a download (`{ "url": "...", "mode": "video" \| "audio" }`) |
| `GET`  | `/api/progress/{id}` | SSE stream for live download progress |
| `GET`  | `/api/status/{id}` | Poll download status by ID |
| `GET`  | `/api/config` | Get current configuration |
| `POST` | `/api/config` | Update configuration |

## Configuration

Settings are stored in `app/config.json` and editable via the **Settings** tab in the UI:

| Key | Default | Description |
|-----|---------|-------------|
| `video_save_path` | `./downloads/video` | Where videos are saved |
| `audio_save_path` | `./downloads/audio` | Where audio files are saved |
| `video_format` | `bestvideo+bestaudio/best` | yt-dlp format selector |
| `video_container` | `mp4` | Output container for video |
| `audio_format` | `mp3` | Audio codec |
| `audio_quality` | `192` | Audio bitrate in kbps |
| `max_results` | `10` | Max YouTube search results |
| `parallel_downloads` | `2` | Concurrent download threads |

## Notes

- Audio downloads require **FFmpeg** to be installed and available on your PATH
- Downloads run in background threads; progress is streamed live via SSE
- The app serves the frontend from FastAPI's static file handler — no separate web server needed
