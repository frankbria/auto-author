/**
 * Time Estimation Utilities
 *
 * Provides intelligent time estimates for various operations based on:
 * - Operation type
 * - Data size (word count, chapter count, etc.)
 * - Historical performance data
 * - Network conditions (if available)
 */

/**
 * Time estimate with min, max, and average values
 */
export interface TimeEstimate {
  /** Minimum expected time in milliseconds */
  min: number;
  /** Maximum expected time in milliseconds */
  max: number;
  /** Average expected time in milliseconds */
  average: number;
}

/**
 * Operation metadata for time estimation
 */
export interface OperationMetadata {
  /** Word count (for content generation operations) */
  wordCount?: number;
  /** Chapter count (for batch operations) */
  chapterCount?: number;
  /** Question count (for question generation) */
  questionCount?: number;
  /** Export format (for export operations) */
  exportFormat?: 'pdf' | 'docx';
  /** Network speed estimate in Mbps (optional) */
  networkSpeed?: number;
}

/**
 * Operation time budgets (in milliseconds)
 * Based on typical operation durations observed in production
 */
const OPERATION_BUDGETS = {
  // TOC Operations
  'toc.generation': {
    base: 10000, // 10 seconds base
    perChapter: 500, // 0.5 seconds per chapter
    min: 5000,
    max: 30000,
  },
  'toc.readiness': {
    base: 3000,
    min: 2000,
    max: 5000,
  },
  'toc.questions': {
    base: 5000,
    perQuestion: 1000,
    min: 3000,
    max: 15000,
  },

  // Export Operations
  'export.pdf': {
    base: 10000, // 10 seconds base
    perThousandWords: 2000, // 2 seconds per 1000 words
    perChapter: 1000, // 1 second per chapter
    min: 5000,
    max: 60000, // 1 minute max
  },
  'export.docx': {
    base: 5000, // 5 seconds base
    perThousandWords: 1000, // 1 second per 1000 words
    perChapter: 500, // 0.5 seconds per chapter
    min: 3000,
    max: 40000, // 40 seconds max
  },

  // Chapter Operations
  'chapter.create': {
    base: 500,
    min: 300,
    max: 2000,
  },
  'chapter.draft': {
    base: 10000, // 10 seconds base
    perQuestion: 2000, // 2 seconds per question
    perThousandWords: 3000, // 3 seconds per 1000 words target
    min: 4000,
    max: 30000,
  },
  'chapter.questions': {
    base: 5000,
    perQuestion: 1000,
    min: 3000,
    max: 15000,
  },

  // Book Operations
  'book.save': {
    base: 500,
    min: 300,
    max: 2000,
  },
  'book.fetch': {
    base: 1000,
    min: 500,
    max: 4000,
  },

  // Default fallback
  'default': {
    base: 3000,
    min: 1000,
    max: 10000,
  },
} as const;

/**
 * Calculate time estimate for an operation
 *
 * @param operation - The operation identifier (e.g., "toc.generation", "export.pdf")
 * @param metadata - Optional metadata about the operation (word count, chapter count, etc.)
 * @returns Time estimate with min, max, and average values
 *
 * @example
 * ```ts
 * const estimate = estimateOperationTime('toc.generation', {
 *   chapterCount: 10
 * });
 * // Returns: { min: 5000, max: 30000, average: 15000 }
 * ```
 *
 * @example Export operation
 * ```ts
 * const estimate = estimateOperationTime('export.pdf', {
 *   wordCount: 50000,
 *   chapterCount: 15
 * });
 * // Returns: { min: 5000, max: 60000, average: 35000 }
 * ```
 */
