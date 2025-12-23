/**
 * Error handling types and interfaces
 * Provides a comprehensive error classification and handling system
 */

/**
 * Error classification types
 * - Transient: Temporary errors that may succeed on retry (network, timeouts)
 * - Permanent: Errors requiring user action (validation, permissions)
 * - System: Infrastructure errors requiring technical support
 * - AI_SERVICE: AI service errors with cached content fallback support
 */
export enum ErrorType {
  TRANSIENT = 'transient',
  PERMANENT = 'permanent',
  SYSTEM = 'system',
  AI_SERVICE = 'ai_service',
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

/**
 * Retry configuration for transient errors
 */
export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxAttempts: number;
  /** Base delay in milliseconds */
  baseDelay: number;
  /** Maximum delay in milliseconds */
  maxDelay: number;
  /** Whether to use exponential backoff */
  useExponentialBackoff: boolean;
}

/**
 * Classified error with context and handling metadata
 */
export interface ClassifiedError {
  /** Error classification type */
  type: ErrorType;
  /** Error severity level */
  severity: ErrorSeverity;
  /** User-friendly error message */
  message: string;
  /** Technical error details */
  details?: string;
  /** HTTP status code if applicable */
  statusCode?: number;
  /** Whether this error can be retried */
  retryable: boolean;
  /** Retry configuration if retryable */
  retryConfig?: RetryConfig;
  /** Unique correlation ID for tracking */
  correlationId: string;
  /** Timestamp when error occurred */
  timestamp: Date;
  /** Original error object */
  originalError?: Error;
  /** Field-specific errors for validation */
  fieldErrors?: Record<string, string>;
  /** Suggested user actions */
  suggestedActions?: string[];
}

/**
 * Error handler result
 */
export interface ErrorHandlerResult<T> {
  /** Whether the operation succeeded */
  success: boolean;
  /** Result data if successful */
  data?: T;
  /** Classified error if failed */
  error?: ClassifiedError;
  /** Number of retry attempts made */
  attempts: number;
}

/**
 * Error notification configuration
 */
export interface ErrorNotificationConfig {
  /** Whether to show notification */
  show: boolean;
  /** Notification display duration in ms */
  duration?: number;
  /** Whether notification can be dismissed */
  dismissible: boolean;
  /** Whether to show retry button */
  showRetry: boolean;
  /** Whether to show support contact */
  showSupport: boolean;
}

/**
 * Default retry configuration for transient errors
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  baseDelay: 2000, // 2 seconds
  maxDelay: 8000, // 8 seconds
  useExponentialBackoff: true,
};

/**
 * HTTP status code to error type mapping
 */
export const HTTP_STATUS_TO_ERROR_TYPE: Record<number, ErrorType> = {
  // 4xx - Client errors (usually permanent)
  400: ErrorType.PERMANENT, // Bad Request
  401: ErrorType.PERMANENT, // Unauthorized
  403: ErrorType.PERMANENT, // Forbidden
  404: ErrorType.PERMANENT, // Not Found
  409: ErrorType.PERMANENT, // Conflict
  422: ErrorType.PERMANENT, // Unprocessable Entity (validation)
  429: ErrorType.AI_SERVICE, // Too Many Requests (rate limit) - special handling for AI services

  // 5xx - Server errors (usually transient or system)
  500: ErrorType.SYSTEM, // Internal Server Error
  502: ErrorType.TRANSIENT, // Bad Gateway
  503: ErrorType.TRANSIENT, // Service Unavailable
  504: ErrorType.TRANSIENT, // Gateway Timeout
};

/**
 * Error type to severity mapping
 */
export const ERROR_TYPE_TO_SEVERITY: Record<ErrorType, ErrorSeverity> = {
  [ErrorType.TRANSIENT]: ErrorSeverity.MEDIUM,
  [ErrorType.PERMANENT]: ErrorSeverity.HIGH,
  [ErrorType.SYSTEM]: ErrorSeverity.CRITICAL,
  [ErrorType.AI_SERVICE]: ErrorSeverity.MEDIUM,
};
