#!/usr/bin/env python3
"""
YouTube Parallel Playlist Downloader
=====================================
A robust, cross-platform Python downloader for YouTube playlists and videos.
Features:
  - Parallel chunked downloading for maximum speed
  - Automatic resumption via yt-dlp download archive (no re-downloading)
  - Interactive wizard mode or full CLI argument support
  - Clean child process management (Ctrl+C kills all background workers)
  - Per-batch log files with error summaries on failure
  - Automatic retry for failed batches
  - Works on Windows, Linux, and macOS
"""

import argparse
import concurrent.futures
import json
import os
import glob
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# Console Colors & Formatting
# ==============================================================================

class Colors:
    ENABLED = True
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @classmethod
    def init(cls, force_no_color: bool = False):
        if force_no_color or not sys.stdout.isatty():
            cls.ENABLED = False
            return
        if platform.system() == "Windows":
            # Enable ANSI escape sequences on Windows 10/11
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                mode = ctypes.c_ulong()
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                cls.ENABLED = True
            except Exception:
                cls.ENABLED = os.environ.get("WT_SESSION") is not None or "ANSICON" in os.environ

    @classmethod
    def paint(cls, text: str, color: str) -> str:
        return f"{color}{text}{cls.RESET}" if cls.ENABLED else text

    @classmethod
    def info(cls, text: str) -> str:
        return f"{cls.paint('[i]', cls.BLUE)} {text}"

    @classmethod
    def success(cls, text: str) -> str:
        return f"{cls.paint('[✓]', cls.GREEN)} {text}"

    @classmethod
    def warn(cls, text: str) -> str:
        return f"{cls.paint('[!]', cls.YELLOW)} {text}"

    @classmethod
    def error(cls, text: str) -> str:
        return f"{cls.paint('[✗]', cls.RED)} {text}"

    @classmethod
    def highlight(cls, text: str) -> str:
        return cls.paint(text, cls.CYAN + cls.BOLD)


# ==============================================================================
# Quality & Format Presets
# ==============================================================================

QUALITY_PRESETS = {
    "best": "bv*+ba/b",
    "2160p": "bv*[height<=2160]+ba/b",
    "4k": "bv*[height<=2160]+ba/b",
    "1440p": "bv*[height<=1440]+ba/b",
    "2k": "bv*[height<=1440]+ba/b",
    "1080p": "bv*[height<=1080]+ba/b",
    "720p": "bv*[height<=720]+ba/b",
    "480p": "bv*[height<=480]+ba/b",
    "360p": "bv*[height<=360]+ba/b",
    "audio": "ba/b",
}


# ==============================================================================
# Prerequisite Checks
# ==============================================================================

def get_js_runtime_args() -> List[str]:
    """Returns arguments for YouTube JavaScript challenge solving (Node.js/Deno) to prevent HTTP 403 Forbidden."""
    args = []
    if shutil.which("node"):
        args.extend(["--js-runtimes", "node", "--remote-components", "ejs:github"])
    elif shutil.which("deno"):
        args.extend(["--js-runtimes", "deno", "--remote-components", "ejs:github"])
    return args


def detect_available_browsers() -> List[Dict[str, Any]]:
    """Detects available web browsers with cookie databases on the host system."""
    home = Path.home()
    system = platform.system()
    candidates = [
        ("chrome", "Google Chrome"),
        ("firefox", "Mozilla Firefox"),
        ("brave", "Brave Browser"),
        ("edge", "Microsoft Edge"),
        ("chromium", "Chromium"),
        ("opera", "Opera"),
        ("vivaldi", "Vivaldi"),
    ]
    results = []

    # Check for cookies.txt file in project root or current working dir
    project_cookies = Path.cwd() / "cookies.txt"
    if project_cookies.is_file():
        results.append({
            "id": "file:cookies.txt",
            "name": "cookies.txt (Found in project folder)",
            "has_cookies": True,
            "recommended": True,
        })

    for b_id, b_name in candidates:
        has_cookies = False
        is_installed = bool(shutil.which(b_id) or shutil.which(f"{b_id}-browser") or shutil.which(f"google-{b_id}"))

        if system == "Linux":
            patterns = {
                "chrome": [str(home / ".config/google-chrome/**/Cookies"), str(home / ".config/chromium/**/Cookies")],
                "chromium": [str(home / ".config/chromium/**/Cookies")],
                "firefox": [str(home / ".mozilla/firefox/**/*.sqlite"), str(home / "snap/firefox/common/.mozilla/firefox/**/*.sqlite")],
                "brave": [str(home / ".config/BraveSoftware/Brave-Browser/**/Cookies")],
                "edge": [str(home / ".config/microsoft-edge/**/Cookies")],
                "opera": [str(home / ".config/opera/**/Cookies")],
                "vivaldi": [str(home / ".config/vivaldi/**/Cookies")],
            }
        elif system == "Darwin":
            patterns = {
                "chrome": [str(home / "Library/Application Support/Google/Chrome/**/Cookies")],
                "firefox": [str(home / "Library/Application Support/Firefox/Profiles/**/*.sqlite")],
                "brave": [str(home / "Library/Application Support/BraveSoftware/Brave-Browser/**/Cookies")],
                "edge": [str(home / "Library/Application Support/Microsoft Edge/**/Cookies")],
                "safari": [str(home / "Library/Containers/com.apple.Safari/Data/Library/Cookies/*.binarycookies")],
            }
        else:  # Windows
            appdata = os.environ.get("APPDATA", "")
            localappdata = os.environ.get("LOCALAPPDATA", "")
            patterns = {
                "chrome": [f"{localappdata}/Google/Chrome/User Data/**/Cookies"],
                "firefox": [f"{appdata}/Mozilla/Firefox/Profiles/**/*.sqlite"],
                "brave": [f"{localappdata}/BraveSoftware/Brave-Browser/User Data/**/Cookies"],
                "edge": [f"{localappdata}/Microsoft/Edge/User Data/**/Cookies"],
            }

        file_list = []
        for p in patterns.get(b_id, []):
            try:
                file_list.extend(glob.glob(p, recursive=True))
            except Exception:
                pass

        if file_list:
            has_cookies = True
            is_installed = True

        if is_installed or has_cookies:
            results.append({
                "id": b_id,
                "name": f"{b_name}" + (" (Cookies detected)" if has_cookies else " (Installed, no active cookies)"),
                "has_cookies": has_cookies,
                "recommended": False,
            })

    return results


