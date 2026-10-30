"""
Unit tests for the automated yt-dlp release and version bumping scripts.
"""

from pathlib import Path
from scripts.check_ytdlp_update import (
    calculate_next_patch_version,
    get_current_tracked_ytdlp,
    get_current_app_version,
)
from scripts.bump_version import bump_version


def test_calculate_next_patch_version():
    assert calculate_next_patch_version("1.4.0") == "1.4.1"
    assert calculate_next_patch_version("v1.4.0") == "1.4.1"
    assert calculate_next_patch_version("1.4.9") == "1.4.10"
    assert calculate_next_patch_version("2.0.0") == "2.0.1"
    assert calculate_next_patch_version("v2.1.3") == "2.1.4"


def test_get_current_tracked_ytdlp():
    tracked = get_current_tracked_ytdlp()
    assert isinstance(tracked, str)
    assert len(tracked) > 0
    # Expected format like 2026.10.26
    parts = tracked.split(".")
    assert len(parts) >= 2


def test_get_current_app_version():
    ver = get_current_app_version()
    assert isinstance(ver, str)
    assert ver.startswith("1.") or ver.startswith("v1.")


def test_bump_version_dry_run():
    # Verify that dry_run executes cleanly without raising any exceptions
    bump_version(new_version="1.4.99", new_ytdlp_version="2026.12.31", dry_run=True)
