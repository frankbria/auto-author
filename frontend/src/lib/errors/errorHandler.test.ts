import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ErrorType,
  ErrorHandler,
  classifyError,
  shouldRetry,
  calculateBackoff,
  extractErrorMessage,
  handleApiError,
} from './errorHandler';

describe('Error Handler Utility - TDD Implementation', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('Error Classification', () => {
    it('should classify network errors correctly', () => {
      const networkError = new Error('Network request failed');
      networkError.name = 'NetworkError';

      expect(classifyError(networkError)).toBe(ErrorType.NETWORK);
    });

    it('should classify fetch failures as network errors', () => {
      const fetchError = new TypeError('Failed to fetch');

      expect(classifyError(fetchError)).toBe(ErrorType.NETWORK);
    });

    it('should classify 400 status as validation error', () => {
      const validationError = { status: 400, message: 'Invalid input' };

      expect(classifyError(validationError)).toBe(ErrorType.VALIDATION);
    });

    it('should classify 401 status as auth error', () => {
      const authError = { status: 401, message: 'Unauthorized' };

      expect(classifyError(authError)).toBe(ErrorType.AUTH);
    });

    it('should classify 403 status as auth error', () => {
      const forbiddenError = { status: 403, message: 'Forbidden' };

      expect(classifyError(forbiddenError)).toBe(ErrorType.AUTH);
    });

    it('should classify 5xx status as server error', () => {
      const serverError = { status: 500, message: 'Internal server error' };

      expect(classifyError(serverError)).toBe(ErrorType.SERVER);
    });

    it('should classify 503 status as server error', () => {
      const serviceError = { status: 503, message: 'Service unavailable' };

      expect(classifyError(serviceError)).toBe(ErrorType.SERVER);
    });

    it('should classify unknown errors correctly', () => {
      const unknownError = { status: 418, message: "I'm a teapot" };

      expect(classifyError(unknownError)).toBe(ErrorType.UNKNOWN);
    });

    it('should handle errors without status codes', () => {
      const genericError = new Error('Something went wrong');

      expect(classifyError(genericError)).toBe(ErrorType.UNKNOWN);
    });
  });

  describe('Retry Logic', () => {
    it('should retry network errors', () => {
      expect(shouldRetry(ErrorType.NETWORK, 0)).toBe(true);
      expect(shouldRetry(ErrorType.NETWORK, 1)).toBe(true);
      expect(shouldRetry(ErrorType.NETWORK, 2)).toBe(true);
    });

    it('should retry 503 service unavailable errors', () => {
      const error = { status: 503 };
      expect(shouldRetry(classifyError(error), 0)).toBe(true);
    });

    it('should retry 429 rate limit errors', () => {
      const error = { status: 429 };
      expect(shouldRetry(classifyError(error), 0)).toBe(true);
    });

    it('should NOT retry validation errors', () => {
      expect(shouldRetry(ErrorType.VALIDATION, 0)).toBe(false);
    });

    it('should NOT retry auth errors', () => {
      expect(shouldRetry(ErrorType.AUTH, 0)).toBe(false);
    });

    it('should NOT retry after max attempts (3)', () => {
      expect(shouldRetry(ErrorType.NETWORK, 3)).toBe(false);
      expect(shouldRetry(ErrorType.NETWORK, 4)).toBe(false);
    });

    it('should respect max retry limit for retryable errors', () => {
      expect(shouldRetry(ErrorType.NETWORK, 0)).toBe(true);
      expect(shouldRetry(ErrorType.NETWORK, 1)).toBe(true);
      expect(shouldRetry(ErrorType.NETWORK, 2)).toBe(true);
      expect(shouldRetry(ErrorType.NETWORK, 3)).toBe(false);
    });
  });

  describe('Exponential Backoff', () => {
    it('should calculate correct backoff for attempt 0: 1000ms', () => {
      expect(calculateBackoff(0)).toBe(1000);
    });

    it('should calculate correct backoff for attempt 1: 2000ms', () => {
      expect(calculateBackoff(1)).toBe(2000);
    });

    it('should calculate correct backoff for attempt 2: 4000ms', () => {
      expect(calculateBackoff(2)).toBe(4000);
    });

    it('should use exponential formula: 1000 * 2^attempt', () => {
      expect(calculateBackoff(3)).toBe(8000);
      expect(calculateBackoff(4)).toBe(16000);
    });

    it('should have maximum backoff cap at 30 seconds', () => {
      expect(calculateBackoff(10)).toBeLessThanOrEqual(30000);
    });
  });

  describe('Error Message Extraction', () => {
    it('should extract message from Error object', () => {
      const error = new Error('Test error message');
      expect(extractErrorMessage(error)).toBe('Test error message');
    });

    it('should extract message from object with message property', () => {
      const error = { message: 'API error message' };
      expect(extractErrorMessage(error)).toBe('API error message');
    });

    it('should extract detail from object with detail property', () => {
      const error = { detail: 'Detailed error info' };
      expect(extractErrorMessage(error)).toBe('Detailed error info');
    });

    it('should prefer message over detail if both exist', () => {
      const error = { message: 'Primary message', detail: 'Secondary detail' };
      expect(extractErrorMessage(error)).toBe('Primary message');
    });

    it('should handle nested error structures', () => {
      const error = { error: { message: 'Nested error' } };
      expect(extractErrorMessage(error)).toBe('Nested error');
    });

    it('should return default message for unknown error formats', () => {
      const error = { unknownField: 'data' };
      expect(extractErrorMessage(error)).toBe('An unexpected error occurred');
    });

    it('should handle string errors', () => {
      expect(extractErrorMessage('String error')).toBe('String error');
    });

    it('should handle null/undefined errors', () => {
      expect(extractErrorMessage(null)).toBe('An unexpected error occurred');
      expect(extractErrorMessage(undefined)).toBe('An unexpected error occurred');
    });
  });

  describe('ErrorHandler Class', () => {
    let errorHandler: ErrorHandler;
    let mockOperation: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      errorHandler = new ErrorHandler({ maxRetries: 3 });
      mockOperation = vi.fn();
    });

    it('should execute operation successfully on first try', async () => {
      mockOperation.mockResolvedValueOnce({ success: true });

      const result = await errorHandler.execute(mockOperation);

      expect(result).toEqual({ success: true });
      expect(mockOperation).toHaveBeenCalledTimes(1);
    });

    it('should retry on network error and succeed', async () => {
      const networkError = new TypeError('Failed to fetch');
      mockOperation
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce({ success: true });

      const promise = errorHandler.execute(mockOperation);

      // Fast-forward through backoff delays
      await vi.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ success: true });
      expect(mockOperation).toHaveBeenCalledTimes(3);
    });

    it('should NOT retry on validation error', async () => {
      const validationError = { status: 400, message: 'Invalid data' };
      mockOperation.mockRejectedValueOnce(validationError);

      await expect(errorHandler.execute(mockOperation)).rejects.toEqual(validationError);
      expect(mockOperation).toHaveBeenCalledTimes(1);
    });

    it('should stop retrying after max attempts', async () => {
      const networkError = new TypeError('Failed to fetch');
      mockOperation.mockRejectedValue(networkError);

      const promise = errorHandler.execute(mockOperation);
      await vi.runAllTimersAsync();

      await expect(promise).rejects.toEqual(networkError);
      expect(mockOperation).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    it('should apply exponential backoff between retries', async () => {
      const networkError = new TypeError('Failed to fetch');
      mockOperation.mockRejectedValue(networkError);

      const promise = errorHandler.execute(mockOperation);

      // First retry after 1000ms
      await vi.advanceTimersByTimeAsync(999);
      expect(mockOperation).toHaveBeenCalledTimes(1);

      await vi.advanceTimersByTimeAsync(1);
      expect(mockOperation).toHaveBeenCalledTimes(2);

      // Second retry after 2000ms
      await vi.advanceTimersByTimeAsync(1999);
      expect(mockOperation).toHaveBeenCalledTimes(2);

      await vi.advanceTimersByTimeAsync(1);
      expect(mockOperation).toHaveBeenCalledTimes(3);

      await vi.runAllTimersAsync();
      await expect(promise).rejects.toEqual(networkError);
    });

    it('should allow custom max retries configuration', async () => {
      const customHandler = new ErrorHandler({ maxRetries: 1 });
      const networkError = new TypeError('Failed to fetch');
      mockOperation.mockRejectedValue(networkError);

      const promise = customHandler.execute(mockOperation);
      await vi.runAllTimersAsync();

      await expect(promise).rejects.toEqual(networkError);
      expect(mockOperation).toHaveBeenCalledTimes(1); // Initial only, no retries
    });
  });

  describe('handleApiError - High-Level API', () => {
    let mockToast: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockToast = vi.fn();
    });

    it('should handle successful API calls without toast', async () => {
      const successOperation = vi.fn().mockResolvedValue({ data: 'success' });

      const result = await handleApiError(successOperation, mockToast);

      expect(result).toEqual({ data: 'success' });
      expect(mockToast).not.toHaveBeenCalled();
    });

    it('should show toast notification on validation error', async () => {
      const validationError = { status: 400, message: 'Invalid input' };
      const failedOperation = vi.fn().mockRejectedValue(validationError);

      await expect(handleApiError(failedOperation, mockToast)).rejects.toEqual(validationError);

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Validation Error',
        description: 'Invalid input',
        variant: 'destructive',
      });
    });

    it('should show toast notification on auth error', async () => {
      const authError = { status: 401, message: 'Unauthorized' };
      const failedOperation = vi.fn().mockRejectedValue(authError);

      await expect(handleApiError(failedOperation, mockToast)).rejects.toEqual(authError);

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Authentication Error',
        description: 'Unauthorized',
        variant: 'destructive',
      });
    });

    it('should show toast notification on network error after retries exhausted', async () => {
      const networkError = new TypeError('Failed to fetch');
      const failedOperation = vi.fn().mockRejectedValue(networkError);

      const promise = handleApiError(failedOperation, mockToast);
      await vi.runAllTimersAsync();

      await expect(promise).rejects.toEqual(networkError);

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Network Error',
        description: 'Failed to fetch',
        variant: 'destructive',
      });
    });

    it('should retry network errors before showing toast', async () => {
      const networkError = new TypeError('Failed to fetch');
      const retryOperation = vi
        .fn()
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce({ data: 'success' });

      const promise = handleApiError(retryOperation, mockToast);
      await vi.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ data: 'success' });
      expect(mockToast).not.toHaveBeenCalled();
      expect(retryOperation).toHaveBeenCalledTimes(2);
    });

    it('should support custom error messages in toast', async () => {
      const error = { status: 500, message: 'Server crashed' };
      const failedOperation = vi.fn().mockRejectedValue(error);

      const promise = handleApiError(failedOperation, mockToast, {
        customMessage: 'Custom error occurred',
      });

      await vi.runAllTimersAsync();

      await expect(promise).rejects.toEqual(error);

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Server Error',
        description: 'Custom error occurred',
        variant: 'destructive',
      });
    });
  });

  describe('Integration Tests', () => {
    it('should handle real-world API error scenario', async () => {
      const mockToast = vi.fn();
      let attempts = 0;

      const flakeyApiCall = vi.fn().mockImplementation(async () => {
        attempts++;
        if (attempts < 3) {
          throw new TypeError('Failed to fetch');
        }
        return { id: 123, title: 'Book Title' };
      });

      const promise = handleApiError(flakeyApiCall, mockToast);
      await vi.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ id: 123, title: 'Book Title' });
      expect(mockToast).not.toHaveBeenCalled();
      expect(attempts).toBe(3);
    });

    it('should handle permanent failure with toast notification', async () => {
      const mockToast = vi.fn();
      const permanentFailure = vi.fn().mockRejectedValue({
        status: 404,
        message: 'Resource not found',
      });

      await expect(handleApiError(permanentFailure, mockToast)).rejects.toEqual({
        status: 404,
        message: 'Resource not found',
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Error',
        description: 'Resource not found',
        variant: 'destructive',
      });
      expect(permanentFailure).toHaveBeenCalledTimes(1);
    });
  });
});
