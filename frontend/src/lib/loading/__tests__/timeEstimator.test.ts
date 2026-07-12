/**
 * Tests for timeEstimator utility
 *
 * Coverage targets:
 * - estimateOperationTime: known ops, unknown op, all metadata types, network speed, clamping
 * - formatTime: seconds, minutes, hours, edge values
 * - getProgressEstimate: zero/negative total, elapsed >= total, mid-range, cap at 95
 * - createProgressTracker: return type, progress increases with time, time-remaining calculation
 * - OPERATION_TIME_BUDGETS: exported and accessible
 */

import {
  estimateOperationTime,
  formatTime,
  getProgressEstimate,
  createProgressTracker,
  OPERATION_TIME_BUDGETS,
} from '../timeEstimator';

// =====================================================================
// estimateOperationTime
// =====================================================================

describe('estimateOperationTime', () => {
  describe('returns correct bounds for every known operation', () => {
    const knownOps: Array<[string, number, number]> = [
      ['toc.generation', 5000, 30000],
      ['toc.readiness', 2000, 5000],
      ['toc.questions', 3000, 15000],
      ['export.pdf', 5000, 60000],
      ['export.docx', 3000, 40000],
      ['export.epub', 3000, 40000],
      ['export.markdown', 2000, 30000],
      ['chapter.create', 300, 2000],
      ['chapter.draft', 4000, 30000],
      ['chapter.questions', 3000, 15000],
      ['book.save', 300, 2000],
      ['book.fetch', 500, 4000],
    ];

    knownOps.forEach(([op, expectedMin, expectedMax]) => {
      it(`${op}: min=${expectedMin} max=${expectedMax}`, () => {
        const result = estimateOperationTime(op);
        expect(result.min).toBe(expectedMin);
        expect(result.max).toBe(expectedMax);
        expect(result.average).toBeGreaterThanOrEqual(expectedMin);
        expect(result.average).toBeLessThanOrEqual(expectedMax);
      });
    });
  });

  describe('unknown operation uses default budget', () => {
    it('returns default min/max for an unrecognised operation key', () => {
      const result = estimateOperationTime('definitely.not.a.real.op');
      expect(result.min).toBe(1000);
      expect(result.max).toBe(10000);
    });

    it('average is the default base time (3000) when no metadata', () => {
      const result = estimateOperationTime('unknown.op');
      expect(result.average).toBe(3000);
    });
  });

  describe('no metadata returns base time', () => {
    it('toc.generation without metadata uses base (10000)', () => {
      const result = estimateOperationTime('toc.generation');
      expect(result.average).toBe(10000);
    });

    it('book.save without metadata uses base (500)', () => {
      const result = estimateOperationTime('book.save');
      expect(result.average).toBe(500);
    });
  });

  describe('chapterCount metadata', () => {
    it('toc.generation with chapterCount=10 adds 5000ms (10 * 500)', () => {
      const result = estimateOperationTime('toc.generation', { chapterCount: 10 });
      expect(result.average).toBe(15000); // 10000 base + 5000
    });

    it('export.pdf with chapterCount=5 adds 5000ms (5 * 1000)', () => {
      const result = estimateOperationTime('export.pdf', { chapterCount: 5 });
      expect(result.average).toBe(15000); // 10000 base + 5000
    });

    it('chapterCount=0 is ignored (falsy check)', () => {
      const withZero = estimateOperationTime('toc.generation', { chapterCount: 0 });
      const withNone = estimateOperationTime('toc.generation');
      expect(withZero.average).toBe(withNone.average);
    });

    it('operation without perChapter ignores chapterCount', () => {
      const withCount = estimateOperationTime('book.save', { chapterCount: 100 });
      const withNone = estimateOperationTime('book.save');
      expect(withCount.average).toBe(withNone.average);
    });
  });

  describe('wordCount metadata', () => {
    it('export.pdf with wordCount=50000 adds 100000ms → clamped to max 60000', () => {
      const result = estimateOperationTime('export.pdf', { wordCount: 50000 });
      // 10000 + (50000/1000)*2000 = 10000 + 100000 = 110000 → clamped to 60000
      expect(result.average).toBe(60000);
    });

    it('export.docx with wordCount=10000 adds 10000ms', () => {
      const result = estimateOperationTime('export.docx', { wordCount: 10000 });
      // 5000 + (10000/1000)*1000 = 5000 + 10000 = 15000
      expect(result.average).toBe(15000);
    });

    it('chapter.draft with wordCount=3000 adds 9000ms (3 * 3000)', () => {
      const result = estimateOperationTime('chapter.draft', { wordCount: 3000 });
      // 10000 + 9000 = 19000
      expect(result.average).toBe(19000);
    });

    it('wordCount=0 is ignored (falsy check)', () => {
      const withZero = estimateOperationTime('export.pdf', { wordCount: 0 });
      const withNone = estimateOperationTime('export.pdf');
      expect(withZero.average).toBe(withNone.average);
    });

    it('operation without perThousandWords ignores wordCount', () => {
      const withCount = estimateOperationTime('toc.readiness', { wordCount: 100000 });
      const withNone = estimateOperationTime('toc.readiness');
      expect(withCount.average).toBe(withNone.average);
    });
  });

  describe('questionCount metadata', () => {
    it('toc.questions with questionCount=5 adds 5000ms (5 * 1000)', () => {
      const result = estimateOperationTime('toc.questions', { questionCount: 5 });
      // 5000 + 5000 = 10000
      expect(result.average).toBe(10000);
    });

    it('chapter.draft with questionCount=3 adds 6000ms (3 * 2000)', () => {
      const result = estimateOperationTime('chapter.draft', { questionCount: 3 });
      // 10000 + 6000 = 16000
      expect(result.average).toBe(16000);
    });

    it('questionCount=0 is ignored (falsy check)', () => {
      const withZero = estimateOperationTime('toc.questions', { questionCount: 0 });
      const withNone = estimateOperationTime('toc.questions');
      expect(withZero.average).toBe(withNone.average);
    });
  });

  describe('networkSpeed metadata', () => {
    it('networkSpeed < 10 Mbps multiplies estimate by 1.2', () => {
      const slow = estimateOperationTime('toc.generation', { networkSpeed: 5 });
      const normal = estimateOperationTime('toc.generation');
      expect(slow.average).toBe(Math.min(Math.round(normal.average * 1.2), 30000));
    });

    it('networkSpeed exactly 10 Mbps does NOT apply the multiplier', () => {
      const at10 = estimateOperationTime('toc.generation', { networkSpeed: 10 });
      const normal = estimateOperationTime('toc.generation');
      expect(at10.average).toBe(normal.average);
    });

    it('networkSpeed > 10 Mbps does NOT apply the multiplier', () => {
      const fast = estimateOperationTime('toc.generation', { networkSpeed: 100 });
      const normal = estimateOperationTime('toc.generation');
      expect(fast.average).toBe(normal.average);
    });

    it('networkSpeed multiplier applies after other metadata additions', () => {
      // 10000 + 10*500 = 15000; * 1.2 = 18000
      const result = estimateOperationTime('toc.generation', { chapterCount: 10, networkSpeed: 5 });
      expect(result.average).toBe(18000);
    });
  });

  describe('clamping to min/max', () => {
    it('average is never below min', () => {
      const result = estimateOperationTime('toc.generation');
      expect(result.average).toBeGreaterThanOrEqual(result.min);
    });

    it('average is never above max', () => {
      const result = estimateOperationTime('export.pdf', {
        wordCount: 1000000,
        chapterCount: 1000,
      });
      expect(result.average).toBe(result.max);
    });

    it('average is clamped to max when combined metadata exceeds it', () => {
      // Large inputs push estimate beyond max
      const result = estimateOperationTime('toc.generation', { chapterCount: 1000 });
      expect(result.average).toBe(30000); // max for toc.generation
    });
  });

  describe('combined metadata', () => {
    it('export.pdf with wordCount + chapterCount combines both contributions', () => {
      // 10000 + (10000/1000)*2000 + 3*1000 = 10000 + 20000 + 3000 = 33000
      const result = estimateOperationTime('export.pdf', { wordCount: 10000, chapterCount: 3 });
      expect(result.average).toBe(33000);
    });
  });
});

