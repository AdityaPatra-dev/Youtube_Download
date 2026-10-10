<div align="center">

  <img src="static/icon.png" width="120" height="120" alt="YouTube Downloader Logo" style="border-radius: 24px;" />

  # ⚡ YouTube Downloader Pro
  
  <p align="center">
    <a href="https://github.com/AdityaPatra-dev/Youtube_Download">
      <img src="https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=22&pause=1200&color=FF0033&center=true&vCenter=true&width=640&lines=High-Performance+Video+%26+Audio+Downloader;Standalone+Desktop+App+for+Windows+%26+Linux;Zero-Config+Docker+Container;Real+4K+%E2%80%A2+1080p+%E2%80%A2+MP3+%E2%80%A2+FLAC+%E2%80%A2+MOV+Engine" alt="Typing Animation" />
    </a>
  </p>

  <p align="center">
    <a href="https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest"><img src="https://img.shields.io/github/v/release/AdityaPatra-dev/Youtube_Download?color=FF0033&logo=github&style=for-the-badge&label=Desktop+Release" alt="Latest Release"></a>
    <a href="https://hub.docker.com/r/adityapatra/youtube-downloader"><img src="https://img.shields.io/docker/v/adityapatra/youtube-downloader/latest?color=2496ED&logo=docker&style=for-the-badge&label=Docker+Hub" alt="Docker Image"></a>
    <img src="https://img.shields.io/badge/Platform-Windows_%7C_Linux_%7C_Docker-38A169?style=for-the-badge&logo=linux&logoColor=white" alt="Platform Support">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License">
  </p>

  <p align="center">
    <a href="#-one-click-downloads">📥 Downloads</a> •
    <a href="#-features">✨ Features</a> •
    <a href="#-installation-guide">📦 Installation</a> •
    <a href="#-docker-deployment">🐳 Docker</a> •
    <a href="#-cli-usage">💻 CLI</a> •
    <a href="#-technical-deep-dive">📖 Technical Docs</a>
  </p>

</div>

---

## 📥 One-Click Downloads

Pre-compiled, self-contained desktop builds with **embedded FFmpeg and yt-dlp**. Zero setup required!

| Platform | Download Link | Package Type | Size | Setup Required |
| :--- | :---: | :---: | :---: | :--- |
| **🪟 Windows 10 / 11** | [**Download .ZIP**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-Windows-x64.zip) | Portable `.exe` | **117 MB** | Extract & double-click `YouTubeDownloader.exe` |
| **🐧 Linux (Universal)** | [**Download .AppImage**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-x86_64.AppImage) | Portable Executable | **159 MB** | `chmod +x` & double-click to run |
| **🐧 Linux (No FUSE)** | [**Download .tar.gz**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-Linux-x86_64.tar.gz) | Portable Tarball | **157 MB** | Extract & run `./youtube-downloader` |

---

## ✨ Features

### 🚀 High-Performance Speed Engine
* **16-Fragment Concurrency**: Splits video and audio streams into 16 parallel HTTP fragment downloads per item.
* **10MB HTTP Chunking**: Maximizes throughput and minimizes TCP handshake latency.
* **Aria2 Multi-Socket Accelerator**: Automatically uses `aria2c` for high-throughput connections if detected.
* **Instant Start Path**: Bypasses redundant metadata scraping for single videos, initializing downloads in milliseconds.

### 🎬 Comprehensive Video & Audio Formats
* **Resolution Control**: Auto-detects real resolutions from YouTube manifests: `4K (2160p)`, `1440p`, `1080p FHD`, `720p HD`, `480p`, `360p`.
* **Video Containers**: MP4 (H.264 / AV1), MKV, WebM, and Apple MOV (with automatic audio transcoding to ensure QuickTime compatibility).
* **Hi-Res Audio Extraction**: Convert audio directly into MP3 (320kbps), M4A, FLAC (Lossless), Opus, or WAV with embedded metadata.

### 🛡️ Smart Resilience & Reliability
* **Filesystem Duplicate Detection**: Uses physical filesystem checking via `--no-overwrites`. If you delete a video, you can re-download it immediately. If you want a different quality or container, it downloads alongside without blocking!
* **Zero Data Loss Mid-Stream Salvager**: If a download is canceled or interrupted, the system automatically runs FFmpeg faststart indexing to reconstruct and repair `.part` files into playable media.
* **Anti-403 EJS Challenge Solver**: Runs YouTube's anti-bot JavaScript cipher challenges locally via Node.js/Deno to avoid `HTTP 403 Forbidden` errors.
* **Browser Cookie Auto-Fallback**: Discovers active Chrome, Firefox, Brave, and Edge browser sessions or custom `cookies.txt` for age-restricted and private media.

### 🖥️ Native Desktop Experience & Port Isolation
* **Frameless Standalone Window**: Opens as a dedicated application window without browser URL bars, tabs, or bookmarks.
* **Port Isolation (`48480`)**: Runs the desktop engine on port `48480`, leaving developer ports like `8000` and `3000` completely free for your coding projects.
* **Interactive Web Studio**: Built-in HTTP 206 streaming player, live real-time SSE progress telemetry, dark/light theme toggle, and playlist item cherry-picking.

---

