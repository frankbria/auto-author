/**
 * Performance Metrics Tracking System
 *
 * This module provides Core Web Vitals tracking and custom operation performance monitoring.
 * It collects metrics, rates them according to industry standards, and reports to analytics.
 *
 * Core Web Vitals tracked:
 * - LCP (Largest Contentful Paint): Loading performance
 * - FID (First Input Delay): Interactivity (deprecated, use INP)
 * - INP (Interaction to Next Paint): Interactivity (new standard)
 * - CLS (Cumulative Layout Shift): Visual stability
 * - TTFB (Time to First Byte): Server response time
 * - FCP (First Contentful Paint): Initial render
 *
 * @module performance/metrics
 */

import { onCLS, onFID, onLCP, onTTFB, onINP, onFCP, type Metric } from 'web-vitals';

/**
 * Performance metric rating categories based on Google's Web Vitals thresholds
 */
export type MetricRating = 'good' | 'needs-improvement' | 'poor';

/**
 * Core Web Vitals metric names
 */
export type WebVitalName = 'CLS' | 'FID' | 'INP' | 'LCP' | 'TTFB' | 'FCP';

/**
 * Custom operation metric data
 */
export interface OperationMetric {
  /** Operation name/identifier */
  name: string;
  /** Duration in milliseconds */
  duration: number;
  /** Start timestamp */
  startTime: number;
  /** End timestamp */
  endTime: number;
  /** Performance budget for this operation */
  budget?: number;
  /** Whether the operation exceeded its budget */
  exceeded_budget: boolean;
  /** Additional context metadata */
  metadata?: Record<string, unknown>;
  /** Metric rating */
  rating: MetricRating;
}

/**
 * Analytics event payload structure
 */
interface AnalyticsEvent {
  event_name: string;
  metric_name: string;
  value: number;
  rating: MetricRating;
  metadata?: Record<string, unknown>;
}

/**
 * Rate a Core Web Vitals metric according to Google's thresholds
 *
 * Thresholds:
 * - LCP: good < 2500ms, poor > 4000ms
 * - FID: good < 100ms, poor > 300ms
 * - INP: good < 200ms, poor > 500ms
 * - CLS: good < 0.1, poor > 0.25
 * - TTFB: good < 800ms, poor > 1800ms
 * - FCP: good < 1800ms, poor > 3000ms
 */
function rateWebVital(metric: Metric): MetricRating {
  const thresholds: Record<WebVitalName, { good: number; poor: number }> = {
    LCP: { good: 2500, poor: 4000 },
    FID: { good: 100, poor: 300 },
    INP: { good: 200, poor: 500 },
    CLS: { good: 0.1, poor: 0.25 },
    TTFB: { good: 800, poor: 1800 },
    FCP: { good: 1800, poor: 3000 },
  };

  const threshold = thresholds[metric.name as WebVitalName];
  if (!threshold) return 'needs-improvement';

  if (metric.value <= threshold.good) return 'good';
  if (metric.value >= threshold.poor) return 'poor';
  return 'needs-improvement';
}

/**
 * Rate a custom operation based on its budget
 */
function rateOperation(duration: number, budget?: number): MetricRating {
  if (!budget) return 'good'; // No budget means no rating

  const ratio = duration / budget;
  if (ratio <= 0.8) return 'good'; // Within 80% of budget
  if (ratio >= 1.2) return 'poor'; // Exceeded by 20% or more
  return 'needs-improvement';
}

/**
 * Send analytics event (placeholder for future analytics integration)
 *
 * In production, this should send to your analytics service
 * (e.g., Google Analytics, Mixpanel, custom endpoint)
 */
function sendToAnalytics(event: AnalyticsEvent): void {
  const isDevelopment = process.env.NODE_ENV === 'development';

  if (isDevelopment) {
    // Development: log to console with color-coded output
    const color = event.rating === 'good' ? '✅' : event.rating === 'poor' ? '❌' : '⚠️';
    console.log(
      `${color} [Performance] ${event.metric_name}:`,
      `${event.value}ms`,
      `(${event.rating})`,
      event.metadata || ''
    );
  } else {
    // Production: send to analytics endpoint
    // TODO: Replace with actual analytics implementation
    // Example: window.gtag?.('event', event.event_name, event);
    // Example: window.analytics?.track(event.event_name, event);

    // For now, store in localStorage for offline scenarios
    try {
      const key = 'performance-metrics';
      const existing = localStorage.getItem(key);
      const metrics = existing ? JSON.parse(existing) : [];
      metrics.push({ ...event, timestamp: Date.now() });

      // Keep only last 100 metrics
      if (metrics.length > 100) {
        metrics.splice(0, metrics.length - 100);
      }

      localStorage.setItem(key, JSON.stringify(metrics));
    } catch (error) {
      console.error('Failed to cache performance metric:', error);
    }
  }
}

