# 🚀 YouTube Downloader & Playlist Engine

<p align="center">
  <b>A high-performance YouTube playlist and video downloader running locally on your machine with parallel batch downloads, stream format inspection, chapter preservation, and a clean local web interface.</b>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://github.com/yt-dlp/yt-dlp"><img src="https://img.shields.io/badge/yt--dlp-Engine-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="yt-dlp"></a>
  <a href="https://ffmpeg.org/"><img src="https://img.shields.io/badge/FFmpeg-Ready-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg Ready"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node.js-Challenge_Solver-339933?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js Solver"></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License"></a>
</p>

<p align="center">
  <a href="#-quick-start">⚡ Quick Start</a> •
  <a href="#-key-features">🌟 Key Features</a> •
  <a href="#-local-web-interface">🌐 Web Interface</a> •
  <a href="#-cli-downloader">💻 CLI Tool</a> •
  <a href="#-turbo-speed-architecture">🚀 Turbo Speed Guide</a> •
  <a href="PROJECT_DOCUMENTATION.md">📖 Full Technical Docs</a>
</p>

---

## 🌟 Key Features

| 🔍 Stream Format Inspector | 🎬 10 Containers & Encodings | ⚡ Turbo Speed Engine | 🛡️ Mid-Stream File Salvager |
| :---: | :---: | :---: | :---: |
| **Real Manifest Detection**<br/>Queries YouTube's live manifest to detect genuine resolutions (4K, 2K, 1080p, 720p) with true framerates and codecs | **10 Output Formats**<br/>Select from MP4 (H.264 / AV1), MKV, WebM, MOV, or audio formats (MP3 320kbps, M4A, FLAC, Opus, WAV) | **16-Fragment Concurrency**<br/>Splits streams into 16 parallel HTTP connections; uses 10MB chunking and optional `aria2c` socket acceleration | **Zero Data Loss on Cancel**<br/>Stopping mid-stream triggers automatic FFmpeg faststart indexing, repairing `.part` files into playable videos |

| 📑 Chapters & Timestamps | 🚫 Anti-403 Challenge Solver | 🍪 Browser Cookie Auto-Fallback | 🌓 Clean Light & Dark UI |
| :---: | :---: | :---: | :---: |
| **Native Chapter Markers**<br/>Embeds video chapters and timeline bookmarks into MP4/MKV files for easy scrubbing in VLC and media players | **Node.js/Deno Solver**<br/>Executes YouTube EJS challenges locally, preventing `HTTP 403 Forbidden` bot-detection errors | **Browser Session Detection**<br/>Discovers Chrome and Firefox cookies for age-restricted media with automatic fallback if database is locked | **Human-Friendly Design**<br/>Clean, high-contrast user interface with zero external framework dependencies and theme persistence |

| 📺 In-Browser Media Player | 📊 Granular Live Telemetry | 📋 Multi-Job Download Queue | 🛡️ SponsorBlock & Item Picker |
| :---: | :---: | :---: | :---: |
| **HTTP 206 Streaming Modal**<br/>Stream downloaded video and audio files instantly with seekable Range requests, speed controls (`0.75x`–`2.0x`), and direct downloads | **Live Speed & ETA Metrics**<br/>Real-time stdout parsing tracks download bandwidth (`14.5 MiB/s`), ETA (`00:32`), size, and smooth percentage progress | **Sequential Queue Manager**<br/>Enqueue incoming jobs without overloading the system; automatically dispatches next job with one-click queue management | **Clean Videos & Cherry-Picking**<br/>Auto-remove sponsors, intros, and outros via SponsorBlock; select specific playlist items with interactive checkboxes |

---

## ⚡ Quick Start

### 1️⃣ Prerequisites
- **Python 3.9+**
- **FFmpeg** (required for stream remuxing)
- **Node.js** (recommended for YouTube challenge solving)

### 2️⃣ Installation
```bash
# Clone the repository
git clone https://github.com/adityapatra/Youtube_Download.git
cd Youtube_Download

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Launch Web Studio
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

### 🐳 Run with Docker (Zero-Config Container)

Everything (FFmpeg, Node.js solver, Aria2 accelerator, Python) is pre-bundled in the image:

```bash
# Option A: One command with Docker Compose
docker compose up -d

# Option B: Direct Docker CLI (pulls pre-built image from Docker Hub)
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  --name youtube-downloader \
  --restart unless-stopped \
  adityapatra/youtube-downloader:latest
```
Open your browser at `http://localhost:8000`. All downloaded media is saved directly into your local `./downloads` folder.

---

### 🖥️ Desktop Application (Windows & Linux)

You can run the downloader as a standalone desktop application or package it into native binaries:

