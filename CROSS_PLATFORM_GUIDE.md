# Cross-Platform Build & Packaging Guide: Windows, Linux & Android

This guide explains how to package and distribute the **YouTube Downloader** project across **Windows (.exe)**, **Linux (AppImage / .deb)**, and **Android (.apk)**, along with architectural recommendations on repository structure.

---

## Table of Contents
1. [Architectural Overview: Shared vs Platform Code](#architectural-overview)
2. [Single Repository (Monorepo) vs Separate Repositories](#monorepo-vs-separate-repositories)
3. [Building for Windows (.exe)](#1-building-for-windows-exe)
   - [Desktop App via PyWebView & PyInstaller](#approach-a-standalone-window-app-pywebview--pyinstaller)
   - [Bundling FFmpeg for Windows](#bundling-ffmpegexe)
   - [Windows Spec File & Build Command](#windows-build-steps)
4. [Building for Linux (AppImage / .deb)](#2-building-for-linux)
   - [Standalone Portable AppImage](#approach-a-portable-appimage)
   - [Desktop Entry (.desktop) & Native Service](#approach-b-native-desktop-integration)
5. [Building for Android (.apk)](#3-building-for-android-apk)
   - [Approach A: Web Wrapper / Capacitor with Embedded Engine](#approach-a-capacitor--webview-apk)
   - [Approach B: Native Android App (Flutter + yt-dlp + FFmpeg-Kit)](#approach-b-native-app-flutter--yt-dlp--ffmpeg-kit)
   - [Android Permissions & Storage Guidelines](#android-permissions--storage)
6. [Decision Matrix & Comparison Table](#summary-decision-matrix)

---

## Architectural Overview

The core application consists of two main layers:
1. **Backend Engine**: Python (`FastAPI`/`Uvicorn`, `yt-dlp`, `ffmpeg`, asynchronous process orchestration).
2. **Frontend UI**: Lightweight web interface (`HTML5`, `Vanilla CSS`, `Vanilla JS`, Server-Sent Events).

```
┌────────────────────────────────────────────────────────┐
│                      Client Layer                      │
│   Windows Desktop (Webview) │ Linux Browser/AppImage   │
│   Android Mobile UI (Native / Webview Shell)           │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Orchestrator                        │
│          FastAPI Server / Local Python Engine          │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
       ┌──────▼──────┐             ┌──────▼──────┐
       │   yt-dlp    │             │   FFmpeg    │
       │ (Extractor) │             │  (Mux/Conv) │
       └─────────────┘             └─────────────┘
```

---

## Monorepo vs Separate Repositories

### The Big Question: Should all platforms be in one repository or split?

| Target Platform | Recommendation | Reason |
| :--- | :--- | :--- |
| **Windows & Linux** | **Keep in the SAME repository** (`Youtube_Download`) | Windows and Linux run the exact same Python codebase, API routes, and HTML/CSS/JS frontend. 98% of the code is identical. Only packaging scripts differ. |
| **Android (Web Wrapper / Capacitor)** | **SAME repository** (`android/` subfolder) | If Android wraps the existing HTML/CSS/JS frontend, keeping it in the same repository avoids copying UI assets back and forth. |
| **Android (Native Kotlin / Flutter)** | **SEPARATE repository** (`Youtube_Download-Android`) | Native Android requires Gradle, Java/Kotlin or Dart, Android SDK/NDK, Android-specific permissions, and mobile UI paradigms. Combining it with a Python backend repo adds clutter and bloats CI/CD pipelines. |

### Recommended Structure for this Repository (Monorepo):
```
Youtube_Download/
├── app.py                      # Core FastAPI server
├── download_playlist.py        # Core CLI orchestrator
├── static/                     # Shared Web UI (HTML/CSS/JS)
├── Dockerfile                  # Docker container definition
├── packaging/
│   ├── windows/
│   │   ├── build_exe.py        # PyInstaller build script
│   │   ├── app.spec            # PyInstaller specification file
│   │   └── get_ffmpeg.ps1      # Helper to download Windows ffmpeg.exe
│   ├── linux/
│   │   ├── AppRun              # Entrypoint for AppImage
│   │   └── youtube-dl.desktop  # Desktop launcher entry
│   └── android/                # (Optional if using Capacitor wrapper)
└── README.md
```

---

## 1. Building for Windows (.exe)

On Windows, the goal is to produce a single double-clickable `.exe` file that starts the server, bundles `ffmpeg.exe`, and opens a native desktop window without showing an ugly command-prompt black box.

### Approach: Standalone Window App (PyWebView + PyInstaller)

#### Step 1: Install Build Dependencies
```bash
pip install pyinstaller pywebview
```

#### Step 2: Create a Desktop Launcher (`launcher.py`)
This script launches the FastAPI server in a background thread and opens a native Windows GUI window pointing to `http://127.0.0.1:8000`:

```python
# packaging/windows/launcher.py
import threading
import uvicorn
import webview
import sys
import os

# Handle PyInstaller temporary unpacked directory
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # Add bundled ffmpeg to PATH
    os.environ["PATH"] = os.path.join(BASE_DIR, "bin") + os.pathsep + os.environ["PATH"]
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from app import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    
    # Open native desktop window
    webview.create_window(
        title="YouTube Downloader Pro",
        url="http://127.0.0.1:8000",
        width=1100,
        height=750,
        resizable=True
    )
    webview.start()
```

#### Step 3: Bundling `ffmpeg.exe`
1. Download standard static Windows builds of `ffmpeg.exe` and `ffprobe.exe` from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
2. Place them into a `bin/` directory:
   ```
   packaging/windows/bin/ffmpeg.exe
   packaging/windows/bin/ffprobe.exe
   ```

#### Step 4: PyInstaller Build Command
Run the build command on a Windows machine:
```bash
pyinstaller --noconfirm --onedir --windowed \
  --add-data "static;static" \
  --add-data "packaging/windows/bin;bin" \
  --name "YouTubeDownloader" \
  --icon "static/icon.ico" \
  packaging/windows/launcher.py
```
This produces a `dist/YouTubeDownloader/` folder containing `YouTubeDownloader.exe` and all dependencies. You can distribute this folder directly as a `.zip` or package it with **Inno Setup** into a standard installer.

---

## 2. Building for Linux

Linux users can run the Python script or Docker container natively, but for desktop users who want a graphical app without installing Python or dependencies, an **AppImage** is the best solution.

### Approach A: Portable AppImage
An AppImage runs across Ubuntu, Fedora, Debian, Arch, and Linux Mint without installation.

#### Step 1: Build a Linux Binary with PyInstaller
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir \
  --add-data "static:static" \
  --name "youtube-downloader" \
  app.py
```

#### Step 2: Assemble AppDir Directory
```bash
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

# Copy compiled binary files
cp -r dist/youtube-downloader/* AppDir/usr/bin/

# Copy desktop file and icon
cp packaging/linux/youtube-downloader.desktop AppDir/
cp packaging/linux/youtube-downloader.desktop AppDir/usr/share/applications/
cp static/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/youtube-downloader.png
cp static/icon.png AppDir/youtube-downloader.png
```

#### Step 3: Create AppRun Script (`AppDir/AppRun`)
```bash
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
# Launch browser on startup
xdg-open "http://127.0.0.1:8000" &
exec "${HERE}/usr/bin/youtube-downloader"
```
```bash
chmod +x AppDir/AppRun
```

#### Step 4: Package with `appimagetool`
```bash
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
./appimagetool-x86_64.AppImage AppDir YouTube-Downloader-x86_64.AppImage
```

---

## 3. Building for Android (.apk)

Building a YouTube downloader on Android requires special handling because Android does not allow running arbitrary background CLI binaries the way a desktop OS does.

### Approach A: Capacitor / WebView APK (Recommended if keeping same UI)
If you want to keep the exact same HTML/CSS/JS frontend:
1. Wrap the static files using **Capacitor** (`@capacitor/core` + `@capacitor/android`).
2. Point the API requests to:
   - Either your local home server / Docker container.
   - Or an embedded lightweight Python engine inside the APK using **Chaquopy** (Python SDK for Android).
3. **Chaquopy** runs Python 3.11 inside the Android app process, enabling direct calls to `yt_dlp` without needing an external server.

### Approach B: Native Android App (Flutter + yt-dlp + FFmpeg-Kit)
If you want the best performance and background downloading support (like the open-source **Seal** app):
1. **UI**: Built with Flutter or Kotlin/Jetpack Compose.
2. **Download Engine**: Runs `yt-dlp` using Python embedded via Chaquopy or JNI bindings.
3. **FFmpeg**: Uses **FFmpeg-Kit for Android** (`com.arthenica:ffmpeg-kit-full`).
4. **Storage**: Writes downloads to `Environment.DIRECTORY_DOWNLOADS` or `Environment.DIRECTORY_MOVIES` using Android's **MediaStore API**.

### Android Permissions & Storage (`AndroidManifest.xml`)
To prevent Android from killing downloads when the screen turns off, declare the following:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- Internet access -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <!-- Storage permissions for saving media -->
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
                     android:maxSdkVersion="28" />
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />

    <!-- Background download services -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
</manifest>
```

> [!WARNING]
> **Google Play Store Policy**:
> Google strictly forbids YouTube downloading apps on the Google Play Store under section 4.4 of the Developer Distribution Agreement. Android builds must be distributed as an `.apk` on **GitHub Releases**, **F-Droid**, or your own website.

---

## Summary Decision Matrix

| Dimension | Windows (.exe) | Linux (AppImage) | Android (.apk) |
| :--- | :--- | :--- | :--- |
| **Codebase Location** | Same repository | Same repository | Separate repo (if native Flutter/Kotlin) or same repo (if Web wrapper) |
| **UI Technology** | Existing Web UI (PyWebView) | Existing Web UI (Browser/Webview) | Flutter / Jetpack Compose or Capacitor |
| **Download Engine** | Python + `yt-dlp` | Python + `yt-dlp` | Python via Chaquopy or mobile wrapper |
| **Media Merger** | Bundled `ffmpeg.exe` | System or bundled `ffmpeg` | `ffmpeg-kit-android` |
| **Distribution** | Direct `.exe` / Inno Setup | `.AppImage` / `.deb` | Direct `.apk` via GitHub Releases |
| **Development Effort** | Low (1–2 days) | Low (1 day) | Medium to High (1–2 weeks) |

