/**
 * Unit tests for AI Error Handler
 */

import { handleAIServiceError, createRetryHandler } from '../aiErrorHandler';
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

    it('should classify a 402 as an entitlement denial with an upgrade path (not retryable)', async () => {
      // Backend structured 402 (no error_type field — derived from status).
      const error = new Error(
        'Request failed: 402 {"error":"Your plan does not include this feature.","error_code":"ENTITLEMENT_REQUIRED","status_code":402}'
      );
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result.canRetry).toBe(false);
      expect(result.data).toBeUndefined();
      expect(result.error).toContain('plan');

      // Notification is an entitlement type, not retryable, and no onRetry wired.
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'entitlement',
          retryable: false,
        }),
        expect.not.objectContaining({ onRetry: expect.anything() })
      );
    });

    it('should classify a 402 via an attached statusCode (bookClient.aiError style)', async () => {
      // bookClient.aiError surfaces detail.error as the message (no digits) and
      // attaches statusCode — the message alone would misclassify as a 500.
      const error = Object.assign(
        new Error('Your plan does not include this feature.'),
        { statusCode: 402 }
      );

      const result = await handleAIServiceError(error);

      expect(result.canRetry).toBe(false);
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'entitlement', retryable: false }),
        expect.anything()
      );
    });

    it('should handle service unavailable without cached content', async () => {
      const error = new Error('Failed: 503 Service Unavailable');
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result.error).toContain('unavailable');
      expect(result.canRetry).toBe(true);

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

    it('shows the quota cap itself, not a generic retry-in-minutes message (#766)', async () => {
      const detail =
        'AI usage limit reached (50 generations per day on the pro plan). It resets at midnight UTC.';
      const error = Object.assign(new Error(detail), { statusCode: 429 });

      const result = await handleAIServiceError(error);

      expect(result.error).toBe(detail);
      expect(result.canRetry).toBe(false);
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'AI usage limit reached',
          details: detail,
          retryable: false,
        }),
        expect.any(Object)
      );
    });

    it.each([
      ['day', 'Daily AI limit reached'],
      ['month', 'Monthly AI limit reached'],
    ])('names the allowance that ran out when the 429 says which (%s) (#803)', async (period, title) => {
      // The period comes from the X-AI-Quota-Period header, so the wording of
      // the message does not have to be recognised.
      const error = Object.assign(new Error('You have used your allowance.'), {
        statusCode: 429,
        quotaPeriod: period,
      });
      const onRetry = jest.fn();

      const result = await handleAIServiceError(error, onRetry);

      expect(result).toEqual({ error: 'You have used your allowance.', canRetry: false });
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({ message: title, details: 'You have used your allowance.', retryable: false }),
        expect.not.objectContaining({ onRetry })
      );
    });

    it('offers a retry for a provider rate limit, with the wait the backend gave in seconds (#803)', async () => {
      const error = Object.assign(new Error('AI service rate limit exceeded'), {
        statusCode: 429,
        retryAfter: 4,
      });

      const result = await handleAIServiceError(error, jest.fn());

      expect(result.canRetry).toBe(true);
      expect(result.retryAfter).toBe(4);
      expect(result.error).toBe('AI service rate limit reached. Please wait 4 seconds before retrying.');
      // The notification's hint says the same wait, not "1 minutes".
      expect(ErrorNotification.showErrorNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestedActions: expect.arrayContaining(['Estimated wait time: 4 seconds']),
        }),
        expect.any(Object)
      );
    });

    it('shows what the backend said about a request it refused, not a generic line (#803)', async () => {
      const message = 'This text is longer than the limit of 32,000 characters. Try a shorter section.';
      const error = Object.assign(new Error(message), { statusCode: 422 });

      const result = await handleAIServiceError(error);

      expect(result).toMatchObject({ error: message, canRetry: false });
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
