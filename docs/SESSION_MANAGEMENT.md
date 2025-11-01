# Session Management System

## Overview

Auto-Author implements a comprehensive session management system that tracks user sessions, provides security features, and enables session monitoring and control.

## Architecture

### Backend Components

1. **Session Models** (`backend/app/models/session.py`)
   - `SessionModel`: Complete session data model
   - `SessionMetadata`: Device and browser information
   - `SessionCreate`: Schema for creating sessions
   - `SessionUpdate`: Schema for updating sessions
   - `SessionResponse`: API response schema

2. **Database Layer** (`backend/app/db/session.py`)
   - MongoDB collection: `sessions`
   - CRUD operations for session management
   - Concurrent session tracking
   - Expired session cleanup

3. **Session Service** (`backend/app/services/session_service.py`)
   - Session lifecycle management
   - Security features (fingerprinting, suspicious activity detection)
   - Activity tracking and idle timeout
   - Session refresh and expiry handling

4. **Session Middleware** (`backend/app/api/middleware/session_middleware.py`)
   - Automatic session creation on authentication
   - Session validation on each request
   - Activity timestamp updates
   - Session ID cookie management

5. **API Endpoints** (`backend/app/api/endpoints/sessions.py`)
   - `GET /api/v1/sessions/current` - Get current session status
   - `POST /api/v1/sessions/refresh` - Refresh session expiry
   - `POST /api/v1/sessions/logout` - Logout current session
   - `POST /api/v1/sessions/logout-all` - Logout all sessions
   - `GET /api/v1/sessions/list` - List user sessions
   - `DELETE /api/v1/sessions/{session_id}` - Delete specific session

### Frontend Components

1. **useSession Hook** (`frontend/src/hooks/useSession.ts`)
   - Session status management
   - Automatic refresh before expiry
   - Activity-based session keep-alive
   - Callbacks for warnings (expiring, idle, suspicious)

2. **SessionWarning Component** (`frontend/src/components/session/SessionWarning.tsx`)
   - Visual warnings for session expiry
   - Idle timeout notifications
   - Suspicious activity alerts
   - User action prompts (stay signed in, logout)

## Features

### Session Tracking
- **Automatic Creation**: Sessions created automatically when users authenticate
- **Activity Monitoring**: Last activity timestamp updated on each request
- **Request Counting**: Track number of requests per session
- **Device Information**: Capture device type, browser, OS, and IP address

### Security Features

1. **Session Fingerprinting**
   - Browser fingerprint based on headers
   - Detects session hijacking attempts
   - Flags suspicious activity when fingerprint changes

2. **Concurrent Session Limits**
   - Maximum 5 concurrent sessions per user (configurable)
   - Oldest sessions automatically deactivated when limit reached

3. **Activity-Based Detection**
   - Abnormal request rate detection
   - Flags sessions with >100 requests/minute as suspicious

4. **CSRF Protection**
   - Unique CSRF token per session
   - Token validation for state-changing operations

### Session Timeouts

1. **Idle Timeout**: 30 minutes of inactivity
   - Warning at 80% (24 minutes)
   - User can refresh with activity

2. **Absolute Timeout**: 12 hours maximum
   - Session expires regardless of activity
   - Auto-refresh available before expiry

3. **Configurable Thresholds**
   - `SESSION_IDLE_TIMEOUT`: Minutes of inactivity before warning
   - `SESSION_ABSOLUTE_TIMEOUT`: Hours before forced logout
   - `SUSPICIOUS_REQUEST_THRESHOLD`: Requests per minute threshold

## Usage

### Backend Usage

#### Create Session (Automatic via Middleware)
```python
# Middleware automatically creates sessions on authentication
# Manual creation:
from app.services.session_service import create_user_session

session = await create_user_session(
    user_id="user_clerk_123",
    request=request,
    clerk_session_id="sess_clerk_456"
)
```

#### Validate Session
```python
from app.services.session_service import validate_session

session = await validate_session(session_id, request)
if session and session.is_suspicious:
    # Handle suspicious activity
    pass
```

#### Refresh Session
```python
from app.services.session_service import refresh_session

refreshed_session = await refresh_session(session_id)
```

### Frontend Usage

