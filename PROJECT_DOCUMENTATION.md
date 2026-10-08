# 🚀 YouTube Downloader & Playlist Engine — Complete Project Documentation

> **A High-Performance, Privacy-First YouTube Media Downloader & Local Web Studio**  
> *Built with Python (FastAPI), yt-dlp, FFmpeg, and Vanilla HTML5/CSS3/JavaScript.*

---

## 📑 Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Deep Feature Breakdown](#3-deep-feature-breakdown)
   - [Real-Time Stream Inspector & Dynamic Resolutions](#real-time-stream-inspector--dynamic-resolutions)
   - [10 Output Formats & Encoding Containers](#10-output-formats--encoding-containers)
   - [Accurate Size Estimation Engine](#accurate-size-estimation-engine)
   - [Turbo Speed & Multi-Connection Optimization](#turbo-speed--multi-connection-optimization)
   - [Chapters & Timestamps Preservation](#chapters--timestamps-preservation)
   - [Zero-Loss Partial File Salvager](#zero-loss-partial-file-salvager)
   - [Anti-Blocking & YouTube Challenge Resolver](#anti-blocking--youtube-challenge-resolver)
   - [Browser Cookie Extractor with Auto-Fallback](#browser-cookie-extractor-with-auto-fallback)
   - [Server-Sent Events (SSE) Live Terminal](#server-sent-events-sse-live-terminal)
   - [Modern Human-Friendly UI with Dark & Light Mode](#modern-human-friendly-ui-with-dark--light-mode)
4. [Project Evolution & Problem Solving History](#4-project-evolution--problem-solving-history)
   - [Phase 1: Legacy PowerShell to Python Migration](#phase-1-legacy-powershell-to-python-migration)
   - [Phase 2: Full-Stack Web Platform Architecture](#phase-2-full-stack-web-platform-architecture)
   - [Phase 3: The 10% to 9% Throttling Loop Issue](#phase-3-the-10-to-9-throttling-loop-issue)
   - [Phase 4: Dynamic Format Analysis vs Static Guessing](#phase-4-dynamic-format-analysis-vs-static-guessing)
   - [Phase 5: Accurate File Size Estimation](#phase-5-accurate-file-size-estimation)
   - [Phase 6: Chapters & Timestamps Embedding](#phase-6-chapters--timestamps-embedding)
   - [Phase 7: HTTP 403 Forbidden & Node.js Challenge Engine](#phase-7-http-403-forbidden--nodejs-challenge-engine)
   - [Phase 8: Eliminating the 20-Minute Playlist Analysis Lag](#phase-8-eliminating-the-20-minute-playlist-analysis-lag)
   - [Phase 9: Silent Worker Thread Crash Diagnosis](#phase-9-silent-worker-thread-crash-diagnosis)
   - [Phase 10: Real-Time Stream Line Buffering with `--newline`](#phase-10-real-time-stream-line-buffering-with---newline)
5. [API Specification & Endpoints](#5-api-specification--endpoints)
6. [CLI Engine (`download_playlist.py`) Manual](#6-cli-engine-download_playlistpy-manual)
7. [Installation & Setup Guide](#7-installation--setup-guide)
8. [File Structure Overview](#8-file-structure-overview)
9. [Future Roadmap & Potential Improvements](#9-future-roadmap--potential-improvements)

---

## 1. Executive Summary

This project is a local YouTube downloading engine and web dashboard engineered to deliver high speeds, privacy, and media preservation. 

Traditional YouTube downloaders rely on slow cloud services, plaster interfaces with intrusive ads, re-encode video with lossy codecs, or fail on large playlists due to network timeouts. This project solves those problems by running **entirely on your local machine**:
- **Direct YouTube CDN Connections**: Streams are downloaded directly from Google edge nodes straight to your hard drive.
- **Saturating Local Bandwidth**: Uses 16-fragment concurrency per video, multi-worker process pools for playlists, and optional `aria2c` multi-socket TCP acceleration.
- **Format Integrity**: Intelligently inspects streams so users download genuine stream resolutions (from 4K 60fps AV1 down to 360p or lossless FLAC audio) without unwanted transcoding.
- **Resilient**: Features an archive database (`.yt-dlp-archive.txt`) to prevent duplicate downloads and an automated FFmpeg repair pipeline to salvage cancelled downloads into playable videos.

---

## 2. High-Level Architecture

The project consists of two operational interfaces sharing a common execution core:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                                 │
│                                                                        │
│   ┌──────────────────────────────┐    ┌───────────────────────────┐   │
│   │       Web UI (Browser)       │    │     CLI Terminal Tool     │   │
│   │    Vanilla JS + HTML5/CSS    │    │   download_playlist.py    │   │
│   │   http://127.0.0.1:8000      │    │  Interactive or Argparse  │   │
│   └──────────────┬───────────────┘    └─────────────┬─────────────┘   │
└──────────────────┼──────────────────────────────────┼──────────────────┘
                   │ HTTP / SSE Events                │ Direct Execution
┌──────────────────▼──────────────────────────────────▼──────────────────┐
│                         CORE BACKEND (Python)                          │
│                                                                        │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │ FastAPI Asynchronous Web Engine (app.py)                      │    │
│   │ • URL Inspector & Stream Parser                              │    │
│   │ • ThreadPoolExecutor Multi-Batch Orchestrator                 │    │
│   │ • State Machine (active, completed, failed, cancelled)        │    │
│   │ • Server-Sent Events (SSE) Live Log Broadcaster               │    │
│   │ • Partial File Recovery Engine (FFmpeg salvage)               │    │
│   └──────────────────────────────┬────────────────────────────────┘    │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │ Subprocess Execution
┌──────────────────────────────────▼─────────────────────────────────────┐
│                    DOWNSTREAM ENGINES & BINARIES                       │
│                                                                        │
│   ┌────────────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│   │        yt-dlp          │  │     FFmpeg     │  │  Node.js/Deno  │  │
│   │  Core download engine  │  │  Muxing, audio │  │  EJS Challenge │  │
│   │  & fragment fetcher    │  │  & salvage fix │  │  Solver Engine │  │
│   └────────────────────────┘  └────────────────┘  └────────────────┘  │
│   ┌────────────────────────┐  ┌────────────────┐                      │
│   │   aria2c (Optional)    │  │ Browser Cookie │                      │
│   │  16-connection sockets │  │   Databases    │                      │
│   └────────────────────────┘  └────────────────┘                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Deep Feature Breakdown

### Real-Time Stream Inspector & Dynamic Resolutions
Instead of showing generic, static resolution buttons (e.g. assuming every video has 4K or 1080p), the app queries the video's actual stream manifest using `yt-dlp -J --no-playlist`:
- Identifies the maximum resolution available (e.g. 2160p 4K, 1440p 2K, 1080p, 720p, 480p, 360p).
- Displays true framerate (e.g. `60fps` vs `30fps`) and primary video codec (`AV1`, `VP9`, `H.264`).
- Highlights the `[MAX]` quality badge automatically.

### 10 Output Formats & Encoding Containers
Supports specialized video and audio containers tailored for compatibility, compression, and editing workflows:

| Format Code | Container | Video Codec | Audio Codec | Primary Use Case |
|---|---|---|---|---|
| `mp4-h264` | `.mp4` | H.264 (AVC) | AAC / M4A | Universal compatibility (TVs, iPhone, Android, Premiere, DaVinci) |
| `mp4-av1` | `.mp4` | AV1 | AAC / M4A | Next-gen compression: 30% smaller files at identical visual quality |
| `webm` | `.webm` | VP9 | Opus | Native YouTube web stream format; ultra-fast zero-transcode download |
| `mkv` | `.mkv` | Original Stream | Original Stream | Preserves all audio tracks, soft subtitles, and chapter markers |
| `mov` | `.mov` | H.264 | AAC / PCM | Optimized for Apple macOS, QuickTime, and Final Cut Pro |
| `mp3` | `.mp3` | None (Audio) | MP3 (320kbps) | Universal audio for cars, phones, and legacy MP3 players |
| `m4a` | `.m4a` | None (Audio) | AAC | High-efficiency native YouTube audio stream with no quality loss |
| `opus` | `.opus` | None (Audio) | Opus (HQ) | Modern speech and music codec used by YouTube |
| `flac` | `.flac` | None (Audio) | Lossless FLAC | Studio archive quality |
| `wav` | `.wav` | None (Audio) | Uncompressed PCM | Audio engineering and DAW editing |

### Accurate Size Estimation Engine
Calculates download sizes before downloading by inspecting actual stream content length, audio and video bitrates, and video duration:
$$\text{Estimated Size} = \left( \frac{\text{Bitrate}_{\text{video}} + \text{Bitrate}_{\text{audio}}}{8} \right) \times \text{Duration (seconds)}$$
- Accounts for playlist length ($\text{Single Size} \times \text{Total Items}$).
- Dynamically recalculates whenever the user switches between containers (e.g., AV1 vs H.264 vs WebM vs Audio).

### Turbo Speed & Multi-Connection Optimization
1. **16-Fragment Concurrency (`--concurrent-fragments=16`)**: Slices single video downloads into 16 simultaneous requests.
2. **10MB HTTP Chunk Slicing (`--http-chunk-size=10M`)**: Reduces latency by requesting larger byte chunks.
3. **16MB Memory Ring Buffer (`--buffer-size=16M`)**: Minimizes disk write stalls on high-bandwidth connections.
4. **`aria2c` Multi-Socket Accelerator**: Automatically utilized if installed on the host system (`-s 16 -x 16 -k 1M -j 16`).
5. **Multi-Worker Playlist Pool**: Batches playlists across up to 8 parallel OS workers.

### Chapters & Timestamps Preservation
- Automatically extracts chapter markers from YouTube video timelines and descriptions.
- Embeds standard chapter cues into MP4 and MKV containers using FFmpeg metadata syntax (`--embed-chapters --embed-metadata`).
- Chapters are recognized natively by VLC, QuickTime, MPV, and modern smart TVs.

### Zero-Loss Partial File Salvager
If a user cancels a download midway through:
1. The engine detects any orphaned `.part` or `.ytdl` files in the download destination.
2. Invokes FFmpeg stream remuxing (`ffmpeg -i partial.part -c copy -movflags faststart repaired.mp4`).
3. Reconstructs missing container headers so the user can immediately open and play the partially downloaded video.

### Anti-Blocking & YouTube Challenge Resolver
YouTube frequently updates its bot detection mechanisms, triggering `HTTP Error 403: Forbidden`. The application automatically passes:
```bash
--js-runtimes node --remote-components ejs:github
```
This executes YouTube's cipher challenges via the local Node.js or Deno runtime, bypassing anti-scraping blocks.

### Browser Cookie Extractor with Auto-Fallback
- Queries the host OS to discover installed browsers (Chrome, Firefox, Brave, etc.) with active cookie databases.
- Allows downloading private, unlisted, and age-restricted videos.
- **Auto-Fallback Engine**: If a browser's SQLite cookie database is locked by an open browser process, the downloader catches the error and automatically restarts the download without cookies so downloads are not halted.

### Server-Sent Events (SSE) Live Terminal
- Uses FastAPI `StreamingResponse` to push real-time terminal stdout updates directly to the web UI.
- Emits formatted log rows with status badges (`[download]`, `[ExtractAudio]`, `[Merger]`, `[ERROR]`, `[WARNING]`).
- Includes a live terminal viewer with "Copy Logs" and "Clear" controls.

### Modern Human-Friendly UI with Dark & Light Mode
- Responsive, high-contrast user interface with zero external framework dependencies.
- Light and Dark mode toggle button with preference stored in `localStorage`.
- Visual preview cards displaying video thumbnails, chapter counts, channel names, and batch job statuses.

---

## 4. Project Evolution & Problem Solving History

### Phase 1: Legacy PowerShell to Python Migration
- **Original State**: Started with `download_playlist.ps1` and `download_playlist_v2.ps1`.
- **Limitation**: Windows-only, rigid terminal interactions, prone to broken sub-processes when interrupted.
- **Evolution**: Built `download_playlist.py` using standard Python 3 libraries (`argparse`, `concurrent.futures`, `subprocess`, `shutil`) to provide cross-platform compatibility across Windows, Linux, and macOS.

### Phase 2: Full-Stack Web Platform Architecture
- **Need**: Provide an intuitive visual interface for users unfamiliar with terminal arguments.
- **Solution**: Developed `app.py` powered by FastAPI and Uvicorn, serving a single-page interface (`index.html`, `style.css`, `app.js`).

### Phase 3: The 10% to 9% Throttling Loop Issue
- **Symptom**: During single video downloads, progress would reach 10%, jump back to 9%, and repeat.
- **Root Cause**: An aggressive `--throttled-rate=100K` flag was causing `yt-dlp` to drop fragments whenever YouTube's CDN dipped momentarily below the threshold, restarting the fragment download from scratch.
- **Resolution**: Removed the artificial rate floor and enabled 16-fragment concurrency with exponential backoff retries (`--retry-sleep=exp=1:20`), maintaining continuous streams.

### Phase 4: Dynamic Format Analysis vs Static Guessing
- **Symptom**: The UI showed static options for 4K and 1080p, even when downloading older videos that only maxed out at 480p or 720p.
- **Resolution**: Created the `/api/inspect` endpoint that executes a fast JSON extraction (`yt-dlp -J --no-playlist`) to detect true resolutions, framerates, codecs, and durations before presenting choices to the user.

### Phase 5: Accurate File Size Estimation
- **Symptom**: Size estimations showed small values (10–100 MB) for long 2-hour lectures that were actually several gigabytes in size.
- **Resolution**: Replaced static lookup heuristics with stream bitrate calculations multiplied by the exact duration extracted from the media manifest.

### Phase 6: Chapters & Timestamps Embedding
- **Need**: Users requested keeping timestamp markers and chapter navigation for long lectures and multi-part courses.
- **Resolution**: Integrated `--embed-chapters` and `--embed-metadata` into the default command pipeline and added a chapter counter badge to the UI preview card.

### Phase 7: HTTP 403 Forbidden & Node.js Challenge Engine
- **Symptom**: YouTube introduced JavaScript player challenges, causing downloads to fail with `HTTP Error 403: Forbidden`.
- **Resolution**: Implemented automatic Node.js/Deno detection with `--js-runtimes node --remote-components ejs:github` to execute challenges locally.

### Phase 8: Eliminating the 20-Minute Playlist Analysis Lag
- **Symptom**: Clicking "Start Turbo Download" hung for up to 20 minutes before downloading single videos from playlists.
- **Root Cause**: 
  1. URLs containing `&list=` query parameters triggered a full crawl of all 400+ playlist items because `--no-playlist` was omitted.
  2. The download trigger endpoint was executing a redundant second inspection instead of reusing metadata already acquired during inspection.
- **Resolution**:
  - Implemented an instant fast-path in `start_download_job` to skip re-inspection if metadata is already present.
  - Added `--no-playlist` when downloading single video targets. Single video downloads now start in **0.01 seconds**.

### Phase 9: Silent Worker Thread Crash Diagnosis
- **Symptom**: Downloads finished in 0.0s with no downloaded files and no error messages in the UI.
- **Root Cause**: 
  1. A missing `import re` in `app.py` caused a `NameError` inside worker threads.
  2. `concurrent.futures.wait(futures)` swallowed worker thread exceptions silently.
  3. `proc` was referenced in `finally:` blocks before assignment, triggering an `UnboundLocalError`.
- **Resolution**: Added `import re`, initialized `proc = None` and `retry_proc = None` before `try:` blocks, and iterated `as_completed(futures)` with `future.result()` to catch and surface worker exceptions directly to the UI.

### Phase 10: Real-Time Stream Line Buffering with `--newline`
- **Symptom**: The progress bar and terminal log stayed blank while downloading, only updating after chunks finished.
- **Root Cause**: `yt-dlp` emits carriage returns (`\r`) rather than newlines (`\n`) for progress ticks. Without a tty, standard pipe readers buffer output until a newline occurs.
- **Resolution**: Added `--newline` to the `yt-dlp` arguments and added `f_log.flush()` after writing output lines, delivering immediate progress updates over SSE.

---

## 5. API Specification & Endpoints

| Endpoint | Method | Description | Request Body / Query | Response |
|---|---|---|---|---|
| `/` | `GET` | Serves main web application | None | HTML |
| `/api/system` | `GET` | Environment health & detected tools | None | JSON (`ytdlp_version`, `ffmpeg_available`, `detected_browsers`, etc.) |
| `/api/browsers` | `GET` | Lists host browsers with cookie databases | None | JSON (`browsers` array) |
| `/api/inspect` | `POST` | Inspects video/playlist manifest | `{ "url": str, "cookies_browser": Optional[str] }` | JSON (`title`, `resolutions`, `audio_info`, `chapters`, `duration`) |
| `/api/download` | `POST` | Starts parallel background download | JSON (`url`, `quality`, `container`, `workers`, `chunk_size`, `title`, etc.) | JSON (`status: "started"`, `total_batches`) |
| `/api/status` | `GET` | Polls active download state | None | JSON (`active`, `status`, `batches`, `completed_batches`) |
| `/api/cancel` | `POST` | Stops active download & salvages partial files | None | JSON (`status: "ok"`, `salvaged` files) |
| `/api/logs/stream` | `GET` | Server-Sent Events (SSE) log stream | None | `text/event-stream` SSE messages |
| `/api/files` | `GET` | Lists files in download directory | `?folder=./downloads` | JSON array of completed files |

---

## 6. CLI Engine (`download_playlist.py`) Manual

The standalone Python CLI downloader works without the web server:

### Interactive Mode
```bash
python download_playlist.py
```
Launches an interactive console wizard guiding you through URL input, quality presets, parallel worker counts, and batch sizes.

### Direct Command Examples
```bash
# Standard 1080p download with 4 parallel workers and batch size of 15
python download_playlist.py "https://youtube.com/playlist?list=..." -q 1080p -w 4 -c 15

# 4K Ultra HD download
python download_playlist.py "https://youtube.com/playlist?list=..." -q 4k -o ./4k_videos

# Audio extraction to high-quality MP3
python download_playlist.py "https://youtube.com/playlist?list=..." --audio-only --audio-format mp3 -o ./music

# Download subset range (e.g. videos 5 to 25)
python download_playlist.py "https://youtube.com/playlist?list=..." --start 5 --end 25

# Use Google Chrome cookies for private/age-gated media
python download_playlist.py "https://youtube.com/playlist?list=..." --cookies-from-browser chrome

# Dry run: preview planned batches and total count without downloading
python download_playlist.py "https://youtube.com/playlist?list=..." --dry-run
```

---

## 7. Installation & Setup Guide

### 1. Requirements
- Python 3.9+
- `ffmpeg` installed and available in system `PATH`
- `node` or `deno` (recommended for YouTube challenge solving)
- `aria2` (optional, for maximum socket speed)

### 2. Setup
```bash
# Clone repository
git clone https://github.com/adityapatra/Youtube_Download.git
cd Youtube_Download

# Install Python requirements
pip install -r requirements.txt
```

### 3. Launching

#### Option A: Local Python
```bash
# Run Web Application
python app.py

# Run CLI Tool
python download_playlist.py
```

#### Option B: Docker Container (Zero-Config)
All binaries (`ffmpeg`, `nodejs`, `aria2`, `python`) are pre-configured:
```bash
# Via Docker Compose:
docker compose up -d

# Via Docker CLI:
docker build -t youtube-downloader:latest .
docker run -d -p 8000:8000 -v $(pwd)/downloads:/app/downloads --name youtube-downloader youtube-downloader:latest
```

---

## 8. File Structure Overview

```text
Youtube_Download/
├── Dockerfile                 # 🐳 Multi-tool container image definition (ffmpeg, node, aria2)
├── docker-compose.yml         # 🐳 One-command container orchestration definition
├── .dockerignore              # 🙈 Excluded build artifacts and local media
├── app.py                     # ⚡ FastAPI web backend, orchestrator, SSE broadcaster
├── download_playlist.py       # 🚀 Standalone Python CLI downloader
├── requirements.txt           # 📦 Dependencies (yt-dlp, fastapi, uvicorn, mutagen)
├── PROJECT_DOCUMENTATION.md   # 📖 Comprehensive technical manual (this document)
├── README.md                  # 📖 Project overview & quickstart guide
├── static/
│   ├── index.html             #    • Clean responsive UI layout
│   ├── style.css              #    • Custom styling, dark/light themes, typography
│   └── app.js                 #    • Frontend state manager, event listeners, SSE reader
├── downloads/                 # 📂 Default destination directory for downloaded media
│   └── .logs/                 #    • Batch log outputs and diagnostics
├── download_playlist.ps1      # 📜 Legacy Windows PowerShell script
└── download_playlist_v2.ps1   # 📜 Legacy PowerShell v2 script
```

---

## 9. Future Roadmap & Potential Improvements

1. **Granular Single-Video Progress Bar**: Parse exact percentage (`45.2%`), speed (`14.5 MiB/s`), and remaining time (`ETA 00:32`) from streaming output to advance the progress bar continuously for single files.
2. **In-Browser Video & Audio Player**: Add a playback modal to stream downloaded videos directly in the browser with speed controls and chapter selection.
3. **Multi-Job Download Queue**: Allow users to queue multiple URLs to download in sequence automatically.
4. **SponsorBlock Integration**: Optional toggle to remove sponsored segments, intro titles, and end cards (`--sponsorblock-remove sponsor,intro`).
5. **Checkbox Selection for Playlists**: Enable selecting specific individual videos from a playlist manifest instead of strictly contiguous ranges.
6. **Native File Explorer Integration**: Add a "Show in Folder" button to open the containing download directory via system file managers (`nautilus`, `explorer`, `open`).

