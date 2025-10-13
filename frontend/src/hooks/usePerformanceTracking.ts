/**
 * usePerformanceTracking Hook
 *
 * React hook for tracking operation performance with automatic cleanup and error handling.
 * Integrates with performance budgets to provide warnings when operations are slow.
 *
 * Usage:
 * ```typescript
 * const { trackOperation } = usePerformanceTracking();
 *
 * const handleExport = async () => {
 *   const result = await trackOperation('export-pdf', async () => {
 *     return await bookClient.exportPDF(bookId);
 *   }, { bookId, format: 'pdf' });
 *
 *   if (result.exceeded_budget) {
 *     console.warn(`Export took ${result.duration}ms`);
 *   }
 * };
 * ```
 *
 * @module hooks/usePerformanceTracking
 */

import { useCallback, useRef } from 'react';
import { PerformanceTracker, type OperationMetric } from '@/lib/performance/metrics';
import { getBudget } from '@/lib/performance/budgets';

/**
 * Result of a tracked operation
 */
export interface TrackedOperationResult<T = unknown> {
  /** Result of the operation */
  data: T;
  /** Performance metric */
  metric: OperationMetric;
}

/**
 * Hook for tracking operation performance
 *
 * Features:
 * - Automatic performance measurement
 * - Budget validation with warnings
 * - Error handling with cleanup
 * - Metadata support for context
 * - Nested operation support
 *
 * @returns Object with trackOperation function
 */
export function usePerformanceTracking() {
  // Track active trackers for cleanup on unmount
  const activeTrackers = useRef<Set<PerformanceTracker>>(new Set());

  /**
   * Track an operation's performance
   *
   * @param operationName - Name of the operation (should match a budget in budgets.ts)
   * @param operation - Async function to track
   * @param metadata - Additional context metadata
   * @returns Promise resolving to operation result and performance metric
   *
   * @example
   * ```typescript
   * // Track a simple operation
   * const result = await trackOperation('book-load', async () => {
   *   return await bookClient.getBook(bookId);
   * });
   *
   * // With metadata
   * const result = await trackOperation('export-pdf', async () => {
   *   return await bookClient.exportPDF(bookId);
   * }, { bookId, chapterCount: 10 });
   *
   * // Check budget
   * if (result.metric.exceeded_budget) {
   *   toast.warning('Export is taking longer than expected');
   * }
   * ```
   */
  const trackOperation = useCallback(
    async <T = unknown>(
      operationName: string,
      operation: () => Promise<T>,
      metadata?: Record<string, unknown>
    ): Promise<TrackedOperationResult<T>> => {
      // Get budget for this operation
      const budget = getBudget(operationName);
      const budgetMs = budget?.target;

      // Create tracker
      const tracker = new PerformanceTracker(operationName, budgetMs, metadata);
      activeTrackers.current.add(tracker);

      try {
        // Execute the operation
        const data = await operation();

        // End tracking and get metric
        const metric = tracker.end();

        // Log warnings if budget exceeded
        if (metric.exceeded_budget && budget) {
          const overrun = metric.duration - budget.target;
          console.warn(
            `⚠️ [Performance] ${operationName} exceeded budget:`,
            `${metric.duration}ms (budget: ${budget.target}ms, overrun: +${overrun}ms)`
          );
        }

        return { data, metric };
      } catch (error) {
        // End tracking even on error
        const metric = tracker.end({ error: error instanceof Error ? error.message : 'Unknown error' });

        // Log error with performance context
        console.error(
          `❌ [Performance] ${operationName} failed after ${metric.duration}ms:`,
          error
        );

        // Re-throw the error so caller can handle it
        throw error;
      } finally {
        // Cleanup
        activeTrackers.current.delete(tracker);
      }
    },
    []
  );

  /**
   * Track a synchronous operation
   *
   * @param operationName - Name of the operation
   * @param operation - Synchronous function to track
   * @param metadata - Additional context metadata
   * @returns Operation result and performance metric
   */
  const trackSync = useCallback(
    <T = unknown>(
      operationName: string,
      operation: () => T,
      metadata?: Record<string, unknown>
    ): TrackedOperationResult<T> => {
      const budget = getBudget(operationName);
      const budgetMs = budget?.target;

      const tracker = new PerformanceTracker(operationName, budgetMs, metadata);
      activeTrackers.current.add(tracker);

      try {
        const data = operation();
        const metric = tracker.end();

        if (metric.exceeded_budget && budget) {
          const overrun = metric.duration - budget.target;
          console.warn(
            `⚠️ [Performance] ${operationName} exceeded budget:`,
            `${metric.duration}ms (budget: ${budget.target}ms, overrun: +${overrun}ms)`
          );
        }

        return { data, metric };
      } catch (error) {
        const metric = tracker.end({ error: error instanceof Error ? error.message : 'Unknown error' });
        console.error(
          `❌ [Performance] ${operationName} failed after ${metric.duration}ms:`,
          error
        );
        throw error;
      } finally {
        activeTrackers.current.delete(tracker);
      }
    },
    []
  );

  /**
   * Create a manual tracker for advanced use cases
   *
   * Useful when you need to track performance across multiple function calls
   * or when the operation isn't a single async function.
   *
   * @param operationName - Name of the operation
   * @param metadata - Additional context metadata
   * @returns Object with end() function to complete tracking
   *
   * @example
   * ```typescript
   * const tracker = createTracker('complex-operation', { phase: 'init' });
   *
   * // ... do some work ...
   * await step1();
   *
   * // ... more work ...
   * await step2();
   *
   * // End tracking
   * const metric = tracker.end();
   * ```
   */
  const createTracker = useCallback(
    (operationName: string, metadata?: Record<string, unknown>) => {
      const budget = getBudget(operationName);
      const budgetMs = budget?.target;

      const tracker = new PerformanceTracker(operationName, budgetMs, metadata);
      activeTrackers.current.add(tracker);

      return {
        /**
         * End tracking and return metric
         * @param additionalMetadata - Additional metadata to include
         */
        end: (additionalMetadata?: Record<string, unknown>): OperationMetric => {
          const metric = tracker.end(additionalMetadata);
          activeTrackers.current.delete(tracker);

          if (metric.exceeded_budget && budget) {
            const overrun = metric.duration - budget.target;
            console.warn(
              `⚠️ [Performance] ${operationName} exceeded budget:`,
              `${metric.duration}ms (budget: ${budget.target}ms, overrun: +${overrun}ms)`
            );
          }

          return metric;
        },

        /**
         * Cancel tracking without reporting
         */
        cancel: () => {
          tracker.cancel();
          activeTrackers.current.delete(tracker);
        },
      };
    },
    []
  );

  return {
    /** Track an async operation */
    trackOperation,
    /** Track a synchronous operation */
    trackSync,
    /** Create a manual tracker for advanced use cases */
    createTracker,
  };
}
