#!/usr/bin/env python3
"""
YouTube TurboDownloader - Localhost Web Interface & API Server
==============================================================
Runs on localhost:8000 with a modern glassmorphism web dashboard,
real-time SSE log streaming, parallel chunk downloads, and resume capability.
"""

import asyncio
import datetime
import json
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

# Import core utilities from download_playlist.py
try:
    from download_playlist import (
        QUALITY_PRESETS,
        BatchJob,
        check_ffmpeg,
        fetch_playlist_info,
        find_ytdlp,
    )
except ImportError:
    # Fallback if imported from another path
    sys.path.insert(0, str(Path(__file__).parent.resolve()))
    from download_playlist import (
        QUALITY_PRESETS,
        BatchJob,
        check_ffmpeg,
        fetch_playlist_info,
        find_ytdlp,
    )

app = FastAPI(title="YouTube TurboDownloader Web API")

BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"


# ==============================================================================
# Global State & Log Broadcast Queue
# ==============================================================================

class GlobalDownloadState:
    def __init__(self):
        self.lock = threading.Lock()
        self.active: bool = False
        self.status: str = "IDLE"  # IDLE, RUNNING, COMPLETED, CANCELLED, FAILED
        self.title: str = ""
        self.url: str = ""
        self.total_batches: int = 0
        self.completed_batches: int = 0
        self.failed_batches: int = 0
        self.batches: List[Dict[str, Any]] = []
        self.active_processes: Dict[subprocess.Popen, BatchJob] = {}
        self.cancelled: bool = False
        self.log_subscribers: List[asyncio.Queue] = []
        self.recent_logs: List[Dict[str, str]] = []

    def broadcast_log(self, text: str, level: str = "info"):
        entry = {"text": text, "level": level, "timestamp": time.time()}
        with self.lock:
            self.recent_logs.append(entry)
            if len(self.recent_logs) > 300:
                self.recent_logs.pop(0)

            # Push to all active SSE queues
            for q in list(self.log_subscribers):
                try:
                    q.put_nowait(entry)
                except Exception:
                    pass

    def cancel_all(self):
        with self.lock:
            self.cancelled = True
            self.status = "CANCELLED"
            self.active = False
            procs = list(self.active_processes.keys())

        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass

        time.sleep(0.5)
        for p in procs:
            try:
                p.kill()
            except Exception:
                pass


state = GlobalDownloadState()


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class InspectRequest(BaseModel):
    url: str
    cookies_browser: Optional[str] = None


class DownloadRequest(BaseModel):
    url: str
    output_dir: str = "./downloads"
    quality: str = "1080p"
    audio_only: bool = False
    audio_format: str = "m4a"
    merge_format: str = "mp4"
    workers: int = 3
    chunk_size: int = 20
    start: int = 1
    end: Optional[int] = None
    cookies_from_browser: Optional[str] = None
    concurrent_fragments: int = 3
    throttled_rate: str = "100K"
    retries: int = 10
    no_archive: bool = False
    embed_subs: bool = False
    embed_thumbnail: bool = False


