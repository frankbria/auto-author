"""
Tests for the transcription WebSocket endpoint (issue #45).

The streaming endpoint previously returned fabricated transcripts
("Processing audio...", "Complete transcription from streaming audio."). It now
returns an explicit NOT_IMPLEMENTED message and closes, so clients are never
fed mock data masquerading as real transcription.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.endpoints.transcription import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_stream_transcription_returns_not_implemented(client):
    """WebSocket sends a NOT_IMPLEMENTED error and closes — no fake transcript."""
    with client.websocket_connect("/transcribe/stream") as ws:
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["code"] == "NOT_IMPLEMENTED"
        assert "not yet available" in message["message"].lower()

        # No further (fabricated) messages — the server closes the connection.
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
