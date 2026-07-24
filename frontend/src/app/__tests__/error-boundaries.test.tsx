/**
 * Error-boundary Sentry wiring (#334). App Router error boundaries catch render
 * errors before they reach window.onerror, so they must capture explicitly.
 */
import { render, screen } from '@testing-library/react';
import * as Sentry from '@sentry/nextjs';
import ErrorPage from '../error';
import GlobalError from '../global-error';

jest.spyOn(console, 'error').mockImplementation(() => {});

beforeEach(() => {
  (Sentry.captureException as jest.Mock).mockClear();
});

describe('app/error.tsx', () => {
  it('captures the error to Sentry on mount', () => {
    const err = new Error('boom');
    render(<ErrorPage error={err} reset={jest.fn()} />);
    expect(Sentry.captureException).toHaveBeenCalledWith(err);
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});

describe('app/global-error.tsx', () => {
  it('captures the error to Sentry on mount', () => {
    const err = new Error('global boom');
    render(<GlobalError error={err} reset={jest.fn()} />);
    expect(Sentry.captureException).toHaveBeenCalledWith(err);
  });
});
