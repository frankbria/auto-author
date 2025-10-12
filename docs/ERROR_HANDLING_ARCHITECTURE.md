# Error Handling Architecture

**Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: 2025-10-12

## Overview

The unified error handling framework provides consistent error classification, automatic retry logic, and user-friendly notifications across the entire application. It replaces ad-hoc try-catch blocks with a systematic approach to error management.

## Core Principles

1. **Error Classification**: All errors categorized as Transient, Permanent, or System
2. **Automatic Recovery**: Transient errors retry automatically with exponential backoff
3. **User-Friendly Messages**: Clear, actionable error messages for all scenarios
4. **Correlation Tracking**: Unique IDs for error tracking and support
5. **Graceful Degradation**: System remains functional despite errors

## Architecture Components

### 1. Error Types (`frontend/src/lib/errors/types.ts`)

#### Error Classification
```typescript
enum ErrorType {
  TRANSIENT = 'transient',  // Temporary, retry possible
  PERMANENT = 'permanent',  // User action required
  SYSTEM = 'system',        // Infrastructure issue
}
```

#### Error Severity
```typescript
enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}
```

#### Classified Error Structure
```typescript
interface ClassifiedError {
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;              // User-friendly message
  details?: string;             // Technical details
  statusCode?: number;          // HTTP status if applicable
  retryable: boolean;
  retryConfig?: RetryConfig;
  correlationId: string;        // Unique tracking ID
  timestamp: Date;
  originalError?: Error;
  fieldErrors?: Record<string, string>;
  suggestedActions?: string[];
}
```

#### Retry Configuration
```typescript
interface RetryConfig {
  maxAttempts: number;          // Default: 3
  baseDelay: number;            // Default: 2000ms
  maxDelay: number;             // Default: 8000ms
  useExponentialBackoff: boolean; // Default: true
}
```

### 2. Error Classification (`frontend/src/lib/errors/classifier.ts`)

Automatically classifies errors based on:
- HTTP status codes
- Error message patterns
- Error type detection

#### HTTP Status Mapping
```typescript
const HTTP_STATUS_TO_ERROR_TYPE: Record<number, ErrorType> = {
  // Client errors (4xx) - Permanent
  400: ErrorType.PERMANENT,  // Bad Request
  401: ErrorType.PERMANENT,  // Unauthorized
  403: ErrorType.PERMANENT,  // Forbidden
  404: ErrorType.PERMANENT,  // Not Found
  409: ErrorType.PERMANENT,  // Conflict
  422: ErrorType.PERMANENT,  // Validation Error
  429: ErrorType.TRANSIENT,  // Rate Limit

  // Server errors (5xx)
  500: ErrorType.SYSTEM,     // Internal Server Error
  502: ErrorType.TRANSIENT,  // Bad Gateway
  503: ErrorType.TRANSIENT,  // Service Unavailable
  504: ErrorType.TRANSIENT,  // Gateway Timeout
};
```

#### Classification Logic
```typescript
export function classifyError(
  error: unknown,
  context?: string
): ClassifiedError {
  // 1. Detect error type (API, Network, Timeout, Validation)
  // 2. Map to error classification
  // 3. Extract field-specific errors
  // 4. Generate user-friendly message
  // 5. Provide suggested actions
  // 6. Assign correlation ID
}
```

### 3. Error Handler (`frontend/src/lib/errors/handler.ts`)

Core wrapper function for all API calls with automatic retry logic.

#### handleApiCall Function
```typescript
async function handleApiCall<T>(
  apiCall: () => Promise<T>,
  options?: HandleApiCallOptions
): Promise<ErrorHandlerResult<T>> {
  // 1. Execute API call
  // 2. On error: Classify error
  // 3. If retryable: Calculate delay and retry
  // 4. If not retryable: Return error
  // 5. Invoke callbacks (onRetry, onSuccess, onFailure)
  // 6. Return result with success/error/attempts
}
```