# ==============================================================================
# Static File & UI Serving
# ==============================================================================

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.api_route("/static/{file_path:path}", methods=["GET", "HEAD"])
async def serve_static(file_path: str):
    target = STATIC_DIR / file_path
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Static asset not found.")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    return Response(content=target.read_bytes(), media_type=mime_type)


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/api/system")
async def get_system_status():
    """Returns detected yt-dlp version, ffmpeg presence, and system metrics."""
    ytdlp_ver = None
    try:
        ytdlp_cmd = find_ytdlp()
        proc = subprocess.run(
            list(ytdlp_cmd) + ["--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=4,
        )
        if proc.returncode == 0:
            ytdlp_ver = proc.stdout.strip()
    except Exception:
        ytdlp_ver = None

    ffmpeg_ready = check_ffmpeg()

    return {
        "ytdlp_version": ytdlp_ver,
        "ffmpeg_available": ffmpeg_ready,
        "os": platform.system(),
        "python_version": platform.python_version(),
    }


@app.post("/api/inspect")
async def inspect_url(req: InspectRequest):
    """Fetches title, total items count, uploader, thumbnail, and items preview."""
    try:
        ytdlp_cmd = find_ytdlp()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {e}")

    try:
        # Run flat playlist JSON extraction
        cmd = list(ytdlp_cmd) + [
            "--flat-playlist",
            "-J",
            "--ignore-errors",
            "--no-warnings",
        ]
        if req.cookies_browser:
            cmd.extend(["--cookies-from-browser", req.cookies_browser])
        cmd.append(req.url)

        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.returncode != 0 and not proc.stdout.strip():
            raise RuntimeError(proc.stderr.strip() or "Failed to inspect URL")

        data = json.loads(proc.stdout)
        title = data.get("title") or "YouTube Media"
        uploader = data.get("uploader") or data.get("channel") or ""
        entries = data.get("entries")

        thumbnails = data.get("thumbnails", [])
        thumb_url = thumbnails[-1].get("url") if thumbnails else None

        if entries is not None:
            valid_entries = [e for e in entries if e is not None]
            total_items = len(valid_entries)
            is_playlist = True
            preview_items = [{"title": e.get("title", f"Video {i+1}"), "id": e.get("id")} for i, e in enumerate(valid_entries[:20])]
        else:
            total_items = 1
            is_playlist = False
            preview_items = [{"title": title, "id": data.get("id")}]

        return {
            "title": title,
            "uploader": uploader,
            "total_items": total_items,
            "is_playlist": is_playlist,
            "thumbnail": thumb_url,
            "entries": preview_items,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/status")
async def get_download_status():
    """Returns current active download job state."""
    with state.lock:
        return {
            "active": state.active,
            "status": state.status,
            "title": state.title,
            "url": state.url,
            "total_batches": state.total_batches,
            "completed_batches": state.completed_batches,
            "failed_batches": state.failed_batches,
            "batches": list(state.batches),
        }


@app.post("/api/cancel")
async def cancel_active_download():
    """Terminates all active background download workers."""
    if not state.active:
        return {"status": "ok", "message": "No active download to cancel."}

    state.cancel_all()
    state.broadcast_log("Download cancelled by user.", level="warn")
    return {"status": "ok", "message": "Cancellation initiated."}


@app.post("/api/download")
async def start_download_job(req: DownloadRequest):
    """Initializes parallel batch chunks and launches background download executor."""
    if state.active:
        raise HTTPException(status_code=409, detail="A download job is already actively running!")

    try:
        ytdlp_cmd = find_ytdlp()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp is not available: {e}")

    # Inspect total items
    try:
        meta = await asyncio.to_thread(
            fetch_playlist_info,
            ytdlp_cmd=ytdlp_cmd,
            url=req.url,
            cookies_browser=req.cookies_from_browser,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not inspect playlist: {e}")

    # Determine chunks
    if not meta.is_playlist or meta.total_items <= 1:
        chunks = [(1, 1)]
    else:
        start_idx = max(1, req.start)
        end_idx = min(meta.total_items, req.end) if req.end else meta.total_items
        if start_idx > end_idx:
            raise HTTPException(status_code=400, detail=f"Start index ({start_idx}) cannot exceed end index ({end_idx})")

        chunks = []
        for i in range(start_idx, end_idx + 1, req.chunk_size):
            chunk_end = min(i + req.chunk_size - 1, end_idx)
            chunks.append((i, chunk_end))

    # Initialize state
    with state.lock:
        state.active = True
        state.status = "RUNNING"
        state.cancelled = False
        state.title = meta.title
        state.url = req.url
        state.total_batches = len(chunks)
        state.completed_batches = 0
        state.failed_batches = 0
        state.batches = [
            {
                "batch_num": idx + 1,
                "start_idx": s,
                "end_idx": e,
                "status": "PENDING",
                "duration": 0.0,
            }
            for idx, (s, e) in enumerate(chunks)
        ]

    state.broadcast_log(f"Starting download: '{meta.title}' ({len(chunks)} batches, {req.workers} workers)", level="info")

    # Launch background thread
    threading.Thread(
        target=_run_download_orchestrator,
        args=(req, chunks, meta.is_playlist, ytdlp_cmd),
        daemon=True,
    ).start()

    return {
        "status": "started",
        "title": meta.title,
        "total_batches": len(chunks),
        "total_items": meta.total_items,
    }


def _run_download_orchestrator(
    req: DownloadRequest,
    chunks: List[tuple],
    is_playlist: bool,
    ytdlp_cmd: List[str],
):
    """Background worker thread executing parallel chunk jobs."""
    output_dir = Path(req.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = output_dir / ".logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    archive_path = None if req.no_archive else (output_dir / ".yt-dlp-archive.txt")

    def run_chunk(batch_dict: Dict[str, Any]):
        if state.cancelled:
            batch_dict["status"] = "CANCELLED"
            return

        batch_num = batch_dict["batch_num"]
        s_idx = batch_dict["start_idx"]
        e_idx = batch_dict["end_idx"]

        batch_dict["status"] = "RUNNING"
        state.broadcast_log(f"Batch #{batch_num} (Videos {s_idx}-{e_idx}): Started", level="info")

        log_file = logs_dir / f"batch_{batch_num:03d}_{s_idx}-{e_idx}.log"

        # Build yt-dlp command
        cmd = list(ytdlp_cmd)
        if is_playlist:
            cmd.extend([f"--playlist-start={s_idx}", f"--playlist-end={e_idx}"])

        cmd.extend([
            f"--concurrent-fragments={req.concurrent_fragments}",
            f"--retries={req.retries}",
            f"--fragment-retries={req.retries}",
            "--retry-sleep=exp=1:30",
            "--continue",
            "--no-overwrites",
            "--ignore-errors",
            f"--output={output_dir}/%(playlist_index)03d - %(title).100s.%(ext)s",
        ])

        if req.throttled_rate:
            cmd.append(f"--throttled-rate={req.throttled_rate}")
        if archive_path:
            cmd.append(f"--download-archive={archive_path}")
        if req.cookies_from_browser:
            cmd.append(f"--cookies-from-browser={req.cookies_from_browser}")

        # Quality / Audio
        if req.audio_only or req.quality == "audio":
            cmd.extend(["--extract-audio", f"--audio-format={req.audio_format}", "--audio-quality=0", "--format=ba/b"])
        else:
            fmt = QUALITY_PRESETS.get(req.quality, QUALITY_PRESETS["1080p"])
            cmd.append(f"--format={fmt}")
            if req.merge_format:
                cmd.append(f"--merge-output-format={req.merge_format}")

        if req.embed_subs:
            cmd.extend(["--write-subs", "--write-auto-subs", "--embed-subs"])
        if req.embed_thumbnail:
            cmd.append("--embed-thumbnail")

        cmd.append(req.url)

        start_time = time.time()
        with open(log_file, "w", encoding="utf-8", errors="replace") as f_log:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )
                with state.lock:
                    state.active_processes[proc] = batch_dict

                # Stream lines into log file & broadcast important lines
                for line in proc.stdout:
                    f_log.write(line)
                    cleaned = line.strip()
                    if cleaned and ("[download]" in cleaned or "[ExtractAudio]" in cleaned or "[Merger]" in cleaned or "ERROR" in cleaned):
                        state.broadcast_log(f"[B#{batch_num}] {cleaned}")

                returncode = proc.wait()
            except Exception as e:
                returncode = -1
                state.broadcast_log(f"Batch #{batch_num} error: {e}", level="error")
            finally:
                with state.lock:
                    state.active_processes.pop(proc, None)

        duration = time.time() - start_time
        batch_dict["duration"] = duration

        if state.cancelled:
            batch_dict["status"] = "CANCELLED"
            return

        if returncode == 0:
            batch_dict["status"] = "COMPLETED"
            with state.lock:
                state.completed_batches += 1
            state.broadcast_log(f"Batch #{batch_num} finished successfully ({duration:.1f}s)", level="success")
        else:
            batch_dict["status"] = "FAILED"
            with state.lock:
                state.failed_batches += 1
            state.broadcast_log(f"Batch #{batch_num} failed with code {returncode}", level="error")

    # Run in ThreadPool
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, req.workers)) as executor:
        futures = [executor.submit(run_chunk, b) for b in state.batches]
        concurrent.futures.wait(futures)

    with state.lock:
        state.active = False
        if state.cancelled:
            state.status = "CANCELLED"
        elif state.failed_batches > 0:
            state.status = "FAILED"
        else:
            state.status = "COMPLETED"

    state.broadcast_log(f"All download jobs concluded. Status: {state.status}", level="success" if state.status == "COMPLETED" else "warn")


# ==============================================================================
# Server-Sent Events (SSE) Live Log Streaming
# ==============================================================================

@app.get("/api/logs/stream")
async def stream_logs(request: Request):
    """Server-Sent Events endpoint pushing real-time log lines to the web UI."""
    queue = asyncio.Queue()
    with state.lock:
        state.log_subscribers.append(queue)
        # Push recent logs to catch up
        for r in state.recent_logs[-15:]:
            queue.put_nowait(r)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(entry)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"
        finally:
            with state.lock:
                if queue in state.log_subscribers:
                    state.log_subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ==============================================================================
# Files Browser
# ==============================================================================

@app.get("/api/files")
async def list_downloaded_files(folder: str = Query("./downloads")):
    """Returns list of completed media files in download destination."""
    target_dir = Path(folder).expanduser().resolve()
    if not target_dir.is_dir():
        return []

    files_list = []
    try:
        for p in sorted(target_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_file() and not p.name.startswith("."):
                size_bytes = p.stat().st_size
                if size_bytes >= 1024 * 1024 * 1024:
                    size_fmt = f"{size_bytes / (1024**3):.2f} GB"
                elif size_bytes >= 1024 * 1024:
                    size_fmt = f"{size_bytes / (1024**2):.1f} MB"
                else:
                    size_fmt = f"{size_bytes / 1024:.0f} KB"

                mod_time = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                files_list.append({
                    "name": p.name,
                    "size_bytes": size_bytes,
                    "size_formatted": size_fmt,
                    "modified": mod_time,
                })
    except Exception as e:
        print(f"File list error: {e}")

    return files_list


# ==============================================================================
# Standalone Launcher
# ==============================================================================

def start_server(host: str = "127.0.0.1", port: int = 8000):
    url = f"http://{host}:{port}"
    print("\n" + "=" * 55)
    print("  YouTube Playlist Downloader — Local Web Interface")
    print("=" * 55)
    print(f"  ➜ Open in browser: {url}")
    print(f"  ➜ Stop server    : Press Ctrl+C")
    print("=" * 55 + "\n")

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Downloader Localhost Web Interface")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port)
