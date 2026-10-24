/**
 * Retry Queue Utility
 *
 * Manages offline operations with automatic retry when connection is restored
 */

import { ErrorHandler, calculateBackoff } from '@/lib/errors/errorHandler';

export interface QueuedOperation<T> {
  id: string;
  operation: () => Promise<T>;
  retryCount: number;
  maxRetries: number;
  /** Operations sharing a group run one at a time, in the order queued (#873). */
  group: string;
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
  private timer: ReturnType<typeof setTimeout> | undefined;
  private failedRounds = 0;

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
      group?: string;
      onSuccess?: (result: T) => void;
      onError?: (error: unknown) => void;
    } = {}
  ): void {
    this.queue.set(id, {
      id,
      operation,
      retryCount: 0,
      maxRetries: options.maxRetries ?? 3,
      group: options.group ?? id,
      onSuccess: options.onSuccess,
      onError: options.onError,
    });
  }

  /**
   * Remove an operation from the queue
   */
  remove(id: string): boolean {
    const removed = this.queue.delete(id);
    this.schedule();
    return removed;
  }

  /**
   * Clear all queued operations
   */
  clear(): void {
    this.queue.clear();
    this.schedule();
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
   * Check if any queued operation's id starts with a prefix
   */
  hasPrefix(prefix: string): boolean {
    return Array.from(this.queue.keys()).some(id => id.startsWith(prefix));
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
    const drained = new Set(this.queue.keys());

    try {
      // Groups run in parallel; a group runs in the order it was queued
      // (Map keeps insertion order), so an older save cannot land last (#873).
      const groups = new Map<string, QueuedOperation<any>[]>();
      for (const op of this.queue.values()) {
        groups.set(op.group, [...(groups.get(op.group) ?? []), op]);
      }
      await Promise.allSettled(
        Array.from(groups.values()).map(async ops => {
          for (const op of ops) {
            await this.processOperation(op);
            // Still queued: it waits for a retry, and so does the rest of its group.
            if (this.queue.has(op.id)) break;
          }
        })
      );
    } finally {
      this.processing = false;
    }

    // Queued during the drain: nothing else would start them until the next
    // `online` event (#873).
    if (Array.from(this.queue.keys()).some(id => !drained.has(id))) {
      await this.processQueue();
    }
    this.schedule();
  }

  /**
   * Op left queued with retries remaining: retry on a backoff timer while
   * online, since `online` may never fire (#1067). Offline waits for `online`.
   */
  private schedule(): void {
    clearTimeout(this.timer);
    this.timer = undefined;
    if (this.queue.size === 0) {
      this.failedRounds = 0;
      return;
    }
    if (this.processing || (typeof navigator !== 'undefined' && !navigator.onLine)) return;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      void this.processQueue();
    }, calculateBackoff(this.failedRounds++));
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
