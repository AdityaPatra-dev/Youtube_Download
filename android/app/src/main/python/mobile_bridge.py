"""
Mobile Python Bridge for Chaquopy on Android.
Handles yt-dlp execution, format extraction, and progress dispatching
directly within the Android runtime.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

QUALITY_MAP = {
    "best": "bv*+ba/b",
    "2160p": "bv*[height<=2160]+ba/b",
    "4k": "bv*[height<=2160]+ba/b",
    "1440p": "bv*[height<=1440]+ba/b",
    "1080p": "bv*[height<=1080]+ba/b",
    "720p": "bv*[height<=720]+ba/b",
    "480p": "bv*[height<=480]+ba/b",
    "360p": "bv*[height<=360]+ba/b",
}


def fetch_video_info(url: str) -> str:
    """
    Extracts video or playlist metadata and available formats.
    Returns JSON string for the Android WebView to consume.
    """
    import yt_dlp

    ydl_opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return json.dumps({"error": "Failed to extract stream information."})

            is_playlist = info.get("_type") == "playlist" or "entries" in info
            entries = info.get("entries", []) if is_playlist else [info]

            items = []
            for idx, entry in enumerate(entries, start=1):
                if not entry:
                    continue
                items.append({
                    "index": idx,
                    "id": entry.get("id"),
                    "title": entry.get("title") or "Unknown Title",
                    "duration": entry.get("duration", 0),
                    "uploader": entry.get("uploader") or entry.get("channel", "Unknown"),
                    "thumbnail": entry.get("thumbnail"),
                })

            formats = []
            if not is_playlist and info.get("formats"):
                seen = set()
                for f in info["formats"]:
                    h = f.get("height")
                    if h and h not in seen and f.get("vcodec") != "none":
                        seen.add(h)
                        formats.append({
                            "height": h,
                            "label": f"{h}p",
                            "fps": f.get("fps"),
                            "ext": f.get("ext"),
                        })
                formats.sort(key=lambda x: x["height"], reverse=True)

            return json.dumps({
                "success": True,
                "is_playlist": is_playlist,
                "title": info.get("title") or "YouTube Media",
                "count": len(items),
                "items": items[:50],  # Limit preview items for performance
                "formats": formats,
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


class AndroidProgressLogger:
    def __init__(self, log_callback: Optional[Callable[[str], None]]):
        self.log_callback = log_callback

    def debug(self, msg: str):
        if self.log_callback and not msg.startswith("[debug]"):
            self.log_callback(msg)

    def info(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)

    def warning(self, msg: str):
        if self.log_callback:
            self.log_callback(f"[WARN] {msg}")

    def error(self, msg: str):
        if self.log_callback:
            self.log_callback(f"[ERROR] {msg}")


def start_download(
    request_json: str,
    on_progress_cb: Any,
    on_log_cb: Any,
    on_complete_cb: Any,
    on_error_cb: Any,
) -> None:
    """
    Executes a download job on Android.
    Invoked by Android Java/Kotlin host.
    """
    import yt_dlp

    try:
        req = json.loads(request_json)
        url = req.get("url")
        quality = req.get("quality", "1080p").lower()
        format_type = req.get("format_type", "mp4").lower()
        output_dir = req.get("output_dir", "/sdcard/Download")
        sponsorblock = req.get("sponsorblock", False)
        embed_chapters = req.get("embed_chapters", True)
        cookies_path = req.get("cookies_path")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        is_audio = format_type in ("mp3", "m4a", "flac", "opus", "wav")

        # Format selector
        if is_audio:
            format_spec = "bestaudio/best"
        else:
            format_spec = QUALITY_MAP.get(quality, "bv*[height<=1080]+ba/b")

        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

        def progress_hook(d: Dict[str, Any]):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100.0) if total > 0 else 0.0

                speed = d.get("speed")
                speed_str = f"{(speed / (1024*1024)):.2f} MB/s" if speed else "Calculating..."

                eta = d.get("eta")
                eta_str = f"{eta//60:02d}:{eta%60:02d}" if eta is not None else "--:--"

                payload = {
                    "percent": round(percent, 1),
                    "speed": speed_str,
                    "eta": eta_str,
                    "downloaded": downloaded,
                    "total": total,
                    "filename": os.path.basename(d.get("filename", "")),
                }
                if on_progress_cb:
                    on_progress_cb.invoke(json.dumps(payload))

            elif status == "finished":
                if on_log_cb:
                    on_log_cb.invoke("Download finished, merging formats with FFmpeg...")

        ydl_opts: Dict[str, Any] = {
            "format": format_spec,
            "outtmpl": output_template,
            "progress_hooks": [progress_hook],
            "logger": AndroidProgressLogger(lambda msg: on_log_cb.invoke(msg) if on_log_cb else None),
            "no_color": True,
            "continuedl": True,
            "nooverwrites": True,  # Clean filesystem duplicate check
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,  # Moderate concurrency suited for mobile CPUs
        }

        if is_audio:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": format_type,
                "preferredquality": "320" if format_type == "mp3" else "0",
            }]
        else:
            ydl_opts["merge_output_format"] = format_type

        if embed_chapters:
            if "postprocessors" not in ydl_opts:
                ydl_opts["postprocessors"] = []
            ydl_opts["postprocessors"].append({"key": "FFmpegEmbedChapters"})

        if sponsorblock:
            if "postprocessors" not in ydl_opts:
                ydl_opts["postprocessors"] = []
            ydl_opts["postprocessors"].append({
                "key": "SponsorBlock",
                "categories": ["sponsor", "intro", "outro"],
                "when": "after_filter",
            })

        if cookies_path and os.path.exists(cookies_path):
            ydl_opts["cookiefile"] = cookies_path

        # Run extraction & download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            retcode = ydl.download([url])
            if retcode == 0:
                if on_complete_cb:
                    on_complete_cb.invoke(json.dumps({"success": True, "output_dir": output_dir}))
            else:
                if on_error_cb:
                    on_error_cb.invoke(f"Download concluded with exit code {retcode}")

    except Exception as e:
        if on_error_cb:
            on_error_cb.invoke(str(e))
