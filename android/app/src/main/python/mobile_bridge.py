"""
Mobile Python Bridge for Chaquopy on Android.
Handles yt-dlp execution, rich format extraction, and high-performance
two-stream downloading with native MediaMuxer hardware muxing on Android.
Supports resolutions up to 4K (2160p), 1440p, 1080p, 720p, and audio-only.
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


def get_height_label(h: int) -> str:
    labels = {
        4320: "8K Ultra HD",
        2160: "4K Ultra HD",
        1440: "1440p 2K QHD",
        1080: "1080p Full HD",
        720: "720p HD",
        480: "480p SD",
        360: "360p",
        240: "240p",
        144: "144p",
    }
    if h in labels:
        return labels[h]
    if h >= 2000:
        return f"{h}p 4K Ultra HD"
    if h >= 1400:
        return f"{h}p 2K QHD"
    if h >= 1000:
        return f"{h}p Full HD"
    if h >= 700:
        return f"{h}p HD"
    return f"{h}p"


def sanitize_filename(name: str) -> str:
    """Removes invalid Android/FAT32 filesystem characters and bounds length."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:100] if len(cleaned) > 100 else (cleaned or "video")


def get_unique_filepath(output_dir: str, title: str, ext: str) -> str:
    """Finds a non-colliding output path without deleting or overwriting existing files."""
    clean_title = sanitize_filename(title)
    final_path = os.path.join(output_dir, f"{clean_title}.{ext}")
    counter = 1
    while os.path.exists(final_path):
        final_path = os.path.join(output_dir, f"{clean_title} ({counter}).{ext}")
        counter += 1
    return final_path


def get_safe_temp_dir(output_dir: str, estimated_bytes: int = 150 * 1024 * 1024) -> str:
    """
    Selects app internal cache directory if space permits to avoid
    Scoped Storage FUSE overhead and MediaStore indexing of incomplete parts.
    """
    try:
        from com.chaquo.python import Python
        context = Python.getPlatform().getApplication()
        cache_dir = str(context.getCacheDir().getAbsolutePath())
        import shutil
        usage = shutil.disk_usage(cache_dir)
        if usage.free > estimated_bytes * 2:
            return cache_dir
    except Exception:
        pass

    try:
        import tempfile
        import shutil
        tdir = tempfile.gettempdir()
        if os.path.exists(tdir) and shutil.disk_usage(tdir).free > estimated_bytes * 2:
            return tdir
    except Exception:
        pass

    return output_dir


