#!/bin/bash
set -e

echo "[*] Uninstalling YouTube Downloader Pro..."

rm -rf "${HOME}/.local/share/youtube-downloader"
rm -f "${HOME}/.local/bin/youtube-downloader"
rm -f "${HOME}/.local/share/applications/youtube-downloader.desktop"
rm -f "${HOME}/.local/share/icons/hicolor/256x256/apps/youtube-downloader.png"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
fi

echo "[✓] Uninstalled successfully."

