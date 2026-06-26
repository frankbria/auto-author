/**
 * usePerformanceTracking hook — unit tests
 *
 * PerformanceTracker and getBudget are both mocked so this file only tests
 * the hook's own orchestration logic (wiring, error propagation, warnings).
 */

jest.mock('@/lib/performance/metrics', () => ({
  PerformanceTracker: jest.fn(),
}));

jest.mock('@/lib/performance/budgets', () => ({
  getBudget: jest.fn(),
}));

import { renderHook, act } from '@testing-library/react';
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';
import { PerformanceTracker } from '@/lib/performance/metrics';
import { getBudget } from '@/lib/performance/budgets';

// ---- helpers ---------------------------------------------------------------

const MockTracker = PerformanceTracker as jest.Mock;
const mockGetBudget = getBudget as jest.Mock;

/** A minimal OperationMetric-shaped object returned by mockEnd. */
function makeMetric(overrides: Partial<{
  duration: number;
  exceeded_budget: boolean;
  rating: 'good' | 'needs-improvement' | 'poor';
}> = {}) {
  return {
    name: 'test-op',
    duration: overrides.duration ?? 200,
    startTime: 0,
    endTime: overrides.duration ?? 200,
    budget: 1000,
    exceeded_budget: overrides.exceeded_budget ?? false,
    metadata: {},
    rating: overrides.rating ?? 'good',
  };
}

// ---- setup -----------------------------------------------------------------

let mockEnd: jest.Mock;
let mockCancel: jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(console, 'warn').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});

  mockEnd = jest.fn().mockReturnValue(makeMetric());
  mockCancel = jest.fn();

  MockTracker.mockImplementation(() => ({
    end: mockEnd,
    cancel: mockCancel,
  }));

  // Default: operation has no configured budget
  mockGetBudget.mockReturnValue(undefined);
});

afterEach(() => {
  jest.restoreAllMocks();
});

// ============================================================================
// trackOperation
// ============================================================================

describe('trackOperation', () => {
  it('returns the data produced by the async operation', async () => {
    const { result } = renderHook(() => usePerformanceTracking());
    let tracked: { data: string; metric: unknown };

    await act(async () => {
      tracked = await result.current.trackOperation('my-op', async () => 'hello');
    });

    expect(tracked!.data).toBe('hello');
  });

  it('returns the metric from tracker.end()', async () => {
    const metric = makeMetric({ duration: 350 });
    mockEnd.mockReturnValue(metric);

    const { result } = renderHook(() => usePerformanceTracking());
    let tracked: { data: unknown; metric: typeof metric };

    await act(async () => {
      tracked = await result.current.trackOperation('my-op', async () => null);
    });

    expect(tracked!.metric).toBe(metric);
  });

  it('creates a PerformanceTracker with the operation name and budget target', async () => {
    mockGetBudget.mockReturnValue({ target: 500, name: 'my-op', warningThreshold: 0.8, description: '', priority: 1 as const });

    const { result } = renderHook(() => usePerformanceTracking());
    await act(async () => {
      await result.current.trackOperation('my-op', async () => null);
    });

    expect(MockTracker).toHaveBeenCalledWith('my-op', 500, undefined);
  });

  it('passes metadata to PerformanceTracker constructor', async () => {
    const meta = { bookId: 'abc', format: 'pdf' };
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await result.current.trackOperation('my-op', async () => null, meta);
    });

    expect(MockTracker).toHaveBeenCalledWith('my-op', undefined, meta);
  });

  it('uses undefined budget when getBudget returns undefined', async () => {
    mockGetBudget.mockReturnValue(undefined);
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await result.current.trackOperation('unknown-op', async () => 42);
    });

    expect(MockTracker).toHaveBeenCalledWith('unknown-op', undefined, undefined);
  });

  it('calls console.warn when budget is exceeded', async () => {
    mockGetBudget.mockReturnValue({ target: 1000, name: 'my-op', warningThreshold: 0.8, description: '', priority: 1 as const });
    mockEnd.mockReturnValue(makeMetric({ duration: 1500, exceeded_budget: true }));

    const { result } = renderHook(() => usePerformanceTracking());
    await act(async () => {
      await result.current.trackOperation('my-op', async () => null);
    });

    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('my-op'),
      expect.stringContaining('1500ms')
    );
  });

  it('does not call console.warn when budget is not exceeded', async () => {
    mockGetBudget.mockReturnValue({ target: 1000, name: 'my-op', warningThreshold: 0.8, description: '', priority: 1 as const });
    mockEnd.mockReturnValue(makeMetric({ duration: 800, exceeded_budget: false }));

    const { result } = renderHook(() => usePerformanceTracking());
    await act(async () => {
      await result.current.trackOperation('my-op', async () => null);
    });

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('re-throws errors thrown by the operation', async () => {
    const boom = new Error('network failure');
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await expect(
        result.current.trackOperation('my-op', async () => { throw boom; })
      ).rejects.toThrow('network failure');
    });
  });

  it('calls tracker.end() even when the operation throws', async () => {
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await expect(
        result.current.trackOperation('my-op', async () => { throw new Error('fail'); })
      ).rejects.toThrow();
    });

    expect(mockEnd).toHaveBeenCalled();
  });

  it('passes the error message to tracker.end() as metadata on failure', async () => {
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await expect(
        result.current.trackOperation('my-op', async () => { throw new Error('oops'); })
      ).rejects.toThrow();
    });

    expect(mockEnd).toHaveBeenCalledWith({ error: 'oops' });
  });

  it('calls console.error on operation failure', async () => {
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await expect(
        result.current.trackOperation('my-op', async () => { throw new Error('bad'); })
      ).rejects.toThrow();
    });

    expect(console.error).toHaveBeenCalled();
  });

  it('handles non-Error thrown values gracefully', async () => {
    const { result } = renderHook(() => usePerformanceTracking());

    await act(async () => {
      await expect(
        result.current.trackOperation('my-op', async () => { throw 'string-error'; })
      ).rejects.toBe('string-error');
    });

    // tracker.end is still called with 'Unknown error' for non-Error throws
    expect(mockEnd).toHaveBeenCalledWith({ error: 'Unknown error' });
  });
});

