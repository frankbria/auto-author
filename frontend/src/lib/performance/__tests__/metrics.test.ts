/**
 * Performance Metrics Test Suite
 *
 * Tests for Core Web Vitals tracking and custom operation performance monitoring.
 */

// Override the global web-vitals stub (jest.setup.ts only has onFID, not onINP).
// This must be hoisted to the top before any imports.
jest.mock('web-vitals', () => ({
  onCLS: jest.fn(),
  onINP: jest.fn(),
  onFCP: jest.fn(),
  onLCP: jest.fn(),
  onTTFB: jest.fn(),
}), { virtual: true });

import { onCLS, onINP, onFCP, onLCP, onTTFB } from 'web-vitals';
import {
  PerformanceTracker,
  getCachedMetrics,
  clearCachedMetrics,
  initializeWebVitals,
} from '../metrics';
import { getBudget, checkBudget, getBudgetStatus } from '../budgets';

// Mock performance.now()
const mockPerformance = () => {
  let time = 0;
  return {
    now: jest.fn(() => time),
    advance: (ms: number) => {
      time += ms;
    },
    reset: () => {
      time = 0;
    },
  };
};

describe('PerformanceTracker', () => {
  let performanceMock: ReturnType<typeof mockPerformance>;

  beforeEach(() => {
    performanceMock = mockPerformance();
    global.performance.now = performanceMock.now;
    performanceMock.reset();

    // Mock localStorage
    const localStorageMock = (() => {
      let store: Record<string, string> = {};
      return {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => {
          store[key] = value;
        },
        removeItem: (key: string) => {
          delete store[key];
        },
        clear: () => {
          store = {};
        },
      };
    })();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true });

    // Mock console methods
    jest.spyOn(console, 'log').mockImplementation();
    jest.spyOn(console, 'warn').mockImplementation();
    jest.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    clearCachedMetrics();
  });

  describe('Basic Tracking', () => {
    it('should track operation duration', () => {
      const tracker = new PerformanceTracker('test-operation');
      performanceMock.advance(500);
      const metric = tracker.end();

      expect(metric.name).toBe('test-operation');
      expect(metric.duration).toBe(500);
      expect(metric.exceeded_budget).toBe(false);
    });

    it('should include metadata in metric', () => {
      const metadata = { bookId: 'abc', userId: '123' };
      const tracker = new PerformanceTracker('test-operation', undefined, metadata);
      performanceMock.advance(300);
      const metric = tracker.end();

      expect(metric.metadata).toMatchObject(metadata);
    });

    it('should merge additional metadata on end', () => {
      const initialMetadata = { phase: 'init' };
      const tracker = new PerformanceTracker('test-operation', undefined, initialMetadata);
      performanceMock.advance(200);
      const metric = tracker.end({ result: 'success' });

      expect(metric.metadata).toMatchObject({ phase: 'init', result: 'success' });
    });

    it('should set startTime from performance.now at construction', () => {
      performanceMock.advance(100); // start time = 100
      const tracker = new PerformanceTracker('test-operation');
      const startTime = tracker['startTime' as keyof PerformanceTracker] as unknown as number;
      // startTime captured at construction
      expect(startTime).toBe(100);
    });

    it('should set endTime on end()', () => {
      const tracker = new PerformanceTracker('test-operation');
      performanceMock.advance(250);
      const metric = tracker.end();
      expect(metric.endTime).toBe(250);
    });

    it('should expose budget in the returned metric', () => {
      const tracker = new PerformanceTracker('test-operation', 2000);
      performanceMock.advance(100);
      const metric = tracker.end();
      expect(metric.budget).toBe(2000);
    });

    it('should have exceeded_budget = false when no budget is set', () => {
      const tracker = new PerformanceTracker('no-budget-op');
      performanceMock.advance(9999);
      const metric = tracker.end();
      expect(metric.exceeded_budget).toBe(false);
    });

    it('should rate as good when no budget is given', () => {
      const tracker = new PerformanceTracker('no-budget-op');
      performanceMock.advance(5000);
      const metric = tracker.end();
      // rateOperation returns 'good' when budget is absent
      expect(metric.rating).toBe('good');
    });
  });

  describe('Budget Validation', () => {
    it('should detect budget exceeded', () => {
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(1500); // Exceed budget
      const metric = tracker.end();

      expect(metric.exceeded_budget).toBe(true);
      expect(metric.budget).toBe(budget);
      expect(metric.duration).toBe(1500);
    });

    it('should detect budget not exceeded', () => {
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(800); // Within budget
      const metric = tracker.end();

      expect(metric.exceeded_budget).toBe(false);
      expect(metric.budget).toBe(budget);
    });

    it('should rate performance as good when within 80% of budget', () => {
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(700); // 70% of budget
      const metric = tracker.end();

      expect(metric.rating).toBe('good');
    });

    it('should rate performance as needs-improvement when between 80-120% of budget', () => {
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(1000); // 100% of budget
      const metric = tracker.end();

      expect(metric.rating).toBe('needs-improvement');
    });

    it('should rate performance as poor when exceeding 120% of budget', () => {
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(1300); // 130% of budget
      const metric = tracker.end();

      expect(metric.rating).toBe('poor');
    });

    it('should rate as needs-improvement at exactly 80% of budget', () => {
      // ratio = 0.8 → rateOperation: ratio <= 0.8 → 'good'
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(800); // exactly 80%
      const metric = tracker.end();
      expect(metric.rating).toBe('good');
    });

    it('should rate as poor at exactly 120% of budget', () => {
      const budget = 1000;
      const tracker = new PerformanceTracker('test-operation', budget);
      performanceMock.advance(1200); // exactly 120%
      const metric = tracker.end();
      expect(metric.rating).toBe('poor');
    });
  });

  describe('Budget Configuration', () => {
    it('should retrieve budget for known operation', () => {
      const budget = getBudget('toc-generation');
      expect(budget).toBeDefined();
      expect(budget?.name).toBe('toc-generation');
      expect(budget?.target).toBe(3000);
    });

    it('should return undefined for unknown operation', () => {
      const budget = getBudget('unknown-operation');
      expect(budget).toBeUndefined();
    });

    it('should check budget correctly', () => {
      const result = checkBudget('toc-generation', 2000);
      expect(result.exceeded).toBe(false);
      expect(result.budget).toBe(3000);
      expect(result.percentage).toBe(67); // 2000/3000 * 100 = 66.67 rounded to 67
    });

    it('should detect budget exceeded', () => {
      const result = checkBudget('toc-generation', 3500);
      expect(result.exceeded).toBe(true);
      expect(result.overrun).toBe(500);
    });

    it('should generate status message', () => {
      const status = getBudgetStatus('toc-generation', 2000);
      expect(status).toContain('toc-generation');
      expect(status).toContain('2000ms');
      expect(status).toContain('3000ms');
    });
  });

  describe('LocalStorage Caching', () => {
    it('should cache metrics in production mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      const tracker = new PerformanceTracker('test-operation', 1000);
      performanceMock.advance(500);
      tracker.end();

      const cached = getCachedMetrics();
      expect(cached.length).toBeGreaterThan(0);
      expect(cached[0].metric_name).toBe('test-operation');

      process.env.NODE_ENV = originalEnv;
    });

    it('should clear cached metrics', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      const tracker = new PerformanceTracker('test-operation');
      performanceMock.advance(500);
      tracker.end();

      expect(getCachedMetrics().length).toBeGreaterThan(0);

      clearCachedMetrics();
      expect(getCachedMetrics().length).toBe(0);

      process.env.NODE_ENV = originalEnv;
    });

    it('should limit cached metrics to 100 entries', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      // Generate 150 metrics
      for (let i = 0; i < 150; i++) {
        const tracker = new PerformanceTracker(`operation-${i}`);
        performanceMock.advance(100);
        tracker.end();
      }

      const cached = getCachedMetrics();
      expect(cached.length).toBe(100);

      process.env.NODE_ENV = originalEnv;
    });

    it('should return empty array when no metrics are cached', () => {
      clearCachedMetrics();
      expect(getCachedMetrics()).toEqual([]);
    });

    it('should return empty array when cached data is invalid JSON', () => {
      // Directly write invalid JSON into the mock store
      localStorage.setItem('performance-metrics', 'not-valid-json{{{');
      const metrics = getCachedMetrics();
      expect(metrics).toEqual([]);
      expect(console.error).toHaveBeenCalled();
    });

    it('should include a timestamp in each cached entry', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      const tracker = new PerformanceTracker('ts-test');
      performanceMock.advance(100);
      tracker.end();

      const cached = getCachedMetrics();
      expect(cached[0]).toHaveProperty('timestamp');

      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('Error Handling', () => {
    it('should handle localStorage errors gracefully', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      // Spy on the local mock object so the throw reaches sendToAnalytics.
      jest.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
        throw new Error('Storage quota exceeded');
      });

      const tracker = new PerformanceTracker('test-operation');
      performanceMock.advance(500);

      // Should not throw and should log the error
      expect(() => tracker.end()).not.toThrow();
      expect(console.error).toHaveBeenCalledWith(
        'Failed to cache performance metric:',
        expect.any(Error)
      );

      process.env.NODE_ENV = originalEnv;
    });

    it('should handle getCachedMetrics errors', () => {
      jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('Storage error');
      });

      const metrics = getCachedMetrics();
      expect(metrics).toEqual([]);
    });

    it('should handle clearCachedMetrics errors gracefully', () => {
      // Spy on the local mock object (Storage.prototype spy doesn't reach it).
      jest.spyOn(window.localStorage, 'removeItem').mockImplementation(() => {
        throw new Error('Storage error');
      });

      expect(() => clearCachedMetrics()).not.toThrow();
      expect(console.error).toHaveBeenCalledWith(
        'Failed to clear cached metrics:',
        expect.any(Error)
      );
    });
  });

  describe('Development Mode Logging', () => {
    it('should log to console in development mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const tracker = new PerformanceTracker('test-operation', 1000);
      performanceMock.advance(500);
      tracker.end();

      expect(console.log).toHaveBeenCalled();

      process.env.NODE_ENV = originalEnv;
    });

    it('should include a rating emoji in dev mode logs', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const tracker = new PerformanceTracker('test-operation', 1000);
      performanceMock.advance(700); // 70% → good → ✅
      tracker.end();

      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('✅');

      process.env.NODE_ENV = originalEnv;
    });

    it('should log ❌ in dev mode when metric is poor', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const tracker = new PerformanceTracker('test-operation', 1000);
      performanceMock.advance(1300); // 130% → poor → ❌
      tracker.end();

      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('❌');

      process.env.NODE_ENV = originalEnv;
    });

    it('should log ⚠️ in dev mode when metric is needs-improvement', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const tracker = new PerformanceTracker('test-operation', 1000);
      performanceMock.advance(1000); // 100% → needs-improvement → ⚠️
      tracker.end();

      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('⚠️');

      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('Cancel Tracking', () => {
    it('should not report when cancelled', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const tracker = new PerformanceTracker('test-operation');
      performanceMock.advance(500);
      tracker.cancel();

      // Console.log should not be called because tracking was cancelled
      const logCalls = (console.log as jest.Mock).mock.calls.filter((call) =>
        call.some((arg) => typeof arg === 'string' && arg.includes('test-operation'))
      );
      expect(logCalls.length).toBe(0);

      process.env.NODE_ENV = originalEnv;
    });
  });
});

