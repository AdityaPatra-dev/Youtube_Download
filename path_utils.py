"""
Cross-Platform Path & Environment Utilities for YouTube Downloader.
Handles runtime path resolution for source runs and PyInstaller frozen bundles
on Windows, Linux, and macOS.
"""
from __future__ import annotations

import os
import sys
import platform
from pathlib import Path
from typing import Optional


def is_frozen() -> bool:
    """Returns True if the application is running inside a PyInstaller frozen bundle."""
    return getattr(sys, "frozen", False)


def get_base_dir() -> Path:
    """
    Returns the root directory of the application:
    - In frozen mode: sys._MEIPASS (the extracted bundle directory containing static/ and assets).
    - In normal mode: the directory containing the source files.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
    return Path(__file__).parent.resolve()


def get_executable_dir() -> Path:
    """
    Returns the directory where the binary or script executable resides.
    Useful for persisting local files next to the .exe / executable.
    """
    if is_frozen():
        return Path(sys.executable).parent.resolve()
    return Path(__file__).parent.resolve()


def get_static_dir() -> Path:
    """Returns the path to the static web directory."""
    static_path = get_base_dir() / "static"
    if not static_path.exists():
        # Fallback to current working directory or executable directory
        cwd_static = Path.cwd() / "static"
        if cwd_static.exists():
            return cwd_static
        exe_static = get_executable_dir() / "static"
        if exe_static.exists():
            return exe_static
    return static_path


def get_default_downloads_dir() -> Path:
    """
    Returns the default downloads directory:
    - User's OS native Downloads folder: ~/Downloads/YouTube_Downloads
    - Fallback: ./downloads next to executable/script
    """
    try:
        user_downloads = Path.home() / "Downloads" / "YouTube_Downloads"
        user_downloads.mkdir(parents=True, exist_ok=True)
        return user_downloads
    except Exception:
        fallback = get_executable_dir() / "downloads"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def setup_bundled_env() -> None:
    """
    Prepends bundled binary paths (e.g., bin/ containing ffmpeg.exe, ffprobe.exe)
    to the system PATH so that yt-dlp and ffmpeg are located automatically.
    """
    candidate_bin_dirs = [
        get_base_dir() / "bin",
        get_executable_dir() / "bin",
        get_executable_dir(),
    ]

    current_path = os.environ.get("PATH", "")
    paths_to_add = []

    for bin_dir in candidate_bin_dirs:
        if bin_dir.is_dir() and str(bin_dir) not in current_path:
            paths_to_add.append(str(bin_dir))

    if paths_to_add:
        os.environ["PATH"] = os.pathsep.join(paths_to_add) + os.pathsep + current_path


# Initialize bundled environment paths on module load
setup_bundled_env()
