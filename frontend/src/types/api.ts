/**
 * Base API Types and Interfaces
 *
 * This file defines the fundamental types and interfaces used across all API operations.
 * It ensures type safety and consistency between frontend and backend communications.
 *
 * @module types/api
 */

/**
 * Standard API response wrapper
 *
 * All API endpoints should return responses conforming to this interface.
 * This provides consistent error handling and metadata across the application.
 *
 * @template T - The type of data returned in successful responses
 *
 * @example
 * ```typescript
 * // Success response
 * const response: ApiResponse<BookProject> = {
 *   success: true,
 *   data: { id: '123', title: 'My Book', ... },
 *   metadata: {
 *     timestamp: '2024-01-15T10:30:00Z',
 *     requestId: 'req_abc123'
 *   }
 * };
 *
 * // Error response
 * const errorResponse: ApiResponse<BookProject> = {
 *   success: false,
 *   error: {
 *     code: 'VALIDATION_ERROR',
 *     message: 'Title is required',
 *     statusCode: 422
 *   }
 * };
 * ```
 */
export interface ApiResponse<T = unknown> {
  /** Whether the API call succeeded */
  success: boolean;

  /** Response data (present only on success) */
  data?: T;

  /** Error details (present only on failure) */
  error?: ApiError;

  /** Response metadata */
  metadata?: ResponseMetadata;
}

/**
 * Detailed error information from API responses
 *
 * Provides comprehensive error context including:
 * - Machine-readable error codes
 * - Human-friendly messages
 * - HTTP status codes
 * - Field-specific validation errors
 * - Correlation IDs for debugging
 *
 * @example
 * ```typescript
 * const validationError: ApiError = {
 *   code: 'VALIDATION_ERROR',
 *   message: 'Invalid book data',
 *   statusCode: 422,
 *   details: 'Multiple validation errors occurred',
 *   fieldErrors: {
 *     title: 'Title must be at least 3 characters',
 *     genre: 'Genre is required'
 *   },
 *   correlationId: 'err_xyz789',
 *   timestamp: '2024-01-15T10:30:00Z'
 * };
 * ```
 */
export interface ApiError {
  /** Machine-readable error code (e.g., 'VALIDATION_ERROR', 'NOT_FOUND') */
  code: string;

  /** Human-readable error message suitable for display */
  message: string;

  /** HTTP status code (400, 404, 500, etc.) */
  statusCode: number;

  /** Additional technical details about the error */
  details?: string;

  /** Field-specific validation errors keyed by field name */
  fieldErrors?: Record<string, string>;

  /** Unique identifier for tracking this error across systems */
  correlationId?: string;

  /** ISO 8601 timestamp when the error occurred */
  timestamp?: string;

  /** Stack trace (only in development mode) */
  stack?: string;
}

/**
 * Metadata about the API response
 *
 * Provides context about the response including:
 * - Request identifiers for debugging
 * - Timestamps for performance monitoring
 * - Pagination information for list responses
 * - Rate limiting information
 */
export interface ResponseMetadata {
  /** Unique identifier for this request */
  requestId?: string;

  /** ISO 8601 timestamp when response was generated */
  timestamp?: string;

  /** Server-side processing time in milliseconds */
  duration?: number;

  /** Pagination information (for list endpoints) */
  pagination?: PaginationMetadata;

  /** Rate limiting information */
  rateLimit?: RateLimitMetadata;

  /** API version used for this response */
  version?: string;
}

/**
 * Pagination metadata for list responses
 *
 * Provides information about paginated results including:
 * - Current page and total pages
 * - Total number of items
 * - Page size limits
 *
 * @example
 * ```typescript
 * const pagination: PaginationMetadata = {
 *   page: 2,
 *   pageSize: 20,
 *   totalItems: 150,
 *   totalPages: 8,
 *   hasNextPage: true,
 *   hasPreviousPage: true
 * };
 * ```
 */
export interface PaginationMetadata {
  /** Current page number (1-indexed) */
  page: number;

  /** Number of items per page */
  pageSize: number;

  /** Total number of items across all pages */
  totalItems: number;

  /** Total number of pages */
  totalPages: number;

  /** Whether there is a next page available */
  hasNextPage: boolean;

  /** Whether there is a previous page available */
  hasPreviousPage: boolean;
}

/**
 * Rate limiting information
 *
 * Indicates current rate limit status for the API consumer.
 * Helps clients implement backoff strategies when approaching limits.
 */
export interface RateLimitMetadata {
  /** Maximum number of requests allowed in the window */
  limit: number;

  /** Number of requests remaining in current window */
  remaining: number;

  /** Unix timestamp when the rate limit resets */
  reset: number;

  /** Time window duration in seconds */
  window: number;
}

/**
 * Common error codes used across the API
 *
 * Provides consistent error codes for common failure scenarios.
 * Use these constants instead of string literals for type safety.
 */
