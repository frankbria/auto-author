# API Profile Endpoints Documentation

This document provides detailed information about the profile-related API endpoints available in Auto Author, their parameters, responses, and usage examples.

## Related Documentation

- [Profile Management Guide](profile-management-guide.md) - Comprehensive guide for profile features
- [Frontend Profile Components](frontend-profile-components.md) - Technical docs for profile UI components
- [Profile Testing Guide](profile-testing-guide.md) - Testing and CI/CD for profile features
- [API Authentication Endpoints](api-auth-endpoints.md) - Authentication API documentation
- [Clerk Integration Guide](clerk-integration-guide.md) - How Clerk authentication is integrated

## Base URL

```
https://api.auto-author.com/v1
```

For local development:

```
http://localhost:8000
```

## Authentication

All API endpoints in this document require authentication using Clerk JWT tokens. Include the token in the `Authorization` header of your request:

```
Authorization: Bearer <token>
```

## Rate Limiting

Profile endpoints implement rate limiting to prevent abuse:
- `/users/me` (GET): 20 requests per minute
- `/users/me` (PATCH): 5 requests per minute
- `/users/me` (DELETE): 3 requests per 5 minutes

Responses include rate limit headers:
```
X-RateLimit-Limit: <requests_allowed>
X-RateLimit-Remaining: <requests_remaining>
X-RateLimit-Reset: <timestamp>
```

---

## Endpoints

### Get Current User Profile

Retrieves the authenticated user's profile information.

**Endpoint**: `GET /users/me`

**Authentication**: Required

**Parameters**: None

**Response Format**:
```json
{
  "id": "6457922acf1d345678abcdef",
  "clerk_id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
  "email": "user@example.com",
  "first_name": "Jane", 
  "last_name": "Doe",
  "display_name": "Jane Doe",
  "avatar_url": "https://img.clerk.com/user_avatar.jpg",
  "bio": "Author and technology enthusiast",
  "role": "user",
  "created_at": "2025-05-01T12:00:00Z",
  "updated_at": "2025-05-17T12:00:00Z",
  "books": ["6457922acf1d34b789fedcba"],
  "preferences": {
    "theme": "dark",
    "email_notifications": true,
    "marketing_emails": false
  }
}
```

**Status Codes**:
- `200 OK`: Profile retrieved successfully
- `401 Unauthorized`: Invalid or missing authentication token
- `500 Internal Server Error`: Server-side error

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..."
```

---

### Update User Profile

Updates the authenticated user's profile information.

**Endpoint**: `PATCH /users/me`

**Authentication**: Required

**Request Body**:
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "bio": "Updated professional bio",
  "preferences": {
    "theme": "light",
    "email_notifications": false,
    "marketing_emails": true
  }
}
```

All fields are optional. Only include fields you want to update.

**Response Format**: Same as GET /users/me (returns updated user object)

**Status Codes**:
- `200 OK`: Profile updated successfully
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Invalid or missing authentication token
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

**Example Request**:
```bash
curl -X PATCH "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Updated professional bio",
    "preferences": {
      "theme": "light"
    }
  }'
```

---

### Delete User Account

Permanently deletes the authenticated user's account and associated data.

**Endpoint**: `DELETE /users/me`

**Authentication**: Required

**Parameters**: None

**Response Format**:
```json
{
  "message": "Account successfully deleted"
}
```

**Status Codes**:
- `200 OK`: Account deleted successfully
- `401 Unauthorized`: Invalid or missing authentication token
- `404 Not Found`: User not found or already deleted
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..."
```

> ⚠️ **Warning**: This operation is irreversible. All user data will be permanently deleted.

---

### Get Clerk User Data

Retrieves user data directly from Clerk. Only administrators can access data for other users.

**Endpoint**: `GET /users/clerk/{clerk_id}`

**Authentication**: Required

**Path Parameters**:
- `clerk_id`: The Clerk user ID

**Response Format**:
```json
{
  "id": "user_2NxAa1pyy8THf937QUAhKR2tXCI",
  "email_addresses": [
    {
      "id": "idn_1234567890",
      "email_address": "user@example.com",
      "verification": {
        "status": "verified",
        "strategy": "email_code"
      }
    }
  ],
  "first_name": "Jane",
  "last_name": "Doe",
  "profile_image_url": "https://img.clerk.com/user_avatar.jpg"
}
```

**Status Codes**:
- `200 OK`: Data retrieved successfully
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Insufficient permissions (non-admin trying to access another user's data)
- `404 Not Found`: User not found in Clerk

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/users/clerk/user_2NxAa1pyy8THf937QUAhKR2tXCI" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..."
```

---

### Administrator Endpoints

The following endpoints are available only to users with administrator permissions:

#### Get All Users

**Endpoint**: `GET /users/admin/users`

**Authentication**: Required (admin only)

**Response**: Array of user objects (same format as GET /users/me)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/users/admin/users" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..."
```

#### Update Any User

**Endpoint**: `PUT /users/{clerk_id}`

**Authentication**: Required (admin or self only)

**Path Parameters**:
- `clerk_id`: The Clerk user ID

**Request Body**: Same format as PATCH /users/me

**Response**: Updated user object

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/users/user_2NxAa1pyy8THf937QUAhKR2tXCI" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin",
    "bio": "Admin user"
  }'
```

#### Delete Any User

**Endpoint**: `DELETE /users/{clerk_id}`

**Authentication**: Required (admin only)

**Path Parameters**:
- `clerk_id`: The Clerk user ID

**Status Codes**:
- `204 No Content`: User successfully deleted
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: User not found

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/users/user_2NxAa1pyy8THf937QUAhKR2tXCI" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..."
```

---

## Security Measures

The profile API incorporates several security features:

1. **Input Sanitization**: All incoming data is sanitized to prevent XSS and SQL injection attacks
2. **Request Auditing**: All profile-related requests are logged for security monitoring
3. **Rate Limiting**: Prevents brute force and DoS attacks
4. **Role-Based Access**: Ensures users can only access appropriate resources
5. **Clerk Integration**: Leverages Clerk's robust authentication system

## Error Handling

All endpoints return standardized error responses:

```json
{
  "detail": "Error message describing the issue"
}
```

Common error scenarios:
- Invalid input format
- Insufficient permissions
- Rate limit exceeded
- Server-side processing errors
- Resource not found

---

*For technical support with the API, please contact api-support@auto-author.com*