// ============================================================================
// trackSync
// ============================================================================

describe('trackSync', () => {
  it('returns the data produced by the sync function', () => {
    const { result } = renderHook(() => usePerformanceTracking());
    let tracked: { data: number; metric: unknown };

    act(() => {
      tracked = result.current.trackSync('sync-op', () => 42);
    });

    expect(tracked!.data).toBe(42);
  });

  it('returns the metric from tracker.end()', () => {
    const metric = makeMetric({ duration: 50 });
    mockEnd.mockReturnValue(metric);

    const { result } = renderHook(() => usePerformanceTracking());
    let tracked: { data: unknown; metric: typeof metric };

    act(() => {
      tracked = result.current.trackSync('sync-op', () => null);
    });

    expect(tracked!.metric).toBe(metric);
  });

  it('passes metadata to PerformanceTracker constructor', () => {
    const meta = { key: 'value' };
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      result.current.trackSync('sync-op', () => null, meta);
    });

    expect(MockTracker).toHaveBeenCalledWith('sync-op', undefined, meta);
  });

  it('calls console.warn when budget is exceeded', () => {
    mockGetBudget.mockReturnValue({ target: 100, name: 'sync-op', warningThreshold: 0.8, description: '', priority: 1 as const });
    mockEnd.mockReturnValue(makeMetric({ duration: 200, exceeded_budget: true }));

    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      result.current.trackSync('sync-op', () => null);
    });

    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('sync-op'),
      expect.stringContaining('200ms')
    );
  });

  it('re-throws errors from the sync function', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      expect(() =>
        result.current.trackSync('sync-op', () => { throw new Error('sync fail'); })
      ).toThrow('sync fail');
    });
  });

  it('still calls tracker.end() when the sync function throws', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      try {
        result.current.trackSync('sync-op', () => { throw new Error('x'); });
      } catch {
        // expected
      }
    });

    expect(mockEnd).toHaveBeenCalled();
  });

  it('logs error to console on sync failure', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      try {
        result.current.trackSync('sync-op', () => { throw new Error('uh oh'); });
      } catch {
        // expected
      }
    });

    expect(console.error).toHaveBeenCalled();
  });

  it('passes "Unknown error" to tracker.end() when a non-Error is thrown', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      try {
        result.current.trackSync('sync-op', () => { throw 'string-error'; });
      } catch {
        // expected
      }
    });

    expect(mockEnd).toHaveBeenCalledWith({ error: 'Unknown error' });
  });
});

// ============================================================================
// createTracker
// ============================================================================

describe('createTracker', () => {
  it('returns an object with end and cancel functions', () => {
    const { result } = renderHook(() => usePerformanceTracking());
    let tracker: { end: (meta?: Record<string, unknown>) => unknown; cancel: () => void };

    act(() => {
      tracker = result.current.createTracker('manual-op');
    });

    expect(typeof tracker!.end).toBe('function');
    expect(typeof tracker!.cancel).toBe('function');
  });

  it('creates a PerformanceTracker with the operation name', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      result.current.createTracker('manual-op');
    });

    expect(MockTracker).toHaveBeenCalledWith('manual-op', undefined, undefined);
  });

  it('passes metadata to PerformanceTracker', () => {
    const meta = { phase: 'init' };
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      result.current.createTracker('manual-op', meta);
    });

    expect(MockTracker).toHaveBeenCalledWith('manual-op', undefined, meta);
  });

  it('end() returns the metric from the underlying tracker', () => {
    const metric = makeMetric({ duration: 900 });
    mockEnd.mockReturnValue(metric);

    const { result } = renderHook(() => usePerformanceTracking());
    let returned: unknown;

    act(() => {
      const tracker = result.current.createTracker('manual-op');
      returned = tracker.end();
    });

    expect(returned).toBe(metric);
  });

  it('end() passes additional metadata to tracker.end()', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      const tracker = result.current.createTracker('manual-op');
      tracker.end({ result: 'success' });
    });

    expect(mockEnd).toHaveBeenCalledWith({ result: 'success' });
  });

  it('end() calls console.warn when budget is exceeded', () => {
    mockGetBudget.mockReturnValue({ target: 500, name: 'manual-op', warningThreshold: 0.8, description: '', priority: 1 as const });
    mockEnd.mockReturnValue(makeMetric({ duration: 700, exceeded_budget: true }));

    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      const tracker = result.current.createTracker('manual-op');
      tracker.end();
    });

    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('manual-op'),
      expect.stringContaining('700ms')
    );
  });

  it('cancel() calls tracker.cancel() on the underlying tracker', () => {
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      const tracker = result.current.createTracker('manual-op');
      tracker.cancel();
    });

    expect(mockCancel).toHaveBeenCalled();
  });

  it('end() uses budget target from getBudget', () => {
    mockGetBudget.mockReturnValue({ target: 2000, name: 'manual-op', warningThreshold: 0.8, description: '', priority: 2 as const });
    const { result } = renderHook(() => usePerformanceTracking());

    act(() => {
      result.current.createTracker('manual-op');
    });

    expect(MockTracker).toHaveBeenCalledWith('manual-op', 2000, undefined);
  });
});
