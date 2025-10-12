/**
 * Unified error handler with automatic retry logic
 * Wraps API calls and provides consistent error handling
 */

import { classifyError } from './classifier';
import { calculateRetryDelay, canRetry, sleep } from './utils';
import {
  ErrorHandlerResult,
  ClassifiedError,
  ErrorType,
  DEFAULT_RETRY_CONFIG,
  RetryConfig,
} from './types';

/**
 * Options for handleApiCall wrapper
 */
export interface HandleApiCallOptions {
  /** Custom retry configuration */
  retryConfig?: Partial<RetryConfig>;
  /** Context string for error tracking */
  context?: string;
  /** Whether to preserve user input on retry */
  preserveInput?: boolean;
  /** Callback before each retry attempt */
  onRetry?: (attempt: number, error: ClassifiedError) => void;
  /** Callback when operation succeeds after retry */
  onSuccess?: (attempts: number) => void;
  /** Callback when all retries exhausted */
  onFailure?: (error: ClassifiedError) => void;
}

/**
 * Wrap an API call with automatic error handling and retry logic
 *
 * @template T - The return type of the API call
 * @param apiCall - The async function to execute
 * @param options - Configuration options
 * @returns Promise with error handler result
 *
 * @example
 * ```typescript
 * const result = await handleApiCall(
 *   () => bookClient.exportPDF(bookId),
 *   {
 *     context: 'Export PDF',
 *     onRetry: (attempt) => console.log(`Retry ${attempt}`),
 *   }
 * );
 *
 * if (result.success) {
 *   console.log('Success:', result.data);
 * } else {
 *   console.error('Failed:', result.error);
 * }
 * ```
 */
export async function handleApiCall<T>(
  apiCall: () => Promise<T>,
  options: HandleApiCallOptions = {}
): Promise<ErrorHandlerResult<T>> {
  const {
    retryConfig,
    context,
    onRetry,
    onSuccess,
    onFailure,
  } = options;

  // Merge retry config with defaults
  const config: RetryConfig = {
    ...DEFAULT_RETRY_CONFIG,
    ...retryConfig,
  };

  let lastError: ClassifiedError | null = null;
  let attempt = 0;

  while (attempt <= config.maxAttempts) {
    try {
      // Execute the API call
      const data = await apiCall();

      // Success!
      if (attempt > 0 && onSuccess) {
        onSuccess(attempt);
      }

      return {
        success: true,
        data,
        attempts: attempt,
      };
    } catch (error) {
      // Classify the error
      const classifiedError = classifyError(error, context);
      lastError = classifiedError;

      // Check if we should retry
      const shouldRetry =
        classifiedError.retryable &&
        classifiedError.type === ErrorType.TRANSIENT &&
        canRetry(attempt, config.maxAttempts);

      if (!shouldRetry) {
        // Not retryable or out of attempts
        if (onFailure) {
          onFailure(classifiedError);
        }

        return {
          success: false,
          error: classifiedError,
          attempts: attempt,
        };
      }

      // Calculate delay for retry
      const delay = calculateRetryDelay(
        attempt,
        config.baseDelay,
        config.maxDelay,
        config.useExponentialBackoff
      );

      // Notify about retry
      if (onRetry) {
        onRetry(attempt + 1, classifiedError);
      }

      // Wait before retrying
      await sleep(delay);

      // Increment attempt counter
      attempt++;
    }
  }

  // Should never reach here, but TypeScript requires it
  return {
    success: false,
    error: lastError!,
    attempts: attempt,
  };
}

/**
 * Create a retry wrapper for a specific API function
 *
 * @template TArgs - The argument types for the API function
 * @template TResult - The return type of the API function
 * @param apiFunc - The API function to wrap
 * @param options - Default options for this wrapper
 * @returns Wrapped function with retry logic
 *
 * @example
 * ```typescript
 * const exportPDFWithRetry = createRetryWrapper(
 *   bookClient.exportPDF,
 *   {
 *     context: 'Export PDF',
 *     retryConfig: { maxAttempts: 5 },
 *   }
 * );
 *
 * const result = await exportPDFWithRetry(bookId, options);
 * ```
 */
export function createRetryWrapper<TArgs extends any[], TResult>(
  apiFunc: (...args: TArgs) => Promise<TResult>,
  defaultOptions: HandleApiCallOptions = {}
) {
  return async (
    ...args: TArgs
  ): Promise<ErrorHandlerResult<TResult>> => {
    return handleApiCall(
      () => apiFunc(...args),
      defaultOptions
    );
  };
}

/**
 * Manual retry function for user-initiated retries
 *
 * @template T - The return type
 * @param operation - The operation to retry
 * @param onRetry - Callback when retry starts
 * @returns Promise with result
 */
export async function manualRetry<T>(
  operation: () => Promise<T>,
  onRetry?: () => void
): Promise<ErrorHandlerResult<T>> {
  if (onRetry) {
    onRetry();
  }

  return handleApiCall(operation, {
    retryConfig: { maxAttempts: 1 },
  });
}