## 📦 Installation Guide

### 🪟 Windows Installation

#### Method 1: Portable Executable (Recommended — No Setup Needed)
1. Download [**`YouTube-Downloader-Windows-x64.zip`**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-Windows-x64.zip).
2. Right-click the `.zip` file and select **Extract All...**.
3. Open the extracted folder and double-click **`YouTubeDownloader.exe`**.
> *Everything (FFmpeg, FFprobe, yt-dlp, and Python runtime) is embedded inside. You do not need to install Python, configure PATH, or set up dependencies!*

#### Method 2: Build from Source on Windows
If you want to compile your own `.exe`:
```cmd
git clone https://github.com/AdityaPatra-dev/Youtube_Download.git
cd Youtube_Download
packaging\windows\build_windows.bat
```
The script will install build dependencies, fetch static Windows binaries, compile with PyInstaller, and output `dist\YouTubeDownloader\YouTubeDownloader.exe`.

---

### 🐧 Linux Installation

#### Method 1: Portable AppImage (Universal)
Works across Ubuntu, Fedora, Debian, Arch, and Linux Mint without installation:
```bash
# 1. Make executable
chmod +x YouTube-Downloader-x86_64.AppImage

# 2. Run
./YouTube-Downloader-x86_64.AppImage
```

#### Method 2: Native App Menu Integration (One-Click)
Installs the app directly into your system's Start / App Menu with the official icon and terminal command:
```bash
git clone https://github.com/AdityaPatra-dev/Youtube_Download.git
cd Youtube_Download
bash packaging/linux/install.sh
```
* **To launch:** Press the **Super** (Windows) key and click **YouTube Downloader Pro**, or type `youtube-downloader` in any terminal.
* **To uninstall:** Run `bash packaging/linux/uninstall.sh`.

#### Method 3: Portable Tarball (For minimal distros without FUSE)
```bash
tar -xzf YouTube-Downloader-Linux-x86_64.tar.gz
cd youtube-downloader
./youtube-downloader
```

---

### 🐳 Docker Deployment

Run the complete, containerized production environment (FFmpeg, Node.js solver, Aria2c accelerator pre-configured):

#### Using Docker CLI:
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  --name youtube-downloader \
  --restart unless-stopped \
  adityapatra/youtube-downloader:latest
```

#### Using Docker Compose:
```yaml
services:
  youtube-downloader:
    image: adityapatra/youtube-downloader:latest
    container_name: youtube-downloader
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/app/downloads
    restart: unless-stopped
```
Run `docker compose up -d`. Open **`http://localhost:8000`** in your browser.

---

### 💻 Manual Python Source Run

If you want to run directly with Python:
```bash
# 1. Clone repository
git clone https://github.com/AdityaPatra-dev/Youtube_Download.git
cd Youtube_Download

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch Desktop App (Native Window on port 48480):
python desktop_launcher.py

# Or launch Headless Server (on port 8000):
python app.py
```

---

## 💻 CLI Usage

Use [`download_playlist.py`](download_playlist.py) for terminal downloads:

```bash
# 1. Download 1080p video or playlist (4 parallel workers)
python download_playlist.py "https://youtu.be/..." -q 1080p -w 4

# 2. 4K Ultra HD download
python download_playlist.py "https://youtu.be/..." -q 4k -o ./4k_videos

# 3. Audio extraction to 320kbps MP3
python download_playlist.py "https://youtu.be/..." --audio-only --audio-format mp3 -o ./music

# 4. Download with Chrome browser session cookies (for age-restricted content)
python download_playlist.py "https://youtu.be/..." --cookies-from-browser chrome

# 5. Interactive Wizard Mode (guided walkthrough)
python download_playlist.py
```

---

## 📖 Technical Deep Dive

Curious about how the parallel concurrency engine works, how YouTube 403 bot challenges are solved, or how cross-platform desktop & mobile packaging was designed?

<div align="center">
  <br />
  <a href="PROJECT_DOCUMENTATION.md">
    <img src="https://img.shields.io/badge/📘_EXPLORE_FULL_ARCHITECTURE_DOCS-FF0033?style=for-the-badge&logo=gitbook&logoColor=white" height="42" alt="Explore Technical Architecture" />
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="CROSS_PLATFORM_GUIDE.md">
    <img src="https://img.shields.io/badge/📱_CROSS--PLATFORM_BUILD_GUIDE-2496ED?style=for-the-badge&logo=android&logoColor=white" height="42" alt="Cross-Platform Guide" />
  </a>
  <br /><br />
</div>

<details>
<summary><b>🔍 Preview Architecture Topics in Technical Documentation</b></summary>

- **Stream Format Inspector**: Live YouTube manifest parsing without blind fallback.
- **Node.js EJS Challenge Solver**: Local execution of anti-scraping JavaScript challenges.
- **Mid-Stream Partial Salvager**: In-place reconstruction of interrupted `.part` files via faststart indexing.
- **Port Isolation**: Multi-tier desktop window orchestration with port hunting (`48480`).
- **Filesystem Duplicate Detection**: Precision skipping via `--no-overwrites` without state-drift.
- **MOV Transcoding Fallback**: Audio recoding pipeline preventing QuickTime conversion errors.

</details>

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
