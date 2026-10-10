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
    "best": "b/bv*+ba/b",
    "2160p": "bv*[height<=2160]+ba/b/b",
    "4k": "bv*[height<=2160]+ba/b/b",
    "1440p": "bv*[height<=1440]+ba/b/b",
    "1080p": "bv*[height<=1080]+ba/b/b",
    "720p": "b[height<=720]/bv*[height<=720]+ba/b/b",
    "480p": "b[height<=480]/bv*[height<=480]+ba/b/b",
    "360p": "b[height<=360]/b",
}


def fetch_video_info(url: str, cookies_content: str = "") -> str:
    """
    Extracts video or playlist metadata and available formats.
    Returns JSON string for the Android WebView to consume.
    """
    import yt_dlp
    import tempfile

    ydl_opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }

    temp_cookie_file = None
    if cookies_content and cookies_content.strip():
        try:
            fd, temp_path = tempfile.mkstemp(prefix="yt_cookies_", suffix=".txt")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(cookies_content)
            ydl_opts["cookiefile"] = temp_path
            temp_cookie_file = temp_path
        except Exception:
            pass
    else:
        for p in [Path("/sdcard/Download/cookies.txt"), Path("/storage/emulated/0/Download/cookies.txt")]:
            if p.is_file():
                ydl_opts["cookiefile"] = str(p)
                break

    try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as initial_err:
            err_msg = str(initial_err)
            if any(term in err_msg.lower() for term in ["bot", "sign in", "confirm"]):
                # Automatic fallback: pure Android mobile client bypass
                ydl_opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            else:
                raise initial_err

        if not info:
            return json.dumps({"error": "Failed to extract stream information."})

        is_playlist = info.get("_type") == "playlist" or "entries" in info
        entries = info.get("entries", []) if is_playlist else [info]

        valid_entries = [e for e in entries if e is not None]
        total_items = max(1, len(valid_entries))
        title = info.get("title") or "YouTube Media"
        uploader = info.get("uploader") or info.get("channel") or ""
        duration = info.get("duration") or 0
        thumbnails = info.get("thumbnails", [])
        thumb_url = thumbnails[-1].get("url") if thumbnails else info.get("thumbnail")

        preview_items = []
        for idx, entry in enumerate(valid_entries[:100], start=1):
            preview_items.append({
                "index": idx,
                "id": entry.get("id"),
                "title": entry.get("title") or f"Item {idx}",
                "duration": entry.get("duration", 0),
                "uploader": entry.get("uploader") or entry.get("channel", uploader),
                "thumbnail": entry.get("thumbnail") or thumb_url,
            })

        chapters = info.get("chapters") or []
        formats = info.get("formats", [])

        # Extract available resolutions
        resolutions = []
        seen_res = set()
        for f in formats:
            h = f.get("height")
            if h and h not in seen_res and f.get("vcodec") != "none":
                seen_res.add(h)
                resolutions.append({
                    "res": f"{h}p",
                    "height": h,
                    "fps": f.get("fps"),
                    "ext": f.get("ext"),
                    "tbr": f.get("tbr"),
                    "is_hdr": "hdr" in (f.get("format_note") or "").lower(),
                })
        resolutions.sort(key=lambda x: x["height"], reverse=True)

        return json.dumps({
            "success": True,
            "title": title,
            "uploader": uploader,
            "total_items": total_items,
            "is_playlist": is_playlist,
            "thumbnail": thumb_url,
            "duration": duration,
            "chapters_count": len(chapters),
            "chapters": chapters[:25],
            "available_resolutions": resolutions,
            "audio_info": {"codec": "AAC/Opus", "bitrate": "160 kbps"},
            "entries": preview_items,
            "preview_items": preview_items,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            try:
                os.unlink(temp_cookie_file)
            except Exception:
                pass


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
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
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

        temp_download_cookie = None
        cookies_text = req.get("cookies_text", "")
        if cookies_text and cookies_text.strip():
            try:
                import tempfile
                fd, tpath = tempfile.mkstemp(prefix="yt_cookie_dl_", suffix=".txt")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(cookies_text)
                ydl_opts["cookiefile"] = tpath
                temp_download_cookie = tpath
            except Exception:
                pass
        elif cookies_path and os.path.exists(cookies_path):
            ydl_opts["cookiefile"] = cookies_path
        else:
            for p in [Path("/sdcard/Download/cookies.txt"), Path("/storage/emulated/0/Download/cookies.txt")]:
                if p.is_file():
                    ydl_opts["cookiefile"] = str(p)
                    break

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
    finally:
        if temp_download_cookie and os.path.exists(temp_download_cookie):
            try:
                os.unlink(temp_download_cookie)
            except Exception:
                pass


