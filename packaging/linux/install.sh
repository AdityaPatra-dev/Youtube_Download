#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================================"
echo "  YouTube Downloader - Linux Desktop Installer"
echo "========================================================"

INSTALL_DIR="${HOME}/.local/share/youtube-downloader"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"

mkdir -p "${BIN_DIR}"
mkdir -p "${DESKTOP_DIR}"
mkdir -p "${ICON_DIR}"

# 1. Check if built binary exists, otherwise build it
if [ ! -d "${ROOT_DIR}/dist/youtube-downloader" ]; then
    echo "[*] Compiled binary not found. Building now..."
    cd "${ROOT_DIR}"
    pyinstaller --noconfirm packaging/linux/app.spec
fi

# 2. Copy application bundle
echo "[*] Installing files to ${INSTALL_DIR}..."
rm -rf "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
cp -r "${ROOT_DIR}/dist/youtube-downloader/"* "${INSTALL_DIR}/"

# 3. Create wrapper script in ~/.local/bin
WRAPPER="${BIN_DIR}/youtube-downloader"
cat << 'EOF' > "${WRAPPER}"
#!/bin/bash
exec "${HOME}/.local/share/youtube-downloader/youtube-downloader" "$@"
EOF
chmod +x "${WRAPPER}"

# 4. Install desktop icon
if [ -f "${ROOT_DIR}/static/icon.png" ]; then
    echo "[*] Installing application icon..."
    cp "${ROOT_DIR}/static/icon.png" "${ICON_DIR}/youtube-downloader.png"
fi

# 5. Install desktop launcher entry
echo "[*] Registering desktop application..."
cat << EOF > "${DESKTOP_DIR}/youtube-downloader.desktop"
[Desktop Entry]
Name=YouTube Downloader Pro
Comment=High-speed parallel YouTube video and playlist downloader
Exec=${WRAPPER}
Icon=youtube-downloader
Terminal=false
Type=Application
Categories=AudioVideo;Video;Network;
StartupWMClass=youtube-downloader
EOF

chmod +x "${DESKTOP_DIR}/youtube-downloader.desktop"

# Refresh desktop database if tool available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
fi

echo "========================================================"
echo "  [SUCCESS] YouTube Downloader installed successfully!"
echo "  You can now launch it by:"
echo "    1. Searching 'YouTube Downloader' in your App Menu"
echo "    2. Running 'youtube-downloader' in any terminal"
echo "========================================================"