def find_ytdlp(custom_path: Optional[str] = None) -> List[str]:
    """Finds yt-dlp executable or python module command, equipped with JS challenge solvers."""
    base_cmd = None
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            base_cmd = [str(p)]
        elif shutil.which(custom_path):
            base_cmd = [custom_path]
        else:
            raise FileNotFoundError(f"Specified yt-dlp path '{custom_path}' was not found or is not executable.")

    # 1. Check if yt-dlp is in PATH
    if not base_cmd:
        which_path = shutil.which("yt-dlp")
        if which_path:
            base_cmd = [which_path]

    # 2. Check if yt-dlp.exe is in current directory or C:\yt-dlp on Windows
    if not base_cmd and platform.system() == "Windows":
        common_paths = [
            Path.cwd() / "yt-dlp.exe",
            Path("C:/yt-dlp/yt-dlp.exe"),
            Path.home() / "yt-dlp.exe",
        ]
        for cp in common_paths:
            if cp.is_file():
                base_cmd = [str(cp)]
                break

    # 3. Check if installed in current python environment
    if not base_cmd:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                base_cmd = [sys.executable, "-m", "yt_dlp"]
        except Exception:
            pass

    if not base_cmd:
        msg = (
            f"{Colors.error('yt-dlp was not found on your system!')}\n\n"
            f"  Please install yt-dlp using one of the following methods:\n"
            f"    • Python pip:  {Colors.paint('pip install yt-dlp', Colors.GREEN)}\n"
            f"    • Standalone:  Download binary from https://github.com/yt-dlp/yt-dlp/releases\n"
            f"    • Windows:     {Colors.paint('winget install yt-dlp', Colors.GREEN)}\n"
            f"    • macOS:       {Colors.paint('brew install yt-dlp', Colors.GREEN)}\n"
            f"    • Linux:       Use your package manager or install via pip.\n\n"
            f"  Or pass --yt-dlp-path=/path/to/yt-dlp"
        )
        raise RuntimeError(msg)

    # Attach JS challenge solver runtimes (Node.js / Deno) to guarantee no 403 Forbidden
    return base_cmd + get_js_runtime_args()


def check_ffmpeg(custom_path: Optional[str] = None) -> bool:
    """Checks if ffmpeg is available."""
    if custom_path and shutil.which(custom_path):
        return True
    if shutil.which("ffmpeg"):
        return True
    if platform.system() == "Windows":
        for cp in [Path("C:/ffmpeg/bin/ffmpeg.exe"), Path.cwd() / "ffmpeg.exe"]:
            if cp.is_file():
                return True
    return False


def salvage_partial_downloads(output_dir: Path) -> List[Path]:
    """
    Finds unfinalized .part or .ytdl files in output_dir and repairs/muxes them
    using ffmpeg into playable .mp4 media files so users can view interrupted downloads.
    """
    if not output_dir.is_dir() or not check_ffmpeg():
        return []

    part_files = list(output_dir.glob("*.part")) + list(output_dir.glob("*.ytdl"))
    if not part_files:
        return []

    salvaged = []
    groups: Dict[str, List[Path]] = {}
    for pf in part_files:
        core = re.sub(r'\.(part|ytdl)$', '', pf.name)
        m = re.match(r'^(.*?)(?:\.f\d+)?(?:\.(?:mp4|m4a|webm|opus|mkv))?$', core)
        base = m.group(1) if m else core
        if base not in groups:
            groups[base] = []
        groups[base].append(pf)

    for base, files in groups.items():
        try:
            video_part = None
            audio_part = None
            for f in files:
                fname_lower = f.name.lower()
                if any(x in fname_lower for x in [".m4a.", ".opus.", ".aac.", ".mp3.", "f140.", "f251.", "audio"]):
                    audio_part = f
                elif any(x in fname_lower for x in [".mp4.", ".webm.", "f137.", "f248.", "f398.", "f299.", "f399.", "video"]):
                    video_part = f

            out_file = output_dir / f"[PARTIAL] {base}.mp4"

            if video_part and audio_part and video_part != audio_part:
                cmd = [
                    "ffmpeg", "-y", "-err_detect", "ignore_err",
                    "-i", str(video_part),
                    "-i", str(audio_part),
                    "-c", "copy",
                    "-movflags", "faststart",
                    str(out_file),
                ]
            else:
                target_part = video_part or files[0]
                if target_part.stat().st_size < 100 * 1024:
                    continue
                cmd = [
                    "ffmpeg", "-y", "-err_detect", "ignore_err",
                    "-i", str(target_part),
                    "-c", "copy",
                    "-movflags", "faststart",
                    str(out_file),
                ]

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            if proc.returncode == 0 and out_file.is_file() and out_file.stat().st_size > 0:
                salvaged.append(out_file)
                for f in files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        except Exception as e:
            pass

    return salvaged


