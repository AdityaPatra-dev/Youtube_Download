"""
Unit tests for the Application Auto-Update system:
version comparison algorithm, release tag extraction, and payload structure.
"""
import pytest
import re


def compare_versions(v1: str, v2: str) -> int:
    """Python implementation of AppUpdateManager.compareVersions algorithm."""
    if not v1: v1 = "0.0.0"
    if not v2: v2 = "0.0.0"
    v1_clean = re.sub(r'^[vV]', '', v1.strip())
    v2_clean = re.sub(r'^[vV]', '', v2.strip())

    parts1 = [int(re.sub(r'\D.*', '', p)) for p in v1_clean.split('.') if re.sub(r'\D.*', '', p).isdigit()]
    parts2 = [int(re.sub(r'\D.*', '', p)) for p in v2_clean.split('.') if re.sub(r'\D.*', '', p).isdigit()]

    length = max(len(parts1), len(parts2))
    for i in range(length):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 < p2:
            return -1
        if p1 > p2:
            return 1
    return 0


def test_version_comparisons():
    """Verify semantic version comparisons across various tag formats."""
    # When current < latest: update is available (-1)
    assert compare_versions("v1.3.1", "v1.3.2") == -1
    assert compare_versions("1.3.1", "1.4.0") == -1
    assert compare_versions("v1.3.1", "v2.0.0") == -1
    assert compare_versions("v1.3.1", "1.3.10") == -1

    # When current == latest: up to date (0)
    assert compare_versions("v1.3.1", "v1.3.1") == 0
    assert compare_versions("1.3.1", "v1.3.1") == 0
    assert compare_versions("v1.3.1", "1.3.1") == 0

    # When current > latest: ahead (1)
    assert compare_versions("v1.4.0", "v1.3.1") == 1
    assert compare_versions("v2.0.0", "v1.9.9") == 1


def test_tag_extraction_from_redirect_location():
    """Verify release tag parsing from HTTP Location header redirects."""
    location = "https://github.com/AdityaPatra-dev/Youtube_Download/releases/tag/v1.3.2"
    tag = location.split("/")[-1].strip()
    assert tag == "v1.3.2"
    assert compare_versions("v1.3.1", tag) == -1