#### useSession Hook
```typescript
import useSession from "@/hooks/useSession";

function MyComponent() {
  const {
    sessionStatus,
    loading,
    error,
    refreshSession,
    logout,
    logoutAll,
  } = useSession({
    autoRefresh: true,
    statusCheckInterval: 60000, // 1 minute
    onSessionExpiring: () => {
      console.log("Session expiring soon!");
    },
    onSessionIdle: () => {
      console.log("Session idle");
    },
    onSuspiciousActivity: () => {
      console.log("Suspicious activity detected!");
    },
  });

  return (
    <div>
      {sessionStatus && (
        <p>Session expires in: {sessionStatus.time_until_expiry_seconds}s</p>
      )}
      <button onClick={refreshSession}>Refresh Session</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

#### SessionWarning Component
```typescript
import { SessionWarning } from "@/components/session/SessionWarning";

function App() {
  return (
    <>
      <SessionWarning
        expiryWarningThreshold={300} // 5 minutes
        autoRefreshOnActivity={true}
      />
      {/* Your app content */}
    </>
  );
}
```

## Database Schema

### Sessions Collection

```javascript
{
  _id: ObjectId,
  session_id: "sess_...",  // Unique session identifier
  user_id: "user_clerk_...",  // User's Clerk ID
  clerk_session_id: "sess_clerk_...",  // Optional Clerk session ID
  created_at: ISODate,
  last_activity: ISODate,
  expires_at: ISODate,
  is_active: Boolean,
  is_suspicious: Boolean,
  metadata: {
    ip_address: String,
    user_agent: String,
    device_type: String,  // "mobile" | "desktop" | "tablet"
    browser: String,  // "Chrome" | "Firefox" | "Safari" | ...
    os: String,  // "Windows" | "MacOS" | "Linux" | "iOS" | "Android"
    fingerprint: String  // Browser fingerprint hash
  },
  request_count: Number,
  last_endpoint: String,
  csrf_token: String,
  suspicious_reason: String,  // Optional, set when flagged
  suspicious_at: ISODate  // Optional, when flagged
}
```

## Security Considerations

1. **Session IDs**: Cryptographically secure random tokens
2. **CSRF Tokens**: Unique per session, validated on state changes
3. **Fingerprinting**: Detects session hijacking attempts
4. **Secure Cookies**: HttpOnly, Secure (HTTPS), SameSite=Lax
5. **Rate Limiting**: Prevents brute force and abuse
6. **Expiry Management**: Automatic cleanup of expired sessions

## Testing

### Backend Tests
Location: `backend/tests/test_services/test_session_service.py`

Run tests:
```bash
cd backend
uv run pytest tests/test_services/test_session_service.py -v
```

Coverage areas:
- Session creation and validation
- Concurrent session limits
- Fingerprint detection
- Session expiry and refresh
- Metadata extraction
- Cleanup operations

### Frontend Tests
Location: `frontend/src/__tests__/useSession.test.tsx`

Run tests:
```bash
cd frontend
npm test useSession.test.tsx
```

Coverage areas:
- Session status fetching
- Session refresh
- Logout operations
- Callback triggering
- Error handling
- Auto-refresh behavior

## Performance Considerations

1. **MongoDB Indexes**: Create indexes on `session_id`, `user_id`, and `expires_at`
2. **Caching**: Session data cached in request state to avoid multiple DB queries
3. **Cleanup**: Periodic cleanup of expired sessions (recommended: daily cron job)
4. **Rate Limiting**: Already implemented via existing middleware

## Monitoring

### Key Metrics
- Active sessions count
- Sessions per user
- Suspicious activity rate
- Session expiry/refresh rate
- Average session duration

### Recommended Monitoring
```python
# Add to periodic monitoring job
from app.db.session import cleanup_expired_sessions, get_concurrent_sessions_count

# Cleanup expired sessions daily
deleted = await cleanup_expired_sessions()
print(f"Cleaned up {deleted} expired sessions")

# Monitor concurrent sessions
for user_id in active_users:
    count = await get_concurrent_sessions_count(user_id)
    if count >= MAX_CONCURRENT_SESSIONS:
        # Alert for potential abuse
        pass
```

## Future Enhancements

1. **Redis Integration**: Move session storage to Redis for better performance
2. **Session Analytics**: Track session duration, device distribution, location
3. **Advanced Fingerprinting**: Use more sophisticated browser fingerprinting
4. **Geolocation**: Track and flag unusual location changes
5. **Device Management**: Allow users to view and manage their active devices
6. **Session History**: Keep audit trail of session starts/ends
