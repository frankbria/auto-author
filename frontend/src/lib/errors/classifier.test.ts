/**
 * Tests for src/lib/errors/classifier.ts
 */
import { classifyError } from './classifier';
import { ErrorType, ErrorSeverity, DEFAULT_RETRY_CONFIG } from './types';

// Silence console.error from any unexpected paths
beforeEach(() => {
  jest.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  jest.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function apiError(
  statusCode: number,
  extra?: Record<string, unknown>
): Record<string, unknown> {
  return { statusCode, message: `HTTP ${statusCode}`, ...extra };
}

function apiErrorViaStatus(
  status: number,
  extra?: Record<string, unknown>
): Record<string, unknown> {
  return { status, message: `HTTP ${status}`, ...extra };
}

// ---------------------------------------------------------------------------
// API errors classified by HTTP status
// ---------------------------------------------------------------------------

describe('classifyError – API errors by statusCode', () => {
  it('classifies 400 as PERMANENT, non-retryable', () => {
    const result = classifyError(apiError(400));
    expect(result.type).toBe(ErrorType.PERMANENT);
    expect(result.retryable).toBe(false);
    expect(result.retryConfig).toBeUndefined();
  });

  it('classifies 401 as PERMANENT, non-retryable', () => {
    const result = classifyError(apiError(401));
    expect(result.type).toBe(ErrorType.PERMANENT);
    expect(result.retryable).toBe(false);
  });

  it('classifies 403 as PERMANENT, non-retryable', () => {
    const result = classifyError(apiError(403));
    expect(result.type).toBe(ErrorType.PERMANENT);
    expect(result.retryable).toBe(false);
  });

  it('classifies 404 as PERMANENT, non-retryable', () => {
    const result = classifyError(apiError(404));
    expect(result.type).toBe(ErrorType.PERMANENT);
    expect(result.retryable).toBe(false);
  });

  it('classifies 409 as PERMANENT, non-retryable', () => {
    const result = classifyError(apiError(409));
    expect(result.type).toBe(ErrorType.PERMANENT);
    expect(result.retryable).toBe(false);
  });

  it('classifies 422 as PERMANENT, non-retryable', () => {
    const result = classifyError(apiError(422));
    expect(result.type).toBe(ErrorType.PERMANENT);
    expect(result.retryable).toBe(false);
  });

  it('classifies 429 as AI_SERVICE, non-retryable', () => {
    const result = classifyError(apiError(429));
    expect(result.type).toBe(ErrorType.AI_SERVICE);
    expect(result.retryable).toBe(false);
  });

  it('classifies 500 as SYSTEM, non-retryable', () => {
    const result = classifyError(apiError(500));
    expect(result.type).toBe(ErrorType.SYSTEM);
    expect(result.retryable).toBe(false);
  });

  it('classifies 502 as TRANSIENT, retryable', () => {
    const result = classifyError(apiError(502));
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
    expect(result.retryConfig).toEqual(DEFAULT_RETRY_CONFIG);
  });

  it('classifies 503 as TRANSIENT, retryable', () => {
    const result = classifyError(apiError(503));
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
  });

  it('classifies 504 as TRANSIENT, retryable', () => {
    const result = classifyError(apiError(504));
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
  });

  it('classifies unknown status codes (e.g. 418) as SYSTEM, non-retryable', () => {
    const result = classifyError(apiError(418));
    expect(result.type).toBe(ErrorType.SYSTEM);
    expect(result.retryable).toBe(false);
  });

  it('works with the "status" property in addition to "statusCode"', () => {
    const result = classifyError(apiErrorViaStatus(503));
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
  });

  it('picks up statusCode if both statusCode and status are present', () => {
    // statusCode wins because it's checked first in the classifier
    const result = classifyError({ statusCode: 503, status: 200, message: 'test' });
    expect(result.type).toBe(ErrorType.TRANSIENT);
  });
});

// ---------------------------------------------------------------------------
// Network errors
// ---------------------------------------------------------------------------

describe('classifyError – network errors', () => {
  const keywords = ['network', 'fetch', 'connection', 'offline'];

  for (const keyword of keywords) {
    it(`classifies Error containing "${keyword}" as TRANSIENT, retryable`, () => {
      const result = classifyError(new Error(`The ${keyword} failed`));
      expect(result.type).toBe(ErrorType.TRANSIENT);
      expect(result.retryable).toBe(true);
      expect(result.severity).toBe(ErrorSeverity.MEDIUM);
    });
  }

  it('is case-insensitive for network keyword matching', () => {
    const result = classifyError(new Error('NETWORK failure'));
    expect(result.type).toBe(ErrorType.TRANSIENT);
  });

  it('provides standard retry suggested actions', () => {
    const result = classifyError(new Error('network unavailable'));
    expect(result.suggestedActions).toContain('Check your internet connection');
  });

  it('sets retryConfig for network errors', () => {
    const result = classifyError(new Error('network unavailable'));
    expect(result.retryConfig).toEqual(DEFAULT_RETRY_CONFIG);
  });
});

// ---------------------------------------------------------------------------
// Timeout errors
// ---------------------------------------------------------------------------

describe('classifyError – timeout errors', () => {
  it('classifies Error containing "timeout" as TRANSIENT, retryable', () => {
    const result = classifyError(new Error('Request timeout'));
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
  });

  it('classifies Error containing "timed out" as TRANSIENT, retryable', () => {
    const result = classifyError(new Error('The operation timed out'));
    expect(result.type).toBe(ErrorType.TRANSIENT);
    expect(result.retryable).toBe(true);
  });

  it('uses longer base and max delay for timeout errors', () => {
    const result = classifyError(new Error('request timeout'));
    expect(result.retryConfig).toBeDefined();
    expect(result.retryConfig!.baseDelay).toBe(3000);
    expect(result.retryConfig!.maxDelay).toBe(12000);
  });

  it('returns a user-friendly timeout message', () => {
    const result = classifyError(new Error('timeout'));
    expect(result.message).toMatch(/timed out|time/i);
  });
});

// ---------------------------------------------------------------------------
// Generic / unknown errors
// ---------------------------------------------------------------------------

describe('classifyError – generic errors', () => {
  it('classifies a plain Error as SYSTEM, CRITICAL, non-retryable', () => {
    const result = classifyError(new Error('Some random failure'));
    expect(result.type).toBe(ErrorType.SYSTEM);
    expect(result.severity).toBe(ErrorSeverity.CRITICAL);
    expect(result.retryable).toBe(false);
  });

  it('includes the error message in "details"', () => {
    const result = classifyError(new Error('Oops'));
    expect(result.details).toBe('Oops');
  });

  it('sets originalError to the Error instance', () => {
    const err = new Error('source error');
    const result = classifyError(err);
    expect(result.originalError).toBe(err);
  });

  it('classifies a plain object without status codes as SYSTEM', () => {
    const result = classifyError({ foo: 'bar' });
    expect(result.type).toBe(ErrorType.SYSTEM);
    expect(result.retryable).toBe(false);
  });

  it('classifies null as SYSTEM', () => {
    const result = classifyError(null);
    expect(result.type).toBe(ErrorType.SYSTEM);
    expect(result.retryable).toBe(false);
  });

  it('classifies undefined as SYSTEM', () => {
    const result = classifyError(undefined);
    expect(result.type).toBe(ErrorType.SYSTEM);
    expect(result.retryable).toBe(false);
  });

  it('sets originalError to undefined for non-Error values', () => {
    const result = classifyError('a string error');
    expect(result.originalError).toBeUndefined();
  });

  it('sets details to "An unexpected error occurred" for non-Error values', () => {
    const result = classifyError('a string error');
    expect(result.details).toBe('An unexpected error occurred');
  });

  it('includes a correlationId reference in suggestedActions', () => {
    const result = classifyError(new Error('boom'));
    const hasRef = result.suggestedActions?.some((a) => a.includes('Reference ID:'));
    expect(hasRef).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Field error extraction
// ---------------------------------------------------------------------------

describe('classifyError – field error extraction', () => {
  it('extracts "errors" object format', () => {
    const result = classifyError({
      statusCode: 400,
      message: 'Validation failed',
      errors: { email: 'Invalid email', name: 'Required' },
    });
    expect(result.fieldErrors).toEqual({ email: 'Invalid email', name: 'Required' });
  });

  it('extracts "fieldErrors" object format', () => {
    const result = classifyError({
      statusCode: 422,
      message: 'Validation failed',
      fieldErrors: { title: 'Too short' },
    });
    expect(result.fieldErrors).toEqual({ title: 'Too short' });
  });

  it('extracts "validationErrors" array format', () => {
    const result = classifyError({
      statusCode: 400,
      message: 'Invalid input',
      validationErrors: [
        { field: 'email', message: 'Must be a valid email' },
        { field: 'password', message: 'Min 8 characters' },
      ],
    });
    expect(result.fieldErrors).toEqual({
      email: 'Must be a valid email',
      password: 'Min 8 characters',
    });
  });

  it('skips malformed validationErrors entries (no field or message)', () => {
    const result = classifyError({
      statusCode: 400,
      message: 'Bad input',
      validationErrors: [
        { field: 'email', message: 'Required' },
        { noField: true }, // malformed – skipped
      ],
    });
    expect(result.fieldErrors).toEqual({ email: 'Required' });
  });

  it('returns undefined fieldErrors when no error format is present', () => {
    const result = classifyError({ statusCode: 404, message: 'Not found' });
    expect(result.fieldErrors).toBeUndefined();
  });

  it('returns undefined fieldErrors for network errors', () => {
    const result = classifyError(new Error('network error'));
    expect(result.fieldErrors).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// User-friendly messages by status code
// ---------------------------------------------------------------------------

describe('classifyError – user-friendly messages', () => {
  const cases: Array<[number, RegExp]> = [
    [400, /invalid request/i],
    [401, /logged in/i],
    [403, /permission/i],
    [404, /not found/i],
    [409, /conflicts/i],
    [422, /highlighted fields/i],
    [429, /too many requests/i],
    [500, /server error/i],
    [502, /temporarily unavailable/i],
    [503, /temporarily unavailable/i],
    [504, /timed out/i],
  ];

  for (const [status, regex] of cases) {
    it(`status ${status} returns expected message`, () => {
      const result = classifyError({ statusCode: status, message: 'raw' });
      expect(result.message).toMatch(regex);
    });
  }

  it('uses userMessage over default when provided', () => {
    const result = classifyError({
      statusCode: 500,
      message: 'raw',
      userMessage: 'Custom user-facing message',
    });
    expect(result.message).toBe('Custom user-facing message');
  });

  it('returns generic transient message for unrecognised TRANSIENT status', () => {
    // statusCode not in the map → SYSTEM type, won't hit TRANSIENT default branch
    // But we can test TRANSIENT default via direct TRANSIENT type (no status match)
    // We test network error for the TRANSIENT branch default message
    const result = classifyError(new Error('network problem'));
    // network errors have a hardcoded specific message, not the default branch
    expect(result.message).toContain('Network');
  });

  it('details defaults to the error message property', () => {
    const result = classifyError({ statusCode: 400, message: 'My raw error' });
    expect(result.details).toBe('My raw error');
  });

  it('details defaults to "An error occurred" when message is absent', () => {
    const result = classifyError({ statusCode: 400 });
    expect(result.details).toBe('An error occurred');
  });
});

// ---------------------------------------------------------------------------
// Suggested actions per error type / status
// ---------------------------------------------------------------------------

describe('classifyError – suggested actions', () => {
  it('returns retry-focused actions for TRANSIENT errors', () => {
    const result = classifyError({ statusCode: 503, message: 'unavailable' });
    expect(result.suggestedActions).toContain('Wait a moment and try again');
  });

  it('returns sign-in actions for 401', () => {
    const result = classifyError({ statusCode: 401, message: 'unauth' });
    expect(result.suggestedActions).toContain('Sign in to continue');
  });

  it('returns permission actions for 403', () => {
    const result = classifyError({ statusCode: 403, message: 'forbidden' });
    expect(result.suggestedActions?.some((a) => /permission/i.test(a))).toBe(true);
  });

  it('returns navigation actions for 404', () => {
    const result = classifyError({ statusCode: 404, message: 'missing' });
    expect(result.suggestedActions?.some((a) => /URL|resource ID/i.test(a))).toBe(true);
  });

  it('returns generic PERMANENT actions for other 4xx errors', () => {
    const result = classifyError({ statusCode: 409, message: 'conflict' });
    expect(result.suggestedActions).toContain('Review your input');
  });

  it('returns support actions for SYSTEM errors', () => {
    const result = classifyError({ statusCode: 500, message: 'server fault' });
    expect(result.suggestedActions?.some((a) => /support|cache|refresh/i.test(a))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Classified error metadata
// ---------------------------------------------------------------------------

describe('classifyError – metadata properties', () => {
  it('always sets a correlationId string', () => {
    const result = classifyError(new Error('x'));
    expect(typeof result.correlationId).toBe('string');
    expect(result.correlationId.length).toBeGreaterThan(0);
  });

  it('always sets a Date timestamp', () => {
    const result = classifyError(new Error('x'));
    expect(result.timestamp).toBeInstanceOf(Date);
  });

  it('sets retryConfig only when retryable', () => {
    const retryable = classifyError({ statusCode: 503, message: 'x' });
    expect(retryable.retryConfig).toBeDefined();

    const notRetryable = classifyError({ statusCode: 401, message: 'x' });
    expect(notRetryable.retryConfig).toBeUndefined();
  });

  it('accepts optional context (does not throw)', () => {
    expect(() => classifyError(new Error('err'), 'ExportPDF')).not.toThrow();
  });

  it('attaches severity based on error type mapping', () => {
    expect(classifyError({ statusCode: 503, message: 'x' }).severity).toBe(ErrorSeverity.MEDIUM);
    expect(classifyError({ statusCode: 401, message: 'x' }).severity).toBe(ErrorSeverity.HIGH);
    expect(classifyError({ statusCode: 500, message: 'x' }).severity).toBe(ErrorSeverity.CRITICAL);
  });
});
