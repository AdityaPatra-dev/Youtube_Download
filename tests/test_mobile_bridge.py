"""
Unit tests for Android mobile Python bridge functions:
format parsing, resolution classification, file sanitization,
and hardware muxing preparation.
"""
import pytest
import os
import sys

# Add Android python module to sys.path for direct unit testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "android", "app", "src", "main", "python")))

from mobile_bridge import (
    sanitize_filename,
    get_height_label,
    get_unique_filepath,
    parse_available_formats,
    fmt_size,
)


def test_sanitize_filename():
    """Verify that illegal FAT32/Android characters are stripped and length is bounded."""
    dirty = 'My Video: The Movie? Part 1 / 2 *<Awesome>| "Edition"'
    clean = sanitize_filename(dirty)
    assert clean == "My Video The Movie Part 1 2 Awesome Edition"
    for char in r'\/*?:"<>|':
        assert char not in clean

    # Bound check
    super_long = "A" * 300
    assert len(sanitize_filename(super_long)) <= 100

    # Empty fallback
    assert sanitize_filename("") == "video"


def test_get_height_label():
    """Verify height to human-readable resolution labels."""
    assert get_height_label(2160) == "4K Ultra HD"
    assert get_height_label(1440) == "1440p 2K QHD"
    assert get_height_label(1080) == "1080p Full HD"
    assert get_height_label(720) == "720p HD"
    assert get_height_label(480) == "480p SD"
    assert get_height_label(360) == "360p"


def test_get_unique_filepath(tmp_path):
    """Verify that get_unique_filepath never overwrites existing files."""
    output_dir = str(tmp_path)
    title = "Test Video"
    ext = "mp4"

    f1 = get_unique_filepath(output_dir, title, ext)
    assert f1.endswith("Test Video.mp4")

    # Create file on disk
    open(f1, "w").close()

    f2 = get_unique_filepath(output_dir, title, ext)
    assert f2.endswith("Test Video (1).mp4")

    open(f2, "w").close()

    f3 = get_unique_filepath(output_dir, title, ext)
    assert f3.endswith("Test Video (2).mp4")


def test_parse_available_formats():
    """Verify format analysis handles 4K, 2K, 1080p, 720p, audio tracks, and tagging."""
    mock_formats = [
        {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "filesize": 15000000, "fps": 30},
        {"format_id": "22", "vcodec": "avc1", "acodec": "mp4a", "height": 720, "filesize": 45000000, "fps": 30},
        {"format_id": "137", "vcodec": "avc1", "acodec": "none", "height": 1080, "filesize": 85000000, "fps": 60},
        {"format_id": "271", "vcodec": "vp9", "acodec": "none", "height": 1440, "filesize": 160000000, "fps": 60},
        {"format_id": "313", "vcodec": "vp9", "acodec": "none", "height": 2160, "filesize": 350000000, "fps": 60},
        {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "filesize": 12000000, "abr": 128},
    ]

    res_list, audio_info = parse_available_formats(mock_formats, duration=300.0, total_items=1)
    assert len(res_list) > 0

    heights = [r["height"] for r in res_list]
    assert 2160 in heights, "4K resolution should be parsed"
    assert 1440 in heights, "1440p resolution should be parsed"
    assert 1080 in heights, "1080p resolution should be parsed"
    assert 720 in heights, "720p resolution should be parsed"
    assert 360 in heights, "360p resolution should be parsed"

    # Highest resolution should have is_max = True
    assert res_list[0]["height"] == 2160
    assert res_list[0]["is_max"] is True

    # Audio info must be populated
    assert audio_info is not None
    assert "size_formatted" in audio_info