# ==============================================================================
# Playlist Metadata
# ==============================================================================

class PlaylistMetadata:
    def __init__(self, url: str, title: str, total_items: int, is_playlist: bool, uploader: str = ""):
        self.url = url
        self.title = title
        self.total_items = total_items
        self.is_playlist = is_playlist
        self.uploader = uploader


def fetch_playlist_info(
    ytdlp_cmd: List[str],
    url: str,
    cookies_file: Optional[str] = None,
    cookies_browser: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> PlaylistMetadata:
    """Extracts title and total items count using yt-dlp flat-playlist json."""
    cmd = list(ytdlp_cmd) + [
        "--flat-playlist",
        "-J",
        "--ignore-errors",
        "--no-warnings",
    ]

    cookie_args = []
    if cookies_file:
        cookie_args = ["--cookies", str(Path(cookies_file).expanduser().resolve())]
    elif cookies_browser:
        if cookies_browser.startswith("file:"):
            c_path = Path(cookies_browser.split("file:", 1)[1]).expanduser().resolve()
            if c_path.is_file():
                cookie_args = ["--cookies", str(c_path)]
        else:
            cookie_args = ["--cookies-from-browser", cookies_browser]

    cmd.extend(cookie_args)

    if extra_args:
        cmd.extend(extra_args)

    cmd.append(url)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to execute yt-dlp: {e}")

    # If cookies failed, retry once without cookies
    if proc.returncode != 0 and cookie_args:
        err_msg = proc.stderr.strip()
        if any(term in err_msg.lower() for term in ["cookie", "could not find", "database", "keyring", "sqlite", "unavailable"]):
            retry_cmd = [a for a in cmd if a not in cookie_args and not a.startswith("--cookies")]
            try:
                proc = subprocess.run(
                    retry_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
            except Exception:
                pass

    if proc.returncode != 0 and not proc.stdout.strip():
        err_msg = proc.stderr.strip() or "Unknown error"
        raise RuntimeError(f"yt-dlp failed to inspect URL:\n{err_msg}")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse yt-dlp JSON output: {e}\nRaw output: {proc.stdout[:500]}")

    title = data.get("title") or "YouTube Media"
    uploader = data.get("uploader") or data.get("channel") or ""

    # Check if playlist or single video
    entries = data.get("entries")
    if entries is not None:
        # It's a playlist or channel
        valid_entries = [e for e in entries if e is not None]
        total_items = len(valid_entries)
        is_playlist = True
    else:
        # Single video
        total_items = 1
        is_playlist = False

    return PlaylistMetadata(
        url=url,
        title=title,
        total_items=total_items,
        is_playlist=is_playlist,
        uploader=uploader,
    )


# ==============================================================================
# Batch Job Definition & Downloader Manager
# ==============================================================================

class BatchJob:
    def __init__(self, batch_num: int, total_batches: int, start_idx: int, end_idx: int, is_playlist: bool):
        self.batch_num = batch_num
        self.total_batches = total_batches
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.is_playlist = is_playlist
        self.status = "PENDING"
        self.exit_code: Optional[int] = None
        self.duration: float = 0.0
        self.error_excerpt: Optional[str] = None
        self.log_path: Optional[Path] = None

    @property
    def label(self) -> str:
        if self.is_playlist:
            return f"Batch {self.batch_num}/{self.total_batches} (Videos {self.start_idx}-{self.end_idx})"
        return "Single Video Download"


class DownloadManager:
    """Manages parallel batch executions, process monitoring, and clean shutdown."""

    def __init__(
        self,
        ytdlp_cmd: List[str],
        url: str,
        output_dir: Path,
        quality: str,
        custom_format: Optional[str] = None,
        audio_only: bool = False,
        audio_format: str = "m4a",
        merge_format: str = "mp4",
        concurrent_fragments: int = 8,
        throttled_rate: Optional[str] = None,
        retries: int = 10,
        cookies_file: Optional[str] = None,
        cookies_browser: Optional[str] = None,
        archive_path: Optional[Path] = None,
        embed_subs: bool = False,
        sub_langs: str = "en.*,all",
        embed_thumbnail: bool = False,
        embed_metadata: bool = True,
        extra_args: Optional[List[str]] = None,
        output_template: Optional[str] = None,
        workers: int = 3,
        max_batch_retries: int = 1,
        verbose: bool = False,
    ):
        self.ytdlp_cmd = ytdlp_cmd
        self.url = url
        self.output_dir = output_dir.expanduser().resolve()
        self.quality = quality
        self.custom_format = custom_format
        self.audio_only = audio_only
        self.audio_format = audio_format
        self.merge_format = merge_format
        self.concurrent_fragments = max(1, concurrent_fragments)
        self.throttled_rate = throttled_rate
        self.retries = retries
        self.cookies_file = cookies_file
        self.cookies_browser = cookies_browser
        self.archive_path = archive_path
        self.embed_subs = embed_subs
        self.sub_langs = sub_langs
        self.embed_thumbnail = embed_thumbnail
        self.embed_metadata = embed_metadata
        self.extra_args = extra_args or []
        self.workers = max(1, workers)
        self.max_batch_retries = max_batch_retries
        self.verbose = verbose

        if output_template:
            self.output_template = output_template
        elif audio_only:
            self.output_template = "%(playlist_index)03d - %(title).100s.%(ext)s"
        else:
            self.output_template = "%(playlist_index)03d - %(title).100s.%(ext)s"

        self.logs_dir = self.output_dir / ".logs"
        self.active_processes: Dict[subprocess.Popen, BatchJob] = {}
        self.lock = threading.Lock()
        self.cancelled = False

    def build_batch_command(self, job: BatchJob, log_file: Path) -> List[str]:
        """Constructs yt-dlp arguments for a given batch."""
        cmd = list(self.ytdlp_cmd)

        if job.is_playlist:
            cmd.extend([
                f"--playlist-start={job.start_idx}",
                f"--playlist-end={job.end_idx}",
            ])

        # High-speed fragment concurrency: use 16 fragments for single video or 8 for playlists
        frag_count = 16 if not job.is_playlist or job.total_batches == 1 else max(self.concurrent_fragments, 8)

        # Core resilience & chunking
        cmd.extend([
            f"--concurrent-fragments={frag_count}",
            f"--retries={self.retries}",
            f"--fragment-retries={self.retries}",
            "--file-access-retries=5",
            "--retry-sleep=exp=1:20",
            "--continue",
            "--no-overwrites",
            "--ignore-errors",
            "--http-chunk-size=10M",
            "--buffer-size=16M",
            f"--output={self.output_dir / (self.output_template if job.is_playlist else '%(title).100s.%(ext)s')}",
        ])

        # If aria2c is installed, utilize aria2c for turbo multi-connection speeds
        if shutil.which("aria2c"):
            cmd.extend([
                "--downloader", "aria2c",
                "--downloader-args", "aria2c:-s 16 -x 16 -k 1M -j 16"
            ])

        if self.throttled_rate:
            cmd.append(f"--throttled-rate={self.throttled_rate}")

        # Download archive: check actual files on disk unless archive_path is explicitly set
        if self.archive_path:
            cmd.append(f"--download-archive={self.archive_path}")
        else:
            cmd.extend(["--no-download-archive", "--no-overwrites"])

        # Cookies
        if self.cookies_file:
            cmd.append(f"--cookies={Path(self.cookies_file).expanduser().resolve()}")
        elif self.cookies_browser:
            if self.cookies_browser.startswith("file:"):
                c_path = Path(self.cookies_browser.split("file:", 1)[1]).expanduser().resolve()
                if c_path.is_file():
                    cmd.append(f"--cookies={c_path}")
            else:
                cmd.append(f"--cookies-from-browser={self.cookies_browser}")

        # Format / Audio options
        if self.audio_only:
            cmd.extend([
                "--extract-audio",
                f"--audio-format={self.audio_format}",
                "--audio-quality=0",
            ])
            if self.custom_format:
                cmd.append(f"--format={self.custom_format}")
            else:
                cmd.append("--format=ba/b")
        else:
            format_str = self.custom_format or QUALITY_PRESETS.get(self.quality, QUALITY_PRESETS["1080p"])
            cmd.append(f"--format={format_str}")
            if self.merge_format == "mov":
                cmd.append("--recode-video=mov")
            elif self.merge_format:
                cmd.append(f"--merge-output-format={self.merge_format}")

        # Subtitles
        if self.embed_subs:
            cmd.extend([
                "--write-subs",
                "--write-auto-subs",
                f"--sub-langs={self.sub_langs}",
                "--embed-subs",
            ])

        # Thumbnails & Metadata
        if self.embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if self.embed_metadata:
            cmd.extend(["--embed-metadata", "--embed-chapters"])
        else:
            cmd.append("--embed-chapters")

        # Any extra user-supplied arguments
        if self.extra_args:
            cmd.extend(self.extra_args)

        # URL goes last
        cmd.append(self.url)
        return cmd

    def run_single_batch(self, job: BatchJob) -> BatchJob:
        """Executes a single batch, logging output to disk."""
        if self.cancelled:
            job.status = "CANCELLED"
            return job

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_name = f"batch_{job.batch_num:03d}_{job.start_idx}-{job.end_idx}.log" if job.is_playlist else "download_single.log"
        job.log_path = self.logs_dir / log_name

        cmd = self.build_batch_command(job, job.log_path)
        job.status = "RUNNING"

        print(Colors.info(f"Started  : {Colors.highlight(job.label)}"))
        start_time = time.time()

        with open(job.log_path, "w", encoding="utf-8", errors="replace") as log_file:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                with self.lock:
                    if self.cancelled:
                        proc.terminate()
                        job.status = "CANCELLED"
                        return job
                    self.active_processes[proc] = job

                returncode = proc.wait()
            except Exception as e:
                returncode = -1
                log_file.write(f"\nExecution error: {e}\n")
            finally:
                with self.lock:
                    self.active_processes.pop(proc, None)

        # Automatic fallback: if cookies caused failure, retry without cookies
        if returncode != 0 and (self.cookies_browser or self.cookies_file) and not self.cancelled:
            err_summary = self._extract_error_summary(job.log_path)
            if any(term in err_summary.lower() for term in ["cookie", "could not find", "database", "keyring", "sqlite", "unavailable"]):
                print(Colors.warning(f"Warning: Cookies failed for {job.label} ({err_summary}). Retrying download without cookies..."))
                retry_cmd = [a for a in cmd if not (a.startswith("--cookies") or a == "--cookies-from-browser" or (self.cookies_browser and a == self.cookies_browser))]
                with open(job.log_path, "a", encoding="utf-8", errors="replace") as log_file:
                    log_file.write("\n--- [System] Retrying download without cookies ---\n")
                    try:
                        proc = subprocess.Popen(
                            retry_cmd,
                            stdout=log_file,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                        )
                        with self.lock:
                            if self.cancelled:
                                proc.terminate()
                                job.status = "CANCELLED"
                                return job
                            self.active_processes[proc] = job
                        returncode = proc.wait()
                    except Exception as e:
                        returncode = -1
                    finally:
                        with self.lock:
                            self.active_processes.pop(proc, None)

        job.duration = time.time() - start_time
        job.exit_code = returncode

        if self.cancelled:
            job.status = "CANCELLED"
            return job

        if returncode == 0:
            job.status = "COMPLETED"
            print(Colors.success(f"Finished : {job.label} ({job.duration:.1f}s)"))
        else:
            job.status = "FAILED"
            # Read last few error lines from log
            job.error_excerpt = self._extract_error_summary(job.log_path)
            print(Colors.error(f"Failed   : {job.label} (Exit Code: {returncode})"))
            if job.error_excerpt:
                print(f"           {Colors.paint('Error:', Colors.RED)} {job.error_excerpt}")
            print(f"           {Colors.paint('Log file:', Colors.DIM)} {job.log_path}")

        return job

    def _extract_error_summary(self, log_path: Path, max_lines: int = 3) -> str:
        """Reads the tail of the log file to grab meaningful error lines."""
        if not log_path.is_file():
            return "Log file not found."
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = [line.strip() for line in f if line.strip()]
            err_lines = [l for l in lines if "ERROR:" in l or "WARNING:" in l or "Exception" in l]
            if err_lines:
                return " | ".join(err_lines[-max_lines:])
            return " | ".join(lines[-max_lines:]) if lines else "No log details available."
        except Exception:
            return "Could not read log."

    def cancel_all(self):
        """Immediately terminates all active child processes and salvages partial videos."""
        with self.lock:
            self.cancelled = True
            procs = list(self.active_processes.keys())

        if procs:
            print(Colors.warn(f"\nStopping {len(procs)} active background download jobs..."))
            for p in procs:
                try:
                    p.terminate()
                except Exception:
                    pass

            # Wait up to 3 seconds for graceful exit, then kill if stubborn
            end_deadline = time.time() + 3.0
            for p in procs:
                remaining = max(0.1, end_deadline - time.time())
                try:
                    p.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    try:
                        p.kill()
                    except Exception:
                        pass

        # Salvage partial downloads so they are immediately playable
        try:
            salvaged = salvage_partial_downloads(self.output_dir)
            if salvaged:
                print(Colors.success(f"[✓] Salvaged {len(salvaged)} interrupted video(s) into playable files:"))
                for s in salvaged:
                    print(Colors.paint(f"    • {s.name}", Colors.GREEN + Colors.BOLD))
        except Exception:
            pass

    def run(self, chunks: List[Tuple[int, int]], is_playlist: bool) -> List[BatchJob]:
        """Runs all batches with worker concurrency and retry management."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        total_batches = len(chunks)
        jobs = [
            BatchJob(idx + 1, total_batches, start, end, is_playlist)
            for idx, (start, end) in enumerate(chunks)
        ]

        # Register signal handlers for clean Ctrl+C shutdown
        prev_sigint = signal.getsignal(signal.SIGINT)
        prev_sigterm = signal.getsignal(signal.SIGTERM)

        def sig_handler(sig, frame):
            self.cancel_all()
            print(Colors.warn("Download cancelled by user."))
            sys.exit(130)

        try:
            signal.signal(signal.SIGINT, sig_handler)
            signal.signal(signal.SIGTERM, sig_handler)
        except (ValueError, AttributeError):
            # Not in main thread or platform restriction
            pass

        print(Colors.paint("\nStarting downloads with " + Colors.highlight(f"{self.workers} parallel workers") + "...\n", Colors.BOLD))

        start_time = time.time()
        completed_jobs: List[BatchJob] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_job = {executor.submit(self.run_single_batch, job): job for job in jobs}
            try:
                for future in concurrent.futures.as_completed(future_to_job):
                    res = future.result()
                    completed_jobs.append(res)
            except KeyboardInterrupt:
                self.cancel_all()
                print(Colors.warn("Interrupted! Terminating processes..."))
                return completed_jobs

        # Automatic retry for failed batches if configured
        failed_jobs = [j for j in completed_jobs if j.status == "FAILED"]
        retry_round = 1
        while failed_jobs and retry_round <= self.max_batch_retries and not self.cancelled:
            print(Colors.warn(f"\nRetrying {len(failed_jobs)} failed batch(es) (Attempt {retry_round}/{self.max_batch_retries})..."))
            time.sleep(2)
            retry_round += 1
            new_completed: List[BatchJob] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_job = {executor.submit(self.run_single_batch, job): job for job in failed_jobs}
                try:
                    for future in concurrent.futures.as_completed(future_to_job):
                        new_completed.append(future.result())
                except KeyboardInterrupt:
                    self.cancel_all()
                    break

            for nj in new_completed:
                for idx, cj in enumerate(completed_jobs):
                    if cj.batch_num == nj.batch_num:
                        completed_jobs[idx] = nj
            failed_jobs = [j for j in completed_jobs if j.status == "FAILED"]

        # Restore original signals
        try:
            signal.signal(signal.SIGINT, prev_sigint)
            signal.signal(signal.SIGTERM, prev_sigterm)
        except (ValueError, AttributeError):
            pass

        total_elapsed = time.time() - start_time
        self._print_summary(completed_jobs, total_elapsed)
        return completed_jobs

    def _print_summary(self, jobs: List[BatchJob], elapsed: float):
        """Prints a comprehensive end-of-run summary report."""
        success_count = sum(1 for j in jobs if j.status == "COMPLETED")
        fail_count = sum(1 for j in jobs if j.status == "FAILED")
        cancelled_count = sum(1 for j in jobs if j.status == "CANCELLED")

        mins, secs = divmod(int(elapsed), 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        print("\n" + "=" * 60)
        print(Colors.paint("  DOWNLOAD SUMMARY REPORT", Colors.BOLD + Colors.CYAN))
        print("=" * 60)
        print(f"  Total Batches   : {len(jobs)}")
        print(f"  Successful      : {Colors.paint(str(success_count), Colors.GREEN)}")
        if fail_count > 0:
            print(f"  Failed          : {Colors.paint(str(fail_count), Colors.RED)}")
        if cancelled_count > 0:
            print(f"  Cancelled       : {Colors.paint(str(cancelled_count), Colors.YELLOW)}")
        print(f"  Time Elapsed    : {time_str}")
        print(f"  Output Folder   : {self.output_dir}")
        if self.archive_path and self.archive_path.is_file():
            print(f"  Archive File    : {self.archive_path}")

        if fail_count > 0:
            print("\n" + Colors.paint("  Failed Batches:", Colors.RED + Colors.BOLD))
            for j in jobs:
                if j.status == "FAILED":
                    print(f"    • {j.label} (Exit Code: {j.exit_code})")
                    if j.log_path:
                        print(f"      Log: {j.log_path}")
            print(Colors.info("\n  Tip: You can re-run the script with the same output directory."))
            print("       Previously downloaded videos will be skipped automatically!")
        print("=" * 60 + "\n")


# ==============================================================================
# Interactive Mode
# ==============================================================================

def run_interactive_wizard(ytdlp_cmd: List[str]) -> argparse.Namespace:
    """Guided wizard when running without CLI arguments."""
    print("=" * 65)
    print(Colors.paint("  YouTube Parallel Playlist Downloader (Interactive Mode)", Colors.BOLD + Colors.CYAN))
    print("=" * 65)

    # 1. URL
    while True:
        url = input(Colors.paint("\n1. Enter YouTube Playlist or Video URL: ", Colors.BOLD)).strip()
        if url:
            break
        print(Colors.warn("URL cannot be empty. Please enter a valid URL."))

    # 2. Output Path
    default_out = str(Path.cwd() / "downloads")
    prompt_out = f"2. Enter Download Folder Path [{Colors.paint(default_out, Colors.DIM)}]: "
    user_out = input(Colors.paint(prompt_out, Colors.BOLD)).strip()
    output_dir = user_out if user_out else default_out

    # 3. Quality Resolution
    print(Colors.paint("\n3. Select Quality / Format:", Colors.BOLD))
    print("   1) 1080p (Full HD) - Recommended")
    print("   2) 4K (2160p)")
    print("   3) 1440p (2K)")
    print("   4) 720p (HD)")
    print("   5) 480p (SD)")
    print("   6) Best Available (Original Quality)")
    print("   7) Audio Only (MP3 / M4A)")
    print("   8) Custom yt-dlp format string")

    choice_quality = input(Colors.paint("   Enter choice (1-8) [1]: ", Colors.BOLD)).strip() or "1"
    quality_map = {
        "1": "1080p",
        "2": "4k",
        "3": "1440p",
        "4": "720p",
        "5": "480p",
        "6": "best",
        "7": "audio",
    }
    audio_only = False
    audio_format = "m4a"
    custom_format = None

    if choice_quality == "7":
        audio_only = True
        print(Colors.paint("\n   Select Audio Format:", Colors.BOLD))
        print("   1) M4A (AAC - fast & high quality) [Default]")
        print("   2) MP3 (Universal)")
        print("   3) OPUS (Best compression)")
        print("   4) FLAC (Lossless)")
        audio_choice = input(Colors.paint("   Enter choice (1-4) [1]: ", Colors.BOLD)).strip() or "1"
        audio_format_map = {"1": "m4a", "2": "mp3", "3": "opus", "4": "flac"}
        audio_format = audio_format_map.get(audio_choice, "m4a")
        quality = "audio"
    elif choice_quality == "8":
        custom_format = input(Colors.paint("   Enter custom yt-dlp format string: ", Colors.BOLD)).strip()
        quality = "best"
    else:
        quality = quality_map.get(choice_quality, "1080p")

    # 4. Concurrency & Chunk Size
    prompt_workers = f"\n4. Number of Parallel Batches [3]: "
    user_workers = input(Colors.paint(prompt_workers, Colors.BOLD)).strip() or "3"
    try:
        workers = max(1, int(user_workers))
    except ValueError:
        workers = 3

    prompt_chunk = f"5. Videos per Batch [20]: "
    user_chunk = input(Colors.paint(prompt_chunk, Colors.BOLD)).strip() or "20"
    try:
        chunk_size = max(1, int(user_chunk))
    except ValueError:
        chunk_size = 20

    # 6. Optional Cookies
    cookies_input = input(Colors.paint("\n6. Cookies file path (optional, press Enter to skip): ", Colors.BOLD)).strip()
    cookies_file = cookies_input if cookies_input else None

    # Summary confirmation
    print("\n" + "-" * 50)
    print(Colors.paint("Configuration Summary:", Colors.BOLD + Colors.CYAN))
    print(f"  URL          : {url}")
    print(f"  Destination  : {output_dir}")
    print(f"  Format       : {'Audio (' + audio_format + ')' if audio_only else (custom_format or quality)}")
    print(f"  Workers      : {workers}")
    print(f"  Batch Size   : {chunk_size}")
    if cookies_file:
        print(f"  Cookies      : {cookies_file}")
    print("-" * 50)

    confirm = input(Colors.paint("\nStart download now? (Y/n): ", Colors.BOLD)).strip().lower()
    if confirm in ("n", "no"):
        print(Colors.warn("Aborted by user."))
        sys.exit(0)

    # Return namespace mock
    return argparse.Namespace(
        url=url,
        output=output_dir,
        quality=quality,
        format=custom_format,
        audio_only=audio_only,
        audio_format=audio_format,
        merge_format="mp4",
        workers=workers,
        chunk_size=chunk_size,
        start=1,
        end=None,
        cookies=cookies_file,
        cookies_from_browser=None,
        concurrent_fragments=8,
        throttled_rate=None,
        retries=10,
        no_archive=False,
        archive_file=None,
        embed_subs=False,
        sub_langs="en.*,all",
        embed_thumbnail=False,
        embed_metadata=True,
        max_batch_retries=1,
        yt_dlp_path=None,
        extra_args=None,
        output_template=None,
        dry_run=False,
        verbose=False,
        no_color=False,
    )


# ==============================================================================
# CLI Argument Parser
# ==============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fast, robust parallel YouTube playlist & video downloader using yt-dlp and ffmpeg.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive Wizard:
    python download_playlist.py

  Quick CLI Download:
    python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./my_playlist

  High Quality 1080p with 4 Parallel Workers:
    python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./videos -q 1080p -w 4 -c 15

  Audio Only (MP3):
    python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./music --audio-only --audio-format mp3

  Download Range (Videos 10 to 50):
    python download_playlist.py "https://youtube.com/playlist?list=PL..." --start 10 --end 50

  Use Browser Cookies:
    python download_playlist.py "https://youtube.com/playlist?list=PL..." --cookies-from-browser chrome
        """,
    )

    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="YouTube playlist or video URL.",
    )
    parser.add_argument(
        "-o", "--output",
        default="./downloads",
        help="Target folder for downloaded files (default: './downloads').",
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["best", "4k", "2160p", "2k", "1440p", "1080p", "720p", "480p", "360p", "audio"],
        default="1080p",
        help="Video resolution preset (default: 1080p).",
    )
    parser.add_argument(
        "-f", "--format",
        default=None,
        help="Custom yt-dlp format selector string (e.g. 'bv*+ba/b'). Overrides --quality.",
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Extract audio only.",
    )
    parser.add_argument(
        "--audio-format",
        choices=["m4a", "mp3", "opus", "flac", "wav"],
        default="m4a",
        help="Audio format when extracting audio (default: 'm4a').",
    )
    parser.add_argument(
        "--merge-format",
        choices=["mp4", "mkv", "webm"],
        default="mp4",
        help="Container format for merged video (default: 'mp4').",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=3,
        help="Number of concurrent chunk download processes (default: 3).",
    )
    parser.add_argument(
        "-c", "--chunk-size",
        type=int,
        default=20,
        help="Number of videos per batch chunk (default: 20).",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Playlist start index (1-based, default: 1).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Playlist end index (optional, default: end of playlist).",
    )
    parser.add_argument(
        "--cookies",
        default=None,
        help="Path to cookies.txt file for restricted/member-only content.",
    )
    parser.add_argument(
        "--cookies-from-browser",
        choices=["chrome", "firefox", "brave", "edge", "opera", "vivaldi", "safari"],
        default=None,
        help="Extract cookies directly from a web browser.",
    )
    parser.add_argument(
        "--concurrent-fragments",
        type=int,
        default=8,
        help="Concurrent fragment downloads per video (default: 8, up to 16 for single videos).",
    )
    parser.add_argument(
        "--throttled-rate",
        default=None,
        help="Minimum download rate before assuming throttling (default: disabled to prevent restart loops).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=10,
        help="Max retries for network / download errors per item (default: 10).",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Disable .yt-dlp-archive.txt tracking (not recommended).",
    )
    parser.add_argument(
        "--archive-file",
        default=None,
        help="Custom path for yt-dlp download archive file.",
    )
    parser.add_argument(
        "--embed-subs",
        action="store_true",
        help="Download and embed subtitles into the video.",
    )
    parser.add_argument(
        "--sub-langs",
        default="en.*,all",
        help="Subtitle languages to download (default: 'en.*,all').",
    )
    parser.add_argument(
        "--embed-thumbnail",
        action="store_true",
        help="Embed video thumbnail into media file.",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Do not embed metadata tags into files.",
    )
    parser.add_argument(
        "--max-batch-retries",
        type=int,
        default=1,
        help="Number of times to retry failed batches at the end of the run (default: 1).",
    )
    parser.add_argument(
        "--output-template",
        default=None,
        help="Custom yt-dlp output naming template.",
    )
    parser.add_argument(
        "--yt-dlp-path",
        default=None,
        help="Explicit path to yt-dlp executable.",
    )
    parser.add_argument(
        "--extra-args",
        nargs=argparse.REMAINDER,
        help="Extra flags to pass directly to yt-dlp (e.g. --extra-args --geo-bypass).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect playlist and display batches without starting downloads.",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch interactive prompt wizard.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose debug logging.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colored output.",
    )

    args = parser.parse_args()
    args.embed_metadata = not args.no_metadata
    return args


