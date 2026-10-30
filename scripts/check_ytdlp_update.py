#!/usr/bin/env python3
"""
scripts/check_ytdlp_update.py
Checks whether an upstream yt-dlp release (GitHub / PyPI) is newer than the
bundled version tracked in .ytdlp-version.
Outputs variables to $GITHUB_OUTPUT for automated release workflows.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
YTDLP_VERSION_FILE = ROOT_DIR / ".ytdlp-version"
APP_FILE = ROOT_DIR / "app.py"
GRADLE_FILE = ROOT_DIR / "android" / "app" / "build.gradle"


def get_current_tracked_ytdlp() -> str:
    if YTDLP_VERSION_FILE.exists():
        return YTDLP_VERSION_FILE.read_text(encoding="utf-8").strip()
    return ""


def get_current_app_version() -> str:
    """Reads current app version from app.py or build.gradle."""
    if APP_FILE.exists():
        content = APP_FILE.read_text(encoding="utf-8")
        m = re.search(r'current_ver\s*=\s*["\']v?([^"\']+)["\']', content)
        if m:
            return m.group(1).strip()
    if GRADLE_FILE.exists():
        content = GRADLE_FILE.read_text(encoding="utf-8")
        m = re.search(r'versionName\s+["\']([^"\']+)["\']', content)
        if m:
            return m.group(1).strip()
    return "1.4.0"


def calculate_next_patch_version(current_ver: str) -> str:
    """Calculates next semantic patch version (e.g. 1.4.0 -> 1.4.1)."""
    clean = current_ver.lstrip("v").strip()
    parts = clean.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return f"{major}.{minor}.{patch + 1}"
    except Exception:
        return f"{clean}.1"


def fetch_latest_ytdlp_version() -> str:
    """Fetches latest yt-dlp version from GitHub API or PyPI fallback."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"User-Agent": "YouTube-Downloader-CI/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # 1. Try GitHub Releases API
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "").lstrip("v").strip()
            if tag:
                return tag
    except Exception as e:
        print(f"[WARN] GitHub API lookup failed: {e}. Falling back to PyPI...", file=sys.stderr)

    # 2. Fallback to PyPI JSON API
    try:
        req = urllib.request.Request("https://pypi.org/pypi/yt-dlp/json", headers={"User-Agent": "YouTube-Downloader-CI/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            version = data.get("info", {}).get("version", "").strip()
            if version:
                return version
    except Exception as e:
        print(f"[ERROR] PyPI lookup failed: {e}", file=sys.stderr)

    raise RuntimeError("Unable to fetch latest yt-dlp version from GitHub or PyPI")


def main():
    parser = argparse.ArgumentParser(description="Check for upstream yt-dlp updates")
    parser.add_argument("--force", action="store_true", help="Force release trigger even if version has not changed")
    args = parser.parse_args()

    current_ytdlp = get_current_tracked_ytdlp()
    latest_ytdlp = fetch_latest_ytdlp_version()
    current_app_ver = get_current_app_version()
    next_app_ver = calculate_next_patch_version(current_app_ver)

    update_available = args.force or (latest_ytdlp != current_ytdlp)

    print(f"Current tracked yt-dlp version : {current_ytdlp or '(none)'}")
    print(f"Latest upstream yt-dlp version : {latest_ytdlp}")
    print(f"Current app version            : v{current_app_ver}")
    print(f"Next app version               : v{next_app_ver}")
    print(f"Update available               : {update_available} (force={args.force})")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"update_available={'true' if update_available else 'false'}\n")
            f.write(f"latest_ytdlp={latest_ytdlp}\n")
            f.write(f"current_ytdlp={current_ytdlp}\n")
            f.write(f"current_app_version=v{current_app_ver}\n")
            f.write(f"next_app_version=v{next_app_ver}\n")


if __name__ == "__main__":
    main()
