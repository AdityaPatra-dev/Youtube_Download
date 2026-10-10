#!/usr/bin/env python3
"""
Downloads static Linux x86_64 binaries (ffmpeg, ffprobe, and yt-dlp)
for bundling into the standalone Linux AppImage and portable distribution.
"""
import os
import sys
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

TARGET_BIN_DIR = Path(__file__).parent / "bin"
FFMPEG_TAR_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"


def download_file(url: str, dest_path: Path) -> None:
    print(f"[*] Downloading {url} -> {dest_path.name}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out:
        shutil.copyfileobj(resp, out)
    size_mb = dest_path.stat().st_size // (1024 * 1024)
    print(f"[OK] Downloaded {dest_path.name} ({size_mb} MB)")


def main():
    TARGET_BIN_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download standalone yt-dlp binary
    ytdlp_bin = TARGET_BIN_DIR / "yt-dlp"
    if not ytdlp_bin.exists():
        download_file(YTDLP_URL, ytdlp_bin)
        os.chmod(ytdlp_bin, 0o755)
    else:
        print(f"[OK] yt-dlp already present in {TARGET_BIN_DIR}")

    # 2. Download and extract static ffmpeg & ffprobe
    ffmpeg_bin = TARGET_BIN_DIR / "ffmpeg"
    ffprobe_bin = TARGET_BIN_DIR / "ffprobe"

    if ffmpeg_bin.exists() and ffprobe_bin.exists():
        print(f"[OK] ffmpeg and ffprobe already present in {TARGET_BIN_DIR}")
        return

    temp_tar = TARGET_BIN_DIR / "ffmpeg.tar.xz"
    download_file(FFMPEG_TAR_URL, temp_tar)

    print("[*] Extracting static Linux ffmpeg and ffprobe...")
    with tarfile.open(temp_tar, "r:xz") as tar:
        for member in tar.getmembers():
            if member.name.endswith("/bin/ffmpeg") or member.name == "bin/ffmpeg":
                member.name = "ffmpeg"
                tar.extract(member, path=TARGET_BIN_DIR)
                os.chmod(ffmpeg_bin, 0o755)
                print("[OK] Extracted static ffmpeg")
            elif member.name.endswith("/bin/ffprobe") or member.name == "bin/ffprobe":
                member.name = "ffprobe"
                tar.extract(member, path=TARGET_BIN_DIR)
                os.chmod(ffprobe_bin, 0o755)
                print("[OK] Extracted static ffprobe")

    if temp_tar.exists():
        temp_tar.unlink()

    print(f"\n[OK] All Linux bundled dependencies ready in {TARGET_BIN_DIR.resolve()}:")
    for f in TARGET_BIN_DIR.iterdir():
        if f.is_file():
            print(f"    - {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

