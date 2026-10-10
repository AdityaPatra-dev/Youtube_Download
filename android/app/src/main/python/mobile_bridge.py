"""
Mobile Python Bridge for Chaquopy on Android.
Handles yt-dlp execution, rich format extraction, and progress dispatching
directly within the Android runtime.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def fmt_size(b: int) -> str:
    if b >= 1024**3:
        return f"~{b / (1024**3):.1f} GB"
    if b >= 1024**2:
        return f"~{b / (1024**2):.1f} MB"
    return f"~{b / 1024:.0f} KB" if b > 0 else "Unknown size"


def parse_available_formats(
    formats: List[Dict[str, Any]], duration: Optional[float] = None, total_items: int = 1
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Analyzes yt-dlp formats and produces complete resolution metadata matching frontend expectations."""
    dur = float(duration) if duration and duration > 0 else 0.0

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
        return int(fallback_rate_kbps * 1000 / 8 * 240)

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

    res_list: List[Dict[str, Any]] = []
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

        sz_mp4 = (h264_v_bytes or av1_v_bytes or vp9_v_bytes) + m4a_bytes
        primary_codec = "H.264" if h264_f else ("AV1" if av1_f else "VP9")
        fps = int(max((f.get("fps") or 30) for f in flist))

        res_list.append({
            "height": h,
            "label": height_labels.get(h, f"{h}p"),
            "is_max": (h == max_h),
            "size_bytes": sz_mp4,
            "size_formatted": fmt_size(sz_mp4),
            "playlist_size_formatted": f"{fmt_size(sz_mp4 * total_items)} ({total_items} items)" if total_items > 1 else fmt_size(sz_mp4),
            "vcodec": primary_codec,
            "fps": fps,
            "codec_sizes": {
                "mp4-h264": sz_mp4,
                "mp4-av1": sz_mp4,
                "webm": sz_mp4,
                "mkv": sz_mp4,
                "mov": sz_mp4,
            },
            "codec_sizes_formatted": {
                "mp4-h264": fmt_size(sz_mp4 * total_items if total_items > 1 else sz_mp4),
                "mp4-av1": fmt_size(sz_mp4 * total_items if total_items > 1 else sz_mp4),
                "webm": fmt_size(sz_mp4 * total_items if total_items > 1 else sz_mp4),
                "mkv": fmt_size(sz_mp4 * total_items if total_items > 1 else sz_mp4),
                "mov": fmt_size(sz_mp4 * total_items if total_items > 1 else sz_mp4),
            },
        })

    # Always ensure standard resolutions are presented even if platform initially reported limited streams
    standard_heights = [1080, 720, 480, 360]
    if len(res_list) < 2:
        for sh in standard_heights:
            if not any(r["height"] == sh for r in res_list):
                rate = fallback_rates.get(sh, {}).get("default", 2000)
                v_bytes = int((rate * 1000 / 8) * (dur if dur > 0 else 240))
                sz = v_bytes + default_audio_bytes
                res_list.append({
                    "height": sh,
                    "label": height_labels.get(sh, f"{sh}p"),
                    "is_max": False,
                    "size_bytes": sz,
                    "size_formatted": fmt_size(sz),
                    "playlist_size_formatted": f"{fmt_size(sz * total_items)} ({total_items} items)" if total_items > 1 else fmt_size(sz),
                    "vcodec": "H.264",
                    "fps": 30,
                    "codec_sizes": {"mp4-h264": sz},
                    "codec_sizes_formatted": {"mp4-h264": fmt_size(sz * total_items if total_items > 1 else sz)},
                })
        res_list.sort(key=lambda x: x["height"], reverse=True)
        if res_list:
            res_list[0]["is_max"] = True

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
                "player_client": ["tv_embedded", "android", "web"],
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
            if any(term in err_msg.lower() for term in ["bot", "sign in", "confirm", "format"]):
                # Fallback to pure android client
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

        resolutions, audio_info = parse_available_formats(formats, duration, total_items=total_items)

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
            "audio_info": audio_info,
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
    request_json: Any,
    on_progress_cb: Any,
    on_log_cb: Any,
    on_complete_cb: Any,
    on_error_cb: Any,
) -> None:
    """
    Executes a download job on Android with zero external FFmpeg dependencies.
    Directly streams progressive video or audio into /sdcard/Download.
    """
    import yt_dlp

    temp_download_cookie = None
    try:
        req = json.loads(request_json) if isinstance(request_json, str) else request_json
        url = req.get("url")
        quality = str(req.get("quality", "720p")).lower()
        container = str(req.get("container", "mp4-h264")).lower()
        is_audio = req.get("audio_only", False) or quality == "audio" or any(a in container for a in ["mp3", "m4a", "flac", "opus", "wav"])
        output_dir = req.get("output_dir", "/sdcard/Download")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        if on_log_cb:
            on_log_cb.invoke(f"Connecting to stream for {url}...")

        # Format selector: on mobile without external FFmpeg, prefer progressive single-file streams
        if is_audio:
            format_spec = "bestaudio[ext=m4a]/bestaudio/ba/b/best"
            output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        else:
            h_match = re.search(r"\d+", quality)
            h = int(h_match.group(0)) if h_match else 720
            format_spec = f"b[height<={h}][ext=mp4]/b[height<={h}]/best[height<={h}][ext=mp4]/b/best"
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
                    on_log_cb.invoke("Download finished! Finalizing file in Downloads...")

        ydl_opts: Dict[str, Any] = {
            "format": format_spec,
            "outtmpl": output_template,
            "progress_hooks": [progress_hook],
            "logger": AndroidProgressLogger(lambda msg: on_log_cb.invoke(msg) if on_log_cb else None),
            "no_color": True,
            "continuedl": True,
            "nooverwrites": False,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,
            "postprocessors": [],  # Pure stream download - zero external ffmpeg subprocess
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "tv_embedded"],
                }
            },
        }

        # Handle cookies
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
        else:
            for p in [Path("/sdcard/Download/cookies.txt"), Path("/storage/emulated/0/Download/cookies.txt")]:
                if p.is_file():
                    ydl_opts["cookiefile"] = str(p)
                    break

        if on_log_cb:
            on_log_cb.invoke("Fetching media stream chunks...")

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
