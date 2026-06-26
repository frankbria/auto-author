"""
Tests for the transcription HTTP endpoints (app/api/endpoints/transcription.py).

The transcription router is not mounted on the main app, so these tests mount it
on a bare FastAPI app and override the auth dependency. The transcription service
is patched throughout — no AWS calls, no real audio.

Covers POST /transcribe, GET /transcribe/status, and POST /transcribe/validate.
The WebSocket /transcribe/stream path is covered in test_transcription_endpoint.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints.transcription import router
from app.core.security import get_current_user_from_session
from app.schemas.transcription import TranscriptionResponse

FAKE_USER = {"id": "u1", "auth_id": "a1", "email": "t@example.com"}


@pytest.fixture
def auth_client():
    """Client whose auth dependency returns a fake user (authenticated)."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_from_session] = lambda: FAKE_USER
    return TestClient(app)


@pytest.fixture
def anon_client():
    """Client with no auth override — the real dependency runs and rejects."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _audio_file(content: bytes = b"fake-audio", content_type: str = "audio/webm"):
    return {"audio": ("clip.webm", content, content_type)}


# --- POST /transcribe ---------------------------------------------------------

def test_transcribe_requires_auth(anon_client):
    resp = anon_client.post("/transcribe", files=_audio_file())
    assert resp.status_code == 401


def test_transcribe_rejects_oversized_file(auth_client):
    big = b"x" * (10 * 1024 * 1024 + 1)
    resp = auth_client.post("/transcribe", files=_audio_file(big))
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


def test_transcribe_rejects_bad_format(auth_client):
    with patch("app.api.endpoints.transcription.transcription_service") as svc:
        svc.validate_audio_format.return_value = False
        resp = auth_client.post("/transcribe", files=_audio_file(content_type="text/plain"))
    assert resp.status_code == 400
    assert "unsupported audio format" in resp.json()["detail"].lower()


def test_transcribe_happy_path(auth_client):
    success = TranscriptionResponse(
        transcript="hello world", confidence=0.95, status="success", duration=1.0
    )
    with patch("app.api.endpoints.transcription.transcription_service") as svc:
        svc.validate_audio_format.return_value = True
        svc.transcribe_audio = AsyncMock(return_value=success)
        resp = auth_client.post(
            "/transcribe", files=_audio_file(), params={"language": "en-US"}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"] == "hello world"
    assert body["status"] == "success"
    svc.transcribe_audio.assert_awaited_once()


def test_transcribe_service_error_returns_500(auth_client):
    failure = TranscriptionResponse(
        transcript="", confidence=0.0, status="error", error_message="boom"
    )
    with patch("app.api.endpoints.transcription.transcription_service") as svc:
        svc.validate_audio_format.return_value = True
        svc.transcribe_audio = AsyncMock(return_value=failure)
        resp = auth_client.post("/transcribe", files=_audio_file())
    assert resp.status_code == 500
    assert "transcription failed" in resp.json()["detail"].lower()


# --- GET /transcribe/status ---------------------------------------------------

def test_status_requires_auth(anon_client):
    assert anon_client.get("/transcribe/status").status_code == 401


def test_status_reports_capabilities(auth_client):
    resp = auth_client.get("/transcribe/status")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("status", "supported_formats", "supported_languages", "max_file_size", "features"):
        assert key in body
    assert body["status"] == "active"
    assert body["features"]["streaming"] is False


# --- POST /transcribe/validate ------------------------------------------------

def test_validate_accepts_valid_sample(auth_client):
    with patch("app.api.endpoints.transcription.transcription_service") as svc:
        svc.validate_audio_format.return_value = True
        svc.estimate_duration.return_value = 2.5
        resp = auth_client.post("/transcribe/validate", files=_audio_file())
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["content_type"] == "audio/webm"
    assert body["estimated_duration"] == 2.5


def test_validate_rejects_oversized_file(auth_client):
    big = b"x" * (10 * 1024 * 1024 + 1)
    resp = auth_client.post("/transcribe/validate", files=_audio_file(big))
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "too large" in body["error"].lower()


def test_validate_rejects_bad_format(auth_client):
    with patch("app.api.endpoints.transcription.transcription_service") as svc:
        svc.validate_audio_format.return_value = False
        resp = auth_client.post(
            "/transcribe/validate", files=_audio_file(content_type="text/plain")
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "unsupported audio format" in body["error"].lower()
