/**
 * Jest mock for @sentry/nextjs (#334).
 *
 * Keeps the test run deterministic and off the real SDK. Tests that assert
 * error/metric reporting spy on these jest.fn()s.
 */
export const init = jest.fn();
export const captureException = jest.fn();
export const captureMessage = jest.fn();
export const captureRequestError = jest.fn();
