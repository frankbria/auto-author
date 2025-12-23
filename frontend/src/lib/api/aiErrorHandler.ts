/**
 * AI Service Error Handler
 * Provides comprehensive error handling for AI service operations with cached content fallback
 */

import { showErrorNotification } from '@/components/errors/ErrorNotification';
import { ErrorType, ErrorSeverity } from '@/lib/errors';

/**
 * AI Service error response structure
 */
export interface AIErrorResponse {
  message: string;
  status_code: number;
  cached_content_available?: boolean;
  cached_content?: unknown;
  estimated_retry_after?: number; // seconds
  error_type?: 'rate_limit' | 'network' | 'service_unavailable' | 'validation' | 'unknown';
}

/**
 * AI Service result with cached content support
 */
export interface AIServiceResult<T> {
  data?: T;
  fromCache?: boolean;
  error?: string;
  retryAfter?: number;
  canRetry?: boolean;
}

/**
 * Extract error details from various error types
 */
function extractErrorDetails(error: unknown): Partial<AIErrorResponse> {
  // Handle Error objects
  if (error instanceof Error) {
    const message = error.message;

    // Try to parse JSON from error message
    try {
      const jsonMatch = message.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        return {
          message: parsed.message || parsed.detail || message,
          status_code: parsed.status_code || extractStatusCode(message),
          cached_content_available: parsed.cached_content_available,
          cached_content: parsed.cached_content,
          estimated_retry_after: parsed.estimated_retry_after,
          error_type: parsed.error_type,
        };
      }
    } catch {
      // Not JSON, continue with plain error message
    }

    // Extract status code from message
    const statusCode = extractStatusCode(message);

    return {
      message,
      status_code: statusCode,
      error_type: determineErrorType(statusCode, message),
    };
  }

  // Handle plain objects
  if (typeof error === 'object' && error !== null) {
    const err = error as Record<string, unknown>;
    return {
      message: String(err.message || err.detail || 'An unknown error occurred'),
      status_code: Number(err.status_code || err.statusCode || 500),
      cached_content_available: Boolean(err.cached_content_available),
      cached_content: err.cached_content,
      estimated_retry_after: Number(err.estimated_retry_after || 0),
      error_type: err.error_type as AIErrorResponse['error_type'],
    };
  }

  // Fallback for unknown error types
  return {
    message: String(error),
    status_code: 500,
    error_type: 'unknown',
  };
}

/**
 * Extract status code from error message
 */
function extractStatusCode(message: string): number {
  const match = message.match(/\b(4\d{2}|5\d{2})\b/);
  return match ? parseInt(match[1], 10) : 500;
}

/**
 * Determine error type from status code and message
 */
function determineErrorType(statusCode: number, message: string): AIErrorResponse['error_type'] {
  if (statusCode === 429) return 'rate_limit';
  if (statusCode === 422 || statusCode === 400) return 'validation';
  if (statusCode === 503 || statusCode === 504) return 'service_unavailable';
  if (message.toLowerCase().includes('network') || message.toLowerCase().includes('fetch')) return 'network';
  return 'unknown';
}

/**
 * Get user-friendly error message based on error type
 */
function getUserFriendlyMessage(errorDetails: Partial<AIErrorResponse>): string {
  const { error_type, estimated_retry_after } = errorDetails;

  switch (error_type) {
    case 'rate_limit':
      return estimated_retry_after
        ? `AI service rate limit reached. Please wait ${Math.ceil(estimated_retry_after / 60)} minutes before retrying.`
        : 'AI service rate limit reached. Please try again in a few minutes.';

    case 'network':
      return 'Network connection issue. Please check your internet connection and try again.';

    case 'service_unavailable':
      return 'AI service is temporarily unavailable. Please try again in a moment.';

    case 'validation':
      return 'Invalid request data. Please check your input and try again.';

    default:
      return errorDetails.message || 'An error occurred while processing your request.';
  }
}

/**
 * Determine if error is retryable
 */
function isRetryable(errorDetails: Partial<AIErrorResponse>): boolean {
  const { error_type, status_code } = errorDetails;

  // Retryable error types
  if (error_type === 'rate_limit') return true;
  if (error_type === 'network') return true;
  if (error_type === 'service_unavailable') return true;

  // Retryable status codes
  if (status_code === 429) return true;
  if (status_code === 503) return true;
  if (status_code === 504) return true;

  return false;
}

