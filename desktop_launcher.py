#!/usr/bin/env python3
"""
Desktop Window Launcher for YouTube Downloader.
Launches the FastAPI backend and presents a dedicated standalone application window:
1. Native pywebview window (WebKitGTK / Cocoa / WebView2)
2. Dedicated Standalone App Mode window (via Chrome / Chromium / Edge / Brave --app)
3. Fallback to default browser tab
"""
from __future__ import annotations

import argparse
import io
import multiprocessing
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------------------
# 1. Critical PyInstaller / Windows Windowed Mode Initialization
# ------------------------------------------------------------------------------
# In PyInstaller windowed mode (console=False on Windows), sys.stdout and sys.stderr
# are None. Standard library logging and Uvicorn formatters crash with:
# AttributeError: 'NoneType' object has no attribute 'isatty'.
# We redirect to a user-local log file or devnull before any other modules load.
if sys.stdout is None or sys.stderr is None:
    try:
        log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "YouTubeDownloader"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
        _log_stream = open(log_file, "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = _log_stream
        if sys.stderr is None:
            sys.stderr = _log_stream
    except Exception:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Ensure paths and bundled binaries are configured
from path_utils import get_base_dir, get_static_dir, is_frozen, setup_bundled_env

setup_bundled_env()

# Import the FastAPI app
from app import app


def find_available_port(start_port: int = 48480, max_attempts: int = 50) -> int:
    """Finds the first available port starting from start_port (default 48480 to keep 8000 free for dev)."""
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start_port


def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    """Polls the server URL until it responds or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status in (200, 302, 307):
                    return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def run_server(port: int) -> None:
    """Runs uvicorn server with safe logging configuration."""
    try:
        import uvicorn
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            use_colors=False,  # Prevents isatty color inspection crash in windowed apps
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"[!] Server error: {e}", file=sys.stderr)


def launch_standalone_app_window(url: str) -> Optional[subprocess.Popen]:
    """
    Launches a dedicated standalone application window without address bar,
    tabs, or browser navigation controls using Chrome, Chromium, Brave, or Edge in App mode.
    """
    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "brave-browser",
        "microsoft-edge",
        "microsoft-edge-stable",
    ]
    if platform.system() == "Windows":
        candidates.extend([
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "chrome.exe",
            "msedge.exe",
        ])

    profile_dir = Path.home() / ".local" / "share" / "youtube-downloader" / "app-profile"
    if platform.system() == "Windows":
        profile_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "YouTubeDownloader" / "app-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    for c in candidates:
        bin_path = shutil.which(c) or (Path(c).exists() and c)
        if bin_path:
            cmd = [
                str(bin_path),
                f"--app={url}",
                "--window-size=1200,800",
                f"--user-data-dir={profile_dir}",
                "--class=youtube-downloader",
                "--app-id=youtube-downloader",
                "--no-first-run",
                "--no-default-browser-check",
            ]
            try:
                proc = subprocess.Popen(cmd)
                return proc
            except Exception:
                continue
    return None


def main():
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="YouTube Downloader Desktop Application")
    parser.add_argument("--port", type=int, default=None, help="Explicit port to run on")
    parser.add_argument("--no-gui", action="store_true", help="Run without opening a GUI window or browser")
    parser.add_argument("--browser-only", action="store_true", help="Force opening in default web browser instead of native window")
    args = parser.parse_args()

    port = args.port or find_available_port(48480)
    server_url = f"http://127.0.0.1:{port}"

    print(f"[*] Starting YouTube Downloader engine on {server_url}...")
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    if not wait_for_server(server_url, timeout=12.0):
        print(f"[!] Warning: Server did not respond within 12 seconds. Attempting to launch UI anyway.")

    if args.no_gui:
        print(f"[OK] Server is running headless at {server_url}. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Exiting...")
            sys.exit(0)

    gui_opened = False

    # Tier 1: Native pywebview window (true embedded Chromium WebView2 on Windows / WebKitGTK on Linux)
    if not args.browser_only:
        try:
            import webview

            window_kwargs = {
                "title": "YouTube Downloader Pro",
                "url": server_url,
                "width": 1200,
                "height": 800,
                "min_size": (800, 600),
                "resizable": True,
            }

            print("[*] Launching pywebview desktop window...")
            webview.create_window(**window_kwargs)
            webview.start()
            gui_opened = True
            print("[*] Desktop window closed by user. Terminating server...")
            sys.exit(0)
        except Exception as e:
            print(f"[!] pywebview window not available ({e}). Trying standalone app mode...")

    # Tier 2: Dedicated Standalone App Mode Window (Chrome/Edge/Brave without URL bar)
    if not gui_opened and not args.browser_only:
        app_proc = launch_standalone_app_window(server_url)
        if app_proc:
            gui_opened = True
            print("[OK] Native application window launched.")
            start_wait = time.time()
            try:
                app_proc.wait()
            except KeyboardInterrupt:
                pass

            # On Windows, if app_proc exited almost instantly (< 3 seconds),
            # Chrome or Edge handed off the window to an existing background browser instance.
            # DO NOT terminate the server! Keep serving until interrupted or closed.
            if time.time() - start_wait < 3.0:
                print("[*] App window active in browser process. Server running in background...")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass

            print("[*] Application window closed by user. Terminating server...")
            sys.exit(0)

    # Tier 3: Default system browser tab fallback
    if not gui_opened:
        print(f"[*] Opening {server_url} in your default browser...")
        webbrowser.open(server_url)
        print("[OK] App running. Press Ctrl+C in this terminal to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Exiting...")
            sys.exit(0)


if __name__ == "__main__":
    main()
