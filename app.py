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
        salvage_partial_downloads,
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
        salvage_partial_downloads,
    )

app = FastAPI(title="YouTube Downloader Web API")

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
        self.output_dir: Optional[Path] = None
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
    container: str = "mp4-h264"
    custom_format: Optional[str] = None
    audio_only: bool = False
    audio_format: str = "m4a"
    merge_format: str = "mp4"
    workers: int = 3
    chunk_size: int = 20
    start: int = 1
    end: Optional[int] = None
    cookies_from_browser: Optional[str] = None
    concurrent_fragments: int = 8
    throttled_rate: Optional[str] = None
    retries: int = 10
    no_archive: bool = False
    embed_subs: bool = False
    embed_thumbnail: bool = False
    embed_chapters: bool = True
    embed_metadata: bool = True


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
        "aria2c_available": bool(shutil.which("aria2c")),
        "os": platform.system(),
        "python_version": platform.python_version(),
    }


def parse_available_formats(formats: List[Dict[str, Any]], duration: Optional[float] = None, total_items: int = 1) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Analyzes yt-dlp format metadata and extracts actual available resolutions, codecs, and true stream sizes."""
    dur = float(duration) if duration and duration > 0 else 0.0

    # 1. Audio stream extraction
    audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
    https_audio = [f for f in audio_formats if "m3u8" not in (f.get("protocol") or "")]
    if https_audio:
        audio_formats = https_audio

    opus_f = next((f for f in audio_formats if "opus" in (f.get("acodec") or "").lower()), None)
    m4a_f = next((f for f in audio_formats if "mp4a" in (f.get("acodec") or "").lower()), None)

    best_audio = None
    for f in audio_formats:
        if not best_audio or (f.get("tbr") or 0) > (best_audio.get("tbr") or 0):
            best_audio = f

    def get_stream_bytes(f: Optional[Dict[str, Any]], fallback_rate_kbps: int) -> int:
        if f:
            sz = f.get("filesize") or f.get("filesize_approx")
            if sz and sz > 0:
                return int(sz)
            if dur > 0 and f.get("tbr"):
                return int((f["tbr"] * 1000 / 8) * dur)
            if dur > 0 and f.get("vbr"):
                return int((f["vbr"] * 1000 / 8) * dur)
        if dur > 0:
            return int((fallback_rate_kbps * 1000 / 8) * dur)
        return int(fallback_rate_kbps * 1000 / 8 * 240)  # default 4-min baseline

    opus_bytes = get_stream_bytes(opus_f, 128)
    m4a_bytes = get_stream_bytes(m4a_f, 192)
    default_audio_bytes = get_stream_bytes(best_audio, 160)

    audio_codec_sizes = {
        "m4a": m4a_bytes,
        "opus": opus_bytes,
        "mp3": int((320 * 1000 / 8) * dur) if dur > 0 else int(default_audio_bytes * 1.5),
        "flac": int((900 * 1000 / 8) * dur) if dur > 0 else int(default_audio_bytes * 3.5),
        "wav": int((1411.2 * 1000 / 8) * dur) if dur > 0 else int(default_audio_bytes * 5.5),
    }

    # 2. Video streams
    video_formats = [f for f in formats if f.get("height") and f.get("height") >= 144 and f.get("vcodec") != "none"]
    has_https_video = any("m3u8" not in (f.get("protocol") or "") for f in video_formats)
    if has_https_video:
        video_formats = [f for f in video_formats if "m3u8" not in (f.get("protocol") or "")]

    by_height_formats: Dict[int, List[Dict[str, Any]]] = {}
    for f in video_formats:
        h = f.get("height")
        if h not in by_height_formats:
            by_height_formats[h] = []
        by_height_formats[h].append(f)

    fallback_rates = {
        2160: {"av1": 15000, "vp9": 18000, "h264": 25000, "default": 20000},
        1440: {"av1": 5500, "vp9": 7500, "h264": 12000, "default": 8000},
        1080: {"av1": 1800, "vp9": 2300, "h264": 3500, "default": 2500},
        720:  {"av1": 900, "vp9": 1300, "h264": 1800, "default": 1400},
        480:  {"av1": 400, "vp9": 500, "h264": 800, "default": 600},
        360:  {"av1": 250, "vp9": 300, "h264": 500, "default": 400},
        240:  {"av1": 150, "vp9": 180, "h264": 300, "default": 220},
        144:  {"av1": 80, "vp9": 100, "h264": 180, "default": 120},
    }

    def fmt_size(b: int) -> str:
        if b >= 1024**3:
            return f"~{b / (1024**3):.1f} GB"
        if b >= 1024**2:
            return f"~{b / (1024**2):.1f} MB"
        return f"~{b / 1024:.0f} KB" if b > 0 else "Unknown size"

    height_labels = {
        2160: "4K Ultra HD",
        1440: "1440p 2K QHD",
        1080: "1080p Full HD",
        720: "720p HD",
        480: "480p SD",
        360: "360p",
        240: "240p",
        144: "144p",
    }

    res_list = []
    sorted_heights = sorted(by_height_formats.keys(), reverse=True)
    max_h = sorted_heights[0] if sorted_heights else None

    for h in sorted_heights:
        flist = by_height_formats[h]
        rates = fallback_rates.get(h, {"av1": 1800, "vp9": 2300, "h264": 3500, "default": 2500})

        av1_f = next((f for f in flist if "av01" in (f.get("vcodec") or "").lower()), None)
        vp9_f = next((f for f in flist if "vp9" in (f.get("vcodec") or "").lower() or "vp09" in (f.get("vcodec") or "").lower()), None)
        h264_f = next((f for f in flist if "avc" in (f.get("vcodec") or "").lower()), None)

        av1_v_bytes = get_stream_bytes(av1_f, rates["av1"])
        vp9_v_bytes = get_stream_bytes(vp9_f, rates["vp9"])
        h264_v_bytes = get_stream_bytes(h264_f, rates["h264"])

        sz_mp4_av1 = av1_v_bytes + m4a_bytes
        sz_mp4_h264 = h264_v_bytes + m4a_bytes
        sz_webm = vp9_v_bytes + opus_bytes
        sz_mkv = max(h264_v_bytes, vp9_v_bytes, av1_v_bytes) + default_audio_bytes
        sz_mov = int(h264_v_bytes * 1.05) + m4a_bytes

        default_sz = sz_mp4_h264 if h264_f else (sz_mp4_av1 if av1_f else sz_webm)
        primary_codec = "H.264" if h264_f else ("AV1" if av1_f else "VP9")
        fps = int(max((f.get("fps") or 30) for f in flist))

        single_sz = default_sz
        playlist_sz = single_sz * total_items

        res_list.append({
            "height": h,
            "label": height_labels.get(h, f"{h}p"),
            "is_max": (h == max_h),
            "size_bytes": single_sz,
            "size_formatted": fmt_size(single_sz),
            "playlist_size_formatted": f"{fmt_size(playlist_sz)} ({total_items} items)" if total_items > 1 else fmt_size(single_sz),
            "vcodec": primary_codec,
            "fps": fps,
            "codec_sizes": {
                "mp4-h264": sz_mp4_h264,
                "mp4-av1": sz_mp4_av1,
                "webm": sz_webm,
                "mkv": sz_mkv,
                "mov": sz_mov,
            },
            "codec_sizes_formatted": {
                "mp4-h264": fmt_size(sz_mp4_h264 * total_items if total_items > 1 else sz_mp4_h264),
                "mp4-av1": fmt_size(sz_mp4_av1 * total_items if total_items > 1 else sz_mp4_av1),
                "webm": fmt_size(sz_webm * total_items if total_items > 1 else sz_webm),
                "mkv": fmt_size(sz_mkv * total_items if total_items > 1 else sz_mkv),
                "mov": fmt_size(sz_mov * total_items if total_items > 1 else sz_mov),
            }
        })

    audio_single_sz = default_audio_bytes
    audio_info = {
        "size_bytes": audio_single_sz,
        "size_formatted": fmt_size(audio_single_sz),
        "playlist_size_formatted": f"{fmt_size(audio_single_sz * total_items)} ({total_items} items)" if total_items > 1 else fmt_size(audio_single_sz),
        "codec": "AAC / MP3 up to 320 kbps",
        "codec_sizes": audio_codec_sizes,
        "codec_sizes_formatted": {
            k: fmt_size(v * total_items if total_items > 1 else v)
            for k, v in audio_codec_sizes.items()
        },
    }

    return res_list, audio_info


@app.post("/api/inspect")
async def inspect_url(req: InspectRequest):
    """Analyzes the video or playlist, extracts actual available resolutions, codecs, and sizes."""
    try:
        ytdlp_cmd = find_ytdlp()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {e}")

    try:
        is_playlist_url = "playlist?list=" in req.url or "/playlist" in req.url
        base_cmd = list(ytdlp_cmd)
        if req.cookies_browser:
            base_cmd.extend(["--cookies-from-browser", req.cookies_browser])

        if not is_playlist_url:
            # Single video direct deep inspection
            cmd = base_cmd + ["-J", "--no-warnings", "--no-playlist", req.url]
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
                raise RuntimeError(proc.stderr.strip() or "Failed to inspect video")

            data = json.loads(proc.stdout)
            title = data.get("title") or "YouTube Video"
            uploader = data.get("uploader") or data.get("channel") or ""
            duration = data.get("duration") or 0
            thumbnails = data.get("thumbnails", [])
            thumb_url = thumbnails[-1].get("url") if thumbnails else None
            formats = data.get("formats", [])

            resolutions, audio_info = parse_available_formats(formats, duration, total_items=1)
            chapters = data.get("chapters") or []

            return {
                "title": title,
                "uploader": uploader,
                "total_items": 1,
                "is_playlist": False,
                "thumbnail": thumb_url,
                "duration": duration,
                "chapters_count": len(chapters),
                "chapters": chapters[:25],
                "available_resolutions": resolutions,
                "audio_info": audio_info,
                "entries": [{"title": title, "id": data.get("id")}],
            }

        # Playlist inspection
        cmd = base_cmd + ["--flat-playlist", "-J", "--ignore-errors", "--no-warnings", req.url]
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
            raise RuntimeError(proc.stderr.strip() or "Failed to inspect playlist")

        data = json.loads(proc.stdout)
        title = data.get("title") or "YouTube Playlist"
        uploader = data.get("uploader") or data.get("channel") or ""
        entries = data.get("entries") or []
        valid_entries = [e for e in entries if e is not None]
        total_items = max(1, len(valid_entries))
        thumbnails = data.get("thumbnails", [])
        thumb_url = thumbnails[-1].get("url") if thumbnails else None

        preview_items = [{"title": e.get("title", f"Video {i+1}"), "id": e.get("id")} for i, e in enumerate(valid_entries[:20])]

        # Sample the first video to extract available resolutions and format specs
        resolutions = []
        audio_info = {}
        if valid_entries and valid_entries[0].get("id"):
            sample_id = valid_entries[0]["id"]
            sample_url = f"https://www.youtube.com/watch?v={sample_id}"
            sample_cmd = base_cmd + ["-J", "--no-warnings", "--no-playlist", sample_url]
            try:
                proc_sample = await asyncio.to_thread(
                    subprocess.run,
                    sample_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if proc_sample.returncode == 0 and proc_sample.stdout.strip():
                    sample_data = json.loads(proc_sample.stdout)
                    duration = sample_data.get("duration") or 0
                    formats = sample_data.get("formats", [])
                    resolutions, audio_info = parse_available_formats(formats, duration, total_items=total_items)
            except Exception:
                pass

        return {
            "title": title,
            "uploader": uploader,
            "total_items": total_items,
            "is_playlist": True,
            "thumbnail": thumb_url,
            "available_resolutions": resolutions,
            "audio_info": audio_info,
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
    """Terminates all active background download workers and salvages partial files."""
    if not state.active:
        return {"status": "ok", "message": "No active download to cancel."}

    target_dir = state.output_dir
    state.cancel_all()

    if target_dir:
        try:
            # Salvage unfinalized partial video files so they are immediately playable
            salvaged = salvage_partial_downloads(target_dir)
            if salvaged:
                salvaged_names = [s.name for s in salvaged]
                state.broadcast_log(f"[✓] Partial video salvaged: '{salvaged[0].name}' (playable in any media player!)", level="success")
                return {
                    "status": "ok",
                    "message": f"Download stopped. Salvaged {len(salvaged)} playable partial video(s)!",
                    "salvaged": salvaged_names,
                }
        except Exception as e:
            print(f"Error salvaging partial downloads: {e}")

    state.broadcast_log("Download cancelled by user.", level="warn")
    return {"status": "ok", "message": "Download stopped."}


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

    target_output_dir = Path(req.output_dir).expanduser().resolve()

    # Initialize state
    with state.lock:
        state.active = True
        state.status = "RUNNING"
        state.cancelled = False
        state.title = meta.title
        state.url = req.url
        state.output_dir = target_output_dir
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

        # Multi-fragment speed acceleration: 16 fragments for single video or 8 for playlists
        frag_count = 16 if not is_playlist or len(chunks) == 1 else max(req.concurrent_fragments, 8)

        cmd.extend([
            f"--concurrent-fragments={frag_count}",
            f"--retries={req.retries}",
            f"--fragment-retries={req.retries}",
            "--file-access-retries=5",
            "--retry-sleep=exp=1:20",
            "--continue",
            "--no-overwrites",
            "--ignore-errors",
            "--http-chunk-size=10M",
            "--buffer-size=16M",
            f"--output={output_dir}/%(playlist_index)03d - %(title).100s.%(ext)s",
        ])

        # If aria2c is installed, utilize aria2c for turbo multi-connection speeds
        if shutil.which("aria2c"):
            cmd.extend([
                "--downloader", "aria2c",
                "--downloader-args", "aria2c:-s 16 -x 16 -k 1M -j 16"
            ])

        if req.throttled_rate:
            cmd.append(f"--throttled-rate={req.throttled_rate}")
        if archive_path:
            cmd.append(f"--download-archive={archive_path}")
        if req.cookies_from_browser:
            cmd.append(f"--cookies-from-browser={req.cookies_from_browser}")

        # Quality / Container / Encoding
        audio_containers = ("mp3", "m4a", "opus", "flac", "wav")
        if req.audio_only or req.quality == "audio" or req.container in audio_containers:
            audio_fmt = req.container if req.container in audio_containers else (req.audio_format or "m4a")
            cmd.extend(["--extract-audio", f"--audio-format={audio_fmt}", "--audio-quality=0"])
            if req.custom_format:
                cmd.append(f"--format={req.custom_format}")
            else:
                cmd.append("--format=ba/b")
        else:
            h_match = re.search(r'\d+', req.quality)
            height_limit = int(h_match.group()) if h_match else None

            merge_fmt = "mp4"
            if req.container == "mp4-av1":
                merge_fmt = "mp4"
                if height_limit:
                    fmt_str = f"bv*[height<={height_limit}][vcodec^=av01]+ba/bv*[height<={height_limit}]+ba/b"
                else:
                    fmt_str = "bv*[vcodec^=av01]+ba/bv*+ba/b"
            elif req.container == "mp4-h264":
                merge_fmt = "mp4"
                if height_limit:
                    fmt_str = f"bv*[height<={height_limit}][vcodec^=avc]+ba[acodec^=mp4a]/bv*[height<={height_limit}]+ba/b"
                else:
                    fmt_str = "bv*[vcodec^=avc]+ba[acodec^=mp4a]/bv*+ba/b"
            elif req.container == "webm":
                merge_fmt = "webm"
                if height_limit:
                    fmt_str = f"bv*[height<={height_limit}][vcodec^=vp9]+ba[acodec^=opus]/bv*[height<={height_limit}]+ba/b"
                else:
                    fmt_str = "bv*[vcodec^=vp9]+ba[acodec^=opus]/bv*+ba/b"
            elif req.container == "mkv":
                merge_fmt = "mkv"
                fmt_str = f"bv*[height<={height_limit}]+ba/b" if height_limit else "bv*+ba/b"
            elif req.container == "mov":
                merge_fmt = "mov"
                fmt_str = f"bv*[height<={height_limit}]+ba/b" if height_limit else "bv*+ba/b"
            elif req.custom_format:
                fmt_str = req.custom_format
                merge_fmt = req.merge_format or "mp4"
            elif height_limit:
                fmt_str = f"bv*[height<={height_limit}]+ba/b"
                merge_fmt = req.merge_format or "mp4"
            else:
                fmt_str = QUALITY_PRESETS.get(req.quality, "bv*+ba/b")
                merge_fmt = req.merge_format or "mp4"

            cmd.append(f"--format={fmt_str}")
            if merge_fmt:
                cmd.append(f"--merge-output-format={merge_fmt}")

        if req.embed_subs:
            cmd.extend(["--write-subs", "--write-auto-subs", "--embed-subs"])
        if req.embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if req.embed_chapters:
            cmd.extend(["--embed-chapters", "--embed-metadata"])

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