/**
 * Handle AI service errors with cached content fallback
 *
 * @param error - The error object from the AI service
 * @param onRetry - Optional callback for retry action
 * @returns AI service result with cached content if available
 */
export async function handleAIServiceError<T>(
  error: unknown,
  onRetry?: () => void | Promise<void>
): Promise<AIServiceResult<T>> {
  const errorDetails = extractErrorDetails(error);
  const userMessage = getUserFriendlyMessage(errorDetails);
  const retryable = isRetryable(errorDetails);

  // Check if cached content is available
  if (errorDetails.cached_content_available && errorDetails.cached_content) {
    // Show warning notification about using cached content
    showErrorNotification(
      {
        type: ErrorType.AI_SERVICE,
        severity: ErrorSeverity.MEDIUM,
        message: 'Using previously generated content',
        details: 'AI service temporarily unavailable. Showing cached content from previous generation.',
        statusCode: errorDetails.status_code,
        retryable: retryable,
        correlationId: `ai-cache-${Date.now()}`,
        timestamp: new Date(),
        suggestedActions: retryable && onRetry
          ? ['The cached content below is from a previous generation', 'Click retry to generate fresh content when available']
          : ['The cached content below is from a previous generation'],
      },
      {
        onRetry,
        duration: 10000, // Show for 10 seconds
      }
    );

    return {
      data: errorDetails.cached_content as T,
      fromCache: true,
      error: userMessage,
      retryAfter: errorDetails.estimated_retry_after,
      canRetry: retryable,
    };
  }

  // No cached content available - show error notification
  const suggestedActions: string[] = [];

  if (errorDetails.error_type === 'rate_limit') {
    suggestedActions.push('Wait for the rate limit to reset');
    if (errorDetails.estimated_retry_after) {
      suggestedActions.push(`Estimated wait time: ${Math.ceil(errorDetails.estimated_retry_after / 60)} minutes`);
    }
  } else if (errorDetails.error_type === 'network') {
    suggestedActions.push('Check your internet connection');
    suggestedActions.push('Try again in a moment');
  } else if (errorDetails.error_type === 'service_unavailable') {
    suggestedActions.push('The AI service is experiencing issues');
    suggestedActions.push('Try again in a few minutes');
  } else if (errorDetails.error_type === 'validation') {
    suggestedActions.push('Check your input data');
    suggestedActions.push('Ensure all required fields are filled');
  }

  showErrorNotification(
    {
      type: retryable ? ErrorType.AI_SERVICE : ErrorType.PERMANENT,
      severity: retryable ? ErrorSeverity.MEDIUM : ErrorSeverity.HIGH,
      message: errorDetails.error_type === 'rate_limit' ? 'AI Service Rate Limited' : 'AI Service Error',
      details: userMessage,
      statusCode: errorDetails.status_code,
      retryable,
      correlationId: `ai-error-${Date.now()}`,
      timestamp: new Date(),
      suggestedActions,
    },
    {
      onRetry: retryable ? onRetry : undefined,
      duration: retryable ? 15000 : 10000,
    }
  );

  return {
    error: userMessage,
    retryAfter: errorDetails.estimated_retry_after,
    canRetry: retryable,
  };
}

/**
 * Create a retry handler with countdown support
 */
export function createRetryHandler(
  retryFn: () => void | Promise<void>,
  retryAfter?: number
): () => void {
  return () => {
    if (retryAfter && retryAfter > 0) {
      // Show countdown before retry
      const minutes = Math.ceil(retryAfter / 60);
      const proceed = confirm(
        `The rate limit resets in approximately ${minutes} minute${minutes === 1 ? '' : 's'}. ` +
        `Retrying now may result in another error. Continue anyway?`
      );

      if (!proceed) return;
    }

    void retryFn();
  };
}

/**
 * Check if a result is from cache
 */
export function isFromCache<T>(result: AIServiceResult<T>): result is AIServiceResult<T> & { fromCache: true; data: T } {
  return result.fromCache === true && result.data !== undefined;
}
