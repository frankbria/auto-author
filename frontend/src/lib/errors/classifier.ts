/**
 * Error classification utility
 * Analyzes errors and assigns appropriate type, severity, and handling strategy
 */

import {
  ClassifiedError,
  ErrorType,
  ErrorSeverity,
  HTTP_STATUS_TO_ERROR_TYPE,
  ERROR_TYPE_TO_SEVERITY,
  DEFAULT_RETRY_CONFIG,
} from './types';
import { generateCorrelationId } from './utils';

/**
 * Classify an error and determine handling strategy
 *
 * @param error - The error to classify
 * @param context - Optional context about where the error occurred
 * @returns Classified error with handling metadata
 */
export function classifyError(
  error: unknown,
  context?: string
): ClassifiedError {
  const correlationId = generateCorrelationId();
  const timestamp = new Date();

  // Handle API errors with status codes
  if (isApiError(error)) {
    const statusCode = error.statusCode || error.status;
    const errorType = statusCode ? (HTTP_STATUS_TO_ERROR_TYPE[statusCode] || ErrorType.SYSTEM) : ErrorType.SYSTEM;
    const severity = ERROR_TYPE_TO_SEVERITY[errorType];
    const retryable = errorType === ErrorType.TRANSIENT;

    return {
      type: errorType,
      severity,
      message: getUserFriendlyMessage(error, errorType),
      details: error.message || 'An error occurred',
      statusCode,
      retryable,
      retryConfig: retryable ? DEFAULT_RETRY_CONFIG : undefined,
      correlationId,
      timestamp,
      originalError: error as Error,
      fieldErrors: extractFieldErrors(error),
      suggestedActions: getSuggestedActions(errorType, statusCode),
    };
  }

  // Handle network errors
  if (isNetworkError(error)) {
    return {
      type: ErrorType.TRANSIENT,
      severity: ErrorSeverity.MEDIUM,
      message: 'Network connection issue. Please check your internet connection.',
      details: error.message,
      retryable: true,
      retryConfig: DEFAULT_RETRY_CONFIG,
      correlationId,
      timestamp,
      originalError: error as Error,
      suggestedActions: [
        'Check your internet connection',
        'Try again in a few moments',
        'Contact support if the problem persists',
      ],
    };
  }

  // Handle timeout errors
  if (isTimeoutError(error)) {
    return {
      type: ErrorType.TRANSIENT,
      severity: ErrorSeverity.MEDIUM,
      message: 'Request timed out. The operation is taking longer than expected.',
      details: error.message,
      retryable: true,
      retryConfig: { ...DEFAULT_RETRY_CONFIG, baseDelay: 3000, maxDelay: 12000 },
      correlationId,
      timestamp,
      originalError: error as Error,
      suggestedActions: [
        'Wait a moment and try again',
        'Check if the server is responding',
        'Contact support if timeouts continue',
      ],
    };
  }

  // Handle validation errors
  if (isValidationError(error)) {
    return {
      type: ErrorType.PERMANENT,
      severity: ErrorSeverity.HIGH,
      message: 'Please correct the highlighted fields and try again.',
      details: error.message,
      retryable: false,
      correlationId,
      timestamp,
      originalError: error as Error,
      fieldErrors: extractFieldErrors(error),
      suggestedActions: [
        'Review the form for errors',
        'Ensure all required fields are filled',
        'Check field format requirements',
      ],
    };
  }

  // Handle generic errors
  const errorMessage =
    error instanceof Error ? error.message : 'An unexpected error occurred';

  return {
    type: ErrorType.SYSTEM,
    severity: ErrorSeverity.CRITICAL,
    message: 'Something went wrong. Our team has been notified.',
    details: errorMessage,
    retryable: false,
    correlationId,
    timestamp,
    originalError: error instanceof Error ? error : undefined,
    suggestedActions: [
      `Reference ID: ${correlationId}`,
      'Try refreshing the page',
      'Contact support if the problem persists',
    ],
  };
}

/**
 * Check if error is an API error with status code
 */
