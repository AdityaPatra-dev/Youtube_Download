<div align="center">

<!-- Header Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=e63946&height=220&section=header&text=YouTube%20Downloader&fontSize=42&fontColor=fff&animation=fadeIn&fontAlignY=38&desc=Parallel%20Playlist%20Downloader%20%E2%80%A2%20Local%20Web%20Interface%20%E2%80%A2%20Light%20%26%20Dark%20Mode&descAlignY=60&descAlign=50" width="100%" alt="YouTube Downloader Banner" />

<!-- Dynamic Animated Typing SVG -->
<a href="#readme">
  <img src="https://readme-typing-svg.demolab.com?font=Inter&size=19&pause=1000&color=E63946&center=true&vCenter=true&width=750&lines=Fast+parallel+playlist+downloads;Clean+local+web+interface+with+Light+%26+Dark+mode;Auto-resume+archive+%E2%80%94+no+duplicate+downloads;Zero-zombie+processes+on+Ctrl%2BC;Choose+4K%2C+1080p%2C+720p%2C+or+Audio-only" alt="Typing SVG" />
</a>

<br/><br/>

<!-- Shields & Badges -->
[![Python Version](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Engine-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Ready-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-475569?style=for-the-badge&logo=linux&logoColor=white)](#prerequisites)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](#license)

<p align="center">
  <b>A clean, human-friendly YouTube playlist and video downloader running on your local machine with parallel batch downloads, automatic resume, and a clean web UI.</b>
</p>

[🌐 Web Interface](#-local-web-interface) • [💻 CLI Downloader](#-python-cli-downloader) • [⚡ Installation Steps](#-installation-steps) • [🌓 Light & Dark Theme](#-light--dark-mode) • [⚙️ CLI Flags](#-cli-options-reference)

</div>

---

## 🌟 Highlights

| ⚡ Parallel Batches | 🔄 Auto-Resume Archive | 🛡️ Clean Process Safety | 🌓 Light & Dark Modes |
| :---: | :---: | :---: | :---: |
| <img src="https://api.iconify.design/fluent-emoji-flat:high-voltage.svg" width="44" height="44" /><br/>Splits large playlists into parallel chunks for **faster downloads** | <img src="https://api.iconify.design/fluent-emoji-flat:counterclockwise-arrows-button.svg" width="44" height="44" /><br/>Logs completed videos to `.yt-dlp-archive.txt` to avoid re-downloading | <img src="https://api.iconify.design/fluent-emoji-flat:shield.svg" width="44" height="44" /><br/>Clean child process termination on `Ctrl+C` — **no background zombies** | <img src="https://api.iconify.design/fluent-emoji-flat:sun-with-face.svg" width="44" height="44" /><br/>Clean, minimal design with instant **Light & Dark mode toggle** |

---

## 🌐 Local Web Interface

Launch the server with one command:

```bash
python app.py
```

Then open **`http://127.0.0.1:8000`** in your browser.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ▶ YouTube Downloader   Local Engine      [yt-dlp Ready] [FFmpeg Ready]  ☼/☾ │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Download YouTube Video or Playlist                                         │
│  Paste any YouTube URL to download with parallel batches and auto-resume.   │
│                                                                             │
│  [ https://youtube.com/playlist?list=PL0c0N7xv8s0...   [Paste] ] [Fetch Info]│
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 🎬 Digital System Design (BEC302)  •  Dr. Vaibhav Jain                │  │
│  │ 📦 52 Videos  •  Type: Playlist  •  Thumbnail Preview Loaded          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Quality & Format:                                                          │
│  [ 1080p Full HD ★ ]  [ 4K ]  [ 1440p ]  [ 720p ]  [ 480p ]  [ Audio Only ]  │
│                                                                             │
│  Parallel Workers: [ ===●======= ] 3 Workers                                │
│  Batch Size:       [ =====●===== ] 20 Videos / Batch                        │
│                                                                             │
│  [                       ▶ START DOWNLOAD                                ]  │
│                                                                             │
│  ┌─ Live Download Output ────────────────────────────────────────────────┐  │
│  │ [Batch #1] Videos 1-20  : [download] 100% of 150.4MiB at 18.2MB/s     │  │
│  │ [Batch #2] Videos 21-40 : [download] 65% of 190.2MiB at 15.1MB/s      │  │
│  │ [Batch #3] Videos 41-52 : RUNNING (3 Workers active)                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 🌓 Light & Dark Mode
- Built-in theme switch button in the header (Sun / Moon icon).
- Remembers your preference via `localStorage` and respects system defaults.
- Clean high-contrast typography in both modes — no distracting fluorescent glows or unnecessary animations.

---

## 🏗️ How It Works

```mermaid
flowchart TD
    classDef client fill:#e63946,stroke:#fff,stroke-width:2px,color:#fff;
    classDef server fill:#2563eb,stroke:#fff,stroke-width:2px,color:#fff;
    classDef worker fill:#059669,stroke:#fff,stroke-width:2px,color:#fff;
    classDef disk fill:#d97706,stroke:#fff,stroke-width:2px,color:#fff;

    UI["🌐 Web UI\n(http://127.0.0.1:8000)"]:::client
    CLI["💻 Python CLI\n(download_playlist.py)"]:::client

    API["⚡ Local Server Engine\n• Metadata Inspector\n• Signal Guardian\n• Live SSE Stream"]:::server

    UI --> API
    CLI --> API

    SUB["yt-dlp Metadata Inspector\nFetches video list & total count"]:::server
    API --> SUB

    GEN["Batch Generator\nChunks: 1-20, 21-40, 41-N"]:::server
    SUB --> GEN

    POOL["Parallel Worker Pool\n(e.g. 3 Workers)"]:::server
    GEN --> POOL

    W1["Worker 1 (Batch 1)\nyt-dlp process"]:::worker
    W2["Worker 2 (Batch 2)\nyt-dlp process"]:::worker
    W3["Worker 3 (Batch 3)\nyt-dlp process"]:::worker

    POOL --> W1
    POOL --> W2
    POOL --> W3

    ARCH[("📑 .yt-dlp-archive.txt\nSkip duplicates")]:::disk
    FFMPEG["🎬 FFmpeg Engine\nMerge Audio/Video"]:::disk
    OUT[("📂 ./downloads\nSaved Media Files")]:::disk

    W1 & W2 & W3 <--> ARCH
    W1 & W2 & W3 --> FFMPEG --> OUT
```

---

## 📦 Installation Steps

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/adityapatra/Youtube_Download.git
cd Youtube_Download
```

### 2️⃣ Install Python Dependencies
```bash
pip install -r requirements.txt
```
> *(Installs `yt-dlp`, `fastapi`, and `uvicorn`)*

### 3️⃣ Ensure FFmpeg is Installed *(Required for merging video & audio)*

<details open>
<summary><b>🪟 Windows</b></summary>

Install via Windows Package Manager:
```powershell
winget install Gyan.FFmpeg
```
*Or download essentials from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add the `bin` folder to your system PATH.*
</details>

<details>
<summary><b>🐧 Linux (Ubuntu / Debian / Fedora / Arch)</b></summary>

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y ffmpeg

# Fedora
sudo dnf install -y ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```
</details>

<details>
<summary><b>🍎 macOS</b></summary>

```bash
brew install ffmpeg
```
</details>

---

## 🚀 How to Run

### 🌐 Option 1: Web Interface *(Recommended)*

Start the local server:
```bash
python app.py
```
Open **`http://127.0.0.1:8000`** in your browser.

---

### 💻 Option 2: Python CLI Downloader

Run interactively with prompts:
```bash
python download_playlist.py
```

Or pass flags directly:

#### 🎯 Standard Download (1080p, 4 parallel workers, 15 videos/batch)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL0c0N7xv8s06alYrdpsYjGXBs1IqIU8QS" -o ./downloads -q 1080p -w 4 -c 15
```

#### 🎬 4K Ultra HD Download
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." -q 4k -o ./4k_videos
```

#### 🎧 Audio-Only (Extract MP3 with metadata)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./music --audio-only --audio-format mp3
```

#### 📑 Download Specific Range (Videos 10 to 50)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." --start 10 --end 50
```

#### 🍪 Use Browser Cookies (for Private / Age-Restricted Playlists)
```bash
# Directly extract session from Chrome, Firefox, Brave, or Edge:
python download_playlist.py "https://youtube.com/playlist?list=PL..." --cookies-from-browser chrome

# Or pass an exported cookies file:
python download_playlist.py "https://youtube.com/playlist?list=PL..." --cookies cookies.txt
```

#### 🔍 Dry Run (Inspect playlist and planned batches without downloading)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." --dry-run
```

---

## 📜 CLI Options Reference

| Flag | Type | Default | Description |
|---|---|---|---|
| `url` | Positional | `None` | YouTube playlist or video URL. If omitted, starts interactive wizard. |
| `-o`, `--output` | `str` | `./downloads` | Destination folder for downloaded files. |
| `-q`, `--quality` | `choice` | `1080p` | Quality preset: `best`, `4k`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `audio`. |
| `-f`, `--format` | `str` | `None` | Custom yt-dlp format selector (e.g. `bv*+ba/b`). Overrides `-q`. |
| `--audio-only` | Flag | `False` | Extracts audio stream only. |
| `--audio-format` | `choice` | `m4a` | Audio container format: `m4a`, `mp3`, `opus`, `flac`, `wav`. |
| `-w`, `--workers` | `int` | `3` | Number of simultaneous parallel download workers. |
| `-c`, `--chunk-size` | `int` | `20` | Number of videos per batch chunk. |
| `--start` | `int` | `1` | 1-based start index in playlist. |
| `--end` | `int` | `End` | 1-based end index in playlist. |
| `--cookies` | `path` | `None` | Path to `cookies.txt` file. |
| `--cookies-from-browser` | `choice` | `None` | Extract cookies from browser: `chrome`, `firefox`, `brave`, `edge`, `opera`. |
| `--embed-subs` | Flag | `False` | Download and embed subtitles into video container. |
| `--embed-thumbnail` | Flag | `False` | Embed thumbnail artwork into media file. |
| `--merge-format` | `choice` | `mp4` | Container format for merged video: `mp4`, `mkv`, `webm`. |
| `--retries` | `int` | `10` | Max retries per video on transient network errors. |
| `--no-archive` | Flag | `False` | Disables `.yt-dlp-archive.txt` tracking. |
| `--dry-run` | Flag | `False` | Fetches metadata and displays batch plan without downloading. |
| `-i`, `--interactive` | Flag | `False` | Forces interactive CLI prompt wizard. |

---

## 📂 Project Structure

```text
Youtube_Download/
├── app.py                     # ⚡ Localhost Web Server & API backend
├── download_playlist.py       # 🚀 Python CLI Downloader & parallel batch engine
├── static/                    # 🎨 Clean Web Assets
│   ├── index.html             #    • Clean Single-Page UI with Light/Dark Mode
│   ├── style.css              #    • Human-friendly styles & color palettes
│   └── app.js                 #    • Client controller, theme toggle & SSE logs
├── download_playlist.ps1      # 📜 Original PowerShell script
├── download_playlist_v2.ps1   # 📜 Interactive PowerShell script
├── requirements.txt           # 📦 Dependencies (yt-dlp, fastapi, uvicorn)
├── .gitignore                 # 🙈 Git ignore rules
└── README.md                  # 📖 Documentation
```

---

## 💡 Troubleshooting & FAQ

> [!NOTE]
> **Why do videos skip immediately when I re-run the downloader?**
> By default, the script creates a `.yt-dlp-archive.txt` file in your download directory. It remembers previously downloaded video IDs so you never waste bandwidth re-downloading videos. To force re-downloading, delete that file or pass `--no-archive`.

> [!TIP]
> **How to get the highest download speed?**
> Increase the workers count with `-w 4` or `-w 6` and adjust chunk size with `-c 15`. You can also tweak `--concurrent-fragments 5` for rapid fragment fetching.

> [!IMPORTANT]
> **Getting "ffmpeg is not recognized" error?**
> Ensure `ffmpeg` is installed and accessible in your system `PATH`. Restart your terminal or command prompt after installing.

---

<div align="center">

<!-- Footer Wave -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=e63946&height=120&section=footer" width="100%" alt="Footer Wave" />

<p><b>Crafted for fast, reliable YouTube playlist downloading.</b></p>
<p>⭐ Star this repository if it helped you!</p>

</div>
