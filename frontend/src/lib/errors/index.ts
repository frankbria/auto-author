/**
 * Unified Error Handling Framework
 * Provides comprehensive error classification, handling, and retry logic
 */

// Types
export type {
  ClassifiedError,
  ErrorHandlerResult,
  RetryConfig,
  ErrorNotificationConfig,
} from './types';

export {
  ErrorType,
  ErrorSeverity,
  DEFAULT_RETRY_CONFIG,
  HTTP_STATUS_TO_ERROR_TYPE,
  ERROR_TYPE_TO_SEVERITY,
} from './types';

// Classification
export { classifyError } from './classifier';

// Handler
export {
  handleApiCall,
  createRetryWrapper,
  manualRetry,
} from './handler';

export type { HandleApiCallOptions } from './handler';

// Utilities
export {
  generateCorrelationId,
  calculateRetryDelay,
  sleep,
  canRetry,
  formatErrorMessage,
  getErrorMessage,
} from './utils';

// TDD Error Handler (Task 4 implementation)
export {
  ErrorHandler,
  classifyError as classifyErrorTDD,
  shouldRetry,
  calculateBackoff,
  extractErrorMessage,
  handleApiError,
} from './errorHandler';
