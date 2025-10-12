/**
 * Error handling utility functions
 */

/**
 * Generate a unique correlation ID for error tracking
 * Format: timestamp-random
 */
export function generateCorrelationId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 9);
  return `${timestamp}-${random}`;
}

/**
 * Calculate retry delay with exponential backoff
 *
 * @param attempt - Current attempt number (0-indexed)
 * @param baseDelay - Base delay in milliseconds
 * @param maxDelay - Maximum delay in milliseconds
 * @param useExponentialBackoff - Whether to use exponential backoff
 * @returns Delay in milliseconds
 */
export function calculateRetryDelay(
  attempt: number,
  baseDelay: number,
  maxDelay: number,
  useExponentialBackoff: boolean
): number {
  if (!useExponentialBackoff) {
    return Math.min(baseDelay, maxDelay);
  }

  // Exponential backoff: baseDelay * 2^attempt
  const delay = baseDelay * Math.pow(2, attempt);
  return Math.min(delay, maxDelay);
}

/**
 * Sleep for specified milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if an error is retryable based on attempt count
 */
export function canRetry(attempt: number, maxAttempts: number): boolean {
  return attempt < maxAttempts;
}

/**
 * Format error message for display
 */
export function formatErrorMessage(message: string, details?: string): string {
  if (!details) return message;
  return `${message}\n\nDetails: ${details}`;
}

/**
 * Extract error message from unknown error
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (typeof error === 'object' && error !== null) {
    const errorObj = error as any;
    return errorObj.message || errorObj.error || JSON.stringify(error);
  }
  return 'An unknown error occurred';
}
