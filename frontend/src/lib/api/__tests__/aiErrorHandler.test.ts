/**
 * Unit tests for AI Error Handler
 */

import { handleAIServiceError, createRetryHandler, isFromCache } from '../aiErrorHandler';
import * as ErrorNotification from '@/components/errors/ErrorNotification';

// Mock the error notification module
jest.mock('@/components/errors/ErrorNotification', () => ({
  showErrorNotification: jest.fn(),
}));

describe('aiErrorHandler', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('handleAIServiceError', () => {
    it('should handle rate limit error with retry after', async () => {
      const error = new Error('Failed to generate: 429 {"message":"Rate limited","status_code":429,"error_type":"rate_limit","estimated_retry_after":120}');
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result.error).toContain('rate limit');
      expect(result.retryAfter).toBe(120);
      expect(result.canRetry).toBe(true);
      expect(result.data).toBeUndefined();
      expect(result.fromCache).toBeUndefined();

      // Verify error notification was shown
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'ai_service',
          retryable: true,
        }),
        expect.objectContaining({
          onRetry,
          duration: 15000,
        })
      );
    });

    it('should handle cached content fallback', async () => {
      const cachedData = { questions: ['Q1', 'Q2', 'Q3'] };
      const error = new Error(
        `Failed to generate: 503 ${JSON.stringify({
          message: 'Service unavailable',
          status_code: 503,
          error_type: 'service_unavailable',
          cached_content_available: true,
          cached_content: cachedData,
        })}`
      );
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result.data).toEqual(cachedData);
      expect(result.fromCache).toBe(true);
      expect(result.canRetry).toBe(true);
      expect(result.error).toContain('unavailable');

      // Verify warning notification was shown for cached content
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'ai_service',
          message: 'Using previously generated content',
        }),
        expect.objectContaining({
          onRetry,
          duration: 10000,
        })
      );
    });

    it('should handle network errors', async () => {
      const error = new Error('Failed to fetch: network error');
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result.error).toMatch(/network|connection/i);
      expect(result.canRetry).toBe(true);
      expect(result.data).toBeUndefined();

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          details: expect.stringMatching(/network|connection/i),
          suggestedActions: expect.arrayContaining([
            expect.stringMatching(/internet.*connection|connection/i),
          ]),
        }),
        expect.any(Object)
      );
    });

    it('should handle service unavailable without cached content', async () => {
      const error = new Error('Failed: 503 Service Unavailable');
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result.error).toContain('unavailable');
      expect(result.canRetry).toBe(true);
      expect(result.fromCache).toBeUndefined();

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          retryable: true,
          suggestedActions: expect.arrayContaining([
            expect.stringContaining('AI service is experiencing issues'),
          ]),
        }),
        expect.objectContaining({
          onRetry,
        })
      );
    });

    it('should handle validation errors as non-retryable', async () => {
      const error = new Error('Failed: 422 {"message":"Invalid input","status_code":422,"error_type":"validation"}');

      const result = await handleAIServiceError(error);

      expect(result.error).toContain('Invalid');
      expect(result.canRetry).toBe(false);

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'permanent',
          retryable: false,
          suggestedActions: expect.arrayContaining([
            expect.stringContaining('Check your input'),
          ]),
        }),
        expect.any(Object)
      );
    });

    it('should handle unknown errors gracefully', async () => {
      const error = new Error('Something went wrong');

      const result = await handleAIServiceError(error);

      expect(result.error).toBeTruthy();
      expect(result.canRetry).toBe(false);

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalled();
    });

    it('should handle non-Error objects', async () => {
      const error = { message: 'Custom error', status_code: 500 };

      const result = await handleAIServiceError(error);

      expect(result.error).toContain('Custom error');

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalled();
    });

    it('should handle string errors', async () => {
      const error = 'Simple error string';

      const result = await handleAIServiceError(error);

      expect(result.error).toBeTruthy();

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalled();
    });

    it('should extract status code from error message', async () => {
      const error = new Error('Request failed with status 429');

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(true); // 429 is retryable

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          statusCode: 429,
          type: 'ai_service',
        }),
        expect.any(Object)
      );
    });

    it('should show estimated wait time for rate limits', async () => {
      const error = new Error(
        `Failed: 429 ${JSON.stringify({
          message: 'Rate limited',
          status_code: 429,
          error_type: 'rate_limit',
          estimated_retry_after: 300, // 5 minutes
        })}`
      );

      const result = await handleAIServiceError(error);

      expect(result.retryAfter).toBe(300);

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestedActions: expect.arrayContaining([
            expect.stringMatching(/5 minutes/),
          ]),
        }),
        expect.any(Object)
      );
    });

    it('should handle errors without onRetry callback', async () => {
      const error = new Error('Failed: 503 Service Unavailable');

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(true);

      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.any(Object),
        expect.objectContaining({
          onRetry: undefined,
        })
      );
    });
  });

  describe('createRetryHandler', () => {
    it('should create retry handler that calls retry function immediately when no retryAfter', () => {
      const retryFn = jest.fn();
      const handler = createRetryHandler(retryFn);

      handler();

      expect(retryFn).toHaveBeenCalledTimes(1);
    });

    it('should prompt user before retrying when retryAfter is set', () => {
      const retryFn = jest.fn();
      const handler = createRetryHandler(retryFn, 120); // 2 minutes

      // Mock confirm to return true
      global.confirm = jest.fn(() => true);

      handler();

      expect(global.confirm).toHaveBeenCalledWith(
        expect.stringContaining('2 minute')
      );
      expect(retryFn).toHaveBeenCalledTimes(1);
    });

    it('should not retry if user cancels confirmation', () => {
      const retryFn = jest.fn();
      const handler = createRetryHandler(retryFn, 120);

      // Mock confirm to return false
      global.confirm = jest.fn(() => false);

      handler();

      expect(global.confirm).toHaveBeenCalled();
      expect(retryFn).not.toHaveBeenCalled();
    });

    it('should handle async retry functions', async () => {
      const retryFn = jest.fn(async () => Promise.resolve());
      const handler = createRetryHandler(retryFn);

      handler();

      // Allow async function to execute
      await new Promise(resolve => setTimeout(resolve, 0));

      expect(retryFn).toHaveBeenCalledTimes(1);
    });
  });

  describe('isFromCache', () => {
    it('should return true for cached results', () => {
      const result = {
        data: { questions: ['Q1'] },
        fromCache: true,
      };

      expect(isFromCache(result)).toBe(true);
    });

    it('should return false for non-cached results', () => {
      const result = {
        data: { questions: ['Q1'] },
        fromCache: false,
      };

      expect(isFromCache(result)).toBe(false);
    });

    it('should return false for results without data', () => {
      const result = {
        fromCache: true,
      };

      expect(isFromCache(result)).toBe(false);
    });

    it('should return false for results without fromCache flag', () => {
      const result = {
        data: { questions: ['Q1'] },
      };

      expect(isFromCache(result)).toBe(false);
    });

    it('should return false for error results', () => {
      const result = {
        error: 'Failed',
        canRetry: true,
      };

      expect(isFromCache(result)).toBe(false);
    });
  });

  describe('error message extraction', () => {
    it('should extract message from JSON error response', async () => {
      const error = new Error(
        `Failed: 500 ${JSON.stringify({
          detail: 'Internal server error',
          status_code: 500,
        })}`
      );

      const result = await handleAIServiceError(error);

      expect(result.error).toContain('Internal server error');
    });

    it('should handle malformed JSON gracefully', async () => {
      const error = new Error('Failed: 500 {invalid json}');

      const result = await handleAIServiceError(error);

      expect(result.error).toBeTruthy();
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalled();
    });

    it('should prioritize message over detail in JSON', async () => {
      const error = new Error(
        `Failed: 500 ${JSON.stringify({
          message: 'Custom message',
          detail: 'Detail message',
        })}`
      );

      const result = await handleAIServiceError(error);

      expect(result.error).toContain('Custom message');
    });
  });

  describe('error type determination', () => {
    it('should identify rate limit errors from status code', async () => {
      const error = new Error('Failed with status 429');

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(true);
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'ai_service',
        }),
        expect.any(Object)
      );
    });

    it('should identify service unavailable errors', async () => {
      const error = new Error('Failed with status 503');

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(true);
      expect(result.error).toContain('unavailable');
    });

    it('should identify validation errors', async () => {
      const error = new Error('Failed with status 422');

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(false);
    });

    it('should identify network errors from message', async () => {
      const error = new Error('Network request failed');

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(true);
      expect(result.error).toMatch(/network|connection/i);
    });
  });
});
