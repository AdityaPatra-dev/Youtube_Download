#!/usr/bin/env python3
"""
Desktop Window Launcher for YouTube Downloader.
Launches the FastAPI backend and presents a native desktop window (via pywebview),
with fallback to default browser if no GUI toolkit is available.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# Ensure paths and bundled binaries are configured
from path_utils import get_base_dir, get_static_dir, is_frozen, setup_bundled_env

setup_bundled_env()

# Import the FastAPI app
from app import app


def find_available_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """Finds the first available port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start_port


def wait_for_server(url: str, timeout: float = 10.0) -> bool:
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
    """Runs uvicorn server."""
    import uvicorn
    # Suppress verbose access logs in desktop mode
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    parser = argparse.ArgumentParser(description="YouTube Downloader Desktop Application")
    parser.add_argument("--port", type=int, default=None, help="Explicit port to run on")
    parser.add_argument("--no-gui", action="store_true", help="Run without opening a GUI window or browser")
    parser.add_argument("--browser-only", action="store_true", help="Force opening in default web browser instead of native window")
    args = parser.parse_args()

    port = args.port or find_available_port(8000)
    server_url = f"http://127.0.0.1:{port}"

    print(f"[*] Starting YouTube Downloader server on {server_url}...")
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    if not wait_for_server(server_url, timeout=10.0):
        print(f"[!] Warning: Server did not respond within 10 seconds. Attempting to launch UI anyway.")

    if args.no_gui:
        print(f"[✓] Server is running headless at {server_url}. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Exiting...")
            sys.exit(0)

    gui_opened = False

    # Attempt native pywebview window if not explicitly browser-only
    if not args.browser_only:
        try:
            import webview

            icon_path = get_static_dir() / "icon.png"
            window_kwargs = {
                "title": "YouTube Downloader Pro",
                "url": server_url,
                "width": 1180,
                "height": 780,
                "min_size": (800, 600),
                "resizable": True,
            }

            print("[*] Launching native desktop window...")
            webview.create_window(**window_kwargs)
            # webview.start blocks until the window is closed by the user
            webview.start()
            gui_opened = True
            print("[*] Desktop window closed by user. Terminating server...")
            sys.exit(0)
        except ImportError:
            print("[i] pywebview not installed. Falling back to default system browser.")
        except Exception as e:
            print(f"[!] pywebview GUI initialization failed ({e}). Falling back to default system browser.")

    if not gui_opened:
        print(f"[*] Opening {server_url} in your default browser...")
        webbrowser.open(server_url)
        print("[✓] App running. Press Ctrl+C in this terminal to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Exiting...")
            sys.exit(0)


if __name__ == "__main__":
    main()