# ==============================================================================
# Main Orchestrator
# ==============================================================================

def main():
    # If no arguments provided or explicitly requested, enter interactive wizard
    if len(sys.argv) == 1:
        Colors.init()
        # Find yt-dlp upfront
        try:
            ytdlp_cmd = find_ytdlp()
        except RuntimeError as e:
            print(e)
            sys.exit(1)

        args = run_interactive_wizard(ytdlp_cmd)
    else:
        args = parse_args()
        Colors.init(force_no_color=args.no_color)
        if args.interactive or not args.url:
            try:
                ytdlp_cmd = find_ytdlp(args.yt_dlp_path)
            except (RuntimeError, FileNotFoundError) as e:
                print(e)
                sys.exit(1)
            args = run_interactive_wizard(ytdlp_cmd)
        else:
            try:
                ytdlp_cmd = find_ytdlp(args.yt_dlp_path)
            except (RuntimeError, FileNotFoundError) as e:
                print(e)
                sys.exit(1)

    # Check ffmpeg availability
    if not check_ffmpeg():
        print(Colors.warn("ffmpeg was not detected in PATH."))
        print("    Note: Merging best video + audio streams or extracting MP3 requires ffmpeg.")
        print("    If downloads fail to merge, please install ffmpeg (see README.md).\n")

    # Clean target directory
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Archive file configuration: Default to filesystem duplicate checking unless --archive-file is explicitly set
    if args.archive_file:
        archive_path = Path(args.archive_file).expanduser().resolve()
    else:
        archive_path = None

    # Fetch playlist information
    print(Colors.info(f"Inspecting URL: {Colors.highlight(args.url)} ..."))
    try:
        meta = fetch_playlist_info(
            ytdlp_cmd=ytdlp_cmd,
            url=args.url,
            cookies_file=args.cookies,
            cookies_browser=args.cookies_from_browser,
            extra_args=args.extra_args,
        )
    except Exception as e:
        print(Colors.error(f"Failed to inspect URL: {e}"))
        sys.exit(1)

    print("\n" + "=" * 60)
    print(Colors.paint("  TARGET INFORMATION", Colors.BOLD + Colors.CYAN))
    print("=" * 60)
    print(f"  Title           : {Colors.highlight(meta.title)}")
    if meta.uploader:
        print(f"  Channel/Uploader: {meta.uploader}")
    print(f"  Type            : {'Playlist' if meta.is_playlist else 'Single Video'}")
    print(f"  Total Items     : {Colors.paint(str(meta.total_items), Colors.GREEN + Colors.BOLD)}")
    print(f"  Output Directory: {output_dir}")
    print("=" * 60)

    # Determine chunk batches
    if not meta.is_playlist or meta.total_items <= 1:
        chunks = [(1, 1)]
    else:
        start_idx = max(1, args.start)
        end_idx = min(meta.total_items, args.end) if args.end else meta.total_items

        if start_idx > end_idx:
            print(Colors.error(f"Start index ({start_idx}) cannot be greater than end index ({end_idx})."))
            sys.exit(1)

        chunks = []
        for i in range(start_idx, end_idx + 1, args.chunk_size):
            chunk_end = min(i + args.chunk_size - 1, end_idx)
            chunks.append((i, chunk_end))

    print(Colors.info(f"Generated {len(chunks)} batch chunk(s) (Batch size: {args.chunk_size}, Concurrency: {args.workers})."))

    if args.dry_run:
        print(Colors.warn("\nDry-run mode enabled. Planned batches:"))
        for idx, (s, e) in enumerate(chunks, 1):
            print(f"  Batch {idx:02d}: Items {s} to {e}")
        print("\nExiting without downloading.")
        sys.exit(0)

    # Initialize manager and run
    manager = DownloadManager(
        ytdlp_cmd=ytdlp_cmd,
        url=args.url,
        output_dir=output_dir,
        quality=args.quality,
        custom_format=args.format,
        audio_only=args.audio_only or (args.quality == "audio"),
        audio_format=args.audio_format,
        merge_format=args.merge_format,
        concurrent_fragments=args.concurrent_fragments,
        throttled_rate=args.throttled_rate,
        retries=args.retries,
        cookies_file=args.cookies,
        cookies_browser=args.cookies_from_browser,
        archive_path=archive_path,
        embed_subs=args.embed_subs,
        sub_langs=args.sub_langs,
        embed_thumbnail=args.embed_thumbnail,
        embed_metadata=args.embed_metadata,
        extra_args=args.extra_args,
        output_template=args.output_template,
        workers=args.workers,
        max_batch_retries=args.max_batch_retries,
        verbose=args.verbose,
    )

    results = manager.run(chunks=chunks, is_playlist=meta.is_playlist)
    if any(j.status == "FAILED" for j in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