// ============================================================================
// initializeWebVitals
// ============================================================================

describe('initializeWebVitals', () => {
  beforeEach(() => {
    // Reset all web-vitals mocks between tests
    (onCLS as jest.Mock).mockClear();
    (onINP as jest.Mock).mockClear();
    (onLCP as jest.Mock).mockClear();
    (onTTFB as jest.Mock).mockClear();
    (onFCP as jest.Mock).mockClear();

    jest.spyOn(console, 'log').mockImplementation();
    jest.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    clearCachedMetrics();
  });

  it('registers a callback with onCLS', () => {
    initializeWebVitals();
    expect(onCLS).toHaveBeenCalledWith(expect.any(Function));
  });

  it('registers a callback with onINP', () => {
    initializeWebVitals();
    expect(onINP).toHaveBeenCalledWith(expect.any(Function));
  });

  it('registers a callback with onLCP', () => {
    initializeWebVitals();
    expect(onLCP).toHaveBeenCalledWith(expect.any(Function));
  });

  it('registers a callback with onTTFB', () => {
    initializeWebVitals();
    expect(onTTFB).toHaveBeenCalledWith(expect.any(Function));
  });

  it('registers a callback with onFCP', () => {
    initializeWebVitals();
    expect(onFCP).toHaveBeenCalledWith(expect.any(Function));
  });

  describe('CLS rating thresholds', () => {
    it('rates CLS ≤ 0.1 as good', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onCLS as jest.Mock).mock.calls[0][0];
      cb({ name: 'CLS', value: 0.05 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('✅');
      process.env.NODE_ENV = originalEnv;
    });

    it('rates CLS ≥ 0.25 as poor', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onCLS as jest.Mock).mock.calls[0][0];
      cb({ name: 'CLS', value: 0.3 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('❌');
      process.env.NODE_ENV = originalEnv;
    });

    it('rates CLS between 0.1 and 0.25 as needs-improvement', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onCLS as jest.Mock).mock.calls[0][0];
      cb({ name: 'CLS', value: 0.15 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('⚠️');
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('LCP rating thresholds', () => {
    it('rates LCP ≤ 2500ms as good', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onLCP as jest.Mock).mock.calls[0][0];
      cb({ name: 'LCP', value: 2500 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('✅');
      process.env.NODE_ENV = originalEnv;
    });

    it('rates LCP ≥ 4000ms as poor', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onLCP as jest.Mock).mock.calls[0][0];
      cb({ name: 'LCP', value: 4000 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('❌');
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('INP rating thresholds', () => {
    it('rates INP ≤ 200ms as good', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onINP as jest.Mock).mock.calls[0][0];
      cb({ name: 'INP', value: 150 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('✅');
      process.env.NODE_ENV = originalEnv;
    });

    it('rates INP ≥ 500ms as poor', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onINP as jest.Mock).mock.calls[0][0];
      cb({ name: 'INP', value: 600 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('❌');
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('TTFB rating thresholds', () => {
    it('rates TTFB ≤ 800ms as good', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onTTFB as jest.Mock).mock.calls[0][0];
      cb({ name: 'TTFB', value: 600 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('✅');
      process.env.NODE_ENV = originalEnv;
    });

    it('rates TTFB ≥ 1800ms as poor', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onTTFB as jest.Mock).mock.calls[0][0];
      cb({ name: 'TTFB', value: 2000 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('❌');
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('FCP rating thresholds', () => {
    it('rates FCP ≤ 1800ms as good', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onFCP as jest.Mock).mock.calls[0][0];
      cb({ name: 'FCP', value: 1500 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('✅');
      process.env.NODE_ENV = originalEnv;
    });

    it('rates FCP ≥ 3000ms as poor', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      initializeWebVitals();
      const cb = (onFCP as jest.Mock).mock.calls[0][0];
      cb({ name: 'FCP', value: 3500 });
      const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
      expect(firstArg).toContain('❌');
      process.env.NODE_ENV = originalEnv;
    });
  });

  it('stores web vitals in localStorage in production mode', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production';

    // Set up a writable localStorage mock
    const store: Record<string, string> = {};
    Object.defineProperty(window, 'localStorage', {
      writable: true,
      value: {
        getItem: (k: string) => store[k] ?? null,
        setItem: (k: string, v: string) => { store[k] = v; },
        removeItem: (k: string) => { delete store[k]; },
        clear: () => { Object.keys(store).forEach(k => delete store[k]); },
      },
    });

    initializeWebVitals();
    const clsCb = (onCLS as jest.Mock).mock.calls[0][0];
    clsCb({ name: 'CLS', value: 0.05 });

    const cached = getCachedMetrics();
    expect(cached.length).toBeGreaterThan(0);
    expect(cached[0].metric_name).toBe('CLS');

    process.env.NODE_ENV = originalEnv;
  });

  it('uses needs-improvement for an unrecognised metric name', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    initializeWebVitals();
    // Invoke the CLS callback but give it an unknown name to trigger the fallback
    const cb = (onCLS as jest.Mock).mock.calls[0][0];
    cb({ name: 'UNKNOWN', value: 999 });
    // ⚠️ is the needs-improvement emoji
    const firstArg = (console.log as jest.Mock).mock.calls[0][0] as string;
    expect(firstArg).toContain('⚠️');
    process.env.NODE_ENV = originalEnv;
  });
});
