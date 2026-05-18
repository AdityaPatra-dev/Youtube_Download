# ================================
# yt-dlp Parallel Playlist Downloader (Interactive)
# ================================

# ==== USER INPUTS ====
$playlistUrl = Read-Host "Enter YouTube Playlist URL"

$outputPath = Read-Host "Enter Download Folder Path (e.g. C:\yt-dlp\)"
if (!(Test-Path $outputPath)) {
    New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
}

$cookiesFile = Read-Host "Enter Cookies File Path (optional, press Enter to skip)"

Write-Host "`nSelect Resolution:"
Write-Host "1 - 4K (2160p)"
Write-Host "2 - 1440p"
Write-Host "3 - 1080p"
Write-Host "4 - 720p"
Write-Host "5 - 480p"
Write-Host "6 - Audio Only"

$choice = Read-Host "Enter choice (1-6)"

switch ($choice) {
    1 { $format = "bv*[height<=2160]+ba/b" }
    2 { $format = "bv*[height<=1440]+ba/b" }
    3 { $format = "bv*[height<=1080]+ba/b" }
    4 { $format = "bv*[height<=720]+ba/b" }
    5 { $format = "bv*[height<=480]+ba/b" }
    6 { $format = "ba/b"; $audioOnly = $true }
    default { $format = "bv*+ba/b" }
}

# ==== CONFIG ====
$chunkSize = 20
$parallelJobs = 3
$ytDlpPath = "yt-dlp"

$normalizedOutputPath = $outputPath.TrimEnd('\\', '/')
$outputTemplate = Join-Path $normalizedOutputPath '%(playlist_index)03d - %(title).80s.%(ext)s'

# ==== FETCH PLAYLIST ====
Write-Host "`nFetching playlist..."
$playlistArgs = @()
if ($cookiesFile -ne "") {
    $playlistArgs += "--cookies=$cookiesFile"
}

$playlistJson = & $ytDlpPath @playlistArgs --flat-playlist -J $playlistUrl | ConvertFrom-Json
$totalVideos = $playlistJson.entries.Count

Write-Host "Total videos: $totalVideos"

# ==== CREATE CHUNKS ====
$chunks = @()
for ($i = 1; $i -le $totalVideos; $i += $chunkSize) {
    $end = [Math]::Min($i + $chunkSize - 1, $totalVideos)
    $chunks += ,@($i, $end)
}

# ==== DOWNLOAD FUNCTION ====
function Start-DownloadJob($start, $end) {

    $args = @(
        "--playlist-start=$start",
        "--playlist-end=$end",
        "--concurrent-fragments=3",
        "--retries=10",
        "--fragment-retries=10",
        "--continue",
        "--no-overwrites",
        "--ignore-errors",
        "--output=$outputTemplate"
    )

    if ($cookiesFile -ne "") {
        $args += "--cookies=$cookiesFile"
    }

    if ($audioOnly) {
        $args += "--extract-audio"
        $args += "--audio-format=m4a"
    }

    if ($choice -ne 6) {
        $args += "--format=$format"
    }

    $args += $playlistUrl

    Start-Process -PassThru -NoNewWindow -FilePath $ytDlpPath -ArgumentList $args
}

# ==== RUN PARALLEL DOWNLOADS ====
Write-Host "`nStarting parallel downloads..."

$running = @()

foreach ($chunk in $chunks) {

    while ($running.Count -ge $parallelJobs) {
        Start-Sleep -Seconds 5
        $running = $running | Where-Object { $_.HasExited -eq $false }
    }

    Write-Host "Starting batch $($chunk[0]) to $($chunk[1])"

    $p = Start-DownloadJob $chunk[0] $chunk[1]

    $running += $p
}

# ==== WAIT FOR COMPLETION ====
Write-Host "`nWaiting for all downloads to finish..."

$running | ForEach-Object { $_.WaitForExit() }

Write-Host "`nALL DOWNLOADS COMPLETED!"