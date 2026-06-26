/**
 * Tests for src/lib/errors/handler.ts
 *
 * handleApiCall, createRetryWrapper, manualRetry
 *
 * Uses jest fake timers to control the `sleep` calls inside handleApiCall.
 */
import { handleApiCall, createRetryWrapper, manualRetry } from './handler';
import { ErrorType } from './types';

// ---------------------------------------------------------------------------
// Helpers to create errors that the classifier will recognise
// ---------------------------------------------------------------------------

/** Produces an error classified as TRANSIENT (retryable=true) */
function transientError(msg = 'network connection lost') {
  return new Error(msg);
}

/** Produces an error classified as PERMANENT (retryable=false) */
function permanentError(statusCode = 401) {
  return { statusCode, message: `HTTP ${statusCode}` };
}

/** Produces an error classified as SYSTEM (retryable=false) */
function systemError(statusCode = 500) {
  return { statusCode, message: `HTTP ${statusCode}` };
}

/** Produces an error classified as AI_SERVICE (retryable=false) */
function aiServiceError() {
  return { statusCode: 429, message: 'Rate limited' };
}

// ---------------------------------------------------------------------------
// handleApiCall
// ---------------------------------------------------------------------------

describe('handleApiCall', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  // ---- success path --------------------------------------------------------

  it('resolves with success=true and data on the first call', async () => {
    const apiCall = jest.fn().mockResolvedValue({ id: 1 });

    const result = await handleApiCall(apiCall);

    expect(result.success).toBe(true);
    expect(result.data).toEqual({ id: 1 });
    expect(result.attempts).toBe(0);
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  it('does NOT call onSuccess when the first attempt succeeds (attempt === 0)', async () => {
    const onSuccess = jest.fn();
    const apiCall = jest.fn().mockResolvedValue('ok');

    await handleApiCall(apiCall, { onSuccess });

    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('calls onSuccess with the attempt count after succeeding on a retry', async () => {
    const onSuccess = jest.fn();
    const err = transientError();
    const apiCall = jest.fn()
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce('done');

    const promise = handleApiCall(apiCall, { onSuccess });
    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(true);
    expect(onSuccess).toHaveBeenCalledWith(1);
  });

  // ---- retry on TRANSIENT errors ------------------------------------------

  it('retries on TRANSIENT (network) errors and returns success if the retry succeeds', async () => {
    const err = transientError();
    const apiCall = jest.fn()
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce({ ok: true });

    const promise = handleApiCall(apiCall);
    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(true);
    expect(apiCall).toHaveBeenCalledTimes(2);
  });

  it('exhausts all attempts and returns failure if every call throws TRANSIENT', async () => {
    const err = transientError();
    const apiCall = jest.fn().mockRejectedValue(err);

    const promise = handleApiCall(apiCall, { retryConfig: { maxAttempts: 2 } });
    promise.catch(() => {});

    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
    // Total calls = maxAttempts + 1 (initial + 2 retries, final check at attempt=2 fails canRetry)
    expect(apiCall).toHaveBeenCalledTimes(3);
  });

  it('returns the classified error when retries are exhausted', async () => {
    const err = transientError();
    const apiCall = jest.fn().mockRejectedValue(err);

    const promise = handleApiCall(apiCall, { retryConfig: { maxAttempts: 1 } });
    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(false);
    expect(result.error?.type).toBe(ErrorType.TRANSIENT);
  });

  // ---- no retry for non-TRANSIENT errors ----------------------------------

  it('does NOT retry PERMANENT errors (401)', async () => {
    const apiCall = jest.fn().mockRejectedValue(permanentError(401));

    const result = await handleApiCall(apiCall);

    expect(result.success).toBe(false);
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  it('does NOT retry SYSTEM errors (500)', async () => {
    const apiCall = jest.fn().mockRejectedValue(systemError(500));

    const result = await handleApiCall(apiCall);

    expect(result.success).toBe(false);
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  it('does NOT retry AI_SERVICE errors (429)', async () => {
    const apiCall = jest.fn().mockRejectedValue(aiServiceError());

    const result = await handleApiCall(apiCall);

    expect(result.success).toBe(false);
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  it('sets attempts to 0 for immediate non-retryable failure', async () => {
    const apiCall = jest.fn().mockRejectedValue(permanentError(403));

    const result = await handleApiCall(apiCall);

    expect(result.attempts).toBe(0);
  });

  // ---- callbacks ----------------------------------------------------------

  it('calls onRetry with (attempt+1, classifiedError) before each retry', async () => {
    const onRetry = jest.fn();
    const err = transientError();
    const apiCall = jest.fn()
      .mockRejectedValueOnce(err)
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce('done');

    const promise = handleApiCall(apiCall, { onRetry });
    await jest.runAllTimersAsync();
    await promise;

    // onRetry called before attempt 1 and attempt 2
    expect(onRetry).toHaveBeenCalledTimes(2);
    expect(onRetry.mock.calls[0][0]).toBe(1); // first retry = attempt+1 = 1
    expect(onRetry.mock.calls[1][0]).toBe(2); // second retry = attempt+1 = 2
    expect(onRetry.mock.calls[0][1]).toBeDefined(); // classified error
  });

  it('calls onFailure with the classified error when retries are exhausted', async () => {
    const onFailure = jest.fn();
    const apiCall = jest.fn().mockRejectedValue(permanentError(403));

    await handleApiCall(apiCall, { onFailure });

    expect(onFailure).toHaveBeenCalledTimes(1);
    expect(onFailure.mock.calls[0][0].type).toBe(ErrorType.PERMANENT);
  });

  it('calls onFailure after exhausting TRANSIENT retries', async () => {
    const onFailure = jest.fn();
    const err = transientError();
    const apiCall = jest.fn().mockRejectedValue(err);

    const promise = handleApiCall(apiCall, {
      retryConfig: { maxAttempts: 1 },
      onFailure,
    });
    await jest.runAllTimersAsync();
    await promise;

    expect(onFailure).toHaveBeenCalledTimes(1);
  });

  // ---- custom retryConfig -------------------------------------------------

  it('respects custom maxAttempts: 0 (no retries, single call)', async () => {
    const err = transientError();
    const apiCall = jest.fn().mockRejectedValue(err);

    const result = await handleApiCall(apiCall, { retryConfig: { maxAttempts: 0 } });

    expect(result.success).toBe(false);
    // With maxAttempts=0: while(attempt <= 0) fires once, canRetry(0,0)=false → failure
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  it('respects custom baseDelay for sleep timing', async () => {
    const onRetry = jest.fn();
    const err = transientError();
    const apiCall = jest.fn()
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce('ok');

    const promise = handleApiCall(apiCall, {
      retryConfig: { maxAttempts: 1, baseDelay: 500, maxDelay: 5000, useExponentialBackoff: false },
      onRetry,
    });

    // Should NOT have retried before 500ms
    await jest.advanceTimersByTimeAsync(499);
    expect(apiCall).toHaveBeenCalledTimes(1);

    // After 500ms, retry fires
    await jest.advanceTimersByTimeAsync(1);
    await promise;

    expect(apiCall).toHaveBeenCalledTimes(2);
  });

  // ---- context is passed through ------------------------------------------

  it('accepts a context string without error', async () => {
    const apiCall = jest.fn().mockResolvedValue('result');

    const result = await handleApiCall(apiCall, { context: 'Unit test context' });

    expect(result.success).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// createRetryWrapper
// ---------------------------------------------------------------------------

describe('createRetryWrapper', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns a function', () => {
    const wrapped = createRetryWrapper(jest.fn());
    expect(typeof wrapped).toBe('function');
  });

  it('calls the wrapped function with the correct arguments', async () => {
    const inner = jest.fn().mockResolvedValue({ data: true });
    const wrapped = createRetryWrapper(inner);

    const result = await wrapped('arg1', 42);

    expect(inner).toHaveBeenCalledWith('arg1', 42);
    expect(result.success).toBe(true);
    expect(result.data).toEqual({ data: true });
  });

  it('returns an ErrorHandlerResult (success:false) on failure', async () => {
    const inner = jest.fn().mockRejectedValue(permanentError(404));
    const wrapped = createRetryWrapper(inner);

    const result = await wrapped('id-123');

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('retries on TRANSIENT errors with default options', async () => {
    const err = transientError();
    const inner = jest.fn()
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce('value');

    const wrapped = createRetryWrapper(inner, {
      retryConfig: { maxAttempts: 1, baseDelay: 100, maxDelay: 500, useExponentialBackoff: false },
    });

    const promise = wrapped();
    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(true);
    expect(inner).toHaveBeenCalledTimes(2);
  });

  it('forwards default options (onFailure) to handleApiCall', async () => {
    const onFailure = jest.fn();
    const inner = jest.fn().mockRejectedValue(permanentError(401));
    const wrapped = createRetryWrapper(inner, { onFailure });

    await wrapped();

    expect(onFailure).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// manualRetry
// ---------------------------------------------------------------------------

describe('manualRetry', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('calls the onRetry callback before executing the operation', async () => {
    const onRetry = jest.fn();
    const operation = jest.fn().mockResolvedValue('success');

    await manualRetry(operation, onRetry);

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('does not throw if onRetry is omitted', async () => {
    const operation = jest.fn().mockResolvedValue('ok');

    await expect(manualRetry(operation)).resolves.toBeDefined();
  });

  it('returns success result when operation succeeds', async () => {
    const operation = jest.fn().mockResolvedValue({ value: 42 });

    const result = await manualRetry(operation);

    expect(result.success).toBe(true);
    expect(result.data).toEqual({ value: 42 });
  });

  it('returns failure result when operation fails', async () => {
    const operation = jest.fn().mockRejectedValue(permanentError(404));

    const result = await manualRetry(operation);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('uses maxAttempts: 1 (single retry at most for TRANSIENT errors)', async () => {
    // maxAttempts:1 → initial call + up to 1 retry = max 2 API calls before failure
    const err = transientError();
    const operation = jest.fn().mockRejectedValue(err);

    const promise = manualRetry(operation);
    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(false);
    // canRetry(0,1)=true → retry once; canRetry(1,1)=false → stop; total=2
    expect(operation).toHaveBeenCalledTimes(2);
  });

  it('succeeds on the retry within manualRetry (maxAttempts: 1)', async () => {
    const err = transientError();
    const operation = jest.fn()
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce('retried success');

    const promise = manualRetry(operation);
    await jest.runAllTimersAsync();
    const result = await promise;

    expect(result.success).toBe(true);
    expect(result.data).toBe('retried success');
    expect(operation).toHaveBeenCalledTimes(2);
  });
});
