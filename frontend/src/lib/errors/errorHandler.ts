/**
 * Error Handler Utility
 *
 * Provides unified error handling with classification, automatic retry logic,
 * exponential backoff, and toast notification integration.
 */

export enum ErrorType {
  NETWORK = 'NETWORK',
  VALIDATION = 'VALIDATION',
  AUTH = 'AUTH',
  SERVER = 'SERVER',
  UNKNOWN = 'UNKNOWN',
}

interface ErrorWithStatus {
  status?: number;
  message?: string;
  detail?: string;
  error?: ErrorWithStatus;
}

interface ErrorHandlerConfig {
  maxRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
}

interface HandleApiErrorOptions {
  customMessage?: string;
}

type ToastFunction = (options: {
  title: string;
  description: string;
  variant?: 'default' | 'destructive';
}) => void;

/**
 * Classify an error into one of the predefined error types
 */
export function classifyError(error: unknown): ErrorType {
  // Network errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return ErrorType.NETWORK;
  }

  if (error instanceof Error && error.name === 'NetworkError') {
    return ErrorType.NETWORK;
  }

  // Check for status code in error object
  const errorWithStatus = error as ErrorWithStatus;
  const status = errorWithStatus?.status;

  if (typeof status === 'number') {
    // Validation errors (4xx)
    if (status === 400) {
      return ErrorType.VALIDATION;
    }

    // Authentication errors
    if (status === 401 || status === 403) {
      return ErrorType.AUTH;
    }

    // Server errors (5xx)
    if (status >= 500 && status < 600) {
      return ErrorType.SERVER;
    }

    // Rate limiting (treat as server error for retry purposes)
    if (status === 429) {
      return ErrorType.SERVER;
    }
  }

  return ErrorType.UNKNOWN;
}

/**
 * Determine if an error should be retried based on type and attempt count
 */
export function shouldRetry(errorType: ErrorType, attemptCount: number, maxRetries = 3): boolean {
  // Don't retry beyond max attempts
  if (attemptCount >= maxRetries) {
    return false;
  }

  // Only retry transient errors
  const retryableErrors = [ErrorType.NETWORK, ErrorType.SERVER];
  return retryableErrors.includes(errorType);
}

/**
 * Calculate exponential backoff delay in milliseconds
 * Formula: baseDelay * 2^attempt, capped at maxDelay
 */
export function calculateBackoff(
  attempt: number,
  baseDelay = 1000,
  maxDelay = 30000
): number {
  const delay = baseDelay * Math.pow(2, attempt);
  return Math.min(delay, maxDelay);
}

/**
 * Extract a user-friendly error message from various error formats
 */
export function extractErrorMessage(error: unknown): string {
  const defaultMessage = 'An unexpected error occurred';

  if (!error) {
    return defaultMessage;
  }

  // Handle Error objects
  if (error instanceof Error) {
    return error.message || defaultMessage;
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }

  // Handle objects with message or detail properties
  if (typeof error === 'object') {
    const errorObj = error as ErrorWithStatus;

    // Check for nested error structure
    if (errorObj.error && typeof errorObj.error === 'object') {
      return extractErrorMessage(errorObj.error);
    }

    // Prefer message over detail
    if (errorObj.message) {
      return errorObj.message;
    }

    if (errorObj.detail) {
      return errorObj.detail;
    }
  }

  return defaultMessage;
}

/**
 * Get a user-friendly error title based on error type
 */
function getErrorTitle(errorType: ErrorType): string {
  const titles: Record<ErrorType, string> = {
    [ErrorType.NETWORK]: 'Network Error',
    [ErrorType.VALIDATION]: 'Validation Error',
    [ErrorType.AUTH]: 'Authentication Error',
    [ErrorType.SERVER]: 'Server Error',
    [ErrorType.UNKNOWN]: 'Error',
  };

  return titles[errorType];
}

/**
 * ErrorHandler class for executing operations with automatic retry logic
 */
export class ErrorHandler {
  private maxRetries: number;
  private baseDelay: number;
  private maxDelay: number;

  constructor(config: ErrorHandlerConfig = {}) {
    this.maxRetries = config.maxRetries ?? 3;
    this.baseDelay = config.baseDelay ?? 1000;
    this.maxDelay = config.maxDelay ?? 30000;
  }

  /**
   * Execute an operation with automatic retry on transient errors
   */
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: unknown;
    let attempt = 0;

    while (attempt < this.maxRetries) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        const errorType = classifyError(error);

        // Check if we should retry
        if (!shouldRetry(errorType, attempt, this.maxRetries)) {
          throw error;
        }

        // Calculate backoff delay
        const delay = calculateBackoff(attempt, this.baseDelay, this.maxDelay);

        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, delay));

        attempt++;
      }
    }

    // All retries exhausted
    throw lastError;
  }
}

/**
 * High-level API for handling errors with toast notifications
 *
 * @param operation - The async operation to execute
 * @param toast - Toast notification function
 * @param options - Additional options like custom error messages
 */
export async function handleApiError<T>(
  operation: () => Promise<T>,
  toast: ToastFunction,
  options: HandleApiErrorOptions = {}
): Promise<T> {
  const handler = new ErrorHandler();

  try {
    return await handler.execute(operation);
  } catch (error) {
    const errorType = classifyError(error);
    const errorMessage = options.customMessage || extractErrorMessage(error);

    // Show toast notification
    toast({
      title: getErrorTitle(errorType),
      description: errorMessage,
      variant: 'destructive',
    });

    // Re-throw for caller to handle
    throw error;
  }
}
