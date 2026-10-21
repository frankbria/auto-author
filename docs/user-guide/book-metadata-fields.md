# Book Metadata Fields Documentation

This document outlines all metadata fields available for books in the Auto Author application, their requirements, and usage guidelines.

## Core Metadata Fields

| Field Name | Required | Data Type | Constraints | Description |
|------------|----------|-----------|------------|-------------|
| `title` | Yes | String | Min: 1 char, Max: 100 chars | The main title of your book. This is displayed prominently and is required for all books. |
| `subtitle` | No | String | Max: 200 chars (frontend), 255 chars (backend) | An optional secondary title that provides additional context or elaborates on the main title. |
| `description` | No | String | Max: 1000 chars (frontend), 5000 chars (backend) | A detailed summary of your book's content. The frontend enforces a 1000 character limit while the backend allows up to 5000 characters for API compatibility. |
| `genre` | No | String | Max: 50 chars (frontend), 100 chars (backend) | The literary category or style of your book. Select from predefined options or specify a custom genre. |
| `target_audience` | No | String | Max: 100 chars | The intended reader demographic for your book, such as "Young Adult" or "Academic". |
| `cover_image_url` | n/a | String | Read-only | The stored cover image URL. It is not a form field or a request field (#797): only `POST /books/{book_id}/cover-image` writes it. |

## Predefined Genre Options

The application provides the following predefined genre options:

- Fiction
- Non-Fiction
- Fantasy
- Science Fiction
- Mystery
- Romance
- Other

## Predefined Target Audience Options

The application provides the following predefined target audience options:

- Children
- Young Adult
- Adult
- General
- Academic
- Professional

## Advanced Metadata

In addition to the core fields, the book model supports a flexible `metadata` field that can store additional information as key-value pairs. This field is available for extending the book's metadata without changing the core data structure.

## Internal Fields

The following fields are managed by the system and cannot be directly edited:

| Field Name | Description |
|------------|-------------|
| `id` | Unique identifier for the book |
| `created_at` | Timestamp when the book was created |
| `updated_at` | Timestamp when the book was last updated |
| `owner_id` | Identifier of the user who owns the book |
| `published` | Boolean indicating if the book is published |
| `toc_items` | Array of table of contents items |
| `collaborators` | Array of users who have access to the book |

## Validation Rules

- **Title** must not be empty and cannot exceed 100 characters
- **Subtitle** is optional but cannot exceed 200 characters when provided
- **Description** is optional but cannot exceed 1000 characters in the frontend (5000 characters in the backend) when provided
- **Genre** is optional but cannot exceed 50 characters in the frontend (100 characters in the backend) when provided
- **Target Audience** is optional but cannot exceed 100 characters when provided
- **Cover Image URL** is optional but must be a valid URL format when provided

## Validation Error Messages

The form validates with Zod (`frontend/src/lib/schemas/bookSchema.ts`) and shows these messages inline, below the field:

| Field | Rule | Message |
|-------|------|---------|
| Title | Required | "Title is required" |
| Title | Max 100 chars | "Title must be 100 characters or less" |
| Subtitle | Max 200 chars | "Subtitle must be 200 characters or less" |
| Description | Max 1000 chars | "Description must be 1000 characters or less" |
| Genre | Max 50 chars | "Genre must be 50 characters or less" |
| Target audience | Max 100 chars | "Target audience must be 100 characters or less" |

The backend validates again with Pydantic (`backend/app/schemas/book.py`) and refuses a bad request with `422 Unprocessable Entity`. API clients are limited by these backend maximums: title 1-100 chars, subtitle 255, description 5000, genre 100, target audience 100. The response body is:

```json
{
  "detail": "Validation error",
  "errors": [{"type": "string_too_long", "loc": ["body", "title"], "msg": "String should have at most 100 characters"}],
  "error_summary": "body -> title: String should have at most 100 characters"
}
```

A missing title reports `Field required`, and an empty one `String should have at least 1 character`. The offending input is never echoed back. A book that does not exist or belongs to someone else is answered `404`, and a missing session `401` (see [Authentication](auth.md#api-authentication-errors)).

## Auto-Save Behavior

Book metadata fields feature auto-save functionality. Changes are automatically saved after 600ms of inactivity (debounce period) after editing a field, provided that all validation rules are satisfied.
