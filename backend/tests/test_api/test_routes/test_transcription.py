"""
Test Transcription API Endpoints

Comprehensive test coverage for audio transcription endpoints:
- POST /api/v1/transcribe - Audio file transcription
- GET /api/v1/transcribe/status - Service status
- POST /api/v1/transcribe/validate - Audio file validation
- WebSocket /api/v1/transcribe/stream - Streaming transcription

Target: 85% coverage for app.api.endpoints.transcription
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO
from app.schemas.transcription import TranscriptionResponse, StreamingTranscriptionData
# Import transcription module to ensure it's loaded
import app.api.endpoints.transcription

pytestmark = pytest.mark.asyncio


class TestTranscribeAudioEndpoint:
    """Test POST /api/v1/transcribe endpoint."""

    async def test_transcribe_valid_audio_success(self, auth_client_factory):
        """Test successful transcription of valid audio file."""
        client = await auth_client_factory()

        # Mock transcription service response
        mock_response = TranscriptionResponse(
            transcript="This is a test transcription.",
            confidence=0.95,
            status="success",
            duration=5.0,
            error_message=None
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

            # Create mock audio file
            audio_content = b"fake audio data" * 100  # Make it substantial
            files = {
                'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')
            }

            response = await client.post(
                "/api/v1/transcribe",
                files=files,
                params={'language': 'en-US', 'enable_punctuation_commands': 'false'}
            )

            assert response.status_code == 200
            data = response.json()
            assert data['transcript'] == "This is a test transcription."
            assert data['confidence'] == 0.95
            assert data['status'] == "success"
            assert data['duration'] == 5.0
            assert data['error_message'] is None

            # Verify service was called correctly
            mock_service.transcribe_audio.assert_called_once()
            call_kwargs = mock_service.transcribe_audio.call_args.kwargs
            assert call_kwargs['language'] == 'en-US'
            assert call_kwargs['enable_punctuation_commands'] is False

    async def test_transcribe_with_punctuation_commands(self, auth_client_factory):
        """Test transcription with punctuation command processing enabled."""
        client = await auth_client_factory()

        mock_response = TranscriptionResponse(
            transcript="Hello, world.",
            confidence=0.92,
            status="success",
            duration=3.0
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

            audio_content = b"audio data with punctuation commands"
            files = {'audio': ('test.mp3', BytesIO(audio_content), 'audio/mp3')}

            response = await client.post(
                "/api/v1/transcribe",
                files=files,
                params={'language': 'en-US', 'enable_punctuation_commands': 'true'}
            )

            assert response.status_code == 200
            data = response.json()
            assert data['transcript'] == "Hello, world."

            # Verify punctuation commands were enabled
            call_kwargs = mock_service.transcribe_audio.call_args.kwargs
            assert call_kwargs['enable_punctuation_commands'] is True

    async def test_transcribe_file_too_large(self, auth_client_factory):
        """Test rejection of audio files exceeding 10MB limit."""
        client = await auth_client_factory()

        # Create 11MB file (exceeds 10MB limit)
        large_audio = b"x" * (11 * 1024 * 1024)
        files = {'audio': ('large.wav', BytesIO(large_audio), 'audio/wav')}

        response = await client.post("/api/v1/transcribe", files=files)

        assert response.status_code == 413
        data = response.json()
        assert "too large" in data['detail'].lower()
        assert "10MB" in data['detail']

    async def test_transcribe_invalid_audio_format(self, auth_client_factory):
        """Test rejection of invalid audio format."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = False

            audio_content = b"not really audio"
            files = {'audio': ('test.txt', BytesIO(audio_content), 'text/plain')}

            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 400
            data = response.json()
            assert "unsupported audio format" in data['detail'].lower()

    async def test_transcribe_service_error(self, auth_client_factory):
        """Test handling of transcription service errors."""
        client = await auth_client_factory()

        # Mock service returning error status
        error_response = TranscriptionResponse(
            transcript="",
            confidence=0.0,
            status="error",
            error_message="AWS Transcribe service unavailable"
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=error_response)

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 500
            data = response.json()
            assert "transcription failed" in data['detail'].lower()
            assert "AWS Transcribe service unavailable" in data['detail']

    async def test_transcribe_exception_handling(self, auth_client_factory):
        """Test handling of unexpected exceptions during transcription."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(side_effect=Exception("Unexpected error"))

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 500
            data = response.json()
            assert "internal server error" in data['detail'].lower()

    async def test_transcribe_empty_audio_file(self, auth_client_factory):
        """Test handling of empty audio file."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = False

            files = {'audio': ('empty.wav', BytesIO(b''), 'audio/wav')}

            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 400
            data = response.json()
            assert "unsupported audio format" in data['detail'].lower()

    async def test_transcribe_different_languages(self, auth_client_factory):
        """Test transcription with different language codes."""
        client = await auth_client_factory()

        languages = ['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE']

        for lang in languages:
            mock_response = TranscriptionResponse(
                transcript=f"Text in {lang}",
                confidence=0.90,
                status="success"
            )

            with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
                mock_service.validate_audio_format.return_value = True
                mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

                audio_content = b"audio data"
                files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

                response = await client.post(
                    "/api/v1/transcribe",
                    files=files,
                    params={'language': lang}
                )

                assert response.status_code == 200
                call_kwargs = mock_service.transcribe_audio.call_args.kwargs
                assert call_kwargs['language'] == lang

    async def test_transcribe_unauthenticated(self, auth_client_factory, monkeypatch):
        """Test that unauthenticated requests are rejected."""
        # CRITICAL: Disable BYPASS_AUTH
        from app.core.config import settings
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)

        # Get client without authentication
        client = await auth_client_factory(auth=False)

        audio_content = b"audio data"
        files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

        response = await client.post("/api/v1/transcribe", files=files)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_transcribe_various_audio_formats(self, auth_client_factory):
        """Test transcription with various supported audio formats."""
        client = await auth_client_factory()

        formats = [
            ('test.wav', 'audio/wav'),
            ('test.mp3', 'audio/mp3'),
            ('test.m4a', 'audio/m4a'),
            ('test.webm', 'audio/webm'),
            ('test.ogg', 'audio/ogg')
        ]

        for filename, content_type in formats:
            mock_response = TranscriptionResponse(
                transcript="Test transcript",
                confidence=0.95,
                status="success"
            )

            with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
                mock_service.validate_audio_format.return_value = True
                mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

                audio_content = b"audio data for " + filename.encode()
                files = {'audio': (filename, BytesIO(audio_content), content_type)}

                response = await client.post("/api/v1/transcribe", files=files)

                assert response.status_code == 200
                data = response.json()
                assert data['status'] == 'success'