// =====================================================================
// formatTime
// =====================================================================

describe('formatTime', () => {
  it('returns "0s" for 0ms', () => {
    expect(formatTime(0)).toBe('0s');
  });

  it('returns "1s" for 1ms (Math.ceil rounding)', () => {
    expect(formatTime(1)).toBe('1s');
  });

  it('returns "1s" for exactly 1000ms', () => {
    expect(formatTime(1000)).toBe('1s');
  });

  it('returns "5s" for 5000ms', () => {
    expect(formatTime(5000)).toBe('5s');
  });

  it('returns "59s" for 59000ms', () => {
    expect(formatTime(59000)).toBe('59s');
  });

  it('returns "1m" for 60000ms (no remaining seconds)', () => {
    expect(formatTime(60000)).toBe('1m');
  });

  it('returns "1m" for 59001ms (ceil rounds up to 60s → 1m)', () => {
    // Math.ceil(59001/1000) = 60 seconds = 1m 0s → "1m"
    expect(formatTime(59001)).toBe('1m');
  });

  it('returns "1m 1s" for 61000ms', () => {
    expect(formatTime(61000)).toBe('1m 1s');
  });

  it('returns "2m 30s" for 150000ms', () => {
    expect(formatTime(150000)).toBe('2m 30s');
  });

  it('returns "59m 59s" for 3599000ms', () => {
    expect(formatTime(3599000)).toBe('59m 59s');
  });

  it('returns "1h" for 3600000ms (no remaining minutes)', () => {
    expect(formatTime(3600000)).toBe('1h');
  });

  it('returns "1h 1m" for 3660000ms', () => {
    expect(formatTime(3660000)).toBe('1h 1m');
  });

  it('returns "2h 30m" for 9000000ms', () => {
    expect(formatTime(9000000)).toBe('2h 30m');
  });

  it('returns "1h" when remaining minutes is exactly 0', () => {
    expect(formatTime(7200000)).toBe('2h');
  });

  it('handles large values (10 hours)', () => {
    expect(formatTime(36000000)).toBe('10h');
  });
});