#### Retry Logic
```
Attempt 1: Execute call
  ↓ (fail - transient error)
Wait 2s (baseDelay * 2^0)
  ↓
Attempt 2: Execute call
  ↓ (fail - transient error)
Wait 4s (baseDelay * 2^1)
  ↓
Attempt 3: Execute call
  ↓ (fail - transient error)
Wait 8s (baseDelay * 2^2)
  ↓
Attempt 4: Execute call
  ↓ (fail or success)
Return result
```

#### Exponential Backoff Formula
```typescript
delay = Math.min(
  baseDelay * Math.pow(2, attemptNumber),
  maxDelay
);
```

### 4. Error Notifications (`frontend/src/components/errors/ErrorNotification.tsx`)

User-facing error display components integrated with toast system.

#### showErrorNotification
```typescript
showErrorNotification(error: ClassifiedError, options?: {
  onRetry?: () => void;
  onDismiss?: () => void;
  duration?: number;
});
```

#### Notification Templates

**Transient Error (with retry)**:
```
⚠️ Network connection issue
Please check your internet connection.

[Retry Button]

Duration: 5 seconds
```

**Permanent Error (validation)**:
```
🔴 Please correct the highlighted fields
- email: Invalid email format
- password: Must be at least 8 characters

What you can do:
• Review the form for errors
• Ensure all required fields are filled

Duration: 7 seconds
```

**System Error (with correlation ID)**:
```
⚠️ Something went wrong
Our team has been notified.

Reference ID: abc123-def456

What you can do:
• Try refreshing the page
• Contact support with the reference ID above

Duration: 10 seconds
```

#### Recovery Notification
```typescript
showRecoveryNotification(message: string, attempts: number);
```

Example:
```
✅ Export completed
Succeeded after 3 attempts

Duration: 3 seconds
```

## Integration Patterns

### Basic Usage
```typescript
import { handleApiCall, showErrorNotification } from '@/lib/errors';

const result = await handleApiCall(
  () => bookClient.exportPDF(bookId),
  {
    context: 'Export PDF',
    onRetry: (attempt) => {
      toast.info(`Retrying (attempt ${attempt})...`);
    },
  }
);

if (result.success) {
  // Handle success
  processData(result.data);
} else {
  // Show error notification
  showErrorNotification(result.error, {
    onRetry: handleRetry,
  });
}
```

### With Loading States
```typescript
const [isLoading, setIsLoading] = useState(false);

const handleAction = async () => {
  setIsLoading(true);

  const result = await handleApiCall(
    () => apiCall(),
    {
      context: 'Save Data',
      onRetry: (attempt) => {
        setProgress(0); // Reset progress on retry
      },
    }
  );

  setIsLoading(false);

  if (result.success) {
    toast.success('Data saved');
  } else {
    showErrorNotification(result.error);
  }
};
```

### Custom Retry Configuration
```typescript
const result = await handleApiCall(
  () => complexOperation(),
  {
    retryConfig: {
      maxAttempts: 5,        // More attempts
      baseDelay: 3000,       // Longer delays
      maxDelay: 15000,
      useExponentialBackoff: true,
    },
  }
);
```

### Manual Retry
```typescript
import { manualRetry } from '@/lib/errors';

const handleRetry = async () => {
  const result = await manualRetry(
    () => apiCall(),
    () => toast.info('Retrying...')
  );

  // Process result
};
```

### Create Retry Wrapper
```typescript
import { createRetryWrapper } from '@/lib/errors';

// Create wrapped version of API method
const exportPDFWithRetry = createRetryWrapper(
  bookClient.exportPDF,
  {
    context: 'Export PDF',
    retryConfig: { maxAttempts: 5 },
  }
);

// Use wrapped method
const result = await exportPDFWithRetry(bookId, options);
```

## Error Flow Diagrams

### Classification Flow
```
Error Occurs
  ↓
Is API Error? → Yes → Extract HTTP Status
  ↓                    ↓
  No                   Map Status to ErrorType
  ↓                    ↓
Is Network Error? → Yes → ErrorType.TRANSIENT
  ↓
  No
  ↓
Is Timeout? → Yes → ErrorType.TRANSIENT (longer delays)
  ↓
  No
  ↓
Is Validation? → Yes → ErrorType.PERMANENT (with field errors)
  ↓
  No
  ↓
ErrorType.SYSTEM (with correlation ID)
```

