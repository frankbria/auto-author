# Book Metadata Fields Documentation

This document outlines all metadata fields available for books in the Auto Author application, their requirements, and usage guidelines.

## Core Metadata Fields

| Field Name | Required | Data Type | Constraints | Description |
|------------|----------|-----------|------------|-------------|
| `title` | Yes | String | Min: 1 char, Max: 100 chars | The main title of your book. This is displayed prominently and is required for all books. |
| `subtitle` | No | String | Max: 200 chars | An optional secondary title that provides additional context or elaborates on the main title. |
| `description` | No | String | Max: 1000 chars (frontend), 5000 chars (backend) | A detailed summary of your book's content. The frontend enforces a 1000 character limit while the backend allows up to 5000 characters for API compatibility. |
| `genre` | No | String | Max: 50 chars (frontend), 100 chars (backend) | The literary category or style of your book. Select from predefined options or specify a custom genre. |
| `target_audience` | No | String | Max: 100 chars | The intended reader demographic for your book, such as "Young Adult" or "Academic". |
| `cover_image_url` | No | String | Must be a valid URL, Max: 300 chars (frontend), 2083 chars (backend) | A link to the book's cover image. Must be a valid URL pointing to an accessible image file. |

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

## Auto-Save Behavior

Book metadata fields feature auto-save functionality. Changes are automatically saved after 600ms of inactivity (debounce period) after editing a field, provided that all validation rules are satisfied.
