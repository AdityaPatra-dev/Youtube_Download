# 🚀 YouTube Downloader & Playlist Studio (`adityapatra/youtube-downloader`)

[![Docker Pulls](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/adityapatra/youtube-downloader)
[![Image Size](https://img.shields.io/badge/Size-~270MB_compressed-success?style=for-the-badge)](https://hub.docker.com/r/adityapatra/youtube-downloader)
[![Architecture](https://img.shields.io/badge/Arch-linux%2Famd64-blue?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](https://github.com/adityapatra/Youtube_Download)

A high-speed, local YouTube media downloading platform and web interface packaged with pre-configured multimedia tools. 

---

## ⚡ 10-Second Quickstart

Pull the image and start the container with a single command:

```bash
docker run -d \
  --name youtube-downloader \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  --restart unless-stopped \
  adityapatra/youtube-downloader:latest
```

Open **`http://localhost:8000`** in your browser. All downloaded videos will appear directly inside your local `./downloads` folder.

---

## 🐳 Docker Compose Setup

Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  youtube-downloader:
    image: adityapatra/youtube-downloader:latest
    container_name: youtube-downloader
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/app/downloads
    environment:
      - HOST=0.0.0.0
      - PORT=8000
```

Start the container:
```bash
docker compose up -d
```

Stop the container:
```bash
docker compose down
```

---

## 📦 What's Pre-Installed Inside

The image is based on `python:3.11-slim` and includes the complete system toolchain:

| Tool | Version / Details | Purpose |
|---|---|---|
| **`yt-dlp`** | Latest Release | High-throughput YouTube extraction & multi-fragment streaming |
| **`ffmpeg`** | v7.1+ | Stream remuxing (`-c copy`), chapter embedding, audio extraction & file salvage |
| **`nodejs`** | v20+ LTS | JavaScript EJS challenge solver (prevents YouTube `HTTP 403 Forbidden` bot detection) |
| **`aria2`** | v1.37+ | Multi-connection 16-socket TCP accelerator |
| **`FastAPI` / `Uvicorn`** | v0.100+ / v0.20+ | Responsive web server and Server-Sent Events (SSE) live logger |

---

## 🌟 Key Capabilities

- **🔍 True Stream Format Inspector**: Detects actual available resolutions (4K 60fps AV1 down to 360p) with live file size estimates.
- **🎬 10 Media Encodings**: Select from MP4 (H.264 / AV1), WebM (VP9), MKV, MOV, or audio formats (MP3 320kbps, M4A, FLAC, WAV, Opus).
- **⚡ Turbo Speed Pipeline**: 16-fragment concurrency, 10MB chunking, and memory ring buffer for max throughput.
- **📑 Native Chapter Markers**: Automatically extracts and embeds YouTube video timeline chapters into MP4/MKV containers.
- **🛡️ Mid-Stream File Salvager**: Cancelling a download automatically converts orphaned `.part` files into playable MP4 videos via FFmpeg faststart indexing.
- **🌓 Modern Light & Dark UI**: Clean interface with theme persistence and zero third-party cloud analytics.

---

## ⚙️ Configuration & Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Network interface to bind the web server |
| `PORT` | `8000` | Port for the web interface and API |
| `PYTHONUNBUFFERED` | `1` | Forces real-time unbuffered log streaming |

### Persistent Storage

| Container Path | Host Recommended | Description |
|---|---|---|
| `/app/downloads` | `./downloads` | Directory where downloaded videos, audio, and archives are saved |

---

## 💻 CLI Usage Inside the Container

You can also run the standalone CLI tool inside the running container:

```bash
# Run interactive CLI wizard
docker exec -it youtube-downloader python download_playlist.py

# Download a video directly via CLI
docker exec -it youtube-downloader python download_playlist.py "https://youtube.com/watch?v=..." -q 1080p
```

---

## 🔄 Updating to the Latest Version

```bash
docker pull adityapatra/youtube-downloader:latest
docker stop youtube-downloader
docker rm youtube-downloader
docker run -d \
  --name youtube-downloader \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  --restart unless-stopped \
  adityapatra/youtube-downloader:latest
```

---

## 📄 License & Source

- **GitHub Repository**: [https://github.com/adityapatra/Youtube_Download](https://github.com/adityapatra/Youtube_Download)
- **License**: MIT