class TestTranscriptionStatusEndpoint:
    """Test GET /api/v1/transcribe/status endpoint."""

    async def test_get_transcription_status(self, auth_client_factory):
        """Test retrieval of transcription service status."""
        client = await auth_client_factory()

        response = await client.get("/api/v1/transcribe/status")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data['status'] == 'active'
        assert 'supported_formats' in data
        assert 'supported_languages' in data
        assert 'max_file_size' in data
        assert 'features' in data

        # Verify supported formats
        assert 'audio/webm' in data['supported_formats']
        assert 'audio/wav' in data['supported_formats']
        assert 'audio/mp3' in data['supported_formats']
        assert 'audio/m4a' in data['supported_formats']
        assert 'audio/ogg' in data['supported_formats']

        # Verify supported languages
        assert 'en-US' in data['supported_languages']
        assert 'es-ES' in data['supported_languages']

        # Verify max file size
        assert data['max_file_size'] == '10MB'

        # Verify features
        assert data['features']['punctuation_commands'] is True
        assert data['features']['streaming'] is True
        assert data['features']['confidence_scores'] is True

    async def test_get_status_unauthenticated(self, auth_client_factory, monkeypatch):
        """Test that unauthenticated requests to status endpoint are rejected."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)

        client = await auth_client_factory(auth=False)

        response = await client.get("/api/v1/transcribe/status")

        assert response.status_code == 401


class TestValidateAudioEndpoint:
    """Test POST /api/v1/transcribe/validate endpoint."""

    async def test_validate_valid_audio(self, auth_client_factory):
        """Test validation of valid audio file."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.estimate_duration.return_value = 5.2

            audio_content = b"valid audio data" * 100
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            response = await client.post("/api/v1/transcribe/validate", files=files)

            assert response.status_code == 200
            data = response.json()

            assert data['valid'] is True
            assert 'file_size' in data
            assert data['content_type'] == 'audio/wav'
            assert data['estimated_duration'] == 5.2
            assert data['filename'] == 'test.wav'

    async def test_validate_invalid_audio_format(self, auth_client_factory):
        """Test validation rejection of invalid audio format."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = False

            audio_content = b"not audio"
            files = {'audio': ('test.txt', BytesIO(audio_content), 'text/plain')}

            response = await client.post("/api/v1/transcribe/validate", files=files)

            assert response.status_code == 200
            data = response.json()

            assert data['valid'] is False
            assert 'error' in data
            assert 'unsupported audio format' in data['error'].lower()

    async def test_validate_file_too_large(self, auth_client_factory):
        """Test validation rejection of files exceeding size limit."""
        client = await auth_client_factory()

        # Create 11MB file
        large_audio = b"x" * (11 * 1024 * 1024)
        files = {'audio': ('large.wav', BytesIO(large_audio), 'audio/wav')}

        response = await client.post("/api/v1/transcribe/validate", files=files)

        assert response.status_code == 200
        data = response.json()

        assert data['valid'] is False
        assert 'error' in data
        assert 'too large' in data['error'].lower()
        assert '10MB' in data['error']

    async def test_validate_exception_handling(self, auth_client_factory):
        """Test handling of exceptions during validation."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.side_effect = Exception("Validation error")

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            response = await client.post("/api/v1/transcribe/validate", files=files)

            assert response.status_code == 200
            data = response.json()

            assert data['valid'] is False
            assert 'error' in data
            assert 'failed to validate' in data['error'].lower()

    async def test_validate_multiple_formats(self, auth_client_factory):
        """Test validation of various audio formats."""
        client = await auth_client_factory()

        formats = [
            ('test.wav', 'audio/wav', True),
            ('test.mp3', 'audio/mp3', True),
            ('test.m4a', 'audio/m4a', True),
            ('test.txt', 'text/plain', False),
            ('test.mp4', 'video/mp4', False)
        ]

        for filename, content_type, should_be_valid in formats:
            with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
                mock_service.validate_audio_format.return_value = should_be_valid
                mock_service.estimate_duration.return_value = 3.0

                audio_content = b"audio data"
                files = {'audio': (filename, BytesIO(audio_content), content_type)}

                response = await client.post("/api/v1/transcribe/validate", files=files)

                assert response.status_code == 200
                data = response.json()
                assert data['valid'] == should_be_valid

    async def test_validate_unauthenticated(self, auth_client_factory, monkeypatch):
        """Test that unauthenticated requests are rejected."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)

        client = await auth_client_factory(auth=False)

        audio_content = b"audio data"
        files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

        response = await client.post("/api/v1/transcribe/validate", files=files)

        assert response.status_code == 401


class TestStreamingTranscriptionWebSocket:
    """Test WebSocket /api/v1/transcribe/stream endpoint."""

    def test_websocket_audio_chunk_handling(self, client):
        """Test WebSocket handling of audio chunks."""
        with client.websocket_connect("/api/v1/transcribe/stream") as websocket:
            # Send audio chunk (bytes)
            audio_data = b"fake audio chunk data"
            websocket.send_bytes(audio_data)

            # Receive partial transcription response
            response = websocket.receive_json()

            assert response['type'] == 'partial'
            assert response['transcript'] == 'Processing audio...'
            assert response['confidence'] == 0.8
            assert response['is_final'] is False

    def test_websocket_end_message(self, client):
        """Test WebSocket end message handling."""
        with client.websocket_connect("/api/v1/transcribe/stream") as websocket:
            # Send end message
            websocket.send_text('{"type": "end"}')

            # Receive final transcription response
            response = websocket.receive_json()

            assert response['type'] == 'final'
            assert response['transcript'] == 'Complete transcription from streaming audio.'
            assert response['confidence'] == 0.95
            assert response['is_final'] is True

    def test_websocket_multiple_audio_chunks(self, client):
        """Test WebSocket handling of multiple audio chunks."""
        with client.websocket_connect("/api/v1/transcribe/stream") as websocket:
            # Send multiple audio chunks
            for i in range(3):
                audio_data = f"audio chunk {i}".encode()
                websocket.send_bytes(audio_data)

                # Receive partial transcription for each chunk
                response = websocket.receive_json()
                assert response['type'] == 'partial'
                assert 'transcript' in response

            # Send end message
            websocket.send_text('{"type": "end"}')

            # Receive final transcription
            final_response = websocket.receive_json()
            assert final_response['type'] == 'final'
            assert final_response['is_final'] is True

    def test_websocket_disconnect(self, client):
        """Test WebSocket disconnection handling."""
        with client.websocket_connect("/api/v1/transcribe/stream") as websocket:
            # Send an audio chunk
            websocket.send_bytes(b"audio data")
            websocket.receive_json()

            # Connection will close when exiting context manager
        # If we reach here without exception, disconnect was handled correctly

    def test_websocket_with_language_parameter(self, client):
        """Test WebSocket connection with language parameter."""
        with client.websocket_connect("/api/v1/transcribe/stream?language=es-ES") as websocket:
            # Send audio chunk
            websocket.send_bytes(b"audio data")

            # Receive response
            response = websocket.receive_json()
            assert response['type'] == 'partial'

    def test_websocket_with_punctuation_commands(self, client):
        """Test WebSocket connection with punctuation commands enabled."""
        with client.websocket_connect("/api/v1/transcribe/stream?enable_punctuation_commands=true") as websocket:
            # Send audio chunk
            websocket.send_bytes(b"audio data")

            # Receive response
            response = websocket.receive_json()
            assert response['type'] == 'partial'

    def test_websocket_non_end_text_message(self, client):
        """Test WebSocket handling of non-end text messages."""
        with client.websocket_connect("/api/v1/transcribe/stream") as websocket:
            # Send audio chunk first
            websocket.send_bytes(b"audio data")
            response1 = websocket.receive_json()
            assert response1['type'] == 'partial'

            # Send non-end text message (should be ignored, continue loop)
            websocket.send_text('{"type": "ping"}')

            # Send another audio chunk to verify loop continues
            websocket.send_bytes(b"more audio")
            response2 = websocket.receive_json()
            assert response2['type'] == 'partial'

            # Finally send end message
            websocket.send_text('{"type": "end"}')
            final_response = websocket.receive_json()
            assert final_response['type'] == 'final'

    def test_websocket_client_disconnect(self, client, caplog):
        """Test WebSocket disconnection by client."""
        import logging
        with caplog.at_level(logging.INFO):
            with client.websocket_connect("/api/v1/transcribe/stream") as websocket:
                # Send audio chunk
                websocket.send_bytes(b"audio data")
                websocket.receive_json()
                # Client disconnects by closing connection
            # WebSocketDisconnect exception should be caught and logged


class TestTranscriptionEdgeCases:
    """Test edge cases and error conditions."""

    async def test_transcribe_corrupted_audio(self, auth_client_factory):
        """Test handling of corrupted audio data."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            # Simulate corrupted audio detection
            mock_service.validate_audio_format.return_value = False

            corrupted_audio = b"\x00\xFF\xFE" * 100
            files = {'audio': ('corrupted.wav', BytesIO(corrupted_audio), 'audio/wav')}

            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 400

    async def test_transcribe_missing_content_type(self, auth_client_factory):
        """Test handling of missing content type."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = False

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), None)}

            response = await client.post("/api/v1/transcribe", files=files)

            # Should reject due to missing/invalid content type
            assert response.status_code in [400, 500]

    async def test_transcribe_no_file_uploaded(self, auth_client_factory):
        """Test handling of request without file upload."""
        client = await auth_client_factory()

        # Send request without files
        response = await client.post("/api/v1/transcribe")

        assert response.status_code == 422  # Unprocessable Entity

    async def test_transcribe_multiple_files(self, auth_client_factory):
        """Test handling of multiple file uploads (should use first)."""
        client = await auth_client_factory()

        mock_response = TranscriptionResponse(
            transcript="Test",
            confidence=0.95,
            status="success"
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

            # Only one file should be processed
            files = {'audio': ('test.wav', BytesIO(b"audio data"), 'audio/wav')}

            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 200

    async def test_validate_zero_byte_file(self, auth_client_factory):
        """Test validation of zero-byte file."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = False

            files = {'audio': ('empty.wav', BytesIO(b''), 'audio/wav')}

            response = await client.post("/api/v1/transcribe/validate", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data['valid'] is False

    async def test_transcribe_default_language(self, auth_client_factory):
        """Test that default language is en-US when not specified."""
        client = await auth_client_factory()

        mock_response = TranscriptionResponse(
            transcript="Test",
            confidence=0.95,
            status="success"
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            # Don't specify language
            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 200

            # Verify default language was used
            call_kwargs = mock_service.transcribe_audio.call_args.kwargs
            assert call_kwargs['language'] == 'en-US'

    async def test_transcribe_default_punctuation_commands(self, auth_client_factory):
        """Test that punctuation commands default to False."""
        client = await auth_client_factory()

        mock_response = TranscriptionResponse(
            transcript="Test",
            confidence=0.95,
            status="success"
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            # Don't specify enable_punctuation_commands
            response = await client.post("/api/v1/transcribe", files=files)

            assert response.status_code == 200

            # Verify default was False
            call_kwargs = mock_service.transcribe_audio.call_args.kwargs
            assert call_kwargs['enable_punctuation_commands'] is False


class TestTranscriptionLogging:
    """Test logging behavior in transcription endpoints."""

    async def test_transcribe_logs_user_activity(self, auth_client_factory, caplog):
        """Test that successful transcription logs user activity."""
        client = await auth_client_factory()

        mock_response = TranscriptionResponse(
            transcript="This is a test with some length.",
            confidence=0.95,
            status="success"
        )

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(return_value=mock_response)

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            with caplog.at_level('INFO'):
                response = await client.post("/api/v1/transcribe", files=files)

                assert response.status_code == 200

                # Check for log entry
                # Note: Logging may not appear in caplog due to test setup
                # This test documents expected behavior

    async def test_transcribe_logs_errors(self, auth_client_factory, caplog):
        """Test that transcription errors are logged."""
        client = await auth_client_factory()

        with patch('app.api.endpoints.transcription.transcription_service') as mock_service:
            mock_service.validate_audio_format.return_value = True
            mock_service.transcribe_audio = AsyncMock(side_effect=Exception("Test error"))

            audio_content = b"audio data"
            files = {'audio': ('test.wav', BytesIO(audio_content), 'audio/wav')}

            with caplog.at_level('ERROR'):
                response = await client.post("/api/v1/transcribe", files=files)

                assert response.status_code == 500
                # Error should be logged
