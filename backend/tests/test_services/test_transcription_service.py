"""
Test Transcription Service functionality
Tests both mock and AWS Transcribe implementations
"""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.services.transcription_service import TranscriptionService
from app.schemas.transcription import TranscriptionResponse
import json


class TestTranscriptionService:
    """Test the transcription service functionality."""
    
    @pytest.fixture
    def mock_aws_credentials(self, monkeypatch):
        """Mock AWS credentials for testing."""
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-key-id')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-secret-key')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
    
    @pytest.fixture
    def clear_aws_credentials(self, monkeypatch):
        """Clear AWS credentials to test mock service."""
        monkeypatch.delenv('AWS_ACCESS_KEY_ID', raising=False)
        monkeypatch.delenv('AWS_SECRET_ACCESS_KEY', raising=False)
        monkeypatch.delenv('AWS_REGION', raising=False)
    
    @pytest.mark.asyncio
    async def test_mock_transcription_service(self, clear_aws_credentials):
        """Test mock transcription when no AWS credentials are available."""
        service = TranscriptionService()
        
        # Should use mock service
        assert service.use_aws is False
        assert service.aws_service is None
        
        # Test transcription
        audio_data = b"fake audio data" * 100
        result = await service.transcribe_audio(
            audio_data=audio_data,
            language='en-US',
            enable_punctuation_commands=False
        )
        
        assert isinstance(result, TranscriptionResponse)
        assert result.status == "success"
        assert result.confidence == 0.95
        assert len(result.transcript) > 0
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_mock_transcription_with_punctuation_commands(self, clear_aws_credentials):
        """Test mock transcription with punctuation command processing."""
        service = TranscriptionService()
        
        # Mock the _mock_transcription to return text with commands
        with patch.object(service, '_mock_transcription', return_value="hello comma world period"):
            result = await service.transcribe_audio(
                audio_data=b"fake audio",
                language='en-US',
                enable_punctuation_commands=True
            )
            
            assert result.transcript == "Hello, world."
    
    @pytest.mark.asyncio
    async def test_aws_transcription_service_initialization(self, mock_aws_credentials):
        """Test that AWS service is initialized when credentials are present."""
        with patch('app.services.transcription_service_aws.AWSTranscriptionService') as mock_aws:
            service = TranscriptionService()
            
            assert service.use_aws is True
            assert service.aws_service is not None
            mock_aws.assert_called_once_with(
                aws_access_key_id='test-key-id',
                aws_secret_access_key='test-secret-key',
                aws_region='us-east-1'
            )
    
    @pytest.mark.asyncio
    async def test_aws_transcription_service_usage(self, mock_aws_credentials):
        """Test that AWS service is used when available."""
        mock_aws_service = AsyncMock()
        mock_response = TranscriptionResponse(
            transcript="AWS transcribed text",
            confidence=0.98,
            status="success",
            duration=5.0
        )
        mock_aws_service.transcribe_audio.return_value = mock_response
        
        with patch('app.services.transcription_service_aws.AWSTranscriptionService', return_value=mock_aws_service):
            service = TranscriptionService()
            service.aws_service = mock_aws_service
            
            result = await service.transcribe_audio(
                audio_data=b"fake audio",
                language='en-US',
                enable_punctuation_commands=False
            )
            
            assert result.transcript == "AWS transcribed text"
            assert result.confidence == 0.98
            mock_aws_service.transcribe_audio.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcription_error_handling(self, clear_aws_credentials):
        """Test error handling in transcription service."""
        service = TranscriptionService()
        
        # Mock an error in _mock_transcription
        with patch.object(service, '_mock_transcription', side_effect=Exception("Test error")):
            result = await service.transcribe_audio(
                audio_data=b"fake audio",
                language='en-US'
            )
            
            assert result.status == "error"
            assert result.confidence == 0.0
            assert result.transcript == ""
            assert "Test error" in result.error_message
    
    def test_validate_audio_format(self, clear_aws_credentials):
        """Test audio format validation."""
        service = TranscriptionService()
        
        # Valid formats
        assert service.validate_audio_format(b"audio", "audio/webm") is True
        assert service.validate_audio_format(b"audio", "audio/wav") is True
        assert service.validate_audio_format(b"audio", "audio/mp3") is True
        
        # Invalid format
        assert service.validate_audio_format(b"audio", "video/mp4") is False
        
        # Too large file
        large_audio = b"x" * (11 * 1024 * 1024)  # 11MB
        assert service.validate_audio_format(large_audio, "audio/wav") is False
    
    def test_estimate_duration(self, clear_aws_credentials):
        """Test audio duration estimation."""
        service = TranscriptionService()
        
        # 44100 Hz * 2 bytes * 10 seconds = 882000 bytes
        audio_data = b"x" * 882000
        duration = service.estimate_duration(audio_data)
        
        assert duration == 10.0
    
    def test_punctuation_command_processing(self, clear_aws_credentials):
        """Test punctuation command processing."""
        service = TranscriptionService()
        
        # Test various punctuation commands
        test_cases = [
            ("hello comma world", "Hello, world"),
            ("question mark", "?"),
            ("new paragraph hello", "Hello"),  # newlines get processed out
            ("quote hello quote", '" hello "'),  # quotes with spaces
            ("multiple period period period", "Multiple..."),
        ]
        
        for input_text, expected in test_cases:
            result = service._process_punctuation_commands(input_text)
            assert expected in result or result == expected