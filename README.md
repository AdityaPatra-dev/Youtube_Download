# YouTube Playlist Downloader (Python & PowerShell + yt-dlp)

A high-performance, robust downloader for YouTube playlists and individual videos using `yt-dlp` and `ffmpeg`.

Downloads videos in parallel batches for maximum speed, includes automatic resumption (never re-downloads previously completed videos), and provides clean background process management.

---

## Files in this Repository

- **[`download_playlist.py`](file:///home/adityapatra/Documents/GitHub/Youtube_Download/download_playlist.py)**: **(Recommended)** Cross-platform, robust Python script with parallel chunking, interactive wizard, CLI options, download resume archive, and graceful process management.
- **[`download_playlist_v2.ps1`](file:///home/adityapatra/Documents/GitHub/Youtube_Download/download_playlist_v2.ps1)**: Interactive PowerShell script (Windows).
- **[`download_playlist.ps1`](file:///home/adityapatra/Documents/GitHub/Youtube_Download/download_playlist.ps1)**: Original PowerShell script with hardcoded configuration.
- **[`requirements.txt`](file:///home/adityapatra/Documents/GitHub/Youtube_Download/requirements.txt)**: Python dependencies (`yt-dlp`).

---

## Key Features (Python Version)

- ⚡ **Parallel Chunk Downloading**: Splits long playlists into batches (e.g. 20 videos) and runs concurrent workers (e.g. 3 workers) for optimal network saturation.
- 🔄 **Smart Resumption & Archive**: Uses a local `.yt-dlp-archive.txt` file so interrupted downloads or re-runs instantly skip already-downloaded videos.
- 🛡️ **Clean Process Management**: Cleanly intercepts `Ctrl+C` / interruptions and terminates all child worker processes, preventing orphaned background processes.
- 🎮 **Dual Modes**: Run interactively (guided wizard with prompts and defaults) or via full Command Line Interface (CLI) for scripts and automations.
- 📊 **Per-Batch Logging**: Keeps logs in `.logs/` and outputs detailed error excerpts if any batch fails.
- 🔁 **Automatic Retry**: Automatically retries failed batches at the end of the run.
- 🌐 **Cross-Platform**: Works out of the box on Windows, Linux, and macOS without modifying paths.
- 🎵 **Format & Audio Extraction**: Supports Best, 4K, 1440p, 1080p, 720p, 480p, or Audio-Only (MP3, M4A, OPUS, FLAC).
- 🍪 **Cookie Support**: Supports `--cookies <file>` and `--cookies-from-browser <browser>` for age-gated or member-only playlists.

---

## Prerequisites

1. **Python 3.7+** (Works on Windows, Linux, macOS)
2. **`yt-dlp`**:
   ```bash
   pip install -r requirements.txt
   # Or standalone binary from: https://github.com/yt-dlp/yt-dlp/releases
   ```
3. **`ffmpeg`** (Required for merging video+audio and audio conversion):
   - **Windows**: `winget install Gyan.FFmpeg` or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to PATH.
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **Fedora**: `sudo dnf install ffmpeg`
   - **macOS**: `brew install ffmpeg`

---

## Python Script Usage

### 1. Interactive Wizard (Easiest)

Simply run the script with no arguments. It will guide you through entering the playlist URL, quality, worker count, and destination folder:

```bash
python download_playlist.py
```

### 2. Command Line (CLI) Examples

#### Basic Download (1080p Default)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./my_playlist
```

#### High-Speed Download (4 Parallel Workers, 15 Videos/Batch, 1080p)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./videos -q 1080p -w 4 -c 15
```

#### 4K Resolution
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." -q 4k -o ./4k_videos
```

#### Audio-Only (MP3 Format)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." -o ./music --audio-only --audio-format mp3
```

#### Download a Specific Range (e.g. Videos 10 to 50)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." --start 10 --end 50
```

#### Embed Subtitles and Thumbnails
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." --embed-subs --embed-thumbnail
```

#### Using Browser Cookies (for Private / Age-restricted Playlists)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." --cookies-from-browser chrome
```

#### Dry Run (Preview playlist info and chunks without downloading)
```bash
python download_playlist.py "https://youtube.com/playlist?list=PL..." --dry-run
```

---

## CLI Options Reference

| Flag | Description | Default |
|---|---|---|
| `url` | Playlist or video URL | Interactive prompt |
| `-o`, `--output` | Destination directory | `./downloads` |
| `-q`, `--quality` | Resolution preset (`best`, `4k`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `audio`) | `1080p` |
| `-f`, `--format` | Custom yt-dlp format selector (overrides `-q`) | `None` |
| `--audio-only` | Extract audio only | `False` |
| `--audio-format` | Audio container (`m4a`, `mp3`, `opus`, `flac`, `wav`) | `m4a` |
| `-w`, `--workers` | Number of simultaneous download batch jobs | `3` |
| `-c`, `--chunk-size` | Number of videos per batch | `20` |
| `--start` | 1-based start index | `1` |
| `--end` | 1-based end index | End of playlist |
| `--cookies` | Path to `cookies.txt` | `None` |
| `--cookies-from-browser` | Extract cookies from browser (`chrome`, `firefox`, `brave`, `edge`, etc.) | `None` |
| `--embed-subs` | Download and embed subtitles | `False` |
| `--embed-thumbnail` | Embed video thumbnail | `False` |
| `--merge-format` | Output container format (`mp4`, `mkv`, `webm`) | `mp4` |
| `--retries` | Retries on network errors | `10` |
| `--no-archive` | Disable download archive tracking | `False` |
| `--dry-run` | Inspect playlist structure without downloading | `False` |
| `-i`, `--interactive` | Force interactive mode | `False` |
| `-h`, `--help` | Show full help menu | |

---

## PowerShell Scripts (Legacy)

If you prefer running via Windows PowerShell:

1. Open PowerShell:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```
2. Interactive version:
   ```powershell
   .\download_playlist_v2.ps1
   ```
3. Static version:
   Configure `$playlistUrl` and `$outputPath` in `download_playlist.ps1` and run:
   ```powershell
   .\download_playlist.ps1
   ```
