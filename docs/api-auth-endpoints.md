# API Authentication Endpoints Documentation

This document details the authentication-related API endpoints in Auto Author, providing a reference for developers integrating with our backend services.

## Overview

Auto Author's API uses JWT-based authentication powered by Clerk. All protected endpoints require a valid JWT token in the `Authorization` header with the `Bearer` prefix.

## Authentication Flow

1. User authenticates via frontend using Clerk
2. Frontend receives JWT token
3. Frontend includes token in API requests
4. Backend validates token using Clerk's public key
5. Backend permits or denies access based on token validity and permissions

## Base URL

```
https://api.auto-author.com/v1
```

For local development:

```
http://localhost:8000
```

## Authentication Endpoints

### Current User

Retrieves information about the currently authenticated user.

**Endpoint**: `GET /users/me`

**Authentication**: Required

**Request Headers**:
```
Authorization: Bearer <jwt_token>
```

**Example Response**:
```json
{
  "id": "user_2xAmple5tring",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "full_name": "Jane Doe",
  "profile_image_url": "https://example.com/avatar.jpg",
  "created_at": "2023-05-14T12:00:00Z",
  "updated_at": "2023-05-14T12:00:00Z",
  "roles": ["user"],
  "subscription_status": "active"
}
```

**Status Codes**:
- `200 OK`: Successfully retrieved user information
- `401 Unauthorized`: Invalid or missing authentication token
- `404 Not Found`: User not found in database

### Session Validation

Validates if the current session is active and returns basic session information.

**Endpoint**: `GET /auth/session`

**Authentication**: Required

**Request Headers**:
```
Authorization: Bearer <jwt_token>
```

**Example Response**:
```json
{
  "active": true,
  "user_id": "user_2xAmple5tring",
  "session_id": "sess_1xAmple5tring",
  "expires_at": "2023-05-15T12:00:00Z",
  "last_active_at": "2023-05-14T12:00:00Z",
  "device_info": {
    "browser": "Chrome",
    "os": "Windows",
    "ip_address": "192.168.1.1"
  }
}
```

**Status Codes**:
- `200 OK`: Session is valid
- `401 Unauthorized`: Invalid or expired session

### Session Refresh

Refreshes the current session and issues a new token.

**Endpoint**: `POST /auth/refresh`

**Authentication**: Required (expired tokens accepted)

**Request Headers**:
```
Authorization: Bearer <jwt_token>
```

**Example Response**:
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ...",
  "expires_at": "2023-05-15T12:00:00Z"
}
```

**Status Codes**:
- `200 OK`: Successfully refreshed token
- `401 Unauthorized`: Refresh token is invalid or expired

### Session Termination

Explicitly terminates the current session.

**Endpoint**: `POST /auth/logout`

**Authentication**: Required

**Request Headers**:
```
Authorization: Bearer <jwt_token>
```

**Example Response**:
```json
{
  "success": true,
  "message": "Session terminated successfully",
  "session_id": "sess_1xAmple5tring"
}
```

**Status Codes**:
- `200 OK`: Session successfully terminated
- `401 Unauthorized`: Invalid authentication token

## Webhook Endpoints

### Authentication Events

Receives and processes authentication events from Clerk.

**Endpoint**: `POST /webhooks/clerk`

**Authentication**: Clerk webhook signature

**Request Headers**:
```
svix-id: <webhook_id>
svix-timestamp: <timestamp>
svix-signature: <signature>
```

**Example Request Body**:
```json
{
  "type": "user.created",
  "data": {
    "id": "user_2xAmple5tring",
    "email_addresses": [
      {"email_address": "user@example.com", "verification": {"status": "verified"}}
    ],
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "object": "event"
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Webhook processed successfully"
}
```

**Status Codes**:
- `200 OK`: Webhook processed successfully
- `401 Unauthorized`: Invalid webhook signature
- `400 Bad Request`: Malformed webhook payload

## Error Responses

All authentication errors follow a standardized format:

```json
{
  "status": "error",
  "code": "unauthorized",
  "message": "Invalid or expired authentication token",
  "details": {
    "error_type": "token_expired",
    "timestamp": "2023-05-14T12:00:00Z",
    "request_id": "req_1xAmple5tring"
  }
}
```

Common error codes:

| Code | Description |
|------|-------------|
| `invalid_token` | The JWT is malformed or has invalid signature |
| `token_expired` | The JWT has expired |
| `insufficient_permissions` | Valid token but insufficient permissions |
| `user_not_found` | Token is valid but user no longer exists |
| `session_terminated` | The session was manually terminated |

## Implementation Examples

### Authentication Request (JavaScript)

```javascript
const fetchUserProfile = async () => {
  const response = await fetch('https://api.auto-author.com/v1/users/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error('Authentication failed');
  }
  
  return response.json();
};
```

### Authentication Request (Python)

```python
import requests

def fetch_user_profile(token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    response = requests.get(
        'https://api.auto-author.com/v1/users/me',
        headers=headers
    )
    
    response.raise_for_status()  # Raise exception for 4XX/5XX status codes
    return response.json()
```

## Security Best Practices

1. **Token Storage**: Never store JWTs in localStorage; use HTTP-only cookies
2. **HTTPS Only**: Always use HTTPS for production API calls
3. **Token Expiration**: Handle token expiration gracefully with refresh flow
4. **Error Handling**: Implement proper error handling for authentication failures
5. **Request Throttling**: Respect rate limits to avoid being blocked

## Related Documentation

- [Login/Logout Flows](./login-logout-flows.md)
- [Authentication Troubleshooting Guide](./auth-troubleshooting.md)
- [Session Management Strategies](./session-management.md)
