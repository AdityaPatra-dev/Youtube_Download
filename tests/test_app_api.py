"""
Unit tests for FastAPI endpoints:
/api/system, /api/app-update/check, /api/status, /api/files/list, and error responses.
"""
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_api_system_status():
    """Verify system diagnostics endpoint returns required engine metrics."""
    response = client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "ytdlp_version" in data
    assert "ffmpeg_available" in data
    assert "detected_browsers" in data
    assert isinstance(data["detected_browsers"], list)


def test_api_status_idle():
    """Verify status endpoint returns clean idle state when no download is active."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "active" in data
    assert "status" in data
    assert "batches" in data
    assert "progress_pct" in data
    assert "speed" in data
    assert "eta" in data
    assert "size" in data
    assert data["active"] is False


def test_api_files_list():
    """Verify files list endpoint returns a list of files."""
    response = client.get("/api/files")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_app_update_check():
    """Verify in-app auto-update endpoint returns status and version metadata."""
    response = client.get("/api/app-update/check")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "current_version" in data
    assert data["current_version"] == "v1.4.1"
    assert "is_update_available" in data
    assert isinstance(data["is_update_available"], bool)


def test_api_inspect_validation():
    """Verify validation error when required URL parameter is missing."""
    response = client.post("/api/inspect", json={})
    assert response.status_code == 422  # Unprocessable Entity
