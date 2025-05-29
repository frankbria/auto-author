# API Endpoints for Chapter Tab Operations

## Overview
These endpoints support all tab-related operations, including loading chapters, updating tab state, and managing chapter metadata.

## Endpoints

### Get All Chapters with Metadata
- **GET** `/api/v1/books/{book_id}/chapters/metadata`
- Returns: List of chapters with status, word count, last modified, etc.

### Get Chapter Content
- **GET** `/api/v1/books/{book_id}/chapters/{chapter_id}/content`
- Returns: Chapter content for the specified chapter.

### Update Tab State (Persistence)
- **POST** `/api/v1/books/{book_id}/tab-state`
- Body: `{ active_chapter_id, open_tab_ids, tab_order, session_id? }`
- Saves the user's current tab state for persistence across sessions.

### Get Tab State
- **GET** `/api/v1/books/{book_id}/tab-state?user_id={user_id}`
- Returns: The last saved tab state for the user and book.

### Bulk Update Chapter Status
- **PATCH** `/api/v1/books/{book_id}/chapters/bulk-status`
- Body: `{ chapter_ids: string[], status: 'draft'|'in-progress'|'completed' }`
- Updates the status of multiple chapters at once.

### Chapter Access Logging
- **POST** `/api/v1/chapter-access`
- Body: `{ user_id, book_id, chapter_id, access_type, ... }`
- Logs chapter access for analytics and tab persistence.

---
For full details, see `api-toc-endpoints.md` and backend API documentation.
