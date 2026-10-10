#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================================"
echo "  YouTube Downloader - Linux AppImage Build Script"
echo "========================================================"

cd "${ROOT_DIR}"

echo "[*] Compiling binary with PyInstaller..."
pyinstaller --noconfirm "${SCRIPT_DIR}/app.spec"

APPDIR="${ROOT_DIR}/build/AppDir"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

echo "[*] Populating AppDir..."
cp -r "${ROOT_DIR}/dist/youtube-downloader/"* "${APPDIR}/usr/bin/"
cp "${SCRIPT_DIR}/AppRun" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"

cp "${SCRIPT_DIR}/youtube-downloader.desktop" "${APPDIR}/youtube-downloader.desktop"
cp "${SCRIPT_DIR}/youtube-downloader.desktop" "${APPDIR}/usr/share/applications/"

# Generate or copy icon if present
if [ -f "${ROOT_DIR}/static/icon.png" ]; then
    cp "${ROOT_DIR}/static/icon.png" "${APPDIR}/youtube-downloader.png"
    cp "${ROOT_DIR}/static/icon.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/youtube-downloader.png"
fi

# Download appimagetool if not available
APPIMAGETOOL="${ROOT_DIR}/build/appimagetool-x86_64.AppImage"
if [ ! -f "${APPIMAGETOOL}" ]; then
    echo "[*] Downloading appimagetool..."
    wget -q -O "${APPIMAGETOOL}" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "${APPIMAGETOOL}"
fi

echo "[*] Packaging AppImage..."
mkdir -p "${ROOT_DIR}/dist"
OUTPUT_APPIMAGE="${ROOT_DIR}/dist/YouTube-Downloader-x86_64.AppImage"
ARCH=x86_64 "${APPIMAGETOOL}" --appimage-extract-and-run "${APPDIR}" "${OUTPUT_APPIMAGE}"

chmod +x "${OUTPUT_APPIMAGE}"

echo "========================================================"
echo "  [SUCCESS] AppImage successfully generated!"
echo "  Location: ${OUTPUT_APPIMAGE}"
echo "========================================================"

