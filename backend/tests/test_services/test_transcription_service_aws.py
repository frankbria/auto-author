"""
Test AWS Transcription Service implementation
"""
import pytest
import json
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from botocore.exceptions import ClientError
from app.services.transcription_service_aws import AWSTranscriptionService
from app.schemas.transcription import TranscriptionResponse


class TestAWSTranscriptionService:
    """Test the AWS Transcription service implementation."""
    
    @pytest.fixture
    def mock_boto3_clients(self):
        """Mock boto3 S3 and Transcribe clients."""
        mock_s3 = Mock()
        mock_transcribe = Mock()
        
        with patch('boto3.client') as mock_client:
            def client_factory(service_name, **kwargs):
                if service_name == 's3':
                    return mock_s3
                elif service_name == 'transcribe':
                    return mock_transcribe
                return Mock()
            
            mock_client.side_effect = client_factory
            yield mock_s3, mock_transcribe
    
    @pytest.fixture
    def aws_service(self, mock_boto3_clients):
        """Create AWS transcription service with mocked clients."""
        mock_s3, mock_transcribe = mock_boto3_clients
        service = AWSTranscriptionService(
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret',
            aws_region='us-east-1'
        )
        service.s3_client = mock_s3
        service.transcribe_client = mock_transcribe
        return service
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, aws_service):
        """Test successful audio transcription."""
        # Mock S3 upload
        aws_service.s3_client.put_object.return_value = {}
        
        # Mock transcription job start
        aws_service.transcribe_client.start_transcription_job.return_value = {}
        
        # Mock transcription job completion
        transcript_uri = "https://s3.amazonaws.com/bucket/transcript.json"
        aws_service.transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {
                    'TranscriptFileUri': transcript_uri
                }
            }
        }
        
        # Mock transcript download
        transcript_data = {
            'results': {
                'transcripts': [{
                    'transcript': 'This is the transcribed text'
                }]
            }
        }
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(transcript_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            # Perform transcription
            result = await aws_service.transcribe_audio(
                audio_data=b"fake audio data",
                language='en-US'
            )
        
        assert isinstance(result, TranscriptionResponse)
        assert result.status == "success"
        assert result.transcript == "This is the transcribed text"
        assert result.confidence == 0.95
        
        # Verify S3 upload was called
        aws_service.s3_client.put_object.assert_called_once()
        
        # Verify transcription job was started
        aws_service.transcribe_client.start_transcription_job.assert_called_once()
        
        # Verify cleanup was attempted
        aws_service.s3_client.delete_object.assert_called_once()
        aws_service.transcribe_client.delete_transcription_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_s3_upload_failure(self, aws_service):
        """Test handling of S3 upload failure."""
        # Mock S3 upload failure
        aws_service.s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'PutObject'
        )
        
        result = await aws_service.transcribe_audio(
            audio_data=b"fake audio data",
            language='en-US'
        )
        
        assert result.status == "error"
        assert "Failed to upload audio" in result.error_message
        assert result.transcript == ""
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_job_start_failure(self, aws_service):
        """Test handling of transcription job start failure."""
        # Mock successful S3 upload
        aws_service.s3_client.put_object.return_value = {}
        
        # Mock transcription job start failure
        aws_service.transcribe_client.start_transcription_job.side_effect = ClientError(
            {'Error': {'Code': 'LimitExceededException', 'Message': 'Limit exceeded'}},
            'StartTranscriptionJob'
        )
        
        result = await aws_service.transcribe_audio(
            audio_data=b"fake audio data",
            language='en-US'
        )
        
        assert result.status == "error"
        assert "Failed to start transcription" in result.error_message
        
        # Verify S3 cleanup was attempted
        aws_service.s3_client.delete_object.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_job_failed_status(self, aws_service):
        """Test handling when transcription job fails."""
        # Mock successful S3 upload and job start
        aws_service.s3_client.put_object.return_value = {}
        aws_service.transcribe_client.start_transcription_job.return_value = {}
        
        # Mock job status as FAILED
        aws_service.transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'FAILED'
            }
        }
        
        result = await aws_service.transcribe_audio(
            audio_data=b"fake audio data",
            language='en-US'
        )
        
        assert result.status == "error"
        assert "Transcription failed or timed out" in result.error_message
    
    @pytest.mark.asyncio
    async def test_wait_for_transcription_timeout(self, aws_service):
        """Test timeout handling in transcription waiting."""
        # Mock job status as IN_PROGRESS forever
        aws_service.transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'IN_PROGRESS'
            }
        }
        
        # Use a very short timeout for testing
        result = await aws_service._wait_for_transcription('test-job', max_wait_time=0.1)
        
        assert result is None
    
    def test_map_language_code(self, aws_service):
        """Test language code mapping."""
        assert aws_service._map_language_code('en-US') == 'en-US'
        assert aws_service._map_language_code('es-ES') == 'es-ES'
        assert aws_service._map_language_code('unknown') == 'en-US'  # Default
    
    def test_validate_audio_format(self, aws_service):
        """Test audio format validation."""
        # Valid formats
        assert aws_service.validate_audio_format(b"audio", "audio/webm") is True
        assert aws_service.validate_audio_format(b"audio", "audio/mp3") is True
        
        # Invalid format
        assert aws_service.validate_audio_format(b"audio", "text/plain") is False
        
        # Too large
        large_audio = b"x" * (11 * 1024 * 1024)
        assert aws_service.validate_audio_format(large_audio, "audio/wav") is False
    
    @pytest.mark.asyncio
    async def test_cleanup_methods(self, aws_service):
        """Test cleanup methods handle errors gracefully."""
        # Mock cleanup failures
        aws_service.s3_client.delete_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'DeleteObject'
        )
        aws_service.transcribe_client.delete_transcription_job.side_effect = ClientError(
            {'Error': {'Code': 'NotFound'}}, 'DeleteTranscriptionJob'
        )
        
        # Should not raise exceptions
        aws_service._cleanup_s3_file('test-file')
        aws_service._cleanup_transcription_job('test-job')
    
    @pytest.mark.asyncio
    async def test_punctuation_command_processing(self, aws_service):
        """Test punctuation command processing in AWS service."""
        # Mock successful transcription with punctuation commands
        aws_service.s3_client.put_object.return_value = {}
        aws_service.transcribe_client.start_transcription_job.return_value = {}
        aws_service.transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {'TranscriptFileUri': 'http://example.com'}
            }
        }
        
        transcript_data = {
            'results': {
                'transcripts': [{
                    'transcript': 'hello comma world period'
                }]
            }
        }
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(transcript_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            result = await aws_service.transcribe_audio(
                audio_data=b"fake audio",
                language='en-US',
                enable_punctuation_commands=True
            )
        
        assert result.transcript == "Hello, world."