#!/usr/bin/env python3
"""
scripts/bump_version.py
Automates version bumping across the entire repository:
  - Updates .ytdlp-version with new yt-dlp release tag
  - Bumps Android versionCode (+1) and versionName in build.gradle
  - Updates AppUpdateManager.java fallback version
  - Updates FastAPI app.py /api/app-update/check current_ver
  - Updates static/index.html & android/app/src/main/assets/web/index.html version labels
  - Updates static/app.js & android/app/src/main/assets/web/app.js fallback strings
  - Updates tests/test_app_api.py assertion
"""

import argparse
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def bump_version(new_version: str, new_ytdlp_version: str = "", dry_run: bool = False):
    clean_version = new_version.lstrip("v").strip()
    v_version = f"v{clean_version}"

    print(f"[*] Target App Version    : {v_version} ({clean_version})")
    if new_ytdlp_version:
        print(f"[*] Target yt-dlp Version : {new_ytdlp_version}")

    changes = []

    # 1. Update .ytdlp-version
    if new_ytdlp_version:
        ytdlp_file = ROOT_DIR / ".ytdlp-version"
        changes.append((ytdlp_file, new_ytdlp_version + "\n"))

    # 2. Update android/app/build.gradle
    gradle_file = ROOT_DIR / "android" / "app" / "build.gradle"
    if gradle_file.exists():
        content = gradle_file.read_text(encoding="utf-8")
        # Bump versionCode
        m_code = re.search(r"versionCode\s+(\d+)", content)
        if m_code:
            old_code = int(m_code.group(1))
            new_code = old_code + 1
            content = re.sub(r"versionCode\s+\d+", f"versionCode {new_code}", content)
        # Update versionName
        content = re.sub(r'versionName\s+["\'][^"\']+["\']', f'versionName "{clean_version}"', content)
        changes.append((gradle_file, content))

    # 3. Update android/app/src/main/java/com/adityapatra/youtubedownloader/AppUpdateManager.java
    mgr_file = ROOT_DIR / "android" / "app" / "src" / "main" / "java" / "com" / "adityapatra" / "youtubedownloader" / "AppUpdateManager.java"
    if mgr_file.exists():
        content = mgr_file.read_text(encoding="utf-8")
        content = re.sub(r'return\s+["\']\d+\.\d+\.\d+["\'];', f'return "{clean_version}";', content)
        changes.append((mgr_file, content))

    # 4. Update app.py
    app_file = ROOT_DIR / "app.py"
    if app_file.exists():
        content = app_file.read_text(encoding="utf-8")
        content = re.sub(r'current_ver\s*=\s*["\']v?[^"\']+["\']', f'current_ver = "{v_version}"', content)
        changes.append((app_file, content))

    # 5. Update index.html (both static/ and android web assets)
    html_files = [
        ROOT_DIR / "static" / "index.html",
        ROOT_DIR / "android" / "app" / "src" / "main" / "assets" / "web" / "index.html",
    ]
    for hf in html_files:
        if hf.exists():
            content = hf.read_text(encoding="utf-8")
            content = re.sub(r'<span id="app-version-label">[^<]+</span>', f'<span id="app-version-label">{v_version}</span>', content)
            content = re.sub(r'<strong id="uptodate-version-tag">[^<]+</strong>', f'<strong id="uptodate-version-tag">{v_version}</strong>', content)
            content = re.sub(r'<span class="v-val" id="modal-curr-ver">[^<]+</span>', f'<span class="v-val" id="modal-curr-ver">{v_version}</span>', content)
            changes.append((hf, content))

    # 6. Update app.js (both static/ and android web assets)
    js_files = [
        ROOT_DIR / "static" / "app.js",
        ROOT_DIR / "android" / "app" / "src" / "main" / "assets" / "web" / "app.js",
    ]
    for jf in js_files:
        if jf.exists():
            content = jf.read_text(encoding="utf-8")
            content = re.sub(
                r'return\s+lbl\s*\?\s*lbl\.textContent\.trim\(\)\s*:\s*["\']v?[^"\']+["\'];',
                f'return lbl ? lbl.textContent.trim() : "{v_version}";',
                content
            )
            changes.append((jf, content))

    # 7. Update tests/test_app_api.py
    test_file = ROOT_DIR / "tests" / "test_app_api.py"
    if test_file.exists():
        content = test_file.read_text(encoding="utf-8")
        content = re.sub(
            r'assert data\["current_version"\]\s*==\s*["\']v?[^"\']+["\']',
            f'assert data["current_version"] == "{v_version}"',
            content
        )
        changes.append((test_file, content))

    print(f"[*] Prepared updates for {len(changes)} files.")
    for path, new_content in changes:
        rel_path = path.relative_to(ROOT_DIR)
        if dry_run:
            print(f"  [DRY-RUN] Would update: {rel_path}")
        else:
            path.write_text(new_content, encoding="utf-8")
            print(f"  [UPDATED] {rel_path}")

    if not dry_run:
        print("[SUCCESS] Version bump complete!")


def main():
    parser = argparse.ArgumentParser(description="Bump app version across codebase")
    parser.add_argument("--version", required=True, help="New app version (e.g. 1.4.1 or v1.4.1)")
    parser.add_argument("--ytdlp", default="", help="New yt-dlp upstream release tag (e.g. 2026.10.26)")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without modifying files")
    args = parser.parse_args()

    bump_version(args.version, args.ytdlp, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
