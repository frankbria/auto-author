# AI Service Error Handling

Comprehensive error handling system for AI service operations with cached content fallback, rate limiting, and retry support.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Usage](#usage)
- [Error Types](#error-types)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Best Practices](#best-practices)

## Overview

The AI error handling system provides a robust, user-friendly way to handle errors from AI service operations. It includes:

- Automatic error classification and handling
- Cached content fallback when AI services are unavailable
- Rate limit detection with countdown timers
- Network error retry support
- User-friendly error messages and notifications
- Comprehensive test coverage

## Features

### 1. Cached Content Fallback

When AI services are temporarily unavailable, the system automatically returns cached content from previous successful operations:

```typescript
const result = await bookClient.generateQuestionsWithErrorHandling(
  bookId,
  retryCallback
);

if (isFromCache(result)) {
  // Using cached content - show warning to user
  console.log('Using cached questions:', result.data.questions);
}
```

### 2. Rate Limit Handling

Rate limit errors display a countdown timer showing when the user can retry:

- Shows estimated wait time (e.g., "Retry in 2:30")
- Countdown updates in real-time
- "Retry Now" button appears when timer reaches zero
- User confirmation before retrying during rate limit period

### 3. Network Error Retry

Network errors show a retry button with appropriate messaging:

- Automatic detection of network errors
- Clear error messages ("Check your internet connection")
- Retry button for immediate retry
- Suggested actions displayed to user

### 4. User-Friendly Notifications

All errors show contextual notifications with:

- Clear, non-technical error messages
- Suggested actions for resolution
- Visual indicators (icons, colors, badges)
- Automatic dismissal or manual close options

## Architecture

### Components

```
frontend/src/
├── lib/
│   ├── api/
│   │   ├── aiErrorHandler.ts          # Core error handling logic
│   │   └── bookClient.ts               # API client with error-handling methods
│   └── errors/
│       └── types.ts                    # Error type definitions
├── components/
│   ├── errors/
│   │   └── ErrorNotification.tsx       # UI components for error display
│   └── examples/
│       └── AIErrorHandlingExample.tsx  # Usage examples
└── tests/
    └── e2e/
        └── ai-error-handling.spec.ts   # E2E tests
```

### Flow Diagram

```
User Action
    ↓
API Call (with error handling wrapper)
    ↓
AI Service
    ↓
Success? ──→ Yes ──→ Return fresh data
    ↓
    No
    ↓
Check for cached content
    ↓
Cached? ──→ Yes ──→ Return cached data + show warning
    ↓
    No
    ↓
Classify error type
    ↓
Show appropriate notification
    ↓
Provide retry option (if applicable)
```

## Usage

### Basic Usage

Use the error-handling versions of API methods:

```typescript
import bookClient from '@/lib/api/bookClient';
import { isFromCache } from '@/lib/api/aiErrorHandler';

async function generateQuestions(bookId: string) {
  const result = await bookClient.generateQuestionsWithErrorHandling(
    bookId,
    () => generateQuestions(bookId) // Retry callback
  );

  // Check if we got cached content
  if (isFromCache(result)) {
    setQuestions(result.data.questions);
    setIsFromCache(true);
    return;
  }

  // Check if we got fresh data
  if (result.data) {
    setQuestions(result.data.questions);
    setIsFromCache(false);
    return;
  }

  // Error occurred - notification already shown
  console.error('Failed:', result.error);
}
```

### Advanced Usage

#### Custom Retry Logic

```typescript
const result = await bookClient.generateTocWithErrorHandling(
  bookId,
  questionResponses,
  async () => {
    // Custom retry logic
    await refreshAuthToken();
    await generateTOC();
  }
);
```

#### Handling Multiple Error States

```typescript
function MyComponent() {
  const [isLoading, setIsLoading] = useState(false);
  const [isFromCache, setIsFromCache] = useState(false);
  const [data, setData] = useState(null);

  async function loadData() {
    setIsLoading(true);

    const result = await bookClient.generateQuestionsWithErrorHandling(
      bookId,
      loadData
    );

    setIsLoading(false);

    if (isFromCache(result)) {
      setData(result.data);
      setIsFromCache(true);
    } else if (result.data) {
      setData(result.data);
      setIsFromCache(false);
    }
  }

  return (
    <div>
      {isFromCache && (
        <Alert variant="warning">
          <Database className="h-4 w-4" />
          Using cached content
        </Alert>
      )}
      {/* Render data */}
    </div>
  );
}
```

## Error Types

### AI_SERVICE

Special error type for AI service operations with enhanced handling:

- **Status Code**: 429 (Rate Limit)
- **Severity**: Medium
- **Retryable**: Yes
- **Features**: Countdown timer, cached content fallback

### TRANSIENT

Temporary errors that may succeed on retry:

- **Examples**: Network errors, timeouts, service unavailable
- **Severity**: Medium
- **Retryable**: Yes

### PERMANENT

Errors requiring user action:

- **Examples**: Validation errors, authentication failures
- **Severity**: High
- **Retryable**: No

### SYSTEM

Infrastructure errors requiring technical support:

- **Examples**: Internal server errors
- **Severity**: Critical
- **Retryable**: No (usually)

## API Reference

### `handleAIServiceError<T>(error, onRetry?)`

Main error handling function.

**Parameters:**
- `error: unknown` - The error object
- `onRetry?: () => void | Promise<void>` - Optional retry callback

**Returns:** `Promise<AIServiceResult<T>>`

```typescript
interface AIServiceResult<T> {
  data?: T;              // Successful or cached data
  fromCache?: boolean;   // True if data is from cache
  error?: string;        // Error message
  retryAfter?: number;   // Seconds until retry allowed
  canRetry?: boolean;    // Whether retry is allowed
}
```

### `isFromCache<T>(result)`

Type guard to check if result is from cache.

**Parameters:**
- `result: AIServiceResult<T>` - The result to check

**Returns:** `boolean`

### `createRetryHandler(retryFn, retryAfter?)`

Creates a retry handler with countdown support.

**Parameters:**
- `retryFn: () => void | Promise<void>` - Retry function
- `retryAfter?: number` - Seconds to wait before retry

**Returns:** `() => void`

### BookClient Methods

All AI methods have error-handling versions:

- `analyzeSummaryWithErrorHandling(bookId, onRetry?)`
- `generateQuestionsWithErrorHandling(bookId, onRetry?)`
- `generateTocWithErrorHandling(bookId, questionResponses, onRetry?)`
- `generateChapterQuestionsWithErrorHandling(bookId, chapterId, options, onRetry?)`
- `generateChapterDraftWithErrorHandling(bookId, chapterId, data, onRetry?)`

## Testing

### Unit Tests

Located in: `frontend/src/lib/api/__tests__/aiErrorHandler.test.ts`

Run with:
```bash
npm test aiErrorHandler
```

Coverage:
- Error classification
- Cached content handling
- Rate limit detection
- Network error handling
- Retry logic
- Message extraction

### E2E Tests

Located in: `frontend/tests/e2e/ai-error-handling.spec.ts`

Run with:
```bash
npx playwright test ai-error-handling
```

Tests:
- Rate limit with countdown timer
- Cached content display
- Network error retry
- Multiple concurrent errors
- Error persistence across navigation
- Different error types

## Best Practices

### 1. Always Use Error-Handling Methods

```typescript
// ✅ Good
const result = await bookClient.generateQuestionsWithErrorHandling(bookId, retry);

// ❌ Bad (no error handling)
const result = await bookClient.generateQuestions(bookId);
```

### 2. Provide Retry Callbacks

```typescript
// ✅ Good - user can retry
const result = await bookClient.generateQuestionsWithErrorHandling(
  bookId,
  () => loadQuestions()
);

// ⚠️ OK but not ideal - no retry option
const result = await bookClient.generateQuestionsWithErrorHandling(bookId);
```

### 3. Check for Cached Content

```typescript
// ✅ Good - handle cached content appropriately
if (isFromCache(result)) {
  showCachedContentWarning();
  setData(result.data);
}

// ❌ Bad - doesn't distinguish cached from fresh
if (result.data) {
  setData(result.data);
}
```

### 4. Show Loading States

```typescript
// ✅ Good - clear loading state
setIsLoading(true);
const result = await bookClient.generateQuestionsWithErrorHandling(bookId);
setIsLoading(false);

// ❌ Bad - no loading feedback
const result = await bookClient.generateQuestionsWithErrorHandling(bookId);
```

### 5. Handle All Result States

```typescript
// ✅ Good - handles all cases
if (isFromCache(result)) {
  // Handle cached content
} else if (result.data) {
  // Handle fresh data
} else if (result.error) {
  // Handle error (notification already shown)
}

// ❌ Bad - doesn't check for errors
if (result.data) {
  setData(result.data);
}
```

### 6. Provide Context in Notifications

The error handler automatically shows notifications, but you can add additional context:

```typescript
const result = await bookClient.generateQuestionsWithErrorHandling(bookId);

if (!result.data && result.error) {
  // Notification already shown, but you can log for debugging
  console.error('Failed to generate questions for book:', bookId, result.error);
}
```

### 7. Test Error Scenarios

Always test:
- Rate limit errors
- Network failures
- Cached content fallback
- Retry functionality
- Multiple concurrent errors

## Examples

See `frontend/src/components/examples/AIErrorHandlingExample.tsx` for complete working examples:

- TOC Questions Generation
- Chapter Draft Generation
- Summary Analysis

## Migration Guide

### Updating Existing Components

**Before:**
```typescript
try {
  const response = await bookClient.generateQuestions(bookId);
  setQuestions(response.questions);
} catch (error) {
  toast.error('Failed to generate questions');
}
```

**After:**
```typescript
const result = await bookClient.generateQuestionsWithErrorHandling(
  bookId,
  () => generateQuestions()
);

if (isFromCache(result)) {
  setQuestions(result.data.questions);
  setIsFromCache(true);
} else if (result.data) {
  setQuestions(result.data.questions);
  setIsFromCache(false);
}
// Error notification automatically shown by error handler
```

## Troubleshooting

### Error notifications not showing

- Ensure you're importing from the correct location
- Check that `showErrorNotification` is not mocked in tests
- Verify toast system is properly configured

### Cached content not appearing

- Check backend sends `cached_content_available: true`
- Verify `cached_content` field is populated
- Ensure `isFromCache()` type guard is used correctly

### Countdown timer not working

- Verify `estimated_retry_after` is sent from backend
- Check that `RetryCountdown` component is rendered
- Ensure timer cleanup on unmount

### Retry not working

- Pass retry callback to error-handling method
- Check that error is marked as retryable
- Verify network/service is actually available on retry

## Support

For issues or questions:

1. Check E2E tests for usage examples
2. Review example components in `frontend/src/components/examples/`
3. See unit tests for detailed behavior documentation
4. Contact the development team

## Changelog

### Version 1.0.0 (2025-01-XX)

- Initial implementation
- Added `AI_SERVICE` error type
- Created `aiErrorHandler.ts` with comprehensive error handling
- Enhanced `ErrorNotification.tsx` with countdown and cached content support
- Added error-handling methods to `bookClient.ts`
- Created E2E and unit tests
- Added example components
- Created documentation
