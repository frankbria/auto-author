"""
Session management service
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Request
import hashlib
import secrets

from app.models.session import SessionModel, SessionCreate, SessionUpdate, SessionMetadata
from app.db.session import (
    create_session,
    get_session_by_id,
    get_active_session_by_user,
    get_user_sessions,
    update_session,
    update_session_activity,
    deactivate_session,
    deactivate_user_sessions,
    get_concurrent_sessions_count,
    flag_suspicious_session,
    cleanup_expired_sessions,
)


# Configuration
MAX_CONCURRENT_SESSIONS = 5  # Maximum concurrent sessions per user
SESSION_IDLE_TIMEOUT = 30  # Minutes of inactivity before warning
SESSION_ABSOLUTE_TIMEOUT = 12  # Hours before forced logout
SUSPICIOUS_REQUEST_THRESHOLD = 100  # Requests per minute that triggers suspicion


def extract_session_metadata(request: Request) -> SessionMetadata:
    """Extract session metadata from request

    Args:
        request: FastAPI request object

    Returns:
        Session metadata
    """
    user_agent = request.headers.get("user-agent", "")

    # Parse device type from user agent
    device_type = "desktop"
    user_agent_lower = user_agent.lower()
    if "mobile" in user_agent_lower or "iphone" in user_agent_lower:
        device_type = "mobile"
    elif "tablet" in user_agent_lower or "ipad" in user_agent_lower:
        device_type = "tablet"

    # Parse browser (simple heuristic)
    browser = "unknown"
    if "Chrome" in user_agent:
        browser = "Chrome"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Safari" in user_agent:
        browser = "Safari"
    elif "Edge" in user_agent:
        browser = "Edge"

    # Parse OS - check iOS/iPhone BEFORE Mac (iOS user agents contain "Mac OS X")
    os = "unknown"
    if "Windows" in user_agent:
        os = "Windows"
    elif "Android" in user_agent:
        os = "Android"
    elif "iOS" in user_agent or "iPhone" in user_agent or "iPad" in user_agent:
        os = "iOS"
    elif "Mac" in user_agent:
        os = "MacOS"
    elif "Linux" in user_agent:
        os = "Linux"

    return SessionMetadata(
        ip_address=request.client.host if request.client else None,
        user_agent=user_agent,
        device_type=device_type,
        browser=browser,
        os=os,
        fingerprint=generate_fingerprint(request),
    )


def generate_fingerprint(request: Request) -> str:
    """Generate a browser fingerprint from request

    Args:
        request: FastAPI request object

    Returns:
        Fingerprint hash
    """
    # Combine various headers to create a fingerprint
    components = [
        request.headers.get("user-agent", ""),
        request.headers.get("accept-language", ""),
        request.headers.get("accept-encoding", ""),
        request.client.host if request.client else "",
    ]

    fingerprint_string = "|".join(components)
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]


async def create_user_session(
    user_id: str,
    request: Request,
    clerk_session_id: Optional[str] = None
) -> SessionModel:
    """Create a new session for a user

    Args:
        user_id: User's Clerk ID
        request: FastAPI request object
        clerk_session_id: Optional Clerk session ID

    Returns:
        Created session model

    Raises:
        ValueError: If user has too many concurrent sessions
    """
    # Check concurrent session limit
    concurrent_count = await get_concurrent_sessions_count(user_id)
    if concurrent_count >= MAX_CONCURRENT_SESSIONS:
        # Deactivate oldest sessions to make room
        sessions = await get_user_sessions(user_id, active_only=True, limit=MAX_CONCURRENT_SESSIONS)
        if len(sessions) >= MAX_CONCURRENT_SESSIONS:
            # Deactivate the oldest session
            oldest_session = sessions[-1]
            await deactivate_session(oldest_session.session_id)

    # Extract metadata from request
    metadata = extract_session_metadata(request)

    # Create session
    session_data = SessionCreate(
        user_id=user_id,
        clerk_session_id=clerk_session_id,
        metadata=metadata,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_ABSOLUTE_TIMEOUT)
    )

    return await create_session(session_data)


async def validate_session(session_id: str, request: Request) -> Optional[SessionModel]:
    """Validate a session and check for suspicious activity

    Args:
        session_id: Session identifier
        request: FastAPI request object

    Returns:
        Session model if valid, None otherwise
    """
    session = await get_session_by_id(session_id)

    if not session:
        return None

    # Check if session is active
    if not session.is_active:
        return None

    # Check if session is expired
    now = datetime.now(timezone.utc)
    if session.expires_at and session.expires_at < now:
        await deactivate_session(session_id)
        return None

    # Check idle timeout
    idle_time = now - session.last_activity
    if idle_time.total_seconds() > (SESSION_IDLE_TIMEOUT * 60):
        # Session is idle but not expired - we'll allow it but flag for warning
        pass

    # Check for fingerprint changes (possible session hijacking)
    current_fingerprint = generate_fingerprint(request)
    if session.metadata.fingerprint and session.metadata.fingerprint != current_fingerprint:
        # Fingerprint changed - flag as suspicious
        await flag_suspicious_session(
            session_id,
            reason="Fingerprint mismatch - possible session hijacking"
        )
        # Still return session but marked as suspicious
        session.is_suspicious = True

    # Check for abnormal request rate
    if session.request_count > 0 and session.last_activity:
        time_since_created = (now - session.created_at).total_seconds() / 60  # minutes
        if time_since_created > 0:
            requests_per_minute = session.request_count / time_since_created
            if requests_per_minute > SUSPICIOUS_REQUEST_THRESHOLD:
                await flag_suspicious_session(
                    session_id,
                    reason=f"Abnormal request rate: {requests_per_minute:.1f} req/min"
                )
                session.is_suspicious = True

    # Update activity and get updated session
    updated_session = await update_session_activity(session_id, request.url.path)

    # Return the updated session if available, otherwise return the original with suspicious flag
    if updated_session:
        # Transfer suspicious flag to updated session if it was set
        if session.is_suspicious:
            updated_session.is_suspicious = True
        return updated_session

    return session


async def refresh_session(session_id: str) -> Optional[SessionModel]:
    """Refresh a session's expiry time

    Args:
        session_id: Session identifier

    Returns:
        Updated session model if found, None otherwise
    """
    session = await get_session_by_id(session_id)

    if not session or not session.is_active:
        return None

    # Extend expiry by SESSION_ABSOLUTE_TIMEOUT hours
    new_expiry = datetime.now(timezone.utc) + timedelta(hours=SESSION_ABSOLUTE_TIMEOUT)

    update_data = SessionUpdate(
        expires_at=new_expiry,
        last_activity=datetime.now(timezone.utc)
    )

    return await update_session(session_id, update_data)


async def end_session(session_id: str) -> bool:
    """End a session (logout)

    Args:
        session_id: Session identifier

    Returns:
        True if session was ended, False otherwise
    """
    return await deactivate_session(session_id)


async def end_all_user_sessions(user_id: str, except_session_id: Optional[str] = None) -> int:
    """End all sessions for a user (e.g., for security purposes)

    Args:
        user_id: User's Clerk ID
        except_session_id: Optional session ID to keep active

    Returns:
        Number of sessions ended
    """
    return await deactivate_user_sessions(user_id, except_session_id)


async def get_session_status(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session status information

    Args:
        session_id: Session identifier

    Returns:
        Session status dictionary
    """
    session = await get_session_by_id(session_id)

    if not session:
        return None

    now = datetime.now(timezone.utc)

    # Calculate idle time
    idle_seconds = (now - session.last_activity).total_seconds()
    idle_warning = idle_seconds > (SESSION_IDLE_TIMEOUT * 60 * 0.8)  # Warn at 80% of timeout

    # Calculate time until expiry
    time_until_expiry = None
    if session.expires_at:
        time_until_expiry = (session.expires_at - now).total_seconds()

    return {
        "session_id": session.session_id,
        "is_active": session.is_active,
        "is_suspicious": session.is_suspicious,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "idle_seconds": int(idle_seconds),
        "idle_warning": idle_warning,
        "time_until_expiry_seconds": int(time_until_expiry) if time_until_expiry else None,
        "request_count": session.request_count,
        "device_type": session.metadata.device_type if session.metadata else None,
        "browser": session.metadata.browser if session.metadata else None,
    }


async def cleanup_old_sessions() -> int:
    """Cleanup expired sessions (should be run periodically)

    Returns:
        Number of sessions cleaned up
    """
    return await cleanup_expired_sessions()
