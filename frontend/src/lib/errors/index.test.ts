/**
 * Tests for src/lib/errors/index.ts
 *
 * Verifies that all expected exports are accessible and have the correct
 * identity / type. We intentionally test through the barrel index so that
 * missing or broken re-exports surface here.
 */

import {
  // Types (values)
  ErrorType,
  ErrorSeverity,
  DEFAULT_RETRY_CONFIG,
  HTTP_STATUS_TO_ERROR_TYPE,
  ERROR_TYPE_TO_SEVERITY,

  // Classifier
  classifyError,

  // Handler
  handleApiCall,
  createRetryWrapper,
  manualRetry,

  // Utilities
  generateCorrelationId,
  calculateRetryDelay,
  sleep,
  canRetry,
  formatErrorMessage,
  getErrorMessage,

  // TDD-variant exports from errorHandler.ts
  ErrorHandler,
  classifyErrorTDD,
  shouldRetry,
  calculateBackoff,
  extractErrorMessage,
  handleApiError,
} from './index';

describe('index re-exports', () => {
  // ---- enums / constants ---------------------------------------------------

  it('exports ErrorType enum with expected members', () => {
    expect(ErrorType.TRANSIENT).toBe('transient');
    expect(ErrorType.PERMANENT).toBe('permanent');
    expect(ErrorType.SYSTEM).toBe('system');
    expect(ErrorType.AI_SERVICE).toBe('ai_service');
  });

  it('exports ErrorSeverity enum with expected members', () => {
    expect(ErrorSeverity.LOW).toBe('low');
    expect(ErrorSeverity.MEDIUM).toBe('medium');
    expect(ErrorSeverity.HIGH).toBe('high');
    expect(ErrorSeverity.CRITICAL).toBe('critical');
  });

  it('exports DEFAULT_RETRY_CONFIG as an object with required fields', () => {
    expect(typeof DEFAULT_RETRY_CONFIG).toBe('object');
    expect(typeof DEFAULT_RETRY_CONFIG.maxAttempts).toBe('number');
    expect(typeof DEFAULT_RETRY_CONFIG.baseDelay).toBe('number');
    expect(typeof DEFAULT_RETRY_CONFIG.maxDelay).toBe('number');
    expect(typeof DEFAULT_RETRY_CONFIG.useExponentialBackoff).toBe('boolean');
  });

  it('exports HTTP_STATUS_TO_ERROR_TYPE mapping', () => {
    expect(HTTP_STATUS_TO_ERROR_TYPE[400]).toBe(ErrorType.PERMANENT);
    expect(HTTP_STATUS_TO_ERROR_TYPE[503]).toBe(ErrorType.TRANSIENT);
    expect(HTTP_STATUS_TO_ERROR_TYPE[500]).toBe(ErrorType.SYSTEM);
    expect(HTTP_STATUS_TO_ERROR_TYPE[429]).toBe(ErrorType.AI_SERVICE);
  });

  it('exports ERROR_TYPE_TO_SEVERITY mapping', () => {
    expect(ERROR_TYPE_TO_SEVERITY[ErrorType.TRANSIENT]).toBe(ErrorSeverity.MEDIUM);
    expect(ERROR_TYPE_TO_SEVERITY[ErrorType.PERMANENT]).toBe(ErrorSeverity.HIGH);
    expect(ERROR_TYPE_TO_SEVERITY[ErrorType.SYSTEM]).toBe(ErrorSeverity.CRITICAL);
  });

  // ---- classifier ----------------------------------------------------------

  it('exports classifyError as a function', () => {
    expect(typeof classifyError).toBe('function');
  });

  it('classifyError works end-to-end via index', () => {
    const result = classifyError({ statusCode: 503, message: 'unavailable' });
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
  });

  // ---- handler -------------------------------------------------------------

  it('exports handleApiCall as a function', () => {
    expect(typeof handleApiCall).toBe('function');
  });

  it('exports createRetryWrapper as a function', () => {
    expect(typeof createRetryWrapper).toBe('function');
  });

  it('exports manualRetry as a function', () => {
    expect(typeof manualRetry).toBe('function');
  });

  it('handleApiCall resolves with success via index', async () => {
    const result = await handleApiCall(() => Promise.resolve('hello'));
    expect(result.success).toBe(true);
    expect(result.data).toBe('hello');
  });

  // ---- utilities -----------------------------------------------------------

  it('exports generateCorrelationId as a function', () => {
    expect(typeof generateCorrelationId).toBe('function');
    expect(typeof generateCorrelationId()).toBe('string');
  });

  it('exports calculateRetryDelay as a function', () => {
    expect(typeof calculateRetryDelay).toBe('function');
    expect(calculateRetryDelay(0, 1000, 5000, false)).toBe(1000);
  });

  it('exports sleep as a function that returns a Promise', () => {
    expect(typeof sleep).toBe('function');
    // We call with 0ms so the promise settles quickly in real time
    expect(sleep(0)).toBeInstanceOf(Promise);
  });

  it('exports canRetry as a function', () => {
    expect(typeof canRetry).toBe('function');
    expect(canRetry(0, 3)).toBe(true);
    expect(canRetry(3, 3)).toBe(false);
  });

  it('exports formatErrorMessage as a function', () => {
    expect(typeof formatErrorMessage).toBe('function');
    expect(formatErrorMessage('msg')).toBe('msg');
  });

  it('exports getErrorMessage as a function', () => {
    expect(typeof getErrorMessage).toBe('function');
    expect(getErrorMessage(new Error('e'))).toBe('e');
  });

  // ---- TDD errorHandler exports -------------------------------------------

  it('exports classifyErrorTDD as a function (distinct from classifyError)', () => {
    expect(typeof classifyErrorTDD).toBe('function');
    expect(classifyErrorTDD).not.toBe(classifyError);
  });

  it('classifyErrorTDD returns a string ErrorType', () => {
    // errorHandler.ts ErrorType members are capitalised strings
    const result = classifyErrorTDD({ status: 400, message: 'bad' });
    expect(typeof result).toBe('string');
  });

  it('exports shouldRetry as a function', () => {
    expect(typeof shouldRetry).toBe('function');
  });

  it('exports calculateBackoff as a function', () => {
    expect(typeof calculateBackoff).toBe('function');
    expect(calculateBackoff(0)).toBe(1000);
  });

  it('exports extractErrorMessage as a function', () => {
    expect(typeof extractErrorMessage).toBe('function');
    expect(extractErrorMessage(new Error('msg'))).toBe('msg');
  });

  it('exports handleApiError as a function', () => {
    expect(typeof handleApiError).toBe('function');
  });

  it('exports ErrorHandler as a class (constructor function)', () => {
    expect(typeof ErrorHandler).toBe('function');
    const handler = new ErrorHandler({ maxRetries: 1 });
    expect(handler).toBeInstanceOf(ErrorHandler);
  });

  it('ErrorHandler.execute succeeds via index import', async () => {
    const handler = new ErrorHandler();
    const result = await handler.execute(() => Promise.resolve(42));
    expect(result).toBe(42);
  });
});
