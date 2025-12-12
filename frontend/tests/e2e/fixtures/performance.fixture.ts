/**
 * Performance Budget Fixtures
 *
 * Performance budgets and measurement utilities for deployment testing.
 *
 * STAGING vs PRODUCTION BUDGETS:
 * - Staging environment: Shared VPS with resource contention, network latency
 * - Production environment: Optimized infrastructure with CDN, dedicated resources
 * - Budgets are ~2-3x more lenient for staging while still catching real regressions
 */

import { Page } from '@playwright/test';

/**
 * Production-grade performance budgets (target values)
 * These represent optimal performance on production infrastructure
 */
const PRODUCTION_BUDGETS = {
  TOC_GENERATION: 3000,      // TOC AI generation
  EXPORT_PDF: 5000,          // PDF export
  EXPORT_DOCX: 5000,         // DOCX export
  AUTO_SAVE: 1000,           // Chapter auto-save
  PAGE_NAVIGATION: 500,      // Page transitions (with CDN, optimized routing)
  DRAFT_GENERATION: 60000,   // AI draft generation (max 60s)
  LCP: 2500,                 // Largest Contentful Paint (Core Web Vital)
  CLS: 0.1,                  // Cumulative Layout Shift (Core Web Vital)
  FID: 100,                  // First Input Delay - browser responsiveness
  CLERK_MODAL_OPEN: 3000     // Clerk authentication modal open time
} as const;

/**
 * Staging-specific performance budgets
 * Account for:
 * - Shared VPS (slower CPU, memory contention)
 * - Network latency to staging server
 * - No CDN (slower static asset delivery)
 * - Cold starts for backend services
 * - Clerk auth overhead on remote server
 */
const STAGING_BUDGETS = {
  TOC_GENERATION: 5000,      // +2s for network/compute overhead
  EXPORT_PDF: 8000,          // +3s for file generation on shared resources
  EXPORT_DOCX: 8000,         // +3s for file generation on shared resources
  AUTO_SAVE: 2000,           // +1s for network round-trip
  PAGE_NAVIGATION: 1500,     // +1s for no CDN, network latency (actual: 985-1090ms)
  DRAFT_GENERATION: 90000,   // +30s for LLM API calls from remote server
  LCP: 3500,                 // +1s for slower asset delivery
  CLS: 0.1,                  // Same - layout stability unaffected by environment
  FID: 200,                  // +100ms for shared resources (still measures responsiveness)
  CLERK_MODAL_OPEN: 10000    // +7s for remote auth flow (actual: 6.6-6.8s)
} as const;

/**
 * Detect if running against staging environment
 */
function isStagingEnvironment(): boolean {
  const deploymentUrl = process.env.DEPLOYMENT_URL || '';
  return deploymentUrl.includes('dev.autoauthor.app') || deploymentUrl.includes('staging');
}

/**
 * Active performance budgets (auto-selects based on environment)
 */
export const PERFORMANCE_BUDGETS = isStagingEnvironment() ? STAGING_BUDGETS : PRODUCTION_BUDGETS;

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
