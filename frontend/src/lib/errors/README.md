# Error Handler Utility - TDD Implementation (Task 4)

## Overview

This error handler provides unified error handling with automatic retry logic, exponential backoff, and toast notification integration.

## Features

- **Error Classification**: Automatically categorizes errors (network, validation, auth, server, unknown)
- **Automatic Retry**: Retries transient errors (network, 5xx) with exponential backoff
- **Exponential Backoff**: 1s, 2s, 4s delay pattern (up to 30s max)
- **Max Retry Limit**: Default 3 attempts before giving up
- **Toast Integration**: Seamless integration with UI toast notifications
- **TypeScript Support**: Full type safety with exported types

## Quick Start

### Basic Usage with Toast Notifications

```typescript
import { handleApiError } from '@/lib/errors';
import { useToast } from '@/components/ui/use-toast';

function MyComponent() {
  const { toast } = useToast();

  const fetchData = async () => {
    try {
      const result = await handleApiError(
        () => fetch('/api/books').then(r => r.json()),
        toast
      );
      // Handle success
      console.log(result);
    } catch (error) {
      // Error already shown in toast, handle cleanup if needed
    }
  };
}
```

### Custom Error Messages

```typescript
await handleApiError(
  () => deleteBook(bookId),
  toast,
  { customMessage: 'Failed to delete book. Please try again.' }
);
```

### Manual Error Handler Configuration

```typescript
import { ErrorHandler } from '@/lib/errors';

const handler = new ErrorHandler({
  maxRetries: 5,        // Override default 3
  baseDelay: 2000,      // Start with 2s instead of 1s
  maxDelay: 60000       // Max 60s instead of 30s
});

const result = await handler.execute(() => apiCall());
```

## API Reference

### `handleApiError<T>(operation, toast, options?): Promise<T>`

High-level API for handling errors with automatic retries and toast notifications.

**Parameters:**
- `operation: () => Promise<T>` - The async operation to execute
- `toast: ToastFunction` - Toast notification function from useToast hook
- `options?: { customMessage?: string }` - Optional custom error message

**Returns:** `Promise<T>` - Result of the operation

**Throws:** The original error after all retries are exhausted

### `ErrorHandler` Class

**Constructor:**
```typescript
new ErrorHandler(config?: {
  maxRetries?: number;    // Default: 3
  baseDelay?: number;     // Default: 1000ms
  maxDelay?: number;      // Default: 30000ms
})
```

**Methods:**
- `execute<T>(operation: () => Promise<T>): Promise<T>` - Execute with retry logic

### Utility Functions

#### `classifyError(error: unknown): ErrorType`

Classify an error into one of: NETWORK, VALIDATION, AUTH, SERVER, UNKNOWN

```typescript
const errorType = classifyError(error);
```

#### `shouldRetry(errorType: ErrorType, attemptCount: number, maxRetries?: number): boolean`

Determine if an error should be retried.

```typescript
if (shouldRetry(ErrorType.NETWORK, 0)) {
  // Retry logic
}
```

#### `calculateBackoff(attempt: number, baseDelay?: number, maxDelay?: number): number`

Calculate exponential backoff delay in milliseconds.

```typescript
const delay = calculateBackoff(2); // Returns 4000ms (4 seconds)
```

#### `extractErrorMessage(error: unknown): string`

Extract a user-friendly error message from various error formats.

```typescript
const message = extractErrorMessage(error);
toast({ title: 'Error', description: message });
```

## Error Classification

| Error Type | HTTP Status | Retry? | Description |
|------------|-------------|--------|-------------|
| `NETWORK` | N/A | ✅ Yes | Network failures, fetch errors |
| `VALIDATION` | 400 | ❌ No | Invalid input data |
| `AUTH` | 401, 403 | ❌ No | Authentication/authorization failures |
| `SERVER` | 5xx, 429 | ✅ Yes | Server errors, rate limiting |
| `UNKNOWN` | Other | ❌ No | Unclassified errors |

## Retry Behavior

### Retryable Errors
- Network errors (TypeError: Failed to fetch)
- Server errors (500, 502, 503, 504)
- Rate limiting (429)

### Non-Retryable Errors
- Validation errors (400)
- Authentication errors (401, 403)
- Other client errors (4xx except 429)
- Unknown errors

### Backoff Pattern

| Attempt | Delay |
|---------|-------|
| 1 | 1 second |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 4 | 8 seconds |
| 5 | 16 seconds |
| Max | 30 seconds |

Formula: `delay = min(baseDelay * 2^attempt, maxDelay)`

## Examples

### Example 1: Simple API Call with Retry

```typescript
import { handleApiError } from '@/lib/errors';
import { useToast } from '@/components/ui/use-toast';

async function createBook(data: BookData) {
  const { toast } = useToast();

  const result = await handleApiError(
    () => fetch('/api/books', {
      method: 'POST',
      body: JSON.stringify(data)
    }).then(r => r.json()),
    toast
  );

  return result;
}
```

### Example 2: Custom Retry Configuration

```typescript
import { ErrorHandler } from '@/lib/errors';

// More aggressive retry for critical operations
const criticalHandler = new ErrorHandler({
  maxRetries: 5,
  baseDelay: 500,
  maxDelay: 10000
});

const result = await criticalHandler.execute(() =>
  fetch('/api/critical-operation').then(r => r.json())
);
```

### Example 3: Manual Error Classification

```typescript
import { classifyError, ErrorType, extractErrorMessage } from '@/lib/errors';

try {
  await someOperation();
} catch (error) {
  const errorType = classifyError(error);
  const message = extractErrorMessage(error);

  if (errorType === ErrorType.AUTH) {
    // Redirect to login
    router.push('/login');
  } else {
    // Show error message
    toast({ title: 'Error', description: message });
  }
}
```

## Testing

The error handler includes comprehensive test coverage (43 tests):

```bash
# Run tests
npm test errorHandler.test.ts

# Run with coverage
npm run test:coverage
```

### Test Coverage Areas

- Error classification for all error types
- Retry logic for transient vs permanent errors
- Exponential backoff timing validation
- Max retry limit enforcement
- Error message extraction from various formats
- Toast notification integration
- Real-world API error scenarios

## Integration with Existing System

This TDD implementation (`errorHandler.ts`) coexists with the existing error handling framework. Both can be used:

```typescript
// Existing system (more comprehensive)
import { handleApiCall } from '@/lib/errors';

// TDD implementation (simpler, focused)
import { handleApiError } from '@/lib/errors';
```

Choose based on your needs:
- Use `handleApiCall` for complex error handling with logging and metrics
- Use `handleApiError` for simple retry logic with toast notifications

## Development Notes

- Implemented using TDD methodology (RED-GREEN-REFACTOR)
- 100% test pass rate (43/43 tests passing)
- Compatible with existing error handling infrastructure
- Designed for easy integration with React hooks and components
- TypeScript strict mode compatible

## Related Files

- Implementation: `errorHandler.ts`
- Tests: `errorHandler.test.ts`
- Exports: `index.ts`
- Types: See inline TypeScript types in `errorHandler.ts`
