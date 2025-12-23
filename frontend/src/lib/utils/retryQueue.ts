/**
 * Retry Queue Utility
 *
 * Manages offline operations with automatic retry when connection is restored
 */

import { ErrorHandler } from '@/lib/errors/errorHandler';

export interface QueuedOperation<T> {
  id: string;
  operation: () => Promise<T>;
  retryCount: number;
  maxRetries: number;
  onSuccess?: (result: T) => void;
  onError?: (error: unknown) => void;
}

/**
 * RetryQueue manages operations that failed due to network issues
 * and retries them when connectivity is restored
 */
export class RetryQueue {
  private queue: Map<string, QueuedOperation<any>>;
  private processing: boolean;
  private errorHandler: ErrorHandler;

  constructor() {
    this.queue = new Map();
    this.processing = false;
    this.errorHandler = new ErrorHandler({
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 30000,
    });

    // Listen for online events to process queue
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => this.processQueue());
    }
  }

  /**
   * Add an operation to the retry queue
   */
  add<T>(
    id: string,
    operation: () => Promise<T>,
    options: {
      maxRetries?: number;
      onSuccess?: (result: T) => void;
      onError?: (error: unknown) => void;
    } = {}
  ): void {
    this.queue.set(id, {
      id,
      operation,
      retryCount: 0,
      maxRetries: options.maxRetries ?? 3,
      onSuccess: options.onSuccess,
      onError: options.onError,
    });
  }

  /**
   * Remove an operation from the queue
   */
  remove(id: string): boolean {
    return this.queue.delete(id);
  }

  /**
   * Clear all queued operations
   */
  clear(): void {
    this.queue.clear();
  }

  /**
   * Get the current queue size
   */
  size(): number {
    return this.queue.size;
  }

  /**
   * Check if an operation is queued
   */
  has(id: string): boolean {
    return this.queue.has(id);
  }

  /**
   * Process all queued operations
   */
  async processQueue(): Promise<void> {
    // Prevent concurrent processing
    if (this.processing || this.queue.size === 0) {
      return;
    }

    this.processing = true;

    try {
      // Process operations in parallel
      const operations = Array.from(this.queue.values());
      await Promise.allSettled(
        operations.map(op => this.processOperation(op))
      );
    } finally {
      this.processing = false;
    }
  }

  /**
   * Process a single queued operation
   */
  private async processOperation<T>(
    queuedOp: QueuedOperation<T>
  ): Promise<void> {
    try {
      // Execute with retry logic
      const result = await this.errorHandler.execute(queuedOp.operation);

      // Remove from queue on success
      this.queue.delete(queuedOp.id);

      // Call success callback
      if (queuedOp.onSuccess) {
        queuedOp.onSuccess(result);
      }
    } catch (error) {
      queuedOp.retryCount++;

      // Check if max retries exceeded
      if (queuedOp.retryCount >= queuedOp.maxRetries) {
        this.queue.delete(queuedOp.id);

        // Call error callback
        if (queuedOp.onError) {
          queuedOp.onError(error);
        }
      }
      // Otherwise, keep in queue for next attempt
    }
  }

  /**
   * Get all queued operation IDs
   */
  getQueuedOperations(): string[] {
    return Array.from(this.queue.keys());
  }
}

// Global retry queue instance
export const retryQueue = new RetryQueue();