def mux_streams(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Muxes video and audio streams using Android's native MediaMuxerHelper (in-process libstagefright),
    falling back to ffmpeg or direct stream preservation if needed.
    """
    # 1. Native Android MediaMuxerHelper
    try:
        from com.adityapatra.youtubedownloader import MediaMuxerHelper
        success = bool(MediaMuxerHelper.mux(video_path, audio_path, output_path))
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            return True
    except Exception as e:
        print(f"Android MediaMuxerHelper failed: {e}")

    # 2. System FFmpeg if available
    try:
        import subprocess
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            return True
    except Exception:
        pass

    # 3. Fallback: Copy the video file so user still receives their video
    try:
        import shutil
        shutil.copy(video_path, output_path)
        return True
    except Exception:
        return False


def parse_available_formats(
    formats: List[Dict[str, Any]], duration: Optional[float] = None, total_items: int = 1
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Analyzes yt-dlp formats and produces complete resolution metadata matching frontend expectations."""
    dur = float(duration) if duration and duration > 0 else 0.0

    # 1. Audio streams
    audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
    https_audio = [f for f in audio_formats if "m3u8" not in (f.get("protocol") or "")]
    if https_audio:
        audio_formats = https_audio

    def select_best_audio(codec_substr: str) -> Optional[Dict[str, Any]]:
        candidates = [f for f in audio_formats if codec_substr in (f.get("acodec") or "").lower()]
        if not candidates:
            return None
        with_sz = [c for c in candidates if (c.get("filesize") or c.get("filesize_approx")) and "m3u8" not in (c.get("protocol") or "")]
        if with_sz:
            return with_sz[0]
        return candidates[0]

    opus_f = select_best_audio("opus")
    m4a_f = select_best_audio("mp4a")

    best_audio = None
    for f in audio_formats:
        if not best_audio or (f.get("tbr") or 0) > (best_audio.get("tbr") or 0):
            best_audio = f

    def get_stream_bytes(f: Optional[Dict[str, Any]], fallback_rate_kbps: int) -> int:
        if f:
            sz = f.get("filesize") or f.get("filesize_approx")
            if sz and sz > 0:
                return int(sz)
            if dur > 0 and f.get("tbr") and f["tbr"] > 0:
                return int((f["tbr"] * 1000 / 8) * dur)
            if dur > 0 and f.get("vbr") and f["vbr"] > 0:
                return int((f["vbr"] * 1000 / 8) * dur)
            if dur > 0 and f.get("abr") and f["abr"] > 0:
                return int((f["abr"] * 1000 / 8) * dur)
        if dur > 0:
            return int((fallback_rate_kbps * 1000 / 8) * dur)
        return int(fallback_rate_kbps * 1000 / 8 * 240)

    opus_bytes = get_stream_bytes(opus_f, 128)
    m4a_bytes = get_stream_bytes(m4a_f, 128)
    default_audio_bytes = get_stream_bytes(best_audio, 128)

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
        4320: {"av1": 25000, "vp9": 35000, "h264": 50000, "default": 35000},
        2160: {"av1": 12000, "vp9": 16000, "h264": 22000, "default": 15000},
        1440: {"av1": 4500,  "vp9": 6500,  "h264": 10000, "default": 6000},
        1080: {"av1": 1600,  "vp9": 2200,  "h264": 3200,  "default": 2400},
        720:  {"av1": 800,   "vp9": 1200,  "h264": 1600,  "default": 1200},
        480:  {"av1": 350,   "vp9": 450,   "h264": 700,   "default": 500},
        360:  {"av1": 220,   "vp9": 280,   "h264": 450,   "default": 350},
        240:  {"av1": 130,   "vp9": 160,   "h264": 260,   "default": 200},
        144:  {"av1": 70,    "vp9": 90,    "h264": 150,   "default": 100},
    }

    res_list: List[Dict[str, Any]] = []
    sorted_heights = sorted(by_height_formats.keys(), reverse=True)
    max_h = sorted_heights[0] if sorted_heights else None

    for h in sorted_heights:
        flist = by_height_formats[h]
        rates = fallback_rates.get(h, {"av1": 1600, "vp9": 2200, "h264": 3200, "default": 2400})

        def select_best_format(codec_substr: str) -> Optional[Dict[str, Any]]:
            candidates = [f for f in flist if codec_substr in (f.get("vcodec") or "").lower()]
            if not candidates:
                return None
            with_sz_https = [c for c in candidates if (c.get("filesize") or c.get("filesize_approx")) and "m3u8" not in (c.get("protocol") or "")]
            if with_sz_https:
                return with_sz_https[0]
            with_sz = [c for c in candidates if (c.get("filesize") or c.get("filesize_approx"))]
            if with_sz:
                return with_sz[0]
            https_only = [c for c in candidates if "m3u8" not in (c.get("protocol") or "")]
            if https_only:
                return https_only[0]
            return candidates[0]

        av1_f = select_best_format("av01")
        vp9_f = select_best_format("vp9") or select_best_format("vp09")
        h264_f = select_best_format("avc")

        av1_v_bytes = get_stream_bytes(av1_f, rates.get("av1", 1600))
        vp9_v_bytes = get_stream_bytes(vp9_f, rates.get("vp9", 2200))
        h264_v_bytes = get_stream_bytes(h264_f, rates.get("h264", 3200))

        sz_mp4_h264 = (h264_v_bytes if h264_f else (av1_v_bytes or vp9_v_bytes)) + m4a_bytes
        sz_mp4_av1 = (av1_v_bytes if av1_f else (h264_v_bytes or vp9_v_bytes)) + m4a_bytes
        sz_webm = (vp9_v_bytes if vp9_f else (av1_v_bytes or h264_v_bytes)) + opus_bytes
        sz_mkv = max(h264_v_bytes, vp9_v_bytes, av1_v_bytes) + default_audio_bytes
        sz_mov = int(h264_v_bytes * 1.05) + m4a_bytes

        default_sz = sz_mp4_h264 if h264_f else (sz_mp4_av1 if av1_f else sz_webm)
        primary_codec = "H.264" if h264_f else ("AV1" if av1_f else "VP9")
        fps = int(max((f.get("fps") or 30) for f in flist))

        res_list.append({
            "height": h,
            "label": get_height_label(h),
            "is_max": (h == max_h),
            "size_bytes": default_sz,
            "size_formatted": fmt_size(default_sz),
            "playlist_size_formatted": f"{fmt_size(default_sz * total_items)} ({total_items} items)" if total_items > 1 else fmt_size(default_sz),
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
            },
        })

    # Fallback only if absolutely zero video streams could be parsed
    if not res_list:
        standard_heights = [2160, 1440, 1080, 720, 480, 360]
        for sh in standard_heights:
            rate = fallback_rates.get(sh, {}).get("default", 2000)
            v_bytes = int((rate * 1000 / 8) * (dur if dur > 0 else 240))
            sz = v_bytes + default_audio_bytes
            res_list.append({
                "height": sh,
                "label": get_height_label(sh),
                "is_max": (sh == 2160),
                "size_bytes": sz,
                "size_formatted": fmt_size(sz),
                "playlist_size_formatted": f"{fmt_size(sz * total_items)} ({total_items} items)" if total_items > 1 else fmt_size(sz),
                "vcodec": "H.264",
                "fps": 30,
                "codec_sizes": {"mp4-h264": sz},
                "codec_sizes_formatted": {"mp4-h264": fmt_size(sz * total_items if total_items > 1 else sz)},
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


def fetch_video_info(url: str, cookies_content: str = "") -> str:
    """
    Extracts video or playlist metadata and available formats.
    Returns JSON string for the Android WebView to consume.
    """
    import yt_dlp
    import tempfile

    ydl_opts: Dict[str, Any] = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
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
        info = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as initial_err:
            err_msg = str(initial_err)
            if any(term in err_msg.lower() for term in ["bot", "sign in", "confirm"]):
                # Fallback to alternate clients that bypass bot checks
                for fallback_client in [["android_vr"], ["ios"], ["mweb"], ["tv"], ["android"]]:
                    try:
                        ydl_opts["extractor_args"] = {"youtube": {"player_client": fallback_client}}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                        if info:
                            break
                    except Exception:
                        continue
                if not info:
                    raise initial_err
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
    Executes a high-quality download job on Android with hardware MediaMuxer remuxing.
    Downloads full 4K, 1440p, 1080p, 720p, or audio streams directly into /sdcard/Download.
    """
    import yt_dlp
    import time

    temp_download_cookie = None
    temp_video_file = None
    temp_audio_file = None

    try:
        req = json.loads(request_json) if isinstance(request_json, str) else request_json
        url = req.get("url")
        quality = str(req.get("quality", "1080p")).lower()
        container = str(req.get("container", "mp4-h264")).lower()
        is_audio = req.get("audio_only", False) or quality == "audio" or any(a in container for a in ["mp3", "m4a", "flac", "opus", "wav"])
        output_dir = req.get("output_dir", "/sdcard/Download")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        if on_log_cb:
            on_log_cb.invoke(f"Connecting to media stream for {url}...")

        # Setup cookies
        cookies_text = req.get("cookies_text", "")
        cookie_path = None
        if cookies_text and cookies_text.strip():
            try:
                import tempfile
                fd, tpath = tempfile.mkstemp(prefix="yt_cookie_dl_", suffix=".txt")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(cookies_text)
                cookie_path = tpath
                temp_download_cookie = tpath
            except Exception:
                pass
        else:
            for p in [Path("/sdcard/Download/cookies.txt"), Path("/storage/emulated/0/Download/cookies.txt")]:
                if p.is_file():
                    cookie_path = str(p)
                    break

        # Base yt-dlp options
        base_opts: Dict[str, Any] = {
            "no_color": True,
            "continuedl": True,
            "nooverwrites": True,
            "overwrites": False,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,
            "postprocessors": [],
            "logger": AndroidProgressLogger(lambda msg: on_log_cb.invoke(msg) if on_log_cb else None),
        }
        if cookie_path:
            base_opts["cookiefile"] = cookie_path

        title = req.get("title") or "YouTube Media"
        clean_title = sanitize_filename(title)

        # Parse target height
        h_match = re.search(r"\d+", quality)
        target_h = int(h_match.group(0)) if h_match else 1080

        # Choose target container extension
        if is_audio:
            out_ext = "m4a" if ("m4a" in container or "aac" in container) else ("mp3" if "mp3" in container else "m4a")
        elif "webm" in container:
            out_ext = "webm"
        elif "mkv" in container:
            out_ext = "mkv"
        else:
            out_ext = "mp4"

        final_output_path = get_unique_filepath(output_dir, clean_title, out_ext)
        temp_dir = get_safe_temp_dir(output_dir)

        # Send immediate initial progress event so UI updates instantly
        if on_progress_cb:
            on_progress_cb.invoke(json.dumps({
                "percent": 1,
                "speed": "Connecting...",
                "eta": "--:--",
                "downloaded": 0,
                "total": 0,
                "filename": clean_title,
                "batches": "1 / 1"
            }))

        formats = []
        if not req.get("title"):
            # Only do full extraction if title was not pre-fetched
            if on_log_cb:
                on_log_cb.invoke("Analyzing video and audio formats...")
            inspect_opts = dict(base_opts)
            inspect_opts["skip_download"] = True
            inspect_opts["quiet"] = True
            with yt_dlp.YoutubeDL(inspect_opts) as ydl:
                meta = ydl.extract_info(url, download=False)
            if meta:
                title = meta.get("title") or title
                clean_title = sanitize_filename(title)
                final_output_path = get_unique_filepath(output_dir, clean_title, out_ext)
                formats = meta.get("formats", [])

        # -------------------------------------------------------------
        # Branch 1: Audio Only Download
        # -------------------------------------------------------------
        if is_audio:
            if on_log_cb:
                on_log_cb.invoke(f"Downloading audio: {clean_title}.{out_ext}...")

            def audio_progress(d: Dict[str, Any]):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    pct = (downloaded / total * 100.0) if total > 0 else 0.0
                    spd = f"{(d.get('speed', 0) / (1024*1024)):.2f} MB/s" if d.get("speed") else "-- MB/s"
                    eta = f"{d.get('eta')//60:02d}:{d.get('eta')%60:02d}" if d.get("eta") is not None else "--:--"
                    payload = {
                        "percent": round(pct, 1),
                        "speed": spd,
                        "eta": eta,
                        "downloaded": downloaded,
                        "total": total,
                        "filename": os.path.basename(final_output_path),
                    }
                    if on_progress_cb:
                        on_progress_cb.invoke(json.dumps(payload))

            audio_opts = dict(base_opts)
            audio_opts["format"] = "bestaudio[ext=m4a]/bestaudio/ba/b/best"
            audio_opts["outtmpl"] = final_output_path
            audio_opts["progress_hooks"] = [audio_progress]

            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                ydl.download([url])

            if on_complete_cb:
                on_complete_cb.invoke(json.dumps({"success": True, "output_dir": output_dir, "file": final_output_path}))
            return

        # -------------------------------------------------------------
        # Branch 2: Check for Existing Matching Progressive Stream
        # -------------------------------------------------------------
        matching_progressive = any(
            f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("height") == target_h
            for f in formats
        )

        if matching_progressive:
            if on_log_cb:
                on_log_cb.invoke(f"Direct stream found for {target_h}p. Downloading in single pass...")

            def prog_hook(d: Dict[str, Any]):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    pct = (downloaded / total * 100.0) if total > 0 else 0.0
                    spd = f"{(d.get('speed', 0) / (1024*1024)):.2f} MB/s" if d.get("speed") else "-- MB/s"
                    eta = f"{d.get('eta')//60:02d}:{d.get('eta')%60:02d}" if d.get("eta") is not None else "--:--"
                    payload = {
                        "percent": round(pct, 1),
                        "speed": spd,
                        "eta": eta,
                        "downloaded": downloaded,
                        "total": total,
                        "filename": os.path.basename(final_output_path),
                    }
                    if on_progress_cb:
                        on_progress_cb.invoke(json.dumps(payload))

            prog_opts = dict(base_opts)
            prog_opts["format"] = f"b[height={target_h}][ext=mp4]/b[height={target_h}]/best[height<={target_h}][ext=mp4]/b/best"
            prog_opts["outtmpl"] = final_output_path
            prog_opts["progress_hooks"] = [prog_hook]

            with yt_dlp.YoutubeDL(prog_opts) as ydl:
                ydl.download([url])

            if on_complete_cb:
                on_complete_cb.invoke(json.dumps({"success": True, "output_dir": output_dir, "file": final_output_path}))
            return

        # -------------------------------------------------------------
        # Branch 3: High-Quality / 4K / 1080p DASH Video + Audio Remux
        # -------------------------------------------------------------
        job_tag = str(int(time.time()))
        temp_video_file = os.path.join(temp_dir, f".temp_v_{job_tag}.mp4")
        temp_audio_file = os.path.join(temp_dir, f".temp_a_{job_tag}.m4a")

        # Step 3a: Video stream download (maps progress 0% - 80%)
        if on_log_cb:
            on_log_cb.invoke(f"Downloading {target_h}p video stream...")

        def video_progress(d: Dict[str, Any]):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                raw_pct = (downloaded / total * 100.0) if total > 0 else 0.0
                effective_pct = raw_pct * 0.80  # 80% weight for video
                spd = f"{(d.get('speed', 0) / (1024*1024)):.2f} MB/s" if d.get("speed") else "-- MB/s"
                eta = f"{d.get('eta')//60:02d}:{d.get('eta')%60:02d}" if d.get("eta") is not None else "--:--"
                payload = {
                    "percent": round(effective_pct, 1),
                    "speed": spd,
                    "eta": eta,
                    "downloaded": downloaded,
                    "total": total,
                    "filename": f"[Video] {os.path.basename(final_output_path)}",
                    "batches": "1 / 1",
                }
                if on_progress_cb:
                    on_progress_cb.invoke(json.dumps(payload))

        # Prefer MP4 container with H.264 or AV1 for native MediaMuxer compatibility
        if "av1" in container:
            v_spec = f"bestvideo[height<={target_h}][vcodec^=av01]/bestvideo[height<={target_h}][ext=mp4]/bestvideo[height<={target_h}]"
        elif "webm" in container:
            v_spec = f"bestvideo[height<={target_h}][vcodec^=vp9]/bestvideo[height<={target_h}][ext=webm]/bestvideo[height<={target_h}]"
        else:
            v_spec = f"bestvideo[height<={target_h}][vcodec^=avc][ext=mp4]/bestvideo[height<={target_h}][ext=mp4]/bestvideo[height<={target_h}]"

        video_opts = dict(base_opts)
        video_opts["format"] = v_spec
        video_opts["outtmpl"] = temp_video_file
        video_opts["progress_hooks"] = [video_progress]

        with yt_dlp.YoutubeDL(video_opts) as ydl:
            ydl.download([url])

        # Step 3b: Audio stream download (maps progress 80% - 95%)
        if on_log_cb:
            on_log_cb.invoke("Downloading high-quality audio stream...")

        def audio_progress(d: Dict[str, Any]):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                raw_pct = (downloaded / total * 100.0) if total > 0 else 0.0
                effective_pct = 80.0 + (raw_pct * 0.15)  # 15% weight for audio (80% - 95%)
                spd = f"{(d.get('speed', 0) / (1024*1024)):.2f} MB/s" if d.get("speed") else "-- MB/s"
                eta = f"{d.get('eta')//60:02d}:{d.get('eta')%60:02d}" if d.get("eta") is not None else "--:--"
                payload = {
                    "percent": round(effective_pct, 1),
                    "speed": spd,
                    "eta": eta,
                    "downloaded": downloaded,
                    "total": total,
                    "filename": f"[Audio] {os.path.basename(final_output_path)}",
                    "batches": "1 / 1",
                }
                if on_progress_cb:
                    on_progress_cb.invoke(json.dumps(payload))

        audio_opts = dict(base_opts)
        audio_opts["format"] = "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio"
        audio_opts["outtmpl"] = temp_audio_file
        audio_opts["progress_hooks"] = [audio_progress]

        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            ydl.download([url])

        # Step 3c: Hardware Remux via MediaMuxer
        if on_log_cb:
            on_log_cb.invoke(f"Muxing {target_h}p video and audio tracks...")

        mux_payload = {
            "percent": 97.0,
            "speed": "Muxing...",
            "eta": "00:01",
            "filename": os.path.basename(final_output_path),
            "batches": "1 / 1",
        }
        if on_progress_cb:
            on_progress_cb.invoke(json.dumps(mux_payload))

        mux_ok = mux_streams(temp_video_file, temp_audio_file, final_output_path)
        if not mux_ok:
            raise RuntimeError(f"Hardware remuxing failed to create output file: {final_output_path}")

        done_payload = {
            "percent": 100.0,
            "speed": "Completed",
            "eta": "00:00",
            "filename": os.path.basename(final_output_path),
            "batches": "1 / 1",
        }
        if on_progress_cb:
            on_progress_cb.invoke(json.dumps(done_payload))

        if on_log_cb:
            on_log_cb.invoke(f"Download completed successfully! Saved to: {final_output_path}")

        if on_complete_cb:
            on_complete_cb.invoke(json.dumps({"success": True, "output_dir": output_dir, "file": final_output_path}))

    except Exception as e:
        if on_error_cb:
            on_error_cb.invoke(str(e))
    finally:
        # Clean up temporary stream chunks safely
        for tmp_f in [temp_video_file, temp_audio_file, temp_download_cookie]:
            if tmp_f and os.path.exists(tmp_f):
                try:
                    os.unlink(tmp_f)
                except Exception:
                    pass