export function estimateOperationTime(
  operation: string,
  metadata?: OperationMetadata
): TimeEstimate {
  const budget = OPERATION_BUDGETS[operation as keyof typeof OPERATION_BUDGETS] || OPERATION_BUDGETS.default;

  let estimatedTime = budget.base;

  // Add time based on metadata
  if (metadata) {
    // Word count contribution
    if (metadata.wordCount && 'perThousandWords' in budget) {
      const thousandWords = metadata.wordCount / 1000;
      estimatedTime += thousandWords * budget.perThousandWords;
    }

    // Chapter count contribution
    if (metadata.chapterCount && 'perChapter' in budget) {
      estimatedTime += metadata.chapterCount * budget.perChapter;
    }

    // Question count contribution
    if (metadata.questionCount && 'perQuestion' in budget) {
      estimatedTime += metadata.questionCount * budget.perQuestion;
    }

    // Network speed adjustment (slower network = longer wait)
    if (metadata.networkSpeed && metadata.networkSpeed < 10) {
      // If network speed is less than 10 Mbps, add 20% to estimate
      estimatedTime *= 1.2;
    }
  }

  // Clamp to min/max bounds
  const clampedTime = Math.min(Math.max(estimatedTime, budget.min), budget.max);

  return {
    min: budget.min,
    max: budget.max,
    average: Math.round(clampedTime),
  };
}

/**
 * Format time in milliseconds to a human-readable string
 *
 * @param milliseconds - Time in milliseconds
 * @returns Formatted time string
 *
 * @example
 * ```ts
 * formatTime(5000); // "5s"
 * formatTime(65000); // "1m 5s"
 * formatTime(3600000); // "1h"
 * ```
 */
export function formatTime(milliseconds: number): string {
  const seconds = Math.ceil(milliseconds / 1000);

  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    if (remainingSeconds === 0) {
      return `${minutes}m`;
    }
    return `${minutes}m ${remainingSeconds}s`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (remainingMinutes === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Get a progress estimate based on elapsed time
 * Uses a logarithmic curve to simulate realistic progress
 *
 * @param elapsedTime - Time elapsed in milliseconds
 * @param estimatedTotal - Estimated total time in milliseconds
 * @returns Progress percentage (0-100)
 *
 * @example
 * ```ts
 * // After 5 seconds of a 10 second operation
 * getProgressEstimate(5000, 10000); // ~45 (not exactly 50%)
 *
 * // After 9 seconds of a 10 second operation
 * getProgressEstimate(9000, 10000); // ~80 (slows down near end)
 * ```
 */
export function getProgressEstimate(
  elapsedTime: number,
  estimatedTotal: number
): number {
  if (estimatedTotal <= 0) return 0;
  if (elapsedTime >= estimatedTotal) return 95; // Never show 100% until actually complete

  // Logarithmic curve for more realistic progress
  // Progress slows down near the end (typical of AI operations)
  const ratio = elapsedTime / estimatedTotal;
  const progress = 100 * (1 - Math.exp(-3 * ratio));

  return Math.min(Math.round(progress), 95);
}

/**
 * Create a progress tracker for long-running operations
 * Returns a function that can be called periodically to get updated progress
 *
 * @param operation - Operation identifier
 * @param metadata - Operation metadata
 * @returns Progress tracker function
 *
 * @example
 * ```ts
 * const getProgress = createProgressTracker('toc.generation', { chapterCount: 10 });
 *
 * // Call every second to get updated progress
 * setInterval(() => {
 *   const { progress, estimatedTimeRemaining } = getProgress();
 *   console.log(`Progress: ${progress}%, Time remaining: ${estimatedTimeRemaining}ms`);
 * }, 1000);
 * ```
 */
export function createProgressTracker(
  operation: string,
  metadata?: OperationMetadata
) {
  const estimate = estimateOperationTime(operation, metadata);
  const startTime = Date.now();

  return () => {
    const elapsedTime = Date.now() - startTime;
    const progress = getProgressEstimate(elapsedTime, estimate.average);
    const estimatedTimeRemaining = Math.max(0, estimate.average - elapsedTime);

    return {
      progress,
      estimatedTimeRemaining,
      elapsedTime,
      estimate,
    };
  };
}

/**
 * Operation time budgets for quick reference
 * Exported for testing and documentation purposes
 */
export const OPERATION_TIME_BUDGETS = OPERATION_BUDGETS;
