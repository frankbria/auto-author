/**
 * Performance Budgets Configuration
 *
 * This module defines performance budgets for all critical operations in the application.
 * Budgets help identify operations that are taking too long and need optimization.
 *
 * Budget Philosophy:
 * - Budgets are based on user experience expectations
 * - Critical path operations have stricter budgets
 * - Non-blocking operations can have more lenient budgets
 * - Budgets should be reviewed and adjusted based on real-world data
 *
 * @module performance/budgets
 */

/**
 * Performance budget for a specific operation
 */
export interface PerformanceBudget {
  /** Operation name/identifier */
  name: string;
  /** Target duration in milliseconds */
  target: number;
  /** Warning threshold (percentage of target) */
  warningThreshold: number;
  /** Description of what the operation does */
  description: string;
  /** Priority level (1 = highest, 3 = lowest) */
  priority: 1 | 2 | 3;
}

/**
 * All performance budgets for the application
 *
 * Budgets are based on:
 * - User research and expectations
 * - Industry standards (e.g., Google's Core Web Vitals)
 * - Technical constraints
 * - Competitive analysis
 */
export const PERFORMANCE_BUDGETS: Record<string, PerformanceBudget> = {
  // Table of Contents Generation
  'toc-generation': {
    name: 'toc-generation',
    target: 3000,
    warningThreshold: 0.8, // Warn at 2400ms (80% of budget)
    description: 'AI-powered table of contents generation from book summary',
    priority: 1,
  },

  'toc-questions': {
    name: 'toc-questions',
    target: 2000,
    warningThreshold: 0.8,
    description: 'Generate clarifying questions for TOC creation',
    priority: 2,
  },

  'toc-readiness': {
    name: 'toc-readiness',
    target: 1500,
    warningThreshold: 0.8,
    description: 'Check if book summary is ready for TOC generation',
    priority: 2,
  },

  // Export Operations
  'export-pdf': {
    name: 'export-pdf',
    target: 5000,
    warningThreshold: 0.8, // Warn at 4000ms
    description: 'Export book to PDF format',
    priority: 1,
  },

  'export-docx': {
    name: 'export-docx',
    target: 5000,
    warningThreshold: 0.8,
    description: 'Export book to DOCX format',
    priority: 1,
  },

  'export-stats': {
    name: 'export-stats',
    target: 1000,
    warningThreshold: 0.8,
    description: 'Fetch book statistics for export preview',
    priority: 2,
  },

  // Draft Generation
  'generate-draft': {
    name: 'generate-draft',
    target: 4000,
    warningThreshold: 0.8, // Warn at 3200ms
    description: 'Generate AI draft from Q&A responses',
    priority: 1,
  },

  // Auto-Save Operations
  'auto-save': {
    name: 'auto-save',
    target: 1000,
    warningThreshold: 0.8, // Warn at 800ms
    description: 'Auto-save chapter content (3-second debounce)',
    priority: 1,
  },

  'manual-save': {
    name: 'manual-save',
    target: 2000,
    warningThreshold: 0.8,
    description: 'Manual save chapter content',
    priority: 1,
  },

  // Chapter Operations
  'chapter-load': {
    name: 'chapter-load',
    target: 500,
    warningThreshold: 0.8, // Warn at 400ms
    description: 'Load chapter content for editing',
    priority: 1,
  },

  'chapter-list': {
    name: 'chapter-list',
    target: 800,
    warningThreshold: 0.8,
    description: 'Load list of chapters for a book',
    priority: 2,
  },

  // Book Operations
  'book-load': {
    name: 'book-load',
    target: 1000,
    warningThreshold: 0.8,
    description: 'Load book metadata and details',
    priority: 2,
  },

  'book-list': {
    name: 'book-list',
    target: 1200,
    warningThreshold: 0.8,
    description: 'Load list of user books',
    priority: 2,
  },

  'book-create': {
    name: 'book-create',
    target: 2000,
    warningThreshold: 0.8,
    description: 'Create new book',
    priority: 2,
  },

  'book-delete': {
    name: 'book-delete',
    target: 1500,
    warningThreshold: 0.8,
    description: 'Delete book and all associated data',
    priority: 2,
  },

  // Search and Analysis
  'search-books': {
    name: 'search-books',
    target: 600,
    warningThreshold: 0.8,
    description: 'Search user books',
    priority: 2,
  },

  'analyze-summary': {
    name: 'analyze-summary',
    target: 2500,
    warningThreshold: 0.8,
    description: 'AI analysis of book summary for readiness assessment',
    priority: 2,
  },

  // Upload Operations
  'cover-upload': {
    name: 'cover-upload',
    target: 3000,
    warningThreshold: 0.8,
    description: 'Upload book cover image',
    priority: 3,
  },

  // Voice Input
  'voice-transcription': {
    name: 'voice-transcription',
    target: 2000,
    warningThreshold: 0.8,
    description: 'Real-time voice transcription (browser API)',
    priority: 2,
  },
};

