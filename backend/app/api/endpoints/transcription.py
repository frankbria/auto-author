from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from app.services.transcription_service import transcription_service
from app.schemas.transcription import TranscriptionResponse, StreamingTranscriptionData
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = "en-US",
    enable_punctuation_commands: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe uploaded audio file to text.
    
    Args:
        audio: Audio file to transcribe
        language: Language code for transcription (default: en-US)
        enable_punctuation_commands: Process voice punctuation commands
        current_user: Authenticated user
        
    Returns:
        TranscriptionResponse with transcript and metadata
    """
    try:
        # Validate file size (max 10MB)
        if audio.size and audio.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum size is 10MB."
            )
        
        # Read audio data
        audio_data = await audio.read()
        
        # Validate audio format
        if not transcription_service.validate_audio_format(audio_data, audio.content_type or ""):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {audio.content_type}"
            )
        
        # Perform transcription
        result = transcription_service.transcribe_audio(
            audio_data=audio_data,
            language=language,
            enable_punctuation_commands=enable_punctuation_commands
        )
        
        if result.status == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {result.error_message}"
            )
        
        logger.info(f"Transcription completed for user {current_user.id}: {len(result.transcript)} characters")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during transcription"
        )

@router.websocket("/transcribe/stream")
async def stream_transcription(
    websocket: WebSocket,
    language: str = "en-US",
    enable_punctuation_commands: bool = False
):
    """
    WebSocket endpoint for real-time audio transcription.
    
    Args:
        websocket: WebSocket connection
        language: Language code for transcription
        enable_punctuation_commands: Process voice punctuation commands
    """
    await websocket.accept()
    
    try:
        # In a real implementation, this would handle streaming audio chunks
        # and provide real-time transcription updates
        
        while True:
            # Receive audio chunk or control message
            data = await websocket.receive()
            
            if data["type"] == "websocket.receive":
                if "bytes" in data:
                    # Process audio chunk
                    audio_chunk = data["bytes"]
                    
                    # Mock streaming transcription
                    # In production, this would use streaming speech recognition
                    mock_partial = StreamingTranscriptionData(
                        type="partial",
                        transcript="Processing audio...",
                        confidence=0.8,
                        is_final=False
                    )
                    
                    await websocket.send_json(mock_partial.dict())
                    
                elif "text" in data:
                    # Handle control messages
                    message = data["text"]
                    if message == '{"type": "end"}':
                        # Send final transcription
                        final_result = StreamingTranscriptionData(
                            type="final",
                            transcript="Complete transcription from streaming audio.",
                            confidence=0.95,
                            is_final=True
                        )
                        await websocket.send_json(final_result.dict())
                        break
                        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket transcription error: {str(e)}")
        await websocket.close(code=1011, reason="Internal server error")

@router.get("/transcribe/status")
async def get_transcription_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get transcription service status and capabilities.
    
    Returns:
        Service status information
    """
    return {
        "status": "active",
        "supported_formats": ["audio/webm", "audio/wav", "audio/mp3", "audio/m4a", "audio/ogg"],
        "supported_languages": ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"],
        "max_file_size": "10MB",
        "features": {
            "punctuation_commands": True,
            "streaming": True,
            "confidence_scores": True
        }
    }

@router.post("/transcribe/validate")
async def validate_audio_file(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Validate audio file without transcribing.
    
    Args:
        audio: Audio file to validate
        current_user: Authenticated user
        
    Returns:
        Validation result
    """
    try:
        # Check file size
        if audio.size and audio.size > 10 * 1024 * 1024:
            return {
                "valid": False,
                "error": "File too large. Maximum size is 10MB."
            }
        
        # Read a small sample to validate format
        audio_sample = await audio.read(1024)
        
        # Validate format
        is_valid = transcription_service.validate_audio_format(
            audio_sample, 
            audio.content_type or ""
        )
        
        if not is_valid:
            return {
                "valid": False,
                "error": f"Unsupported audio format: {audio.content_type}"
            }
        
        # Estimate duration
        duration = transcription_service.estimate_duration(audio_sample)
        
        return {
            "valid": True,
            "file_size": audio.size,
            "content_type": audio.content_type,
            "estimated_duration": duration,
            "filename": audio.filename
        }
        
    except Exception as e:
        logger.error(f"Audio validation error: {str(e)}")
        return {
            "valid": False,
            "error": "Failed to validate audio file"
        }