function isApiError(error: unknown): error is { statusCode?: number; status?: number; message?: string } {
  return (
    typeof error === 'object' &&
    error !== null &&
    ('statusCode' in error || 'status' in error)
  );
}

/**
 * Check if error is a network error
 */
function isNetworkError(error: unknown): error is Error {
  if (!(error instanceof Error)) return false;
  const message = error.message.toLowerCase();
  return (
    message.includes('network') ||
    message.includes('fetch') ||
    message.includes('connection') ||
    message.includes('offline')
  );
}

/**
 * Check if error is a timeout error
 */
function isTimeoutError(error: unknown): error is Error {
  if (!(error instanceof Error)) return false;
  const message = error.message.toLowerCase();
  return message.includes('timeout') || message.includes('timed out');
}

/**
 * Check if error is a validation error
 */
function isValidationError(error: unknown): error is Error {
  if (!isApiError(error)) return false;
  const statusCode = error.statusCode || error.status;
  return statusCode === 400 || statusCode === 422;
}

/**
 * Extract field-specific errors from API response
 */
function extractFieldErrors(error: unknown): Record<string, string> | undefined {
  if (!isApiError(error)) return undefined;

  // Check for common error response formats
  const errorObj = error as any;

  // Format: { errors: { field: "message" } }
  if (errorObj.errors && typeof errorObj.errors === 'object') {
    return errorObj.errors;
  }

  // Format: { fieldErrors: { field: "message" } }
  if (errorObj.fieldErrors && typeof errorObj.fieldErrors === 'object') {
    return errorObj.fieldErrors;
  }

  // Format: { validationErrors: [{ field, message }] }
  if (Array.isArray(errorObj.validationErrors)) {
    return errorObj.validationErrors.reduce((acc: Record<string, string>, err: any) => {
      if (err.field && err.message) {
        acc[err.field] = err.message;
      }
      return acc;
    }, {});
  }

  return undefined;
}

/**
 * Get user-friendly message based on error type
 */
function getUserFriendlyMessage(error: unknown, errorType: ErrorType): string {
  const errorObj = error as any;
  const statusCode = errorObj.statusCode || errorObj.status;

  // Use custom message if provided
  if (errorObj.userMessage) {
    return errorObj.userMessage;
  }

  // Default messages by status code
  switch (statusCode) {
    case 400:
      return 'Invalid request. Please check your input and try again.';
    case 401:
      return 'You need to be logged in to perform this action.';
    case 403:
      return 'You don\'t have permission to perform this action.';
    case 404:
      return 'The requested resource was not found.';
    case 409:
      return 'This action conflicts with existing data.';
    case 422:
      return 'Please correct the highlighted fields and try again.';
    case 429:
      return 'Too many requests. Please wait a moment and try again.';
    case 500:
      return 'A server error occurred. Our team has been notified.';
    case 502:
    case 503:
      return 'The service is temporarily unavailable. Please try again shortly.';
    case 504:
      return 'Request timed out. Please try again.';
    default:
      return errorType === ErrorType.TRANSIENT
        ? 'A temporary error occurred. Please try again.'
        : 'An error occurred. Please try again or contact support.';
  }
}

/**
 * Get suggested actions based on error type and status code
 */
function getSuggestedActions(errorType: ErrorType, statusCode?: number): string[] {
  if (errorType === ErrorType.TRANSIENT) {
    return [
      'Wait a moment and try again',
      'Check your internet connection',
      'Contact support if the problem persists',
    ];
  }

  if (errorType === ErrorType.PERMANENT) {
    if (statusCode === 401) {
      return ['Sign in to continue', 'Check your credentials', 'Reset your password if needed'];
    }
    if (statusCode === 403) {
      return [
        'Verify you have the required permissions',
        'Contact your administrator',
        'Try logging out and back in',
      ];
    }
    if (statusCode === 404) {
      return [
        'Check the URL or resource ID',
        'Go back to the previous page',
        'Return to the dashboard',
      ];
    }
    return ['Review your input', 'Correct any errors', 'Try a different approach'];
  }

  // System errors
  return [
    'Try refreshing the page',
    'Clear your browser cache',
    'Contact support with the reference ID above',
  ];
}