/**
 * Get performance budget for an operation
 * @param operationName - Name of the operation
 * @returns Budget configuration or undefined if not found
 */
export function getBudget(operationName: string): PerformanceBudget | undefined {
  return PERFORMANCE_BUDGETS[operationName];
}

/**
 * Get all budgets for a specific priority level
 * @param priority - Priority level (1 = highest, 3 = lowest)
 * @returns Array of budgets matching the priority
 */
export function getBudgetsByPriority(priority: 1 | 2 | 3): PerformanceBudget[] {
  return Object.values(PERFORMANCE_BUDGETS).filter((budget) => budget.priority === priority);
}

/**
 * Check if a duration exceeds the budget
 * @param operationName - Name of the operation
 * @param duration - Actual duration in milliseconds
 * @returns Object indicating if budget was exceeded and by how much
 */
export function checkBudget(
  operationName: string,
  duration: number
): {
  exceeded: boolean;
  budget: number | null;
  overrun: number;
  percentage: number;
  shouldWarn: boolean;
} {
  const budget = getBudget(operationName);

  if (!budget) {
    return {
      exceeded: false,
      budget: null,
      overrun: 0,
      percentage: 0,
      shouldWarn: false,
    };
  }

  const exceeded = duration > budget.target;
  const overrun = Math.max(0, duration - budget.target);
  const percentage = (duration / budget.target) * 100;
  const warningThresholdMs = budget.target * budget.warningThreshold;
  const shouldWarn = duration > warningThresholdMs;

  return {
    exceeded,
    budget: budget.target,
    overrun,
    percentage: Math.round(percentage),
    shouldWarn,
  };
}

/**
 * Get formatted budget status message
 * @param operationName - Name of the operation
 * @param duration - Actual duration in milliseconds
 * @returns Human-readable status message
 */
export function getBudgetStatus(operationName: string, duration: number): string {
  const result = checkBudget(operationName, duration);

  if (!result.budget) {
    return `${operationName}: ${duration}ms (no budget defined)`;
  }

  if (result.exceeded) {
    return `${operationName}: ${duration}ms ⚠️ EXCEEDED budget of ${result.budget}ms by ${result.overrun}ms (${result.percentage}%)`;
  }

  if (result.shouldWarn) {
    return `${operationName}: ${duration}ms ⚠️ Near budget limit of ${result.budget}ms (${result.percentage}%)`;
  }

  return `${operationName}: ${duration}ms ✅ Within budget of ${result.budget}ms (${result.percentage}%)`;
}

/**
 * Get all critical (priority 1) operations
 * These operations directly impact user experience and should be monitored closely
 */
export function getCriticalOperations(): PerformanceBudget[] {
  return getBudgetsByPriority(1);
}

/**
 * Generate performance budget report for all operations
 * @returns Array of all budget configurations
 */
export function generateBudgetReport(): PerformanceBudget[] {
  return Object.values(PERFORMANCE_BUDGETS).sort((a, b) => {
    // Sort by priority (1 first), then by target time
    if (a.priority !== b.priority) {
      return a.priority - b.priority;
    }
    return a.target - b.target;
  });
}