/**
 * Performance tracker class for custom operations
 *
 * Usage:
 * ```typescript
 * const tracker = new PerformanceTracker('export-pdf', 5000);
 * // ... do work ...
 * const result = tracker.end({ bookId: 'abc', format: 'pdf' });
 * ```
 */
export class PerformanceTracker {
  private name: string;
  private startTime: number;
  private budget?: number;
  private metadata?: Record<string, unknown>;

  /**
   * Create a new performance tracker
   * @param name - Operation name
   * @param budget - Performance budget in milliseconds (optional)
   * @param metadata - Additional context data (optional)
   */
  constructor(name: string, budget?: number, metadata?: Record<string, unknown>) {
    this.name = name;
    this.budget = budget;
    this.metadata = metadata;
    this.startTime = performance.now();
  }

  /**
   * End the performance measurement and return the metric
   * @param additionalMetadata - Additional metadata to include
   * @returns Operation metric with timing and rating
   */
  end(additionalMetadata?: Record<string, unknown>): OperationMetric {
    const endTime = performance.now();
    const duration = endTime - this.startTime;
    const exceeded_budget = this.budget ? duration > this.budget : false;
    const rating = rateOperation(duration, this.budget);

    const metric: OperationMetric = {
      name: this.name,
      duration: Math.round(duration),
      startTime: this.startTime,
      endTime,
      budget: this.budget,
      exceeded_budget,
      rating,
      metadata: { ...this.metadata, ...additionalMetadata },
    };

    // Report to analytics
    sendToAnalytics({
      event_name: 'custom_performance',
      metric_name: this.name,
      value: metric.duration,
      rating: metric.rating,
      metadata: metric.metadata,
    });

    return metric;
  }

  /**
   * Cancel the tracking without reporting
   */
  cancel(): void {
    // Simply don't report anything
  }
}

/**
 * Initialize Core Web Vitals tracking
 *
 * Call this once on app initialization to start collecting Web Vitals.
 * Metrics are automatically reported when they become available.
 *
 * @example
 * ```typescript
 * // In app layout or entry point
 * useEffect(() => {
 *   if (typeof window !== 'undefined') {
 *     initializeWebVitals();
 *   }
 * }, []);
 * ```
 */
export function initializeWebVitals(): void {
  // CLS - Cumulative Layout Shift (visual stability)
  onCLS((metric) => {
    const rating = rateWebVital(metric);
    sendToAnalytics({
      event_name: 'web_vital',
      metric_name: 'CLS',
      value: metric.value,
      rating,
    });
  });

  // FID - First Input Delay (interactivity - deprecated)
  onFID((metric) => {
    const rating = rateWebVital(metric);
    sendToAnalytics({
      event_name: 'web_vital',
      metric_name: 'FID',
      value: metric.value,
      rating,
    });
  });

  // INP - Interaction to Next Paint (interactivity - new standard)
  onINP((metric) => {
    const rating = rateWebVital(metric);
    sendToAnalytics({
      event_name: 'web_vital',
      metric_name: 'INP',
      value: metric.value,
      rating,
    });
  });

  // LCP - Largest Contentful Paint (loading performance)
  onLCP((metric) => {
    const rating = rateWebVital(metric);
    sendToAnalytics({
      event_name: 'web_vital',
      metric_name: 'LCP',
      value: metric.value,
      rating,
    });
  });

  // TTFB - Time to First Byte (server response)
  onTTFB((metric) => {
    const rating = rateWebVital(metric);
    sendToAnalytics({
      event_name: 'web_vital',
      metric_name: 'TTFB',
      value: metric.value,
      rating,
    });
  });

  // FCP - First Contentful Paint (initial render)
  onFCP((metric) => {
    const rating = rateWebVital(metric);
    sendToAnalytics({
      event_name: 'web_vital',
      metric_name: 'FCP',
      value: metric.value,
      rating,
    });
  });
}

/**
 * Get cached performance metrics from localStorage
 * Useful for debugging or displaying recent performance data
 *
 * @returns Array of cached metrics or empty array
 */
export function getCachedMetrics(): AnalyticsEvent[] {
  try {
    const key = 'performance-metrics';
    const existing = localStorage.getItem(key);
    return existing ? JSON.parse(existing) : [];
  } catch (error) {
    console.error('Failed to retrieve cached metrics:', error);
    return [];
  }
}

/**
 * Clear cached performance metrics from localStorage
 */
export function clearCachedMetrics(): void {
  try {
    localStorage.removeItem('performance-metrics');
  } catch (error) {
    console.error('Failed to clear cached metrics:', error);
  }
}
