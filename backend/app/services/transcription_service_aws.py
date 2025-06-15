import logging
import json
import time
import uuid
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from app.schemas.transcription import TranscriptionResponse
import re

logger = logging.getLogger(__name__)

class AWSTranscriptionService:
    """Service for handling audio transcription using AWS Transcribe."""
    
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, aws_region: str = 'us-east-1'):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        self.transcribe_client = boto3.client(
            'transcribe',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        self.bucket_name = "auto-author-transcriptions"  # You'll need to create this bucket
        self.aws_region = aws_region
        
        self.punctuation_commands = {
            'comma': ',',
            'period': '.',
            'question mark': '?',
            'exclamation point': '!',
            'colon': ':',
            'semicolon': ';',
            'dash': '-',
            'quote': '"',
            'open quote': '"',
            'close quote': '"',
            'new line': '\n',
            'new paragraph': '\n\n'
        }

    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = 'en-US',
        enable_punctuation_commands: bool = False
    ) -> TranscriptionResponse:
        """
        Transcribe audio data to text using AWS Transcribe.
        
        Args:
            audio_data: Raw audio bytes
            language: Language code for transcription
            enable_punctuation_commands: Whether to process voice punctuation commands
            
        Returns:
            TranscriptionResponse with transcript and metadata
        """
        try:
            # Generate unique job name and file name
            job_name = f"transcription_{uuid.uuid4().hex[:8]}"
            file_key = f"audio/{job_name}.webm"  # Assuming webm format from browser
            
            # Upload audio to S3
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Body=audio_data,
                    ContentType='audio/webm'
                )
            except ClientError as e:
                logger.error(f"Failed to upload audio to S3: {str(e)}")
                return TranscriptionResponse(
                    transcript="",
                    confidence=0.0,
                    status="error",
                    error_message=f"Failed to upload audio: {str(e)}"
                )
            
            # Start transcription job
            try:
                media_uri = f"s3://{self.bucket_name}/{file_key}"
                
                self.transcribe_client.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': media_uri},
                    MediaFormat='webm',  # or 'mp3', 'mp4', 'wav' based on your audio format
                    LanguageCode=self._map_language_code(language),
                    Settings={
                        'ShowSpeakerLabels': False,
                        'ShowAlternatives': False
                    }
                )
            except ClientError as e:
                logger.error(f"Failed to start transcription job: {str(e)}")
                # Clean up S3 file
                self._cleanup_s3_file(file_key)
                return TranscriptionResponse(
                    transcript="",
                    confidence=0.0,
                    status="error",
                    error_message=f"Failed to start transcription: {str(e)}"
                )
            
            # Wait for transcription to complete
            transcript_text = await self._wait_for_transcription(job_name)
            
            # Clean up S3 file and transcription job
            self._cleanup_s3_file(file_key)
            self._cleanup_transcription_job(job_name)
            
            if transcript_text is None:
                return TranscriptionResponse(
                    transcript="",
                    confidence=0.0,
                    status="error",
                    error_message="Transcription failed or timed out"
                )
            
            # Process punctuation commands if enabled
            if enable_punctuation_commands:
                transcript_text = self._process_punctuation_commands(transcript_text)
            
            return TranscriptionResponse(
                transcript=transcript_text,
                confidence=0.95,  # AWS doesn't provide overall confidence scores easily
                status="success",
                duration=len(audio_data) / 44100.0  # Approximate duration
            )
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return TranscriptionResponse(
                transcript="",
                confidence=0.0,
                status="error",
                error_message=str(e)
            )

    async def _wait_for_transcription(self, job_name: str, max_wait_time: int = 60) -> Optional[str]:
        """
        Wait for transcription job to complete and return the transcript.
        
        Args:
            job_name: Name of the transcription job
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Transcript text or None if failed
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    
                    # Download and parse transcript
                    import urllib.request
                    with urllib.request.urlopen(transcript_uri) as url:
                        data = json.loads(url.read().decode())
                        return data['results']['transcripts'][0]['transcript']
                
                elif status == 'FAILED':
                    logger.error(f"Transcription job failed: {job_name}")
                    return None
                
                # Job still in progress, wait a bit
                await self._async_sleep(2)
                
            except ClientError as e:
                logger.error(f"Error checking transcription job status: {str(e)}")
                return None
        
        logger.error(f"Transcription job timed out: {job_name}")
        return None

    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)

    def _map_language_code(self, language: str) -> str:
        """
        Map language codes to AWS Transcribe language codes.
        
        Args:
            language: Input language code
            
        Returns:
            AWS Transcribe language code
        """
        language_map = {
            'en-US': 'en-US',
            'en-GB': 'en-GB',
            'es-ES': 'es-ES',
            'fr-FR': 'fr-FR',
            'de-DE': 'de-DE',
            'it-IT': 'it-IT',
            'pt-BR': 'pt-BR',
            'ja-JP': 'ja-JP',
            'ko-KR': 'ko-KR',
            'zh-CN': 'zh-CN'
        }
        return language_map.get(language, 'en-US')

    def _process_punctuation_commands(self, transcript: str) -> str:
        """
        Process voice commands for punctuation in the transcript.
        
        Args:
            transcript: Raw transcript text
            
        Returns:
            Processed transcript with punctuation applied
        """
        processed = transcript.lower()
        
        # Replace punctuation commands with actual punctuation
        for command, punctuation in self.punctuation_commands.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(command) + r'\b'
            processed = re.sub(pattern, punctuation, processed)
        
        # Clean up spacing around punctuation
        processed = re.sub(r'\s+([,.!?;:])', r'\1', processed)
        processed = re.sub(r'\s+', ' ', processed)
        processed = processed.strip()
        
        # Capitalize first letter and letters after sentence endings
        if processed:
            processed = processed[0].upper() + processed[1:]
            processed = re.sub(r'([.!?]\s+)(\w)', 
                             lambda m: m.group(1) + m.group(2).upper(), 
                             processed)
        
        return processed

    def _cleanup_s3_file(self, file_key: str):
        """Clean up S3 file after transcription."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
        except ClientError as e:
            logger.warning(f"Failed to delete S3 file {file_key}: {str(e)}")

    def _cleanup_transcription_job(self, job_name: str):
        """Clean up transcription job."""
        try:
            self.transcribe_client.delete_transcription_job(
                TranscriptionJobName=job_name
            )
        except ClientError as e:
            logger.warning(f"Failed to delete transcription job {job_name}: {str(e)}")

    def validate_audio_format(self, audio_data: bytes, content_type: str) -> bool:
        """
        Validate that the audio data is in a supported format.
        
        Args:
            audio_data: Raw audio bytes
            content_type: MIME type of the audio
            
        Returns:
            True if format is supported, False otherwise
        """
        supported_types = [
            'audio/webm',
            'audio/wav',
            'audio/mp3',
            'audio/mp4',
            'audio/m4a',
            'audio/flac'
        ]
        
        if content_type not in supported_types:
            return False
            
        # Basic size validation (max 10MB for real-time transcription)
        if len(audio_data) > 10 * 1024 * 1024:
            return False
            
        return True

    def estimate_duration(self, audio_data: bytes, sample_rate: int = 44100) -> float:
        """
        Estimate audio duration based on data size.
        
        Args:
            audio_data: Raw audio bytes
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Estimated duration in seconds
        """
        # Rough estimation - actual implementation would need proper audio parsing
        return len(audio_data) / (sample_rate * 2)  # Assuming 16-bit audio