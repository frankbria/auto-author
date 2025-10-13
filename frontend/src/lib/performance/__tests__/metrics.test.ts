/**
 * Performance Metrics Test Suite
 *
 * Tests for Core Web Vitals tracking and custom operation performance monitoring.
 */

import { PerformanceTracker, getCachedMetrics, clearCachedMetrics } from '../metrics';
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
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });

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
  });

  describe('Error Handling', () => {
    it('should handle localStorage errors gracefully', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      // Make localStorage throw an error
      jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('Storage quota exceeded');
      });

      const tracker = new PerformanceTracker('test-operation');
      performanceMock.advance(500);

      // Should not throw
      expect(() => tracker.end()).not.toThrow();

      process.env.NODE_ENV = originalEnv;
    });

    it('should handle getCachedMetrics errors', () => {
      jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('Storage error');
      });

      const metrics = getCachedMetrics();
      expect(metrics).toEqual([]);
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
