# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Windows Standalone Executable
Bundles desktop_launcher.py, FastAPI, static assets, and Windows binaries (ffmpeg, yt-dlp).
"""
import os
import sys
from pathlib import Path

block_cipher = None
ROOT_DIR = Path(SPECPATH).parent.parent.resolve()

datas = [
    (str(ROOT_DIR / "static"), "static"),
]

# Include packaging/windows/bin if it exists (contains ffmpeg.exe, ffprobe.exe, yt-dlp.exe)
bin_dir = ROOT_DIR / "packaging" / "windows" / "bin"
if bin_dir.exists():
    datas.append((str(bin_dir), "bin"))

# Check for icon
icon_path = ROOT_DIR / "static" / "icon.ico"
icon_file = str(icon_path) if icon_path.exists() else None

hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "pydantic",
    "mutagen",
    "yt_dlp",
    "webview",
]

a = Analysis(
    [str(ROOT_DIR / "desktop_launcher.py")],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YouTubeDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode: suppresses CMD console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YouTubeDownloader",
)

