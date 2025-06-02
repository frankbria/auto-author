from pydantic import BaseModel
from typing import Optional

class TranscriptionRequest(BaseModel):
    audio_data: bytes
    language: str = 'en-US'
    enable_punctuation_commands: bool = False

class TranscriptionResponse(BaseModel):
    transcript: str
    confidence: float
    status: str
    duration: Optional[float] = None
    error_message: Optional[str] = None

class StreamingTranscriptionData(BaseModel):
    type: str  # 'partial' or 'final'
    transcript: str
    confidence: Optional[float] = None
    is_final: bool = False
