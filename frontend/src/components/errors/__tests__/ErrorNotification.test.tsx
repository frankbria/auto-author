/**
 * Tests for ErrorNotification component and helper functions.
 * Covers: ErrorNotification component rendering, showErrorNotification, showRecoveryNotification,
 * and the internal RetryCountdown component.
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  ErrorNotification,
  showErrorNotification,
  showRecoveryNotification,
} from '../ErrorNotification';
import { ClassifiedError, ErrorType, ErrorSeverity } from '@/lib/errors';

// Mock sonner toast – each method is a tracked jest.fn()
jest.mock('sonner', () => ({
  toast: Object.assign(jest.fn(), {
    error: jest.fn(),
    warning: jest.fn(),
    success: jest.fn(),
  }),
}));

import { toast as sonnerToast } from 'sonner';

// Typed access to mock sub-methods
const mockToast = sonnerToast as unknown as {
  error: jest.Mock;
  warning: jest.Mock;
  success: jest.Mock;
};

// Factory for ClassifiedError
function makeError(overrides: Partial<ClassifiedError> = {}): ClassifiedError {
  return {
    type: ErrorType.TRANSIENT,
    severity: ErrorSeverity.MEDIUM,
    message: 'Something went wrong',
    retryable: false,
    correlationId: 'corr-123',
    timestamp: new Date(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// ErrorNotification component
// ---------------------------------------------------------------------------

describe('ErrorNotification component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with role="alert"', () => {
    render(<ErrorNotification error={makeError()} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('displays the error message in the heading', () => {
    const error = makeError({ message: 'Custom error occurred' });
    render(<ErrorNotification error={error} />);
    expect(screen.getByText('Custom error occurred')).toBeInTheDocument();
  });

  it('displays error details when provided', () => {
    const error = makeError({ details: 'Detailed technical description' });
    render(<ErrorNotification error={error} />);
    expect(screen.getByText('Detailed technical description')).toBeInTheDocument();
  });

  it('does not render details paragraph when details is absent', () => {
    render(<ErrorNotification error={makeError()} />);
    // Only the heading, no second paragraph with gray-300 class
    expect(screen.queryByText('Detailed technical description')).not.toBeInTheDocument();
  });

  it('displays field errors when provided', () => {
    const error = makeError({
      type: ErrorType.PERMANENT,
      fieldErrors: { title: 'Title is required', author: 'Invalid author' },
    });
    render(<ErrorNotification error={error} />);
    expect(screen.getByText('title:')).toBeInTheDocument();
    expect(screen.getByText('Title is required')).toBeInTheDocument();
    expect(screen.getByText('author:')).toBeInTheDocument();
    expect(screen.getByText('Invalid author')).toBeInTheDocument();
  });

  it('does not render field errors list when fieldErrors is absent', () => {
    render(<ErrorNotification error={makeError()} />);
    expect(screen.queryByText('title:')).not.toBeInTheDocument();
  });

  it('does not render field errors list when fieldErrors is empty', () => {
    const error = makeError({ fieldErrors: {} });
    render(<ErrorNotification error={error} />);
    // Empty object → Object.keys.length === 0 → no list rendered
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('displays suggested actions when provided', () => {
    const error = makeError({
      suggestedActions: ['Refresh the page', 'Contact support'],
    });
    render(<ErrorNotification error={error} />);
    expect(screen.getByText('What you can do:')).toBeInTheDocument();
    expect(screen.getByText('Refresh the page')).toBeInTheDocument();
    expect(screen.getByText('Contact support')).toBeInTheDocument();
  });

  it('does not render actions section when suggestedActions is absent', () => {
    render(<ErrorNotification error={makeError()} />);
    expect(screen.queryByText('What you can do:')).not.toBeInTheDocument();
  });

  it('shows Reference ID for SYSTEM errors', () => {
    const error = makeError({ type: ErrorType.SYSTEM, correlationId: 'sys-err-42' });
    render(<ErrorNotification error={error} />);
    expect(screen.getByText(/Reference ID: sys-err-42/)).toBeInTheDocument();
  });

  it('does not show Reference ID for non-SYSTEM errors', () => {
    const error = makeError({ type: ErrorType.TRANSIENT, correlationId: 'corr-99' });
    render(<ErrorNotification error={error} />);
    expect(screen.queryByText(/Reference ID:/)).not.toBeInTheDocument();
  });

  it('shows "Cached Content" badge when isFromCache=true with AI_SERVICE error', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE });
    render(<ErrorNotification error={error} isFromCache={true} />);
    expect(screen.getByText('Cached Content')).toBeInTheDocument();
  });

  it('does not show "Cached Content" badge when isFromCache=false', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE });
    render(<ErrorNotification error={error} isFromCache={false} />);
    expect(screen.queryByText('Cached Content')).not.toBeInTheDocument();
  });

  it('shows "Generate Fresh" button when AI_SERVICE + isFromCache + retryable + onRetry', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE, retryable: true });
    render(<ErrorNotification error={error} isFromCache={true} onRetry={jest.fn()} />);
    expect(screen.getByText('Generate Fresh')).toBeInTheDocument();
  });

  it('shows "Retry" button label (not "Generate Fresh") when not from cache', () => {
    const error = makeError({ retryable: true });
    render(<ErrorNotification error={error} onRetry={jest.fn()} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
    expect(screen.queryByText('Generate Fresh')).not.toBeInTheDocument();
  });

  it('does not show Retry button when retryable=false', () => {
    const error = makeError({ retryable: false });
    render(<ErrorNotification error={error} onRetry={jest.fn()} />);
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('does not show Retry button when onRetry is not provided', () => {
    const error = makeError({ retryable: true });
    render(<ErrorNotification error={error} />);
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('calls onRetry when Retry button is clicked', () => {
    const onRetry = jest.fn();
    const error = makeError({ retryable: true });
    render(<ErrorNotification error={error} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('calls onRetry when "Generate Fresh" button is clicked', () => {
    const onRetry = jest.fn();
    const error = makeError({ type: ErrorType.AI_SERVICE, retryable: true });
    render(<ErrorNotification error={error} isFromCache={true} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Generate Fresh'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('shows Dismiss button in action area when onDismiss provided', () => {
    render(<ErrorNotification error={makeError()} onDismiss={jest.fn()} />);
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
  });

  it('does not show Dismiss button when onDismiss is absent', () => {
    render(<ErrorNotification error={makeError()} />);
    expect(screen.queryByText('Dismiss')).not.toBeInTheDocument();
  });

  it('calls onDismiss when Dismiss button is clicked', () => {
    const onDismiss = jest.fn();
    render(<ErrorNotification error={makeError()} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('calls onDismiss when the corner X icon button is clicked', () => {
    const onDismiss = jest.fn();
    render(<ErrorNotification error={makeError()} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('shows RetryCountdown instead of Retry button when retryAfter > 0', () => {
    const error = makeError();
    render(<ErrorNotification error={error} retryAfter={60} onRetry={jest.fn()} />);
    expect(screen.getByText(/Retry in 1:00/)).toBeInTheDocument();
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  // Background-color class assertions
  it('applies red background for SYSTEM error type', () => {
    const { container } = render(<ErrorNotification error={makeError({ type: ErrorType.SYSTEM })} />);
    expect(container.querySelector('[class*="bg-red-900"]')).toBeInTheDocument();
  });

  it('applies orange background for PERMANENT error type', () => {
    const { container } = render(<ErrorNotification error={makeError({ type: ErrorType.PERMANENT })} />);
    expect(container.querySelector('[class*="bg-orange-900"]')).toBeInTheDocument();
  });

  it('applies yellow background for TRANSIENT error type', () => {
    const { container } = render(<ErrorNotification error={makeError({ type: ErrorType.TRANSIENT })} />);
    expect(container.querySelector('[class*="bg-yellow-900"]')).toBeInTheDocument();
  });

  it('applies yellow background for AI_SERVICE error (not cached)', () => {
    const { container } = render(
      <ErrorNotification error={makeError({ type: ErrorType.AI_SERVICE })} isFromCache={false} />
    );
    expect(container.querySelector('[class*="bg-yellow-900"]')).toBeInTheDocument();
  });

  it('applies blue background for AI_SERVICE error when isFromCache=true', () => {
    const { container } = render(
      <ErrorNotification error={makeError({ type: ErrorType.AI_SERVICE })} isFromCache={true} />
    );
    expect(container.querySelector('[class*="bg-blue-900"]')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// RetryCountdown (internal component, tested via ErrorNotification)
// ---------------------------------------------------------------------------

describe('RetryCountdown', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it('displays the initial countdown in M:SS format', () => {
    jest.useFakeTimers();
    render(
      <ErrorNotification error={makeError()} retryAfter={65} onRetry={jest.fn()} />
    );
    expect(screen.getByText('Retry in 1:05')).toBeInTheDocument();
    jest.useRealTimers();
  });

  it('decrements the countdown every second', () => {
    jest.useFakeTimers();
    render(
      <ErrorNotification error={makeError()} retryAfter={5} onRetry={jest.fn()} />
    );

    expect(screen.getByText('Retry in 0:05')).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(1000); });
    expect(screen.getByText('Retry in 0:04')).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(2000); });
    expect(screen.getByText('Retry in 0:02')).toBeInTheDocument();
  });

  it('shows "Retry Now" button when countdown reaches zero', () => {
    jest.useFakeTimers();
    render(
      <ErrorNotification error={makeError()} retryAfter={2} onRetry={jest.fn()} />
    );

    act(() => { jest.advanceTimersByTime(2000); });
    expect(screen.getByText('Retry Now')).toBeInTheDocument();
  });

  it('calls onRetry when "Retry Now" button is clicked', () => {
    jest.useFakeTimers();
    const onRetry = jest.fn();
    render(
      <ErrorNotification error={makeError()} retryAfter={1} onRetry={onRetry} />
    );

    act(() => { jest.advanceTimersByTime(1000); });
    fireEvent.click(screen.getByText('Retry Now'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// showErrorNotification helper function
// ---------------------------------------------------------------------------

describe('showErrorNotification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // --- TRANSIENT ---
  it('calls toast.error with retry action for TRANSIENT + retryable + onRetry', () => {
    const onRetry = jest.fn();
    const error = makeError({ type: ErrorType.TRANSIENT, retryable: true });
    showErrorNotification(error, { onRetry });
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        action: expect.objectContaining({ label: 'Retry', onClick: onRetry }),
      })
    );
  });

  it('falls to else branch for TRANSIENT + retryable but no onRetry (uses correlationId description)', () => {
    const error = makeError({ type: ErrorType.TRANSIENT, retryable: true });
    showErrorNotification(error); // no onRetry
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        description: expect.stringContaining(error.correlationId),
      })
    );
  });

  it('falls to else branch for TRANSIENT + not retryable', () => {
    const error = makeError({ type: ErrorType.TRANSIENT, retryable: false });
    showErrorNotification(error, { onRetry: jest.fn() });
    // retryable=false so condition fails → else branch
    expect(mockToast.error).toHaveBeenCalled();
  });

  // --- PERMANENT ---
  it('calls toast.error with fieldErrors as description for PERMANENT errors', () => {
    const error = makeError({
      type: ErrorType.PERMANENT,
      fieldErrors: { title: 'Required', email: 'Invalid' },
    });
    showErrorNotification(error);
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        description: expect.stringContaining('title: Required'),
      })
    );
  });

  it('calls toast.error with details for PERMANENT error without fieldErrors', () => {
    const error = makeError({
      type: ErrorType.PERMANENT,
      details: 'This value already exists',
    });
    showErrorNotification(error);
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({ description: 'This value already exists' })
    );
  });

  it('calls toast.error with suggestedActions joined for PERMANENT without fieldErrors or details', () => {
    const error = makeError({
      type: ErrorType.PERMANENT,
      suggestedActions: ['Check your input', 'Try a different value'],
    });
    showErrorNotification(error);
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        description: 'Check your input\nTry a different value',
      })
    );
  });

  // --- AI_SERVICE + isFromCache ---
  it('calls toast.warning for AI_SERVICE when isFromCache=true', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE });
    showErrorNotification(error, { isFromCache: true });
    expect(mockToast.warning).toHaveBeenCalledWith(error.message, expect.any(Object));
  });

  it('includes "Generate Fresh" action for AI_SERVICE + isFromCache + onRetry', () => {
    const onRetry = jest.fn();
    const error = makeError({ type: ErrorType.AI_SERVICE });
    showErrorNotification(error, { isFromCache: true, onRetry });
    expect(mockToast.warning).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        action: expect.objectContaining({ label: 'Generate Fresh', onClick: onRetry }),
      })
    );
  });

  it('does not include action for AI_SERVICE + isFromCache when no onRetry', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE });
    showErrorNotification(error, { isFromCache: true });
    expect(mockToast.warning).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({ action: undefined })
    );
  });

  // --- AI_SERVICE + retryAfter ---
  it('calls toast.error with extended duration for AI_SERVICE + retryAfter', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE });
    showErrorNotification(error, { retryAfter: 30 });
    expect(mockToast.error).toHaveBeenCalled();
    const [, opts] = mockToast.error.mock.calls[0];
    // countdown duration should be at least retryAfter * 1000
    expect(opts.duration).toBeGreaterThanOrEqual(30000);
  });

  // --- AI_SERVICE generic ---
  it('calls toast.error with Retry action for AI_SERVICE + retryable + onRetry', () => {
    const onRetry = jest.fn();
    const error = makeError({ type: ErrorType.AI_SERVICE, retryable: true });
    showErrorNotification(error, { onRetry });
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        action: expect.objectContaining({ label: 'Retry', onClick: onRetry }),
      })
    );
  });

  it('calls toast.error without a truthy action for AI_SERVICE when not retryable', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE, retryable: false });
    showErrorNotification(error, { onRetry: jest.fn() });
    expect(mockToast.error).toHaveBeenCalled();
    const [, opts] = mockToast.error.mock.calls[0];
    // onRetry && error.retryable evaluates to false when retryable is false
    expect(opts.action).toBeFalsy();
  });

  // --- SYSTEM (else branch) ---
  it('calls toast.error with correlationId for SYSTEM errors', () => {
    const error = makeError({ type: ErrorType.SYSTEM, correlationId: 'sys-ref-999' });
    showErrorNotification(error);
    expect(mockToast.error).toHaveBeenCalledWith(
      error.message,
      expect.objectContaining({
        description: expect.stringContaining('sys-ref-999'),
      })
    );
  });

  // --- Duration override ---
  it('respects custom duration when provided', () => {
    const error = makeError({ type: ErrorType.TRANSIENT, retryable: true });
    showErrorNotification(error, { onRetry: jest.fn(), duration: 9999 });
    const [, opts] = mockToast.error.mock.calls[0];
    expect(opts.duration).toBe(9999);
  });

  // --- Default durations ---
  it('uses 5000ms default duration for TRANSIENT errors', () => {
    const error = makeError({ type: ErrorType.TRANSIENT, retryable: true });
    showErrorNotification(error, { onRetry: jest.fn() });
    const [, opts] = mockToast.error.mock.calls[0];
    expect(opts.duration).toBe(5000);
  });

  it('uses 15000ms default duration for AI_SERVICE (not from cache)', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE, retryable: false });
    showErrorNotification(error);
    const [, opts] = mockToast.error.mock.calls[0];
    expect(opts.duration).toBe(15000);
  });

  it('uses 10000ms default duration for AI_SERVICE + isFromCache', () => {
    const error = makeError({ type: ErrorType.AI_SERVICE });
    showErrorNotification(error, { isFromCache: true });
    const [, opts] = mockToast.warning.mock.calls[0];
    expect(opts.duration).toBe(10000);
  });

  it('uses 7000ms default duration for PERMANENT errors', () => {
    const error = makeError({ type: ErrorType.PERMANENT });
    showErrorNotification(error);
    const [, opts] = mockToast.error.mock.calls[0];
    expect(opts.duration).toBe(7000);
  });

  it('wires onDismiss callback into the toast options', () => {
    const onDismiss = jest.fn();
    const error = makeError({ type: ErrorType.PERMANENT });
    showErrorNotification(error, { onDismiss });
    const [, opts] = mockToast.error.mock.calls[0];
    expect(opts.onDismiss).toBe(onDismiss);
  });
});

// ---------------------------------------------------------------------------
// showRecoveryNotification helper function
// ---------------------------------------------------------------------------

describe('showRecoveryNotification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('calls toast.success without description when attempts === 1', () => {
    showRecoveryNotification('Operation completed', 1);
    expect(mockToast.success).toHaveBeenCalledWith(
      'Operation completed',
      expect.objectContaining({ duration: 2000 })
    );
    // No description field in the options (or undefined)
    const [, opts] = mockToast.success.mock.calls[0];
    expect(opts.description).toBeUndefined();
  });

  it('calls toast.success with description when attempts > 1', () => {
    showRecoveryNotification('Saved successfully', 3);
    expect(mockToast.success).toHaveBeenCalledWith(
      'Saved successfully',
      expect.objectContaining({
        description: expect.stringContaining('3'),
        duration: 3000,
      })
    );
  });

  it('uses plural "attempts" for attempts === 2', () => {
    showRecoveryNotification('Retry succeeded', 2);
    const [, opts] = mockToast.success.mock.calls[0];
    expect(opts.description).toBe('Succeeded after 2 attempts');
  });
});