#### 1. Universal Desktop Launcher
```bash
python desktop_launcher.py
```
* Opens directly in a native desktop window (via `pywebview`) without console windows.
* Automatically finds an open port and cleanly terminates background workers when the window closes.

#### 2. Windows Executable (`.exe`)
* Run the one-click build script:
  ```cmd
  packaging\windows\build_windows.bat
  ```
* Bundles `desktop_launcher.py`, Web UI assets, and static Windows builds of `ffmpeg.exe` and `yt-dlp.exe` into `dist/YouTubeDownloader/`.

#### 3. Linux Portable AppImage
* Run the AppImage packager:
  ```bash
  bash packaging/linux/build_appimage.sh
  ```
* Outputs `dist/YouTube-Downloader-x86_64.AppImage` which runs on Ubuntu, Fedora, Debian, Arch, and Mint.

#### 4. Automated Multi-Platform GitHub Actions
* Pushing a release tag (e.g. `v1.2.0`) or clicking **Run workflow** under GitHub Actions automatically builds both the Windows `.zip` and Linux `.AppImage` and publishes them to **GitHub Releases**.


---

## 🌐 Local Web Interface

The web studio runs on your local network with zero external cloud dependencies:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ▶ YouTube Downloader   Local Engine      [yt-dlp Ready] [FFmpeg Ready]  ☼/☾ │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Download YouTube Video or Playlist                                         │
│  Paste any YouTube URL to scan stream formats and download at turbo speed.  │
│                                                                             │
│  [ https://youtube.com/watch?v=...                      ] [Fetch Details]   │
│                                                                             │
│  ┌─ Stream Detected ─────────────────────────────────────────────────────┐  │
│  │ 🎬 Lecture 01: Recursion Tree & Stack Space  •  Strivers DSA          │  │
│  │ 📦 1 Video  •  ⏱️ 22m 45s  •  📑 6 Chapters / Timestamps Embedded      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Available Resolutions (Auto-Detected from Stream):                         │
│  [ 1080p FHD (MAX) ]   [ 720p HD ]   [ 480p SD ]   [ 360p ]   [ Audio ]     │
│       ~80 MB              ~42 MB        ~24 MB       ~14 MB     ~8.5 MB     │
│                                                                             │
│  Output File Type & Encoding:                                               │
│  [ MP4 (H.264 / AAC) — Universal compatibility (Default)                 ▼ ]│
│                                                                             │
│  Parallel Workers: [ ===●======= ] 3 Workers                                │
│  Batch Size:       [ =====●===== ] 20 Videos / Batch                        │
│                                                                             │
│  [                       ▶ START TURBO DOWNLOAD                          ]  │
│                                                                             │
│  ┌─ Live SSE Output ─────────────────────────────────────────────────────┐  │
│  │ [B#1] [download] 100% of 80.4MiB at 18.2MiB/s ETA 00:00                │  │
│  │ [B#1] Finished successfully (Chapters & Metadata Embedded)            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 🌓 Theme Switcher
Toggle between **Light Mode** and **Dark Mode** at any time using the header toggle button. Themes use high-contrast color palettes and persist via browser `localStorage`.

---

## 💻 CLI Downloader

If you prefer working directly in the terminal, use the standalone Python CLI tool without starting the web server:

### Interactive Mode
```bash
python download_playlist.py
```
Provides an interactive console wizard guiding you through URLs, quality options, workers, and format presets.

### Command Line Examples
```bash
# Standard 1080p playlist download (4 parallel workers, 15 videos/batch)
python download_playlist.py "https://youtube.com/playlist?list=..." -q 1080p -w 4 -c 15

# 4K Ultra HD download
python download_playlist.py "https://youtube.com/playlist?list=..." -q 4k -o ./4k_videos

# Audio extraction to 320kbps MP3
python download_playlist.py "https://youtube.com/playlist?list=..." --audio-only --audio-format mp3 -o ./music

# Download specific video range (videos 10 to 50)
python download_playlist.py "https://youtube.com/playlist?list=..." --start 10 --end 50

# Use Chrome browser cookies for age-restricted / private videos
python download_playlist.py "https://youtube.com/playlist?list=..." --cookies-from-browser chrome

# Dry run (inspect playlist and show planned batches without downloading)
python download_playlist.py "https://youtube.com/playlist?list=..." --dry-run
```

---

## 🚀 Turbo Speed Architecture

The engine incorporates deep performance optimizations:

1. **Zero-Lag Fast Path**: Bypasses redundant metadata scraping when downloading single videos or pre-inspected playlists, starting downloads in **0.01 seconds**.
2. **16-Fragment Concurrency (`--concurrent-fragments=16`)**: Fetches 16 video fragments in parallel per file.
3. **10MB HTTP Chunking (`--http-chunk-size=10M`)**: Requests larger byte ranges to minimize TCP handshake latency.
4. **16MB Memory Ring Buffer (`--buffer-size=16M`)**: Buffers stream data in RAM to prevent disk I/O bottlenecks.
5. **Aria2 Multi-Connection Accelerator**: Automatically utilizes `aria2c` if installed (`-s 16 -x 16 -k 1M -j 16`).
6. **Parallel Multi-Process Playlist Workers**: Distributes playlist downloads across multiple independent processes.
7. **Zero-Transcoding Stream Copy**: Merges DASH video and audio streams using FFmpeg stream copy (`-c copy`) without lossy re-encoding.
8. **Smart Archive Resume (`.yt-dlp-archive.txt`)**: Tracks completed video IDs locally to prevent duplicate downloads.

---

## ⚙️ CLI Options Reference

| Flag | Type | Default | Description |
|---|---|---|---|
| `url` | Positional | `None` | YouTube playlist or video URL. If omitted, starts interactive wizard. |
| `-o`, `--output` | `str` | `./downloads` | Destination folder for downloaded media. |
| `-q`, `--quality` | `choice` | `1080p` | Quality preset: `best`, `4k`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `audio`. |
| `-f`, `--format` | `str` | `None` | Custom format selector (e.g. `bv*+ba/b`). Overrides `-q`. |
| `--audio-only` | Flag | `False` | Extracts audio stream only. |
| `--audio-format` | `choice` | `m4a` | Audio format: `m4a`, `mp3`, `opus`, `flac`, `wav`. |
| `-w`, `--workers` | `int` | `3` | Number of simultaneous parallel download workers. |
| `-c`, `--chunk-size` | `int` | `20` | Number of videos per batch chunk. |
| `--start` | `int` | `1` | 1-based start index in playlist. |
| `--end` | `int` | `End` | 1-based end index in playlist. |
| `--cookies` | `path` | `None` | Path to a `cookies.txt` file. |
| `--cookies-from-browser` | `choice` | `None` | Extract cookies from browser: `chrome`, `firefox`, `brave`, `edge`. |
| `--embed-subs` | Flag | `False` | Embed subtitles into the video container. |
| `--embed-thumbnail` | Flag | `False` | Embed thumbnail artwork into media file. |
| `--merge-format` | `choice` | `mp4` | Container format for merged video: `mp4`, `mkv`, `webm`. |
| `--retries` | `int` | `10` | Max retries per video on network errors. |
| `--no-archive` | Flag | `False` | Disables archive tracking (forces re-downloading existing files). |
| `--dry-run` | Flag | `False` | Displays batch plan without downloading. |

---

## 📂 Project Structure

```text
Youtube_Download/
├── app.py                     # FastAPI web backend, orchestrator, SSE broadcaster
├── download_playlist.py       # Standalone Python CLI downloader
├── requirements.txt           # Dependencies (yt-dlp, fastapi, uvicorn, mutagen)
├── PROJECT_DOCUMENTATION.md   # Complete technical documentation & architecture manual
├── README.md                  # Project overview & quickstart guide
├── static/
│   ├── index.html             # Clean responsive UI layout
│   ├── style.css              # Custom styling, dark/light themes, typography
│   └── app.js                 # Frontend state manager, event listeners, SSE reader
├── downloads/                 # Default destination directory for downloaded media
│   └── .logs/                 # Batch log outputs and diagnostics
├── download_playlist.ps1      # Legacy Windows PowerShell script
└── download_playlist_v2.ps1   # Legacy PowerShell v2 script
```

---

## 💡 Troubleshooting & FAQ

> [!NOTE]
> **Why do videos skip immediately when I re-run the downloader?**  
> By default, the application maintains a `.yt-dlp-archive.txt` file in your download directory to prevent re-downloading files you already have. To re-download, uncheck "Auto-Resume Archive" in the web UI or pass `--no-archive` in the CLI.

> [!TIP]
> **How can I achieve the absolute fastest download speeds?**  
> 1. Install `aria2` (`sudo apt install aria2` on Ubuntu/Debian, `sudo dnf install aria2` on Fedora, or `winget install aria2` on Windows).  
> 2. For playlists, increase parallel workers to 4–6. Single videos already download using 16 concurrent fragments.

> [!IMPORTANT]
> **Encountering "HTTP Error 403: Forbidden"?**  
> Ensure **Node.js** is installed on your system. The downloader automatically runs YouTube's EJS cipher challenges through Node.js to bypass anti-scraping blocks.

---

## 📖 In-Depth Documentation

For detailed information on system architecture, the evolution history, bug resolution logs, and API specifications, consult the complete technical documentation:

👉 **[Read PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