// =====================================================================
// getProgressEstimate
// =====================================================================

describe('getProgressEstimate', () => {
  it('returns 0 when estimatedTotal is 0', () => {
    expect(getProgressEstimate(5000, 0)).toBe(0);
  });

  it('returns 0 when estimatedTotal is negative', () => {
    expect(getProgressEstimate(5000, -100)).toBe(0);
  });

  it('returns 95 when elapsedTime equals estimatedTotal', () => {
    expect(getProgressEstimate(10000, 10000)).toBe(95);
  });

  it('returns 95 when elapsedTime exceeds estimatedTotal', () => {
    expect(getProgressEstimate(15000, 10000)).toBe(95);
  });

  it('returns 0 at the very start (elapsedTime=0)', () => {
    expect(getProgressEstimate(0, 10000)).toBe(0);
  });

  it('returns a positive value when some time has elapsed', () => {
    expect(getProgressEstimate(1000, 10000)).toBeGreaterThan(0);
  });

  it('progress increases as elapsed time increases', () => {
    const total = 10000;
    const p1 = getProgressEstimate(1000, total);
    const p2 = getProgressEstimate(3000, total);
    const p3 = getProgressEstimate(6000, total);
    expect(p1).toBeLessThan(p2);
    expect(p2).toBeLessThan(p3);
  });

  it('never exceeds 95 for any in-range elapsed time', () => {
    const total = 10000;
    for (let elapsed = 0; elapsed <= total; elapsed += 500) {
      expect(getProgressEstimate(elapsed, total)).toBeLessThanOrEqual(95);
    }
  });

  it('returns a whole number (Math.round applied)', () => {
    const result = getProgressEstimate(3333, 10000);
    expect(Number.isInteger(result)).toBe(true);
  });

  it('progress at 50% elapsed is less than 50% (logarithmic, starts fast, slows down)', () => {
    // Logarithmic curve: progress at half-time > 50
    const progress = getProgressEstimate(5000, 10000);
    expect(progress).toBeGreaterThan(50);
  });

  it('handles very small estimatedTotal', () => {
    expect(getProgressEstimate(0, 1)).toBe(0);
    expect(getProgressEstimate(1, 1)).toBe(95);
  });
});

