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
    <a href="#-one-click-downloads">📥 Download App</a> •
    <a href="#-quick-run-options">⚡ Quick Run</a> •
    <a href="#-key-features">✨ Features</a> •
    <a href="#-docker-deployment">🐳 Docker</a> •
    <a href="#-technical-deep-dive">📖 Technical Docs</a>
  </p>

</div>

---

## 📥 One-Click Downloads

Pre-compiled, self-contained desktop builds with **embedded FFmpeg and yt-dlp**. Zero setup required!

| Platform | Download | Package Type | Requirements |
| :--- | :---: | :---: | :--- |
| **🪟 Windows 10 / 11** | [**Download .ZIP**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-Windows-x64.zip) | Portable App (117 MB) | Extract & run `YouTubeDownloader.exe` |
| **🐧 Linux (Universal)** | [**Download .AppImage**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-x86_64.AppImage) | Self-Contained (159 MB) | `chmod +x` and double-click |
| **🐧 Linux (No FUSE)** | [**Download .tar.gz**](https://github.com/AdityaPatra-dev/Youtube_Download/releases/latest/download/YouTube-Downloader-Linux-x86_64.tar.gz) | Portable Tarball (157 MB) | Extract & run `youtube-downloader` |

---

## ✨ Key Highlights

<div align="center">

| 🚀 Turbo Concurrency | 🎬 10+ Encodings | 🛡️ Smart Resume |
| :---: | :---: | :---: |
| 16-fragment parallel chunk downloads with optional aria2 acceleration | 4K, 1440p, 1080p, MP4, MKV, MOV, MP3 (320k), FLAC, Opus, WAV | Native filesystem duplicate check; re-downloads deleted files cleanly |

| 🍪 Cookie Auto-Fallback | 📑 Chapter Markers | ✂️ SponsorBlock Clean |
| :---: | :---: | :---: |
| Auto-detects Chrome/Firefox cookies for age-restricted & member videos | Native YouTube chapters and timestamps embedded into containers | Auto-skip intros, sponsors, and outros; download cherry-picked items |

</div>

---

## ⚡ Quick Run Options

### Option 1: Native Desktop Application (Linux)
Install directly into your Linux App Grid / Start Menu:
```bash
git clone https://github.com/AdityaPatra-dev/Youtube_Download.git
cd Youtube_Download
bash packaging/linux/install.sh
```
> 💡 *Launches on isolated port `48480`, leaving port `8000` completely free for your development work.*

---

### Option 2: Docker Container (One-Liner)
Run the complete production stack (Python, FFmpeg, Node.js challenge solver, Aria2) with zero dependencies:

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  --name youtube-downloader \
  adityapatra/youtube-downloader:latest
```
🌐 Open **`http://localhost:8000`** in your browser. All media is saved to `./downloads`.

---

### Option 3: Python Source
```bash
# Clone & install dependencies
git clone https://github.com/AdityaPatra-dev/Youtube_Download.git
cd Youtube_Download
pip install -r requirements.txt

# Run Desktop Window:
python desktop_launcher.py

# Or run Headless Server:
python app.py
```

---

## 💻 CLI Cheat Sheet

Prefer working directly from your terminal? Use [`download_playlist.py`](download_playlist.py):

```bash
# Download 1080p video or playlist (4 parallel workers)
python download_playlist.py "https://youtu.be/..." -q 1080p -w 4

# Extract highest-quality MP3 (320 kbps) with album art
python download_playlist.py "https://youtu.be/..." --audio-only --audio-format mp3

# Download with Chrome browser session cookies
python download_playlist.py "https://youtu.be/..." --cookies-from-browser chrome
```

---

## 📖 Technical Deep Dive

Curious about how the parallel engine works, how YouTube 403 bot challenges are solved, or how cross-platform desktop & mobile packaging was designed?

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
<summary><b>🔍 Click here to preview architecture topics covered in technical docs</b></summary>

- **Stream Format Inspector**: Live YouTube manifest parsing without blind fallback.
- **Node.js EJS Challenge Solver**: Local execution of anti-scraping JavaScript challenges.
- **Mid-Stream Partial Salvager**: In-place reconstruction of interrupted `.part` files via faststart indexing.
- **Port Isolation**: Multi-tier desktop window orchestration with port hunting (`48480`).
- **Filesystem Duplicate Detection**: Precision skipping via `--no-overwrites` without state-drift.

</details>

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