export const ApiErrorCode = {
  // Client errors (4xx)
  BAD_REQUEST: 'BAD_REQUEST',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',

  // Server errors (5xx)
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
  GATEWAY_TIMEOUT: 'GATEWAY_TIMEOUT',

  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',

  // Application-specific errors
  BOOK_NOT_FOUND: 'BOOK_NOT_FOUND',
  CHAPTER_NOT_FOUND: 'CHAPTER_NOT_FOUND',
  EXPORT_FAILED: 'EXPORT_FAILED',
  GENERATION_FAILED: 'GENERATION_FAILED',
} as const;

export type ApiErrorCodeType = typeof ApiErrorCode[keyof typeof ApiErrorCode];

/**
 * HTTP status codes
 *
 * Common HTTP status codes for reference.
 * Use these constants for consistency.
 */
export const HttpStatus = {
  // Success
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,

  // Client errors
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,

  // Server errors
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
} as const;

export type HttpStatusType = typeof HttpStatus[keyof typeof HttpStatus];

/**
 * Type guard to check if a response is successful
 *
 * @param response - The API response to check
 * @returns True if the response indicates success
 *
 * @example
 * ```typescript
 * const response = await api.getBook(id);
 * if (isSuccessResponse(response)) {
 *   // TypeScript knows response.data exists
 *   console.log(response.data.title);
 * }
 * ```
 */
export function isSuccessResponse<T>(
  response: ApiResponse<T>
): response is ApiResponse<T> & { success: true; data: T } {
  return response.success === true && response.data !== undefined;
}

/**
 * Type guard to check if a response is an error
 *
 * @param response - The API response to check
 * @returns True if the response indicates an error
 *
 * @example
 * ```typescript
 * const response = await api.getBook(id);
 * if (isErrorResponse(response)) {
 *   // TypeScript knows response.error exists
 *   console.error(response.error.message);
 * }
 * ```
 */
export function isErrorResponse<T>(
  response: ApiResponse<T>
): response is ApiResponse<T> & { success: false; error: ApiError } {
  return response.success === false && response.error !== undefined;
}

/**
 * Validates that a response object conforms to the ApiResponse interface
 *
 * Performs runtime validation of response structure.
 * Useful when receiving data from external sources.
 *
 * @param obj - The object to validate
 * @returns True if the object is a valid ApiResponse
 *
 * @example
 * ```typescript
 * const rawData = await fetch('/api/books');
 * const json = await rawData.json();
 *
 * if (!isValidApiResponse(json)) {
 *   throw new Error('Invalid API response format');
 * }
 *
 * // Now TypeScript knows json is ApiResponse<unknown>
 * const response = json as ApiResponse<BookProject>;
 * ```
 */
export function isValidApiResponse(obj: unknown): obj is ApiResponse<unknown> {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const response = obj as Record<string, unknown>;

  // Must have a boolean success field
  if (typeof response.success !== 'boolean') {
    return false;
  }

  // If success is true, should have data
  // If success is false, should have error
  if (response.success) {
    return 'data' in response;
  } else {
    return 'error' in response && isValidApiError(response.error);
  }
}

/**
 * Validates that an object conforms to the ApiError interface
 *
 * @param obj - The object to validate
 * @returns True if the object is a valid ApiError
 */
export function isValidApiError(obj: unknown): obj is ApiError {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const error = obj as Record<string, unknown>;

  return (
    typeof error.code === 'string' &&
    typeof error.message === 'string' &&
    typeof error.statusCode === 'number'
  );
}

/**
 * Creates a standardized success response
 *
 * Helper function for creating properly typed success responses.
 *
 * @param data - The response data
 * @param metadata - Optional response metadata
 * @returns A properly formatted success response
 *
 * @example
 * ```typescript
 * const response = createSuccessResponse(
 *   { id: '123', title: 'My Book' },
 *   { requestId: 'req_abc', timestamp: new Date().toISOString() }
 * );
 * ```
 */
export function createSuccessResponse<T>(
  data: T,
  metadata?: ResponseMetadata
): ApiResponse<T> {
  return {
    success: true,
    data,
    metadata,
  };
}

/**
 * Creates a standardized error response
 *
 * Helper function for creating properly typed error responses.
 *
 * @param error - The error details
 * @param metadata - Optional response metadata
 * @returns A properly formatted error response
 *
 * @example
 * ```typescript
 * const response = createErrorResponse({
 *   code: ApiErrorCode.NOT_FOUND,
 *   message: 'Book not found',
 *   statusCode: HttpStatus.NOT_FOUND,
 *   correlationId: generateCorrelationId()
 * });
 * ```
 */
export function createErrorResponse<T = never>(
  error: ApiError,
  metadata?: ResponseMetadata
): ApiResponse<T> {
  return {
    success: false,
    error,
    metadata,
  };
}
