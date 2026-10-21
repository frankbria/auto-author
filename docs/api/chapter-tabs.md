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
- **POST** `/api/v1/books/{book_id}/chapters/tab-state`
- Body: `{ active_chapter_id, open_tab_ids, tab_order }`
- Saves the signed-in user's tab state for this book. `open_tab_ids` holds at most 20 ids and no duplicates; `tab_order` has no duplicates and must contain every id in `open_tab_ids`, otherwise the request is refused with `422`.

### Get Tab State
- **GET** `/api/v1/books/{book_id}/chapters/tab-state`
- Returns: `{ book_id, tab_state: { active_chapter_id, open_tab_ids, tab_order, last_updated } }` for the signed-in user, or `tab_state: null` when none was saved. The user comes from the session; there is no `user_id` parameter.

### Bulk Update Chapter Status
- **PATCH** `/api/v1/books/{book_id}/chapters/bulk-status`
- Body: `{ chapter_ids: string[], status: 'draft'|'in-progress'|'completed'|'published' }`
- Updates the status of multiple chapters at once.

### Chapter Access Logging
- **POST** `/api/v1/chapter-access`
- Body: `{ user_id, book_id, chapter_id, access_type, ... }`
- Logs chapter access for analytics and tab persistence.

---
## Tab State Persistence

Tab state (open tabs, order, active tab) is kept in two places:

- **Browser**: `localStorage`, key `tabState_{book_id}`, with a `last_updated` timestamp.
- **Backend**: the two tab-state endpoints above, stored per user and book.

`useChapterTabs` saves both about one second after the state changes, and a failed save is logged but not shown to the user. On load it reads both, uses the one with the newer `last_updated`, and falls back to the browser copy if the backend call fails. The saved state is then reconciled with the chapters the book has now (`lib/utils/reconcileTabState.ts`): chapters that no longer exist are dropped, chapters missing from the saved order are appended, and the active chapter is the one named in a `?chapter=` link, else the saved one, else the first open tab.

## Frontend Component Map

All under `frontend/src/`.

| Piece | File | Role |
|-------|------|------|
| `ChapterTabs` | `components/chapters/ChapterTabs.tsx` | Entry point, used on the book page. Wires the hooks to `TabBar` (or `MobileChapterTabs` at 768px and below) and `TabContent`, creates and deletes chapters, handles Ctrl+1 to Ctrl+9, and swipe navigation on mobile |
| `TabBar` | `components/chapters/TabBar.tsx` | Renders the tabs in `tab_order`, drag-and-drop reordering (`@hello-pangea/dnd`), scrolling and the overflow menu (`TabOverflowMenu.tsx`) |
| `ChapterTab` | `components/chapters/ChapterTab.tsx` | One tab: title, status indicator (`statusConfig`), close button, Enter/Space to select |
| `TabContent` | `components/chapters/TabContent.tsx` | Shows the editor for the active chapter |
| `TabContextMenu` | `components/chapters/TabContextMenu.tsx` | Chapter options menu: edit, set status, delete (preview and duplicate only when a handler is passed) |
| `useChapterTabs` | `hooks/useChapterTabs.ts` | Tab state and actions (`setActiveChapter`, `reorderTabs`, `closeTab`, `updateChapterStatus`, `saveTabState`, `refreshChapters`). Loads chapters from the TOC, falling back to the metadata endpoint |
| `useTocSync` | `hooks/useTocSync.ts` | Calls `refreshChapters` when the TOC changes: a `tocUpdated` window event, a `toc-updated-{book_id}` localStorage key for other browser tabs, and optional polling (off by default). The TOC editor fires it with `triggerTocUpdateEvent` after a save |

Types are in `types/chapter-tabs.ts`.

## Extending

- **Tab actions**: add an entry to `TabContextMenu.tsx` and pass its handler from `ChapterTabs.tsx`.
- **Statuses**: update `statusConfig` in `ChapterTab.tsx` and the `ChapterStatus` enum in `backend/app/schemas/book.py` together.
- **Keyboard shortcuts**: the only handler is the `keydown` effect in `ChapterTabs.tsx`.
- **Other features**: read or change tab state through `useChapterTabs`, and call `triggerTocUpdateEvent(bookId)` after anything that changes the chapter list.

For TOC endpoints, see [toc.md](toc.md).
