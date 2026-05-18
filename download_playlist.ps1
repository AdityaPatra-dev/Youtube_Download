# ================================

# yt-dlp Parallel Playlist Downloader

# ================================

# ==== CONFIG ====

$playlistUrl = 'https://youtube.com/playlist?list=PL0c0N7xv8s06alYrdpsYjGXBs1IqIU8QS&si=hOQBXo2HtZnhv8QO'
$outputPath = "C:\yt-dlp\MyPlaylist"
$chunkSize = 20          # Videos per batch
$parallelJobs = 3        # Number of simultaneous processes
$ytDlpPath = "yt-dlp"   # Change if yt-dlp.exe is not in PATH
$cookiesFile = ""       # Optional: "C:\path\cookies.txt"

# ==== CREATE FOLDER ====

New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

# ==== GET PLAYLIST SIZE ====

Write-Host "Fetching playlist info..."
$playlistJson = & $ytDlpPath --flat-playlist -J $playlistUrl | ConvertFrom-Json
$totalVideos = $playlistJson.entries.Count

Write-Host "Total videos: $totalVideos"

# ==== CREATE CHUNKS ====

$chunks = @()
for ($i = 1; $i -le $totalVideos; $i += $chunkSize) {
$end = [Math]::Min($i + $chunkSize - 1, $totalVideos)
$chunks += ,@($i, $end)
}

# ==== FUNCTION TO START DOWNLOAD ====

function Start-DownloadJob($start, $end) {
$args = @(
"--playlist-start=$start",
"--playlist-end=$end",
"--concurrent-fragments=8",
"--throttled-rate=100K",
"--retries=infinite",
"--fragment-retries=infinite",
"--file-access-retries=infinite",
"--retry-sleep=2",
"--ignore-errors",
"--continue",
"--no-overwrites",
"--format=bv*+ba/b",
"--merge-output-format=mp4",
"--output=$outputPath%(playlist_index)s - %(title).80s.%(ext)s"
)

if ($cookiesFile -ne "") {
    $args += "--cookies=$cookiesFile"
}

$args += $playlistUrl

Start-Process -FilePath $ytDlpPath -ArgumentList $args

}

# ==== RUN PARALLEL DOWNLOADS ====

Write-Host "Starting parallel downloads..."

$running = @()

foreach ($chunk in $chunks) {
while ($running.Count -ge $parallelJobs) {
Start-Sleep -Seconds 5
$running = Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*yt-dlp*" }
}

Write-Host "Starting batch $($chunk[0]) to $($chunk[1])"
Start-DownloadJob $chunk[0] $chunk[1]

}

Write-Host "All download jobs started!"
