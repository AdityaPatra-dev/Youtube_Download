# YouTube Playlist Downloader (PowerShell + yt-dlp)

This project downloads a full YouTube playlist in parallel using `yt-dlp` and `ffmpeg`.

## Files in this folder

- `download_playlist.ps1`: Main PowerShell script.
- `download_playlist_redme.txt`: Raw setup notes.

## Prerequisites

1. Windows PowerShell
2. `ffmpeg`
3. `yt-dlp`

## 1) Install ffmpeg

1. Open: https://www.gyan.dev/ffmpeg/builds/
2. Download the essentials build (for example `ffmpeg-release-essentials.7z`).
3. Extract it (WinRAR/7-Zip).
4. Add ffmpeg to PATH:
   - Open Windows Search and type: Environment Variables
   - Open "Edit the system environment variables"
   - Click Environment Variables
   - Under System variables, select Path, then Edit
   - Click New and add the folder path that contains `ffmpeg.exe`
   - Click OK to save

## 2) Install yt-dlp

1. Open: https://github.com/yt-dlp/yt-dlp/releases
2. Download `yt-dlp.exe`.
3. Put it in a folder you control, for example `C:\yt-dlp\`.
4. Add that folder to PATH (same method as ffmpeg).

If you do not want to add it to PATH, set `$ytDlpPath` in the script to the full path, for example:

```powershell
$ytDlpPath = "C:\yt-dlp\yt-dlp.exe"
```

## 3) Configure the script

Open `download_playlist.ps1` and update these variables:

- `$playlistUrl`: YouTube playlist URL.
- `$outputPath`: Folder where files are saved.

Optional tuning:

- `$chunkSize`: Videos per batch.
- `$parallelJobs`: Number of simultaneous batches.
- `$cookiesFile`: Path to cookies file if needed for restricted/private content.

## 4) Run the downloader

In PowerShell:

```powershell
cd "C:\Users\patra\OneDrive\Desktop\youtube_Download"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\download_playlist.ps1
```

## How the script works

1. Creates the output folder if it does not exist.
2. Uses `yt-dlp --flat-playlist -J` to read playlist metadata.
3. Splits the playlist into chunks.
4. Starts download processes per chunk using `Start-Process`.
5. Applies retry/continue flags to improve resilience.

## Notes and troubleshooting

- If PowerShell says `yt-dlp` is not recognized, either:
  - add yt-dlp folder to PATH, or
  - set `$ytDlpPath` to full executable path.
- If merging fails, ffmpeg is not correctly installed or not in PATH.
- Use a writable output folder, for example `C:\yt-dlp\MyPlaylist`.
- If some videos are skipped, the script uses `--ignore-errors` and continues.