### Retry Decision Flow
```
Error Classified
  ↓
Is ErrorType.TRANSIENT? → No → Return error immediately
  ↓
  Yes
  ↓
Is retryable flag true? → No → Return error immediately
  ↓
  Yes
  ↓
Attempts < maxAttempts? → No → Return error (exhausted)
  ↓
  Yes
  ↓
Calculate delay (exponential backoff)
  ↓
Wait for delay
  ↓
Increment attempt counter
  ↓
Retry API call
```

## Migration Guide

### Before (Ad-hoc Error Handling)
```typescript
try {
  const data = await bookClient.exportPDF(bookId);
  downloadBlob(data, 'book.pdf');
  toast.success('Exported');
} catch (err) {
  console.error('Export failed:', err);
  toast.error('Export failed. Try again.');
}
```

### After (Unified Error Handling)
```typescript
const result = await handleApiCall(
  () => bookClient.exportPDF(bookId),
  {
    context: 'Export PDF',
    onRetry: (attempt) => toast.info(`Retrying (${attempt})...`),
    onSuccess: (attempts) => {
      if (attempts > 1) {
        showRecoveryNotification('Export completed', attempts);
      }
    },
  }
);

if (result.success) {
  downloadBlob(result.data, 'book.pdf');
  toast.success('Exported');
} else {
  showErrorNotification(result.error, {
    onRetry: handleRetryExport,
  });
}
```

## File Structure

```
frontend/src/lib/errors/
├── index.ts                # Public API exports
├── types.ts                # TypeScript interfaces
├── classifier.ts           # Error classification logic
├── handler.ts              # Retry wrapper and logic
└── utils.ts                # Helper functions

frontend/src/components/errors/
├── index.ts                # Component exports
└── ErrorNotification.tsx   # Notification components
```

## Testing Strategy

### Unit Tests
- Error classification for various error types
- Retry delay calculations
- Correlation ID generation
- Message formatting

### Integration Tests
- API call wrapping with retry logic
- Notification display for error types
- Recovery notification after retries
- State management during retries

### E2E Tests
- Complete error flows (transient → retry → success)
- User retry interactions
- Error notification dismissal
- Multiple concurrent error scenarios

## Performance Considerations

### Optimization
- Error classification is synchronous (no async overhead)
- Retry delays use native setTimeout (no polling)
- Notifications throttled to prevent spam
- Correlation IDs generated efficiently

### Memory Management
- Errors contain only necessary data
- Original errors stored as weak references
- Notification cleanup on unmount
- No persistent error storage

## Security Considerations

### Information Disclosure
- Technical error details hidden from users
- System errors show correlation ID only
- Stack traces never exposed to UI
- Sensitive data scrubbed from logs

### Rate Limiting
- Exponential backoff prevents DoS
- Max attempts cap prevents infinite retries
- Delay limits prevent resource exhaustion
- Manual retry requires user action

## Monitoring and Observability

### Metrics to Track
- Error rate by type (Transient/Permanent/System)
- Retry success rate
- Average retry attempts before success
- Most common error status codes
- Correlation ID usage in support tickets

### Logging
- All errors logged with correlation ID
- Retry attempts logged with delay
- Success after retry logged with attempt count
- User actions (manual retry, dismiss) logged

## Future Enhancements

### Short-term
1. Backend integration for correlation ID tracking
2. Error analytics dashboard
3. Custom error handlers per API endpoint
4. Retry strategy profiles (aggressive, conservative)

### Long-term
1. Circuit breaker pattern for failing services
2. Fallback strategies for degraded service
3. User preferences for retry behavior
4. Error prediction and prevention

## References

- [Export Architecture](./EXPORT_ARCHITECTURE.md)
- [UI Improvements TODO](../UI_IMPROVEMENTS_TODO.md)
- [Implementation Plan](../IMPLEMENTATION_PLAN.md)