// =====================================================================
// createProgressTracker
// =====================================================================

describe('createProgressTracker', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns a function', () => {
    const tracker = createProgressTracker('toc.generation');
    expect(typeof tracker).toBe('function');
  });

  it('initial call returns progress=0 (no time elapsed)', () => {
    const tracker = createProgressTracker('toc.generation');
    const { progress } = tracker();
    expect(progress).toBe(0);
  });

  it('initial elapsedTime is 0', () => {
    const tracker = createProgressTracker('toc.generation');
    const { elapsedTime } = tracker();
    expect(elapsedTime).toBe(0);
  });

  it('returns the estimate object from estimateOperationTime', () => {
    const tracker = createProgressTracker('toc.generation', { chapterCount: 10 });
    const { estimate } = tracker();
    expect(estimate).toMatchObject({
      min: 5000,
      max: 30000,
      average: 15000,
    });
  });

  it('progress increases as time advances', () => {
    const tracker = createProgressTracker('toc.generation');
    const { progress: p1 } = tracker();

    jest.advanceTimersByTime(5000);
    const { progress: p2 } = tracker();

    expect(p2).toBeGreaterThan(p1);
  });

  it('estimatedTimeRemaining decreases as time advances', () => {
    const tracker = createProgressTracker('toc.generation');
    const { estimatedTimeRemaining: r1 } = tracker();

    jest.advanceTimersByTime(3000);
    const { estimatedTimeRemaining: r2 } = tracker();

    expect(r2).toBeLessThan(r1);
  });

  it('estimatedTimeRemaining is never negative', () => {
    const tracker = createProgressTracker('toc.generation');
    // Advance way past the estimated total
    jest.advanceTimersByTime(999999);
    const { estimatedTimeRemaining } = tracker();
    expect(estimatedTimeRemaining).toBeGreaterThanOrEqual(0);
  });

  it('progress never exceeds 95', () => {
    const tracker = createProgressTracker('toc.generation');
    jest.advanceTimersByTime(999999);
    const { progress } = tracker();
    expect(progress).toBeLessThanOrEqual(95);
  });

  it('elapsedTime is tracked correctly', () => {
    const tracker = createProgressTracker('book.save');
    jest.advanceTimersByTime(200);
    const { elapsedTime } = tracker();
    expect(elapsedTime).toBeGreaterThanOrEqual(200);
  });

  it('accepts operation metadata and uses it for the estimate', () => {
    const trackerWithMeta = createProgressTracker('export.pdf', { chapterCount: 5 });
    const { estimate } = trackerWithMeta();
    // 10000 + 5*1000 = 15000
    expect(estimate.average).toBe(15000);
  });
});

// =====================================================================
// OPERATION_TIME_BUDGETS
// =====================================================================

describe('OPERATION_TIME_BUDGETS', () => {
  it('is exported and is an object', () => {
    expect(typeof OPERATION_TIME_BUDGETS).toBe('object');
    expect(OPERATION_TIME_BUDGETS).not.toBeNull();
  });

  it('contains toc.generation budget', () => {
    expect(OPERATION_TIME_BUDGETS['toc.generation']).toBeDefined();
    expect(OPERATION_TIME_BUDGETS['toc.generation'].base).toBe(10000);
  });

  it('contains export.pdf budget', () => {
    expect(OPERATION_TIME_BUDGETS['export.pdf']).toBeDefined();
    expect(OPERATION_TIME_BUDGETS['export.pdf'].min).toBe(5000);
  });

  it('contains export.epub and export.markdown budgets (#194 — no silent DOCX fallback)', () => {
    expect(OPERATION_TIME_BUDGETS['export.epub']).toBeDefined();
    expect(OPERATION_TIME_BUDGETS['export.markdown']).toBeDefined();
  });

  it('contains default budget', () => {
    expect(OPERATION_TIME_BUDGETS['default']).toBeDefined();
    expect(OPERATION_TIME_BUDGETS['default'].base).toBe(3000);
  });
});
