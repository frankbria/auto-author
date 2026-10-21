# API Profile Endpoints Documentation

This document provides detailed information about the profile-related API endpoints available in Auto Author, their parameters, responses, and usage examples.

## Related Documentation

- [Profile Management Guide](../user-guide/profile-management.md) - Comprehensive guide for profile features
- [Authentication User Guide](../user-guide/auth.md) - Sign-in, sessions and auth error messages
- [Session Management](../development/session-management.md) - How sessions and cookies are configured

## Base URL

```
https://api.auto-author.com/v1
```

For local development:

```
http://localhost:8000
```

## Authentication

Every endpoint in this document requires a signed-in user. The API authenticates the better-auth session cookie (`better-auth.session_token`, or `__Secure-better-auth.session_token` over HTTPS) that the sign-in flow sets; there is no separate bearer token. Browser clients send the cookie automatically on same-site requests.

An unauthenticated request is answered `401` (for example `Not authenticated. Please sign in.`); an account with an unverified email address gets `403`; and `503` with a `Retry-After` header means the session could not be checked and should be retried. The full list of messages is in the [Authentication User Guide](../user-guide/auth.md#api-authentication-errors). In the browser, the frontend signs the user out and redirects to sign-in on any `401`.

## Rate Limiting

Profile endpoints implement rate limiting to prevent abuse:
- `/users/me` (GET): 20 requests per minute
- `/users/me` (PATCH): 5 requests per minute
- `/users/me` (DELETE): 3 requests per 5 minutes
- `/users/me/export` (GET): 10 requests per hour

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
  "auth_id": "Xf3kq9TzR2bLw8NmPa1cVy7D",
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

`avatar_url` is not writable here (#797): sending it returns `422`. It is
written only by `POST /users/me/avatar`.

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

### Export Account Data

`GET /users/me/export` returns the authenticated user's data as one JSON
document, sent as an attachment (`auto-author-data.json`) (#790). It takes no
id: every query is scoped to the session's own account.

| Key | Holds |
|---|---|
| `exported_at` | when the export was built |
| `profile` | `email`, `first_name`, `last_name`, `display_name`, `bio`, `avatar_url`, `preferences`, `plan`, `stripe_subscription_status`, `created_at`, `updated_at`, `terms_version`, `terms_accepted_at`, each only if the account has it |
| `books` | every book the account owns, as stored, with chapter content |
| `questions`, `question_responses`, `question_ratings` | every row that carries the account's id |

Ids are strings and dates are ISO 8601 in UTC. The response is sent with
`Cache-Control: no-store`. A book's `collaborators` list is left out, because it
would name other accounts. Not included: the audit log, chapter
access log and usage counters, uploaded image files (their URLs are), and
anything better-auth or the payment processor holds (password hash, sessions,
two-factor secrets, payment records). The response is built in memory.

---

### Delete User Account

Deactivates the authenticated user's account. All owned content — books and their
questions, responses, ratings, and chapter access logs — is permanently
cascade-deleted (issue #179). The better-auth identity (user, credential
accounts, sessions, 2FA secret) is removed (#763), so the account cannot sign
in and the same email can sign up again as a new, unconnected account. The
uploaded avatar and every book's cover and thumbnail file are deleted as well
(#785); a storage failure there is logged and does not fail the request. If the
content cascade fails, the request returns 500 and the account stays active
(its subscription is already cancelled) so it can be retried.

The user record is replaced by a deactivated record (#954):

| Field | Holds |
|---|---|
| `auth_id` | the account id |
| `deleted_at` | when the account was deactivated; every "is this account closed" check reads this field |
| `purge_at` | `deleted_at` plus 548 days (18 months) |
| `retained` | `email`, `first_name`, `last_name`, `display_name`, `created_at`, `plan`, `stripe_customer_id`, `cancelled_subscription` (`id`, `plan`, `status` of the subscription that account deletion cancelled), and `terms_version` and `terms_accepted_at` (#960), each only if the account had a value for it (a field that is missing or null is left out) |

Nothing else survives: no bio, avatar URL, preferences or book list. The
retained fields are nested so that they sit outside the unique indexes on
`email` and `stripe_customer_id`.

The backend erases a record whose `purge_at` has passed to a tombstone of
`auth_id` and `deleted_at` (#784). It checks at startup and once a day. An
admin erases one earlier with `DELETE /users/{auth_id}`: on an active account
that call deactivates it, and on a deactivated one it erases it (404 once it is
erased). This is how support honours a request for earlier erasure.

**Endpoint**: `DELETE /users/me`

**Authentication**: Required

**Parameters**: None

**Response Format**:
```json
{
  "message": "Account deactivated"
}
```

**Status Codes**:
- `200 OK`: Account deactivated
- `401 Unauthorized`: Invalid or missing authentication token
- `404 Not Found`: User not found or already deleted
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Content cascade failed — account left active, retry
- `502 Bad Gateway`: The subscription could not be cancelled — nothing was deleted, retry

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ..."
```

> ⚠️ **Warning**: This operation is irreversible. All books and related content are permanently deleted, and a deactivated account cannot be reactivated.

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

#### Deactivate or Erase Any User

Deactivates an active account exactly as `DELETE /users/me` does. For an admin,
the same call on an account that is already deactivated erases its retained
record to the tombstone (#954).

**Endpoint**: `DELETE /users/{auth_id}`

**Authentication**: Required (admin, or the user's own id)

**Path Parameters**:
- `auth_id`: The better-auth user ID

**Status Codes**:
- `204 No Content`: Account deactivated, or a deactivated account erased
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: User not found or already erased
- `502 Bad Gateway`: The subscription could not be cancelled — nothing was deleted, retry

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
