@echo off
setlocal
echo ========================================================
echo   YouTube Downloader - Windows Build Script
echo ========================================================

echo [*] Installing dependencies and packaging tools...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pywebview pythonnet

echo [*] Downloading bundled FFmpeg, FFprobe, and yt-dlp...
python packaging\windows\setup_ffmpeg.py

echo [*] Compiling standalone Windows executable with PyInstaller...
pyinstaller --noconfirm packaging\windows\app.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] Build finished successfully!
    echo   Executable located at:
    echo   dist\YouTubeDownloader\YouTubeDownloader.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check the logs above.
)
pause

