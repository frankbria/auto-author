/**
 * Tests for src/lib/errors/utils.ts
 */
import {
  generateCorrelationId,
  calculateRetryDelay,
  sleep,
  canRetry,
  formatErrorMessage,
  getErrorMessage,
} from './utils';

describe('generateCorrelationId', () => {
  it('returns a non-empty string', () => {
    const id = generateCorrelationId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  it('has the format <timestamp>-<random> (exactly one hyphen section)', () => {
    const id = generateCorrelationId();
    const parts = id.split('-');
    expect(parts.length).toBe(2);
    expect(parts[0].length).toBeGreaterThan(0);
    expect(parts[1].length).toBeGreaterThan(0);
  });

  it('generates unique IDs on successive calls', () => {
    const ids = new Set(Array.from({ length: 20 }, () => generateCorrelationId()));
    // All 20 should be unique (random component makes collision virtually impossible)
    expect(ids.size).toBe(20);
  });
});

describe('calculateRetryDelay', () => {
  describe('without exponential backoff', () => {
    it('returns baseDelay when baseDelay <= maxDelay', () => {
      expect(calculateRetryDelay(0, 1000, 5000, false)).toBe(1000);
    });

    it('returns baseDelay for any attempt number', () => {
      expect(calculateRetryDelay(5, 1000, 5000, false)).toBe(1000);
    });

    it('is capped at maxDelay when baseDelay > maxDelay', () => {
      expect(calculateRetryDelay(0, 10000, 5000, false)).toBe(5000);
    });
  });

  describe('with exponential backoff', () => {
    it('returns baseDelay on attempt 0 (2^0 = 1)', () => {
      expect(calculateRetryDelay(0, 1000, 30000, true)).toBe(1000);
    });

    it('returns baseDelay * 2 on attempt 1', () => {
      expect(calculateRetryDelay(1, 1000, 30000, true)).toBe(2000);
    });

    it('returns baseDelay * 4 on attempt 2', () => {
      expect(calculateRetryDelay(2, 1000, 30000, true)).toBe(4000);
    });

    it('returns baseDelay * 8 on attempt 3', () => {
      expect(calculateRetryDelay(3, 1000, 30000, true)).toBe(8000);
    });

    it('is capped at maxDelay for large attempt numbers', () => {
      const result = calculateRetryDelay(10, 1000, 5000, true);
      expect(result).toBe(5000);
    });

    it('exactly equals maxDelay when computed delay exceeds it', () => {
      // baseDelay=2000, attempt=3 → 2000 * 8 = 16000 > maxDelay=8000
      expect(calculateRetryDelay(3, 2000, 8000, true)).toBe(8000);
    });
  });
});

describe('sleep', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns a Promise', () => {
    const result = sleep(100);
    expect(result).toBeInstanceOf(Promise);
    // clean up pending timer
    jest.runAllTimers();
  });

  it('does not resolve before the specified time', async () => {
    const resolved = jest.fn();
    sleep(1000).then(resolved);

    await jest.advanceTimersByTimeAsync(999);
    expect(resolved).not.toHaveBeenCalled();

    await jest.advanceTimersByTimeAsync(1);
    expect(resolved).toHaveBeenCalled();
  });

  it('resolves with undefined after the specified time', async () => {
    let resolvedValue: unknown = 'sentinel';
    sleep(500).then((v) => {
      resolvedValue = v;
    });

    await jest.advanceTimersByTimeAsync(500);
    expect(resolvedValue).toBeUndefined();
  });

  it('resolves for 0ms immediately', async () => {
    const resolved = jest.fn();
    sleep(0).then(resolved);

    await jest.advanceTimersByTimeAsync(0);
    expect(resolved).toHaveBeenCalled();
  });
});

describe('canRetry', () => {
  it('returns true when attempt is below maxAttempts', () => {
    expect(canRetry(0, 3)).toBe(true);
    expect(canRetry(1, 3)).toBe(true);
    expect(canRetry(2, 3)).toBe(true);
  });

  it('returns false when attempt equals maxAttempts', () => {
    expect(canRetry(3, 3)).toBe(false);
  });

  it('returns false when attempt exceeds maxAttempts', () => {
    expect(canRetry(4, 3)).toBe(false);
    expect(canRetry(100, 3)).toBe(false);
  });

  it('returns false immediately when maxAttempts is 0', () => {
    expect(canRetry(0, 0)).toBe(false);
  });

  it('works correctly for maxAttempts of 1', () => {
    expect(canRetry(0, 1)).toBe(true);
    expect(canRetry(1, 1)).toBe(false);
  });
});

describe('formatErrorMessage', () => {
  it('returns just the message when no details provided', () => {
    expect(formatErrorMessage('Something went wrong')).toBe('Something went wrong');
  });

  it('returns just the message when details is undefined', () => {
    expect(formatErrorMessage('Something went wrong', undefined)).toBe('Something went wrong');
  });

  it('returns message with Details section when details are provided', () => {
    const result = formatErrorMessage('Something went wrong', 'Request timed out');
    expect(result).toBe('Something went wrong\n\nDetails: Request timed out');
  });

  it('includes empty details if details is an empty string', () => {
    // empty string is falsy, so treated as no details
    const result = formatErrorMessage('Error', '');
    expect(result).toBe('Error');
  });
});

describe('getErrorMessage', () => {
  it('returns the message from an Error instance', () => {
    expect(getErrorMessage(new Error('Test error'))).toBe('Test error');
  });

  it('returns the message from an Error subclass', () => {
    class CustomError extends Error {}
    const err = new CustomError('Custom error');
    expect(getErrorMessage(err)).toBe('Custom error');
  });

  it('returns a string error as-is', () => {
    expect(getErrorMessage('plain string error')).toBe('plain string error');
  });

  it('extracts message from an object with a message property', () => {
    expect(getErrorMessage({ message: 'object message' })).toBe('object message');
  });

  it('extracts error string from an object with an error string property', () => {
    expect(getErrorMessage({ error: 'error string value' })).toBe('error string value');
  });

  it('prefers message over error property', () => {
    expect(getErrorMessage({ message: 'primary', error: 'secondary' })).toBe('primary');
  });

  it('falls back to JSON.stringify for objects with no message or error', () => {
    const result = getErrorMessage({ code: 42, reason: 'unknown' });
    expect(result).toBe('{"code":42,"reason":"unknown"}');
  });

  it('returns default message for null', () => {
    expect(getErrorMessage(null)).toBe('An unknown error occurred');
  });

  it('returns default message for undefined', () => {
    expect(getErrorMessage(undefined)).toBe('An unknown error occurred');
  });

  it('returns default message for a number', () => {
    expect(getErrorMessage(42)).toBe('An unknown error occurred');
  });

  it('returns default message for a boolean', () => {
    expect(getErrorMessage(false)).toBe('An unknown error occurred');
  });
});
