# Book Metadata API Endpoints

This document outlines the API endpoints available for managing book metadata in the Auto Author application.

## Base URL

```
http://localhost:8000/api/v1
```

Replace with the appropriate production URL in deployment environments.

## Authentication

All endpoints require authentication using a Bearer token:

```
Authorization: Bearer <clerk_jwt_token>
```

## Book Metadata Endpoints

### Create a New Book

Creates a new book with the specified metadata.

**Endpoint:** `POST /books`

**Rate Limit:** 10 requests per 60 seconds

**Request Body:**

```json
{
  "title": "My Awesome Book",
  "subtitle": "A Journey Through Words",
  "description": "This book explores the creative writing process",
  "genre": "Non-fiction",
  "target_audience": "Writers and aspiring authors",
  "cover_image_url": "https://example.com/cover.jpg",
  "metadata": { "draft_version": "1.0" }
}
```

**Required Fields:**
- `title`: String (1-100 characters)

**Optional Fields:**
- `subtitle`: String (up to 200 characters)
- `description`: String (up to 5000 characters)
- `genre`: String (up to 100 characters)
- `target_audience`: String (up to 100 characters)
- `cover_image_url`: String (valid URL)
- `metadata`: Object (for custom metadata)

**Response:** `201 Created`

```json
{
  "id": "60a12b456c89d1234567890a",
  "title": "My Awesome Book",
  "subtitle": "A Journey Through Words",
  "description": "This book explores the creative writing process",
  "genre": "Non-fiction",
  "target_audience": "Writers and aspiring authors",
  "cover_image_url": "https://example.com/cover.jpg",
  "metadata": { "draft_version": "1.0" },
  "created_at": "2025-05-22T10:30:00Z",
  "updated_at": "2025-05-22T10:30:00Z",
  "owner_id": "usr_123456789",
  "toc_items": [],
  "published": false,
  "collaborators": []
}
```

### Get All User Books

Retrieves all books owned by the authenticated user.

**Endpoint:** `GET /books`

**Rate Limit:** 20 requests per 60 seconds

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100, max: 100)

**Response:** `200 OK`

```json
[
  {
    "id": "60a12b456c89d1234567890a",
    "title": "My Awesome Book",
    "subtitle": "A Journey Through Words",
    "description": "This book explores the creative writing process",
    "genre": "Non-fiction",
    "target_audience": "Writers and aspiring authors",
    "cover_image_url": "https://example.com/cover.jpg",
    "metadata": { "draft_version": "1.0" },
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T10:30:00Z",
    "owner_id": "usr_123456789",
    "toc_items": [],
    "published": false,
    "collaborators": []
  }
]
```

### Get Book by ID

Retrieves a specific book by its ID.

**Endpoint:** `GET /books/{book_id}`

**Rate Limit:** 20 requests per 60 seconds

**Path Parameters:**
- `book_id`: The unique identifier of the book

**Response:** `200 OK`

```json
{
  "id": "60a12b456c89d1234567890a",
  "title": "My Awesome Book",
  "subtitle": "A Journey Through Words",
  "description": "This book explores the creative writing process",
  "genre": "Non-fiction",
  "target_audience": "Writers and aspiring authors",
  "cover_image_url": "https://example.com/cover.jpg",
  "metadata": { "draft_version": "1.0" },
  "created_at": "2025-05-22T10:30:00Z",
  "updated_at": "2025-05-22T10:30:00Z",
  "owner_id": "usr_123456789",
  "toc_items": [],
  "published": false,
  "collaborators": [],
  "owner": {
    "id": "usr_123456789",
    "name": "Jane Doe",
    "email": "jane@example.com"
  }
}
```

### Update Book Metadata

Updates the metadata of a specific book.

**Endpoint:** `PUT /books/{book_id}`

**Rate Limit:** 15 requests per 60 seconds

**Path Parameters:**
- `book_id`: The unique identifier of the book

**Request Body:**

```json
{
  "title": "Updated Book Title",
  "description": "A revised description of the book",
  "published": true
}
```

**Optional Fields:** (include only the fields you want to update)
- `title`: String (1-100 characters)
- `subtitle`: String (up to 200 characters)
- `description`: String (up to 5000 characters)
- `genre`: String (up to 100 characters)
- `target_audience`: String (up to 100 characters)
- `cover_image_url`: String (valid URL)
- `metadata`: Object (for custom metadata)
- `published`: Boolean

**Response:** `200 OK`

```json
{
  "id": "60a12b456c89d1234567890a",
  "title": "Updated Book Title",
  "subtitle": "A Journey Through Words",
  "description": "A revised description of the book",
  "genre": "Non-fiction",
  "target_audience": "Writers and aspiring authors",
  "cover_image_url": "https://example.com/cover.jpg",
  "metadata": { "draft_version": "1.0" },
  "created_at": "2025-05-22T10:30:00Z",
  "updated_at": "2025-05-22T11:45:00Z",
  "owner_id": "usr_123456789",
  "toc_items": [],
  "published": true,
  "collaborators": []
}
```

### Delete a Book

Deletes a specific book.

**Endpoint:** `DELETE /books/{book_id}`

**Rate Limit:** 5 requests per 60 seconds

**Path Parameters:**
- `book_id`: The unique identifier of the book

**Response:** `204 No Content`

## Error Responses

### 400 Bad Request

Returned when the request contains invalid data.

```json
{
  "detail": "Invalid book ID format"
}
```

### 401 Unauthorized

Returned when authentication is missing or invalid.

```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden

Returned when the user does not have access to the requested book.

```json
{
  "detail": "You don't have access to this book"
}
```

### 404 Not Found

Returned when the requested book does not exist.

```json
{
  "detail": "Book not found"
}
```

### 429 Too Many Requests

Returned when the rate limit is exceeded.

```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error

Returned when an unexpected error occurs on the server.

```json
{
  "detail": "Failed to retrieve book: [error details]"
}
```
