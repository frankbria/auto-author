/**
 * Performance Budget Fixtures
 *
 * Performance budgets and measurement utilities for deployment testing.
 */

import { Page } from '@playwright/test';

/**
 * Performance budgets in milliseconds
 * Based on DEPLOYMENT-TESTING-CHECKLIST.md requirements
 */
export const PERFORMANCE_BUDGETS = {
  TOC_GENERATION: 3000,      // TOC AI generation
  EXPORT_PDF: 5000,          // PDF export
  EXPORT_DOCX: 5000,         // DOCX export
  AUTO_SAVE: 1000,           // Chapter auto-save
  PAGE_NAVIGATION: 500,      // Page transitions
  DRAFT_GENERATION: 60000,   // AI draft generation (max 60s)
  LCP: 2500,                 // Largest Contentful Paint (Core Web Vital)
  CLS: 0.1                   // Cumulative Layout Shift (Core Web Vital)
} as const;

export interface PerformanceResult {
  duration: number;
  withinBudget: boolean;
  budgetMs: number;
  operation: string;
}

/**
 * Measure the performance of an operation against a budget
 *
 * @param page Playwright page object
 * @param operation Async function to measure
 * @param budgetMs Performance budget in milliseconds
 * @param operationName Name of the operation for reporting
 * @returns Performance measurement result
 */
export async function measureOperation(
  page: Page,
  operation: () => Promise<void>,
  budgetMs: number,
  operationName: string
): Promise<PerformanceResult> {
  const start = performance.now();

  try {
    await operation();
  } catch (error) {
    const duration = performance.now() - start;
    console.error(`Operation "${operationName}" failed after ${duration}ms:`, error);
    throw error;
  }

  const duration = performance.now() - start;
  const withinBudget = duration <= budgetMs;

  // Log performance result
  const status = withinBudget ? '✅' : '❌';
  console.log(`${status} ${operationName}: ${duration.toFixed(0)}ms (budget: ${budgetMs}ms)`);

  return {
    duration,
    withinBudget,
    budgetMs,
    operation: operationName
  };
}

/**
 * Get Core Web Vitals from the page
 */
export async function getCoreWebVitals(page: Page) {
  return await page.evaluate(() => {
    return new Promise((resolve) => {
      const metrics: { lcp?: number; cls?: number; fid?: number } = {};

      // LCP - Largest Contentful Paint
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1] as any;
        metrics.lcp = lastEntry.renderTime || lastEntry.loadTime;
      }).observe({ type: 'largest-contentful-paint', buffered: true });

      // CLS - Cumulative Layout Shift
      new PerformanceObserver((list) => {
        let clsValue = 0;
        for (const entry of list.getEntries() as any[]) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        }
        metrics.cls = clsValue;
      }).observe({ type: 'layout-shift', buffered: true });

      // Return metrics after a short delay to collect data
      setTimeout(() => resolve(metrics), 1000);
    });
  });
}
