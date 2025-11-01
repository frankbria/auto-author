"""
Session models for tracking user sessions
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SessionMetadata(BaseModel):
    """Metadata about a user session"""

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None  # mobile, desktop, tablet
    browser: Optional[str] = None
    os: Optional[str] = None
    fingerprint: Optional[str] = None  # Browser fingerprint for security


class SessionModel(BaseModel):
    """User session model"""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User's Clerk ID")
    clerk_session_id: Optional[str] = Field(None, description="Clerk's session ID if available")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    # Session state
    is_active: bool = True
    is_suspicious: bool = False  # Flag for suspicious activity

    # Metadata
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)

    # Activity tracking
    request_count: int = 0
    last_endpoint: Optional[str] = None

    # Security
    csrf_token: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123xyz",
                "user_id": "user_clerk_123",
                "clerk_session_id": "sess_clerk_456",
                "created_at": "2025-01-01T00:00:00Z",
                "last_activity": "2025-01-01T00:30:00Z",
                "expires_at": "2025-01-01T12:00:00Z",
                "is_active": True,
                "is_suspicious": False,
                "metadata": {
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0...",
                    "device_type": "desktop",
                    "browser": "Chrome",
                    "os": "Windows"
                },
                "request_count": 42,
                "last_endpoint": "/api/v1/books",
                "csrf_token": "csrf_token_here"
            }
        }


class SessionCreate(BaseModel):
    """Schema for creating a new session"""

    user_id: str
    clerk_session_id: Optional[str] = None
    metadata: Optional[SessionMetadata] = None
    expires_at: Optional[datetime] = None


class SessionUpdate(BaseModel):
    """Schema for updating a session"""

    last_activity: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_suspicious: Optional[bool] = None
    metadata: Optional[SessionMetadata] = None
    request_count: Optional[int] = None
    last_endpoint: Optional[str] = None
    expires_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    """Response schema for session data"""

    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    is_active: bool
    is_suspicious: bool
    request_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123xyz",
                "user_id": "user_clerk_123",
                "created_at": "2025-01-01T00:00:00Z",
                "last_activity": "2025-01-01T00:30:00Z",
                "expires_at": "2025-01-01T12:00:00Z",
                "is_active": True,
                "is_suspicious": False,
                "request_count": 42
            }
        }
