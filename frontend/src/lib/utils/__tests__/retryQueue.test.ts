/**
 * Tests for RetryQueue utility
 */

import { RetryQueue } from '../retryQueue';

describe('RetryQueue', () => {
  let queue: RetryQueue;

  beforeEach(() => {
    queue = new RetryQueue();
  });

  afterEach(() => {
    queue.clear();
  });

  describe('add', () => {
    it('should add an operation to the queue', () => {
      const operation = jest.fn();
      queue.add('test-1', operation);

      expect(queue.has('test-1')).toBe(true);
      expect(queue.size()).toBe(1);
    });

    it('should accept optional callbacks', () => {
      const operation = jest.fn();
      const onSuccess = jest.fn();
      const onError = jest.fn();

      queue.add('test-1', operation, {
        onSuccess,
        onError,
        maxRetries: 5,
      });

      expect(queue.has('test-1')).toBe(true);
    });
  });

  describe('remove', () => {
    it('should remove an operation from the queue', () => {
      const operation = jest.fn();
      queue.add('test-1', operation);

      expect(queue.has('test-1')).toBe(true);

      const removed = queue.remove('test-1');

      expect(removed).toBe(true);
      expect(queue.has('test-1')).toBe(false);
      expect(queue.size()).toBe(0);
    });

    it('should return false when removing non-existent operation', () => {
      const removed = queue.remove('non-existent');

      expect(removed).toBe(false);
    });
  });

  describe('clear', () => {
    it('should clear all operations', () => {
      queue.add('test-1', jest.fn());
      queue.add('test-2', jest.fn());
      queue.add('test-3', jest.fn());

      expect(queue.size()).toBe(3);

      queue.clear();

      expect(queue.size()).toBe(0);
    });
  });

  describe('processQueue', () => {
    it('should process successful operations', async () => {
      const operation = jest.fn().mockResolvedValue('success');
      const onSuccess = jest.fn();

      queue.add('test-1', operation, { onSuccess });

      await queue.processQueue();

      expect(operation).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalledWith('success');
      expect(queue.has('test-1')).toBe(false);
    });

    it('should call onError callback after max retries exceeded', async () => {
      // The ErrorHandler internally retries, then queue increments retryCount on each failure.
      // When retryCount >= maxRetries, onError is called and operation is removed.
      const operation = jest.fn().mockRejectedValue(new Error('Network error'));
      const onError = jest.fn();

      queue.add('test-1', operation, { onError, maxRetries: 0 });

      // Single attempt - maxRetries is 0, so it should fail immediately
      await queue.processQueue();

      expect(queue.has('test-1')).toBe(false);
      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });

    it('should not process queue concurrently', async () => {
      const operation = jest.fn().mockResolvedValue('success');

      queue.add('test-1', operation);

      // Start two concurrent process calls
      const promise1 = queue.processQueue();
      const promise2 = queue.processQueue();

      await Promise.all([promise1, promise2]);

      // Operation should only be called once due to concurrent processing guard
      expect(operation).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple operations in parallel', async () => {
      const op1 = jest.fn().mockResolvedValue('result1');
      const op2 = jest.fn().mockResolvedValue('result2');
      const op3 = jest.fn().mockResolvedValue('result3');

      queue.add('test-1', op1);
      queue.add('test-2', op2);
      queue.add('test-3', op3);

      await queue.processQueue();

      expect(op1).toHaveBeenCalled();
      expect(op2).toHaveBeenCalled();
      expect(op3).toHaveBeenCalled();
      expect(queue.size()).toBe(0);
    });
  });

  describe('getQueuedOperations', () => {
    it('should return all queued operation IDs', () => {
      queue.add('test-1', jest.fn());
      queue.add('test-2', jest.fn());
      queue.add('test-3', jest.fn());

      const operations = queue.getQueuedOperations();

      expect(operations).toEqual(['test-1', 'test-2', 'test-3']);
    });

    it('should return empty array when queue is empty', () => {
      const operations = queue.getQueuedOperations();

      expect(operations).toEqual([]);
    });
  });

  describe('online event listener', () => {
    it('should process queue when browser comes online', async () => {
      const operation = jest.fn().mockResolvedValue('success');
      queue.add('test-1', operation);

      // Simulate browser coming online
      const onlineEvent = new Event('online');
      window.dispatchEvent(onlineEvent);

      // Wait for async processing
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(operation).toHaveBeenCalled();
    });
  });
});
