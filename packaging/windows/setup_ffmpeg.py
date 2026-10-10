#!/usr/bin/env python3
"""
Downloads static Windows binaries (ffmpeg.exe, ffprobe.exe, and yt-dlp.exe)
for bundling into the standalone Windows application.
"""
import os
import sys
import shutil
import urllib.request
import zipfile
from pathlib import Path

TARGET_BIN_DIR = Path(__file__).parent / "bin"
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
YTDLP_EXE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"


def download_file(url: str, dest_path: Path) -> None:
    print(f"[*] Downloading {url} -> {dest_path.name}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out:
        shutil.copyfileobj(resp, out)
    print(f"[✓] Downloaded {dest_path.name} ({dest_path.stat().st_size // (1024*1024)} MB)")


def main():
    TARGET_BIN_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download yt-dlp.exe
    ytdlp_exe = TARGET_BIN_DIR / "yt-dlp.exe"
    if not ytdlp_exe.exists():
        download_file(YTDLP_EXE_URL, ytdlp_exe)
    else:
        print(f"[✓] yt-dlp.exe already present in {TARGET_BIN_DIR}")

    # 2. Download and extract ffmpeg.exe & ffprobe.exe
    ffmpeg_exe = TARGET_BIN_DIR / "ffmpeg.exe"
    ffprobe_exe = TARGET_BIN_DIR / "ffprobe.exe"

    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        print(f"[✓] ffmpeg.exe and ffprobe.exe already present in {TARGET_BIN_DIR}")
        return

    temp_zip = TARGET_BIN_DIR / "ffmpeg.zip"
    download_file(FFMPEG_ZIP_URL, temp_zip)

    print("[*] Extracting ffmpeg.exe and ffprobe.exe...")
    with zipfile.ZipFile(temp_zip, "r") as z:
        for member in z.namelist():
            if member.endswith("bin/ffmpeg.exe"):
                with z.open(member) as src, open(ffmpeg_exe, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                print("[✓] Extracted ffmpeg.exe")
            elif member.endswith("bin/ffprobe.exe"):
                with z.open(member) as src, open(ffprobe_exe, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                print("[✓] Extracted ffprobe.exe")

    # Clean up temporary zip
    if temp_zip.exists():
        temp_zip.unlink()

    print(f"\n[✓] All Windows dependencies ready in {TARGET_BIN_DIR.resolve()}:")
    for f in TARGET_BIN_DIR.iterdir():
        print(f"    - {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

