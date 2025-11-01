"""
Session management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import List, Dict, Any

from app.core.security import get_current_user
from app.models.session import SessionResponse
from app.services.session_service import (
    get_session_status,
    refresh_session,
    end_session,
    end_all_user_sessions,
    get_user_sessions,
)
from app.db.session import get_session_by_id

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/current", response_model=Dict[str, Any])
async def get_current_session_status(
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """Get current session status

    Returns information about the current session including:
    - Active status
    - Time until expiry
    - Idle time
    - Request count
    - Device information
    """
    # Get session from request state
    if not hasattr(request.state, "session"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found"
        )

    session = request.state.session
    session_status = await get_session_status(session.session_id)

    if not session_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return session_status


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_current_session(
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """Refresh the current session's expiry time

    Extends the session by the configured absolute timeout period.
    Use this to keep a session alive during active usage.
    """
    # Get session from request state
    if not hasattr(request.state, "session"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found"
        )

    session = request.state.session
    updated_session = await refresh_session(session.session_id)

    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive"
        )

    return {
        "message": "Session refreshed successfully",
        "expires_at": updated_session.expires_at.isoformat() if updated_session.expires_at else None
    }


@router.post("/logout")
async def logout_current_session(
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """Logout from the current session

    Deactivates the current session. The user will need to authenticate again.
    """
    # Get session from request state
    if not hasattr(request.state, "session"):
        return {"message": "No active session to logout"}

    session = request.state.session
    success = await end_session(session.session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all_sessions(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    keep_current: bool = True
):
    """Logout from all sessions

    Deactivates all sessions for the current user.
    Useful for security purposes (e.g., password change, suspicious activity).

    Args:
        keep_current: If True, keeps the current session active
    """
    user_id = current_user.get("clerk_id") or current_user.get("id")

    current_session_id = None
    if keep_current and hasattr(request.state, "session"):
        current_session_id = request.state.session.session_id

    count = await end_all_user_sessions(user_id, current_session_id)

    return {
        "message": f"Logged out from {count} session(s)",
        "sessions_ended": count,
        "current_session_kept": keep_current and current_session_id is not None
    }


@router.get("/list", response_model=List[SessionResponse])
async def list_user_sessions(
    current_user: Dict = Depends(get_current_user),
    active_only: bool = False,
    limit: int = 10
):
    """List all sessions for the current user

    Args:
        active_only: If True, only return active sessions
        limit: Maximum number of sessions to return (default: 10)

    Returns:
        List of sessions ordered by most recent activity
    """
    user_id = current_user.get("clerk_id") or current_user.get("id")

    sessions = await get_user_sessions(user_id, active_only, limit)

    return [
        SessionResponse(
            session_id=s.session_id,
            user_id=s.user_id,
            created_at=s.created_at,
            last_activity=s.last_activity,
            expires_at=s.expires_at,
            is_active=s.is_active,
            is_suspicious=s.is_suspicious,
            request_count=s.request_count
        )
        for s in sessions
    ]


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a specific session

    Can only delete sessions belonging to the current user.

    Args:
        session_id: The ID of the session to delete
    """
    user_id = current_user.get("clerk_id") or current_user.get("id")

    # Verify the session belongs to the current user
    session = await get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete session belonging to another user"
        )

    success = await end_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )

    return {"message": "Session deleted successfully"}
