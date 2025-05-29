# Tab State Persistence and Session Management

## Overview
Tab state persistence ensures that your open tabs, their order, and the active tab are restored across sessions and devices. This is achieved through a combination of localStorage and backend API endpoints.

## How It Works
- **Local Persistence**: Tab state (open tabs, order, active tab) is saved to localStorage on every change.
- **Backend Persistence**: When logged in, tab state is also saved to the backend via the `/tab-state` API endpoint.
- **Session Restoration**: On page load, the app restores tab state from localStorage and, if available, from the backend for the current user and book.
- **Cross-Device Sync**: Backend persistence allows tab state to sync across devices and browsers when logged in.

## API Endpoints
- **POST** `/api/v1/books/{book_id}/tab-state` — Save tab state
- **GET** `/api/v1/books/{book_id}/tab-state?user_id={user_id}` — Retrieve tab state

## Session Management
- Tab state is associated with user sessions. Logging out or switching users resets the tab state to the default for the new session.
- Session ID is used to distinguish between different browser sessions if needed.

## Troubleshooting
- If tab state does not persist, check login status and browser storage settings.

---
